# Cálculos do painel
# Autor: Marcelo Pereira
# O painel tem filtro de anos e época do ano, então as contas são refeitas aqui
# a partir das bases tratadas, só com os dias do filtro escolhido.

import numpy as np
import pandas as pd

from src import config

EPOCAS = {
    "Ano inteiro": list(range(1, 13)),
    "Período chuvoso (nov a mar)": [11, 12, 1, 2, 3],
    "Período seco (abr a out)": [4, 5, 6, 7, 8, 9, 10],
}
# Estação com poucos dados no filtro fica marcada: menos de 25% dos dias do filtro com dado
# (no mínimo 60 dias e no máximo 1 ano de exigência, para funcionar com filtros curtos e longos)
MIN_PCT_ESTACAO = 0.25
MIN_COBERTURA_ANO = 0.25    # região-ano com menos de 25% dos dias com dado aparece como lacuna


def carregar():
    """Lê as bases tratadas que o executar.py gera."""
    D, T = config.TRATADOS, config.TABELAS
    diaria = pd.read_csv(D / "chuva_diaria.csv", parse_dates=["data"])
    mensal = pd.read_csv(D / "chuva_mensal.csv")
    estacoes = pd.read_csv(D / "estacoes.csv")
    desastres = pd.read_csv(D / "desastres.csv", parse_dates=["data_evento"])
    evento_2022 = pd.read_csv(T / "evento_15fev2022.csv")
    return diaria, mensal, estacoes, desastres, evento_2022


def filtrar(df, anos, meses, col_data=None):
    """Mantém só as linhas dos anos e meses escolhidos."""
    if col_data:
        ano, mes = df[col_data].dt.year, df[col_data].dt.month
    else:
        ano, mes = df["ano"], df["mes"]
    return df[ano.between(anos[0], anos[1]) & mes.isin(meses)]


def dias_no_filtro(anos, meses):
    """Quantos dias do calendário entram no filtro (para transformar contagens em 'por ano')."""
    dias = pd.date_range(f"{anos[0]}-01-01", f"{anos[1]}-12-31", freq="D")
    dias = dias[dias.month.isin(meses)]
    return len(dias), len(dias) / (anos[1] - anos[0] + 1)


def por_estacao(diaria_f, estacoes, anos, meses):
    """
    Resumo de cada pluviômetro do Cemaden no filtro.
    As contagens são divididas pelos dias com dado e multiplicadas pelos dias de um
    ano do filtro, para comparar estações que funcionaram em épocas diferentes.
    """
    total_dias, dias_por_ano = dias_no_filtro(anos, meses)
    cem = diaria_f[diaria_f["fonte"] == "Cemaden"]
    validos = cem[cem["valido"]]
    g = validos.groupby("codigo")

    t = pd.DataFrame({
        "dias_validos": g.size(),
        "dias_acima_50mm": g["chuva_dia_mm"].apply(lambda x: int((x > 50).sum())),
        "dias_acima_100mm": g["chuva_dia_mm"].apply(lambda x: int((x > 100).sum())),
        "chuva_media_dia": g["chuva_dia_mm"].mean(),
        "maior_24h_mm": g["max_24h_mm"].max(),
    })
    # data da maior chuva em 24 h de cada estação
    linha_max = validos.dropna(subset=["max_24h_mm"]).groupby("codigo")["max_24h_mm"].idxmax()
    t["data_maior_24h"] = validos.loc[linha_max.values].set_index("codigo")["data"].dt.strftime("%d/%m/%Y")

    t["dias_50_por_ano"] = t["dias_acima_50mm"] / t["dias_validos"] * dias_por_ano
    t["dias_100_por_ano"] = t["dias_acima_100mm"] / t["dias_validos"] * dias_por_ano
    t["chuva_por_ano_mm"] = t["chuva_media_dia"] * dias_por_ano
    t["cobertura_pct"] = t["dias_validos"] / total_dias * 100
    t["anos_de_dado"] = t["dias_validos"] / 365.25

    cadastro = estacoes[estacoes["fonte"] == "Cemaden"].set_index("codigo")
    t = cadastro[["estacao", "regiao", "latitude", "longitude"]].join(t)
    t["dias_validos"] = t["dias_validos"].fillna(0)
    t["cobertura_pct"] = t["cobertura_pct"].fillna(0)
    minimo = min(365, max(60, MIN_PCT_ESTACAO * total_dias))
    t["poucos_dados"] = t["dias_validos"] < minimo
    return t.reset_index()


def media_regioes(est):
    """Resumo de cada região: média das estações com dados suficientes no filtro."""
    ok = est[~est["poucos_dados"]]
    return ok.groupby("regiao").agg(
        estacoes=("codigo", "size"),
        dias_50_por_ano=("dias_50_por_ano", "mean"),
        dias_100_por_ano=("dias_100_por_ano", "mean"),
        chuva_por_ano_mm=("chuva_por_ano_mm", "mean"),
        maior_24h_mm=("maior_24h_mm", "max"),
        cobertura_pct=("cobertura_pct", "mean"),
    ).reset_index()


def serie_anual(diaria_f, meses):
    """
    Dias de chuva forte por ano em cada região, ano a ano.
    Quando a região teve menos de 25% dos dias com dado naquele ano, o valor
    fica vazio, para o gráfico mostrar a lacuna em vez de um número enganoso.
    """
    cem = diaria_f[diaria_f["fonte"] == "Cemaden"]
    n_estacoes = cem.groupby("regiao")["codigo"].nunique()
    linhas = []
    for (regiao, ano), g in cem.groupby(["regiao", "ano"]):
        dias_do_ano = pd.date_range(f"{ano}-01-01", f"{ano}-12-31")
        dias_ano = int(dias_do_ano.month.isin(meses).sum())
        validos = g[g["valido"]]
        cobertura = len(validos) / (n_estacoes[regiao] * dias_ano)
        taxa = (validos["chuva_dia_mm"] > 50).sum() / len(validos) * dias_ano if len(validos) else np.nan
        linhas.append({"regiao": regiao, "ano": ano, "cobertura_pct": cobertura * 100,
                       "dias_50_por_estacao": taxa if cobertura >= MIN_COBERTURA_ANO else np.nan})
    return pd.DataFrame(linhas)


def maior_chuva(diaria_f):
    """Maior acumulado de 24 h entre todos os pluviômetros no filtro."""
    cem = diaria_f[(diaria_f["fonte"] == "Cemaden") & diaria_f["valido"]].dropna(subset=["max_24h_mm"])
    if cem.empty:
        return None
    return cem.loc[cem["max_24h_mm"].idxmax()]


def validacao_central(diaria_f, dias_por_ano):
    """
    Confere se a chuva forte da área central é real ou erro de equipamento:
    1) quantos dias acima de 50 mm numa estação central tiveram outra estação
       central com pelo menos 25 mm no mesmo dia;
    2) chuva média por ano da área central e das demais regiões, só nos dias
       em que as duas tinham dado (para não comparar épocas diferentes).
    """
    cem = diaria_f[(diaria_f["fonte"] == "Cemaden") & diaria_f["valido"]]
    central = cem[cem["regiao"] == config.REGIAO_CENTRAL]
    tabela = central.pivot_table(index="data", columns="estacao", values="chuva_dia_mm")

    comparaveis, confirmados = 0, 0
    for _, r in central[central["chuva_dia_mm"] > 50].iterrows():
        outras = tabela.loc[r["data"]].drop(r["estacao"]).dropna()
        if len(outras) > 0:
            comparaveis += 1
            if (outras >= 25).any():
                confirmados += 1

    grupo = np.where(cem["regiao"] == config.REGIAO_CENTRAL, "central", "demais")
    media_dia = cem.groupby(["data", grupo])["chuva_dia_mm"].mean().unstack().dropna()
    return {
        "comparaveis": comparaveis,
        "confirmados": confirmados,
        "dias_em_comum": len(media_dia),
        "anual_central": media_dia["central"].mean() * dias_por_ano if len(media_dia) else np.nan,
        "anual_demais": media_dia["demais"].mean() * dias_por_ano if len(media_dia) else np.nan,
    }


def inmet_resumo(diaria_f):
    """Nos dias com mais de 50 mm na área central, em quantos o INMET também passou de 50 mm."""
    central = diaria_f[(diaria_f["regiao"] == config.REGIAO_CENTRAL) & diaria_f["valido"]]
    maximo = central.groupby("data")["chuva_dia_mm"].max()
    inmet = diaria_f[(diaria_f["fonte"] == "INMET") & diaria_f["valido"]].set_index("data")["chuva_dia_mm"]
    dias = pd.concat([maximo.rename("central"), inmet.rename("inmet")], axis=1, join="inner")
    fortes = dias[dias["central"] > 50]
    return {"dias_fortes": len(fortes), "inmet_tambem": int((fortes["inmet"] > 50).sum()),
            "mediana_inmet": fortes["inmet"].median(), "mediana_central": fortes["central"].median()}
