# Leitura e tratamento da chuva (Cemaden e INMET)
# Autor: Marcelo Pereira
# Ideia geral: deixar as duas fontes no mesmo formato, uma linha por estação e
# por hora (em UTC). Hora sem registro fica vazia (NaN) e conta como falha.
# Depois calculo o total de cada dia (no horário de Brasília) e os acumulados.

import numpy as np
import pandas as pd

from src import config, download

# todas as horas do período, para conseguir ver onde faltou dado
INICIO_UTC = pd.Timestamp(f"{config.ANO_INICIO}-01-01", tz=config.FUSO_LOCAL).tz_convert("UTC")
FIM_UTC = pd.Timestamp(f"{config.ANO_FIM}-12-31 23:00", tz=config.FUSO_LOCAL).tz_convert("UTC")
HORAS = pd.date_range(INICIO_UTC, FIM_UTC, freq="h", name="data_hora_utc")

MEDIDAS = ["chuva_dia_mm", "max_3h_mm", "max_24h_mm", "max_72h_mm"]


# ----- Cemaden -----

def ler_cemaden():
    """
    Lê todos os CSVs de dados/entrada/cemaden (com as subpastas de região).

    Como o arquivo do PED funciona:
    - cada linha é uma medição, e o sensor 10 é a chuva em mm;
    - sem chuva a estação manda um registro por hora, com chuva manda a cada 10 min;
    - qualificacao = 2 é dado marcado como suspeito pelo próprio Cemaden (descarto).
    Algumas estações vieram em mais de um arquivo, então junto tudo e tiro as repetidas.
    """
    colunas = ["codestacao", "nome", "datahora", "id_sensor",
               "latitude", "longitude", "qualificacao", "valor"]
    lista = []
    for arq in sorted(config.ENTRADA_CEMADEN.rglob("*.csv")):
        df = pd.read_csv(arq, encoding_errors="replace", usecols=colunas)
        df = df[df["id_sensor"] == 10]
        df["regiao"] = config.REGIOES.get(arq.parent.name, "Outras")
        lista.append(df)

    if len(lista) == 0:
        raise FileNotFoundError("Nenhum CSV do Cemaden em dados/entrada/cemaden.")

    bruto = pd.concat(lista, ignore_index=True)
    qtd_suspeitos = int((bruto["qualificacao"] == 2).sum())
    bruto = bruto[bruto["qualificacao"] != 2]
    bruto = bruto.drop_duplicates(["codestacao", "datahora"])
    bruto["data_hora_utc"] = pd.to_datetime(bruto["datahora"]).dt.tz_localize("UTC")

    estacoes = bruto.groupby("codestacao").agg(
        estacao=("nome", "first"),
        regiao=("regiao", "first"),
        latitude=("latitude", "first"),
        longitude=("longitude", "first"),
    ).reset_index()
    estacoes = estacoes.rename(columns={"codestacao": "codigo"})
    estacoes["fonte"] = "Cemaden"

    # junto os registros de 10 em 10 minutos num total por hora
    bruto["hora"] = bruto["data_hora_utc"].dt.floor("h")
    horaria = bruto.groupby(["codestacao", "hora"])["valor"].sum().reset_index()
    horaria.columns = ["codigo", "data_hora_utc", "chuva_mm"]
    return horaria, estacoes, qtd_suspeitos


# ----- INMET -----

def ler_inmet():
    """
    Lê os CSVs anuais da estação A610.
    O arquivo tem 8 linhas de cabeçalho, separador ";" e vírgula como decimal.
    -9999 quer dizer sem medição. Em 2019 o INMET mudou o formato da data e da hora,
    por isso tem essa padronização antes de converter.
    """
    arquivos = download.arquivos_inmet()
    if len(arquivos) == 0:
        raise FileNotFoundError("Nenhum CSV do INMET em dados/entrada/inmet.")

    lista = []
    for arq in arquivos:
        df = pd.read_csv(arq, sep=";", skiprows=8, encoding="latin-1", dtype=str)

        # o nome das colunas muda um pouco entre os anos, então procuro pelo começo
        col_data = [c for c in df.columns if c.upper().startswith("DATA")][0]
        col_hora = [c for c in df.columns if c.upper().startswith("HORA")][0]
        col_chuva = [c for c in df.columns if "PRECIPITA" in c.upper()][0]

        data = df[col_data].str.strip().str.replace("/", "-", regex=False)   # 2019/01/01 -> 2019-01-01
        hora = df[col_hora].str.strip().str.replace(" UTC", "", regex=False)  # "0100 UTC" -> "0100"
        hora = hora.str.replace(":", "", regex=False).str.zfill(4)            # "01:00" -> "0100"
        chuva = pd.to_numeric(df[col_chuva].str.replace(",", ".", regex=False), errors="coerce")
        chuva = chuva.where(chuva >= 0)  # tira o -9999

        lista.append(pd.DataFrame({
            "data_hora_utc": pd.to_datetime(data + " " + hora, format="%Y-%m-%d %H%M",
                                            errors="coerce", utc=True),
            "chuva_mm": chuva,
        }))

    horaria = pd.concat(lista).dropna().drop_duplicates("data_hora_utc")
    horaria["codigo"] = config.ESTACAO_INMET

    lat, lon = coordenadas_inmet(arquivos[-1])
    estacao = pd.DataFrame([{
        "codigo": config.ESTACAO_INMET,
        "estacao": config.NOME_INMET,
        "regiao": "Estação oficial (INMET)",
        "latitude": lat,
        "longitude": lon,
        "fonte": "INMET",
    }])
    return horaria[["codigo", "data_hora_utc", "chuva_mm"]], estacao


def coordenadas_inmet(arquivo):
    info = {}
    with open(arquivo, encoding="latin-1") as f:
        for _ in range(8):
            chave, _, valor = f.readline().partition(";")
            info[chave.strip().upper()] = valor.strip()
    lat = float(info["LATITUDE:"].replace(",", "."))
    lon = float(info["LONGITUDE:"].replace(",", "."))
    return lat, lon


# ----- Séries diárias e mensais -----

def serie_completa(horaria, codigo):
    """Chuva de uma estação com todas as horas do período (hora sem dado = NaN)."""
    s = horaria[horaria["codigo"] == codigo].set_index("data_hora_utc")["chuva_mm"]
    s = s[~s.index.duplicated()]
    return s.reindex(HORAS)


def diaria_estacao(s):
    """Total do dia (horário de Brasília) e maiores acumulados de 3, 24 e 72 horas."""
    janelas = {"max_3h_mm": 3, "max_24h_mm": 24, "max_72h_mm": 72}

    # acumulado móvel: soma das últimas X horas, só se tiver 80% das horas com dado
    acumulados = pd.DataFrame(index=s.index)
    for nome, horas in janelas.items():
        minimo = int(np.ceil(horas * config.MIN_COBERTURA_JANELA))
        acumulados[nome] = s.rolling(horas, min_periods=minimo).sum()

    # converte para o horário de Brasília e fica só com o dia
    dia = s.index.tz_convert(config.FUSO_LOCAL).tz_localize(None).normalize()
    acumulados["data"] = dia

    tabela = pd.DataFrame({"data": dia, "chuva": s.values})
    diaria = tabela.groupby("data")["chuva"].agg(
        chuva_dia_mm=lambda x: x.sum(min_count=1),  # min_count=1 para dia sem nada ficar NaN e não 0
        horas_com_registro="count",
    )
    # para cada dia, o maior acumulado que terminou dentro dele
    diaria = diaria.join(acumulados.groupby("data")[list(janelas)].max())
    return diaria


def montar_diaria(horaria, estacoes):
    """Junta a chuva diária de todas as estações e marca quais dias valem."""
    lista = []
    for codigo in estacoes["codigo"]:
        d = diaria_estacao(serie_completa(horaria, codigo))
        d["codigo"] = codigo
        lista.append(d.reset_index())
    diaria = pd.concat(lista, ignore_index=True)
    diaria = diaria.merge(estacoes[["codigo", "estacao", "regiao", "fonte"]], on="codigo")

    diaria["valido"] = diaria["horas_com_registro"] >= config.MIN_HORAS_DIA

    # Zero falso (só no Cemaden). Uso o percentil 75 da rede no dia como referência
    # de "a maioria das estações".
    cemaden_ok = diaria[(diaria["fonte"] == "Cemaden") & diaria["valido"]]
    p75 = cemaden_ok.groupby("data")["chuva_dia_mm"].quantile(0.75).rename("p75_rede")
    diaria = diaria.merge(p75, on="data", how="left")

    diaria["zero_falso"] = (
        (diaria["fonte"] == "Cemaden")
        & diaria["valido"]
        & (diaria["chuva_dia_mm"] < config.ZERO_FALSO_MAX_ESTACAO_MM)
        & (diaria["p75_rede"] > config.ZERO_FALSO_REDE_P75_MM)
    )
    diaria["valido"] = diaria["valido"] & ~diaria["zero_falso"]

    # dia que não vale fica sem valor, para não entrar nas contas sem querer
    diaria.loc[~diaria["valido"], MEDIDAS] = np.nan
    diaria["ano"] = diaria["data"].dt.year
    diaria["mes"] = diaria["data"].dt.month
    diaria[MEDIDAS + ["p75_rede"]] = diaria[MEDIDAS + ["p75_rede"]].round(1)
    return diaria


def montar_mensal(diaria):
    """
    Total de cada mês por estação. O mês vale se tiver 80% dos dias válidos e se o
    total não ficar abaixo de 20% do que a rede marcou no mesmo mês. Essa segunda
    regra pega estação que ficou o mês todo marcando zero.
    """
    m = diaria.groupby(["codigo", "estacao", "regiao", "fonte", "ano", "mes"]).agg(
        chuva_mes_mm=("chuva_dia_mm", lambda x: x.sum(min_count=1)),
        dias_validos=("valido", "sum"),
        dias=("valido", "size"),
        dias_acima_50mm=("chuva_dia_mm", lambda x: int((x > 50).sum())),
    ).reset_index()
    m["pct_dias_validos"] = (m["dias_validos"] / m["dias"] * 100).round(1)
    m["valido"] = m["dias_validos"] / m["dias"] >= config.MIN_DIAS_MES

    cemaden_ok = m[(m["fonte"] == "Cemaden") & m["valido"]]
    p75 = cemaden_ok.groupby(["ano", "mes"])["chuva_mes_mm"].quantile(0.75).rename("p75_rede_mes")
    m = m.merge(p75, on=["ano", "mes"], how="left")

    baixo_demais = (
        (m["fonte"] == "Cemaden")
        & (m["p75_rede_mes"] > 50)
        & (m["chuva_mes_mm"] < 0.2 * m["p75_rede_mes"])
    )
    m.loc[baixo_demais, "valido"] = False
    m["total_baixo_demais"] = baixo_demais
    m["chuva_mes_mm"] = m["chuva_mes_mm"].round(1)
    return m.drop(columns=["p75_rede_mes"])


def resumo_estacoes(estacoes, diaria, horaria):
    """Primeiro e último registro e % de dias válidos de cada estação."""
    validos = diaria.groupby("codigo")["valido"].agg(dias_validos="sum", dias="size")
    com_dado = horaria.dropna(subset=["chuva_mm"])
    periodo = com_dado.groupby("codigo")["data_hora_utc"].agg(["min", "max"])

    r = estacoes.set_index("codigo").join(validos).join(periodo)
    r["primeiro_registro"] = r["min"].dt.tz_convert(config.FUSO_LOCAL).dt.strftime("%Y-%m-%d")
    r["ultimo_registro"] = r["max"].dt.tz_convert(config.FUSO_LOCAL).dt.strftime("%Y-%m-%d")
    r["pct_dias_validos"] = (r["dias_validos"] / r["dias"] * 100).round(1)
    return r.drop(columns=["min", "max", "dias"]).reset_index()


def carregar():
    """Lê as duas fontes e devolve as tabelas horária, diária, mensal e o resumo das estações."""
    hor_cemaden, est_cemaden, qtd_suspeitos = ler_cemaden()
    hor_inmet, est_inmet = ler_inmet()

    horaria = pd.concat([hor_cemaden, hor_inmet], ignore_index=True)
    estacoes = pd.concat([est_cemaden, est_inmet], ignore_index=True)

    diaria = montar_diaria(horaria, estacoes)
    mensal = montar_mensal(diaria)

    # se o mês foi reprovado por total baixo demais, os dias dele também não valem
    reprovados = mensal.loc[mensal["total_baixo_demais"], ["codigo", "ano", "mes"]]
    reprovados = reprovados.assign(reprovado=True)
    diaria = diaria.merge(reprovados, on=["codigo", "ano", "mes"], how="left")
    diaria["valido"] = diaria["valido"] & diaria["reprovado"].isna()
    diaria = diaria.drop(columns=["reprovado"])
    diaria.loc[~diaria["valido"], MEDIDAS] = np.nan

    resumo = resumo_estacoes(estacoes, diaria, horaria)
    return horaria, diaria, mensal, resumo, qtd_suspeitos
