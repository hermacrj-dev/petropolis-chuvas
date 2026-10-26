# Análises do projeto
# Autor: Marcelo Pereira
# Perguntas:
# 1. Onde chove mais forte em Petrópolis?
# 2. Em que meses a chuva forte se concentra em cada região?
# 3. A estação oficial do INMET (Pico do Couto) representa a chuva dos bairros?
# 4. Quanto chovia na área central nos dias de desastre? A partir de quantos mm
#    os desastres ficam mais frequentes?

import numpy as np
import pandas as pd

from src import chuva, config

DIAS_ANO = 365.25
UM_DIA = pd.Timedelta(days=1)


# ----- Qualidade dos dados -----

def disponibilidade(diaria):
    """% de dias válidos de cada estação em cada ano."""
    t = diaria.groupby(["estacao", "regiao", "fonte", "ano"])["valido"].mean() * 100
    return t.round(1).rename("pct_dias_validos").reset_index()


# ----- 1. Onde chove mais forte -----

def extremos_por_estacao(diaria, resumo):
    """
    Quantos dias de chuva forte cada estação teve.
    Como cada estação ficou parada em épocas diferentes, não dá para comparar a
    contagem direto. Por isso divido pelos dias válidos e transformo em
    "dias por ano de dado válido".
    """
    validos = diaria[diaria["valido"]]
    g = validos.groupby("codigo")

    t = pd.DataFrame({
        "dias_validos": g.size(),
        "dias_acima_50mm": g["chuva_dia_mm"].apply(lambda x: int((x > 50).sum())),
        "dias_acima_100mm": g["chuva_dia_mm"].apply(lambda x: int((x > 100).sum())),
        "maior_chuva_dia_mm": g["chuva_dia_mm"].max(),
    })

    linha_max = g["chuva_dia_mm"].idxmax()
    datas_max = diaria.loc[linha_max.values, ["codigo", "data"]].set_index("codigo")["data"]
    t["data_maior_chuva"] = datas_max.dt.strftime("%d/%m/%Y")

    t["anos_de_dados"] = (t["dias_validos"] / DIAS_ANO).round(1)
    t["dias_acima_50mm_por_ano"] = (t["dias_acima_50mm"] / t["dias_validos"] * DIAS_ANO).round(2)
    t["dias_acima_100mm_por_ano"] = (t["dias_acima_100mm"] / t["dias_validos"] * DIAS_ANO).round(2)

    cadastro = resumo.set_index("codigo")[["estacao", "regiao", "fonte", "latitude", "longitude"]]
    t = cadastro.join(t).reset_index()
    return t.sort_values("dias_acima_50mm_por_ano", ascending=False)


def extremos_por_regiao(ext):
    """Média das estações de cada região. O INMET entra como uma linha separada."""
    cemaden = ext[ext["fonte"] == "Cemaden"]
    t = cemaden.groupby("regiao").agg(
        estacoes=("codigo", "size"),
        dias_acima_50mm_por_ano=("dias_acima_50mm_por_ano", "mean"),
        dias_acima_100mm_por_ano=("dias_acima_100mm_por_ano", "mean"),
    ).round(2)

    inmet = ext[ext["fonte"] == "INMET"].set_index("regiao")
    inmet = inmet[["dias_acima_50mm_por_ano", "dias_acima_100mm_por_ano"]]
    inmet["estacoes"] = 1

    t = pd.concat([t, inmet]).sort_values("dias_acima_50mm_por_ano", ascending=False)
    return t.reset_index()


# ----- 2. Quando chove -----

def calendario(mensal):
    """
    Chuva média de cada mês do ano por região.
    Primeiro faço a média de cada estação (só com meses válidos) e depois a média
    das estações da região, para uma estação com mais anos não pesar mais.
    """
    v = mensal[mensal["valido"]]
    por_estacao = v.groupby(["regiao", "estacao", "mes"]).agg(
        chuva_mm=("chuva_mes_mm", "mean"),
        dias_acima_50mm=("dias_acima_50mm", "mean"),
        anos=("ano", "nunique"),
    ).reset_index()

    t = por_estacao.groupby(["regiao", "mes"]).agg(
        chuva_media_mm=("chuva_mm", "mean"),
        dias_acima_50mm=("dias_acima_50mm", "mean"),
        estacoes=("estacao", "nunique"),
    ).reset_index()
    return t.round(2)


# ----- 3. Estação oficial x bairros -----

def maximo_area_central(diaria, medida="chuva_dia_mm"):
    """Para cada dia, o maior valor entre as estações da área central que funcionaram."""
    central = diaria[(diaria["regiao"] == config.REGIAO_CENTRAL) & diaria["valido"]]
    central = central.dropna(subset=[medida])
    g = central.groupby("data")

    linha_max = g[medida].idxmax()
    qual_estacao = central.loc[linha_max.values, ["data", "estacao"]].set_index("data")["estacao"]

    return pd.DataFrame({
        "central_mm": g[medida].max(),
        "estacoes_centrais": g.size(),
        "estacao_do_maximo": qual_estacao,
    })


def serie_inmet(diaria, medida):
    inmet = diaria[(diaria["fonte"] == "INMET") & diaria["valido"]]
    return inmet.set_index("data")[medida]


def inmet_x_central(diaria):
    """Compara dia a dia o maior total da área central com o total do INMET."""
    central = maximo_area_central(diaria)
    inmet = serie_inmet(diaria, "chuva_dia_mm").rename("inmet_mm")
    dias = central.join(inmet, how="inner").reset_index()

    # dias de chuva forte na área central: o INMET também viu?
    fortes = dias[dias["central_mm"] > 50]
    tem_fortes = len(fortes) > 0
    inmet_viu = fortes["inmet_mm"] > 50

    resumo = pd.DataFrame([{
        "dias_comparados": len(dias),
        "dias_com_mais_de_50mm_na_area_central": len(fortes),
        "desses_com_mais_de_50mm_no_inmet": int(inmet_viu.sum()),
        "pct_captados_pelo_inmet": round(inmet_viu.mean() * 100, 1) if tem_fortes else np.nan,
        "mediana_inmet_nesses_dias_mm": round(fortes["inmet_mm"].median(), 1) if tem_fortes else np.nan,
        "mediana_central_nesses_dias_mm": round(fortes["central_mm"].median(), 1) if tem_fortes else np.nan,
    }])
    return dias, resumo


def evento_15fev2022(diaria, horaria, estacoes):
    """Tabela do dia 15/02/2022 por estação e a chuva hora a hora (para o gráfico)."""
    dia = pd.Timestamp(config.DATA_EVENTO_2022)
    colunas = ["estacao", "regiao", "fonte", "horas_com_registro", "valido", "chuva_dia_mm", "max_3h_mm"]
    t = diaria[diaria["data"] == dia][colunas].copy()
    t["defesa_civil_mm"] = t["estacao"].map(config.DEFESA_CIVIL_15FEV2022_MM)
    t = t.sort_values("chuva_dia_mm", ascending=False)

    # hora a hora, só das estações que funcionaram e marcaram chuva
    com_dado = t[t["valido"] & (t["chuva_dia_mm"] > 0)]["estacao"].tolist()
    codigos = estacoes.set_index("estacao").loc[com_dado, "codigo"]

    inicio = pd.Timestamp(f"{config.DATA_EVENTO_2022} 12:00", tz=config.FUSO_LOCAL).tz_convert("UTC")
    fim = pd.Timestamp(f"{config.DATA_EVENTO_2022} 23:00", tz=config.FUSO_LOCAL).tz_convert("UTC")

    lista = []
    for nome, codigo in codigos.items():
        s = chuva.serie_completa(horaria, codigo).loc[inicio:fim]
        lista.append(pd.DataFrame({
            "estacao": nome,
            "hora_local": s.index.tz_convert(config.FUSO_LOCAL).tz_localize(None),
            "chuva_mm": s.values,
            "acumulado_mm": s.fillna(0).cumsum().values,
        }))

    if len(lista) == 0:
        return t, pd.DataFrame()
    return t, pd.concat(lista, ignore_index=True)


# ----- 4. Chuva nos dias de desastre e limiares -----

def chuva_nos_desastres(diaria, eventos):
    """
    Para cada desastre, o maior acumulado de 24 e 72 horas na área central e no INMET.
    A data do registro pode estar um dia antes ou depois da chuva que causou o
    desastre, então pego o maior valor do dia anterior até o dia seguinte.
    """
    central24 = maximo_area_central(diaria, "max_24h_mm")
    central72 = maximo_area_central(diaria, "max_72h_mm")["central_mm"]
    inmet24 = serie_inmet(diaria, "max_24h_mm")
    inmet72 = serie_inmet(diaria, "max_72h_mm")

    linhas = []
    for _, ev in eventos.iterrows():
        d = ev["data_evento"]
        janela = slice(d - UM_DIA, d + UM_DIA)
        c24 = central24.loc[janela]
        tem_central = c24["central_mm"].notna().any()

        linhas.append({
            "data_evento": d,
            "tipo": ev["tipo"],
            "obitos": ev.get("obitos", 0),
            "desalojados": ev.get("desalojados", 0),
            "desabrigados": ev.get("desabrigados", 0),
            "central_24h_mm": c24["central_mm"].max() if not c24.empty else np.nan,
            "estacao_do_maximo": c24.loc[c24["central_mm"].idxmax(), "estacao_do_maximo"] if tem_central else None,
            "estacoes_centrais_com_dado": int(c24["estacoes_centrais"].max()) if not c24.empty else 0,
            "central_72h_mm": central72.loc[janela].max(),
            "inmet_24h_mm": inmet24.loc[janela].max(),
            "inmet_72h_mm": inmet72.loc[janela].max(),
        })

    t = pd.DataFrame(linhas)
    colunas_numero = t.select_dtypes("number").columns
    t[colunas_numero] = t[colunas_numero].round(1)
    return t


def episodios(serie, limiar):
    """
    Agrupa os dias acima do limiar em episódios. Dias seguidos de chuva forte
    contam como um episódio só (senão uma semana de chuva viraria 5 "alarmes").
    """
    dias = serie[serie >= limiar].index.sort_values()
    if len(dias) == 0:
        return []

    grupos = []
    atual = [dias[0]]
    for d in dias[1:]:
        if (d - atual[-1]).days <= 1:
            atual.append(d)
        else:
            grupos.append(atual)
            atual = [d]
    grupos.append(atual)
    return grupos


def limiares(diaria, eventos):
    """
    Testa cada limiar de chuva (no período que tem dado de desastre):
    - recall: dos desastres com dado de chuva, quantos tiveram chuva acima do limiar
      (de um dia antes até um dia depois);
    - precisão: dos episódios de chuva acima do limiar, quantos tiveram desastre.
    Não usei acurácia porque com tão poucos desastres ela fica perto de 100% sempre.
    """
    fim = pd.Timestamp(f"{config.ANO_FIM_DESASTRES}-12-31")
    datas_desastre = [d for d in eventos["data_evento"] if d <= fim]

    fontes = [("central", "Área central (Cemaden)"), ("inmet", "Pico do Couto (INMET)")]
    linhas = []
    for fonte, rotulo in fontes:
        for medida in ["max_24h_mm", "max_72h_mm"]:
            if fonte == "central":
                s = maximo_area_central(diaria, medida)["central_mm"]
            else:
                s = serie_inmet(diaria, medida)
            s = s[s.index <= fim].dropna()

            # só conta os desastres em que havia dado de chuva por perto
            desastres_com_dado = [d for d in datas_desastre if not s.loc[d - UM_DIA:d + UM_DIA].empty]

            for lim in config.LIMIARES_TESTADOS:
                captados = 0
                for d in desastres_com_dado:
                    if s.loc[d - UM_DIA:d + UM_DIA].max() >= lim:
                        captados += 1

                eps = episodios(s, lim)
                com_desastre = 0
                for ep in eps:
                    teve = any(abs((d - e).days) <= 1 for d in ep for e in datas_desastre)
                    if teve:
                        com_desastre += 1

                n = len(desastres_com_dado)
                linhas.append({
                    "fonte": rotulo,
                    "medida": medida.replace("max_", "").replace("_mm", ""),
                    "limiar_mm": lim,
                    "desastres_com_dado": n,
                    "desastres_captados": captados,
                    "episodios_acima": len(eps),
                    "episodios_com_desastre": com_desastre,
                    "recall": round(captados / n, 2) if n > 0 else np.nan,
                    "precisao": round(com_desastre / len(eps), 2) if len(eps) > 0 else np.nan,
                })
    return pd.DataFrame(linhas)


def indicadores(resumo, diaria, ext, eventos, info_atlas, comparacao):
    """Números principais, para o relatório e para conferir rápido no terminal."""
    n_cemaden = (resumo["fonte"] == "Cemaden").sum()
    eh_cemaden = ext["fonte"] == "Cemaden"
    eh_central = ext["regiao"] == config.REGIAO_CENTRAL

    central = ext[eh_central]["dias_acima_50mm_por_ano"].mean()
    outras = ext[eh_cemaden & ~eh_central]["dias_acima_50mm_por_ano"].mean()
    inmet = ext[ext["fonte"] == "INMET"]["dias_acima_50mm_por_ano"].mean()

    pct_cemaden = diaria[diaria["fonte"] == "Cemaden"]["valido"].mean() * 100
    pct_inmet = diaria[diaria["fonte"] == "INMET"]["valido"].mean() * 100

    linhas = [
        ("Período analisado", f"{config.ANO_INICIO} a {config.ANO_FIM}"),
        ("Pluviômetros do Cemaden", n_cemaden),
        ("Dias válidos na rede do Cemaden (%)", round(pct_cemaden, 1)),
        ("Dias válidos no INMET (%)", round(pct_inmet, 1)),
        ("Dias acima de 50 mm por ano, área central (média das estações)", round(central, 2)),
        ("Dias acima de 50 mm por ano, demais regiões (média das estações)", round(outras, 2)),
        ("Dias acima de 50 mm por ano, INMET Pico do Couto", round(inmet, 2)),
        ("Desastres em Petrópolis no período (Atlas)", len(eventos)),
        ("Último ano disponível no Atlas", info_atlas["ultimo_ano_na_base"]),
        ("Dias com mais de 50 mm na área central em que o INMET também passou de 50 mm (%)",
         comparacao.iloc[0]["pct_captados_pelo_inmet"]),
    ]
    return pd.DataFrame(linhas, columns=["indicador", "valor"])
