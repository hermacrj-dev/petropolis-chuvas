# Download do INMET e do Atlas Digital de Desastres
# Autor: Marcelo Pereira
# O Cemaden não tem download automático: os arquivos foram pedidos no PED
# (ped.cemaden.gov.br) e já estão em dados/entrada/cemaden.

import time
import zipfile

import requests

from src import config


def baixar_arquivo(url, destino, tentativas=3):
    """Baixa um arquivo. Tenta de novo se a conexão cair. Devolve (deu_certo, mensagem)."""
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.get(url, headers=config.HEADERS, stream=True, timeout=120)
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}"
            with open(destino, "wb") as arq:
                for pedaco in resp.iter_content(chunk_size=1024 * 1024):
                    arq.write(pedaco)
            return True, "ok"
        except requests.RequestException as erro:
            if tentativa == tentativas:
                return False, str(erro)
            time.sleep(3 * tentativa)  # espera um pouco antes de tentar de novo
    return False, "falha"


def arquivos_inmet():
    arquivos = []
    for p in config.ENTRADA_INMET.glob("*.[cC][sS][vV]"):
        if f"_{config.ESTACAO_INMET}_" in p.name.upper():
            arquivos.append(p)
    return sorted(arquivos)


def arquivos_atlas():
    return sorted(config.ENTRADA_ATLAS.glob("*.xlsx"))


def baixar_inmet():
    # O INMET disponibiliza um zip por ano com todas as estações do Brasil.
    # Baixo o zip, tiro só o CSV do Pico do Couto e apago o resto.
    ja_tenho = " ".join(p.name.upper() for p in arquivos_inmet())
    for ano in range(config.ANO_INICIO, config.ANO_FIM + 1):
        if f"-{ano}_A_" in ja_tenho:
            continue

        zip_temp = config.ENTRADA_INMET / f"_temp_{ano}.zip"
        ok, msg = baixar_arquivo(config.URL_INMET.format(ano=ano), zip_temp)
        if not ok:
            print(f"  INMET {ano}: não consegui baixar ({msg})")
            zip_temp.unlink(missing_ok=True)
            continue

        try:
            with zipfile.ZipFile(zip_temp) as z:
                for nome in z.namelist():
                    if f"_{config.ESTACAO_INMET}_" in nome.upper():
                        nome_arquivo = nome.split("/")[-1]
                        (config.ENTRADA_INMET / nome_arquivo).write_bytes(z.read(nome))
                        print(f"  INMET {ano}: ok")
                        break
        except zipfile.BadZipFile:
            print(f"  INMET {ano}: o zip veio corrompido")
        finally:
            zip_temp.unlink(missing_ok=True)


def baixar_atlas():
    if arquivos_atlas():
        return  # já baixado

    for url in config.URLS_ATLAS:
        destino = config.ENTRADA_ATLAS / url.split("/")[-1]
        ok, _ = baixar_arquivo(url, destino)
        # um .xlsx de verdade começa com "PK" (é um zip por dentro).
        # Quando o arquivo não existe o site devolve uma página de erro.
        if ok and destino.read_bytes()[:2] == b"PK":
            print(f"  Atlas: ok ({destino.name})")
            return
        destino.unlink(missing_ok=True)

    print("  Atlas: não consegui baixar. Baixe em https://atlasdigital.mdr.gov.br "
          "e salve em dados/entrada/atlas")


def executar():
    print("Download")
    baixar_inmet()
    baixar_atlas()
    n = len(list(config.ENTRADA_CEMADEN.rglob("*.csv")))
    print(f"  Cemaden: {n} arquivo(s) em dados/entrada/cemaden")
