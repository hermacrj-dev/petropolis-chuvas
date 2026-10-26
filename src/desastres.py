# Desastres em Petrópolis (Atlas Digital de Desastres no Brasil)
# Autor: Marcelo Pereira

import re

import pandas as pd

from src import config, download


def data_do_protocolo(protocolo):
    """
    O protocolo termina com a data do evento no formato AAAAMMDD,
    ex.: RJ-F-3303906-13214-20220215.
    Uso essa data porque a coluna "data" da planilha às vezes traz a data do
    reconhecimento e não a do desastre (o de 17/03/2013 aparece como 08/04/2013).
    """
    achou = re.search(r"(\d{8})\s*$", str(protocolo))
    if achou is None:
        return pd.NaT
    return pd.to_datetime(achou.group(1), format="%Y%m%d", errors="coerce")


def carregar():
    arquivos = download.arquivos_atlas()
    if len(arquivos) == 0:
        raise FileNotFoundError("Nenhuma planilha do Atlas em dados/entrada/atlas.")

    bruto = pd.read_excel(arquivos[-1], dtype=str)
    bruto.columns = [str(c).strip().lower() for c in bruto.columns]

    datas = bruto["protocolo"].map(data_do_protocolo)
    # alguns protocolos vêm com número errado (apareceu ano 1013), então filtro anos possíveis
    anos_ok = datas.dt.year.between(1991, config.ANO_FIM + 1)
    ultimo_ano = int(datas[anos_ok].dt.year.max())

    # O nome da coluna de tipologia muda entre versões da planilha, e algumas versões têm
    # uma coluna só com o código (ex.: 13) e outra com o nome (ex.: Chuvas Intensas).
    # Uso a primeira coluna de tipologia que tenha texto, e não só números.
    col_tipo = None
    for c in bruto.columns:
        if "tipolog" in c and "sub" not in c:
            valores = bruto[c].dropna().astype(str).str.strip()
            if not valores.str.isdigit().all():
                col_tipo = c
                break
    if col_tipo is None:
        raise ValueError("Não achei a coluna com o nome do tipo de desastre na planilha do Atlas.")

    codigo_ibge = pd.to_numeric(bruto["ibge"], errors="coerce")
    petro = bruto[codigo_ibge == config.COD_IBGE_PETROPOLIS].copy()
    petro["data_evento"] = datas[petro.index]
    petro["tipo"] = petro[col_tipo].str.strip()

    colunas_numero = []
    for c in ["obitos", "desabrigados", "desalojados", "desaparecidos"]:
        if c in petro.columns:
            petro[c] = pd.to_numeric(petro[c], errors="coerce").fillna(0).astype(int)
            colunas_numero.append(c)

    petro = petro[petro["data_evento"].dt.year.between(config.ANO_INICIO, config.ANO_FIM)]

    # Às vezes o mesmo evento tem dois registros (03/03/2018 aparece como enxurrada e
    # como chuvas intensas). Junto pela data e, para as vítimas, pego o maior valor
    # em vez de somar, senão contaria as mesmas pessoas duas vezes.
    regras = {"protocolo": "count", "tipo": lambda x: " + ".join(sorted(set(x)))}
    for c in colunas_numero:
        regras[c] = "max"
    eventos = petro.groupby("data_evento").agg(regras).reset_index()
    eventos = eventos.rename(columns={"protocolo": "registros"}).sort_values("data_evento")

    info = {
        "arquivo": arquivos[-1].name,
        "ultimo_ano_na_base": ultimo_ano,
        "registros_petropolis": int(len(petro)),
        "eventos_petropolis": int(len(eventos)),
    }
    return eventos, info
