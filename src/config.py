# Configurações do projeto
# Projeto: Chuva nos bairros e desastres em Petrópolis
# Autor: Marcelo Pereira - Ciência de Dados e BI, UCP

from pathlib import Path

# Período do estudo
# A rede do Cemaden em Petrópolis começou a funcionar no segundo semestre de 2013,
# então comecei em 2014 para ter só anos completos.
ANO_INICIO = 2014
ANO_FIM = 2025
ANO_FIM_DESASTRES = 2022  # a planilha do Atlas que consegui baixar vai até 2022

COD_IBGE_PETROPOLIS = 3303906
FUSO_LOCAL = "America/Sao_Paulo"  # o INMET e o Cemaden mandam o horário em UTC

# Estação do INMET (Pico do Couto)
ESTACAO_INMET = "A610"
NOME_INMET = "Pico do Couto (INMET)"

# Separei as estações do Cemaden em 4 regiões, pela localização de cada uma.
# A chave é o nome da pasta em dados/entrada/cemaden.
REGIOES = {
    "1_area_central": "Área central (1º distrito)",
    "2_correas_nogueira_araras": "Corrêas, Nogueira e Araras",
    "3_itaipava_e_vales": "Itaipava e vales",
    "4_pedro_do_rio_e_posse": "Pedro do Rio e Posse",
}
REGIAO_CENTRAL = "Área central (1º distrito)"

# Regras de qualidade
MIN_HORAS_DIA = 20           # o dia só vale se tiver pelo menos 20 horas com registro
MIN_COBERTURA_JANELA = 0.80  # acumulado de 24h/72h só se 80% das horas tiverem dado
MIN_DIAS_MES = 0.80          # o mês só vale com 80% dos dias válidos

# "Zero falso": tinha estação marcando 0 mm em dia de temporal (equipamento parado).
# Se a estação marcou menos de 1 mm e a maioria da rede passou de 20 mm, descarto o dia.
ZERO_FALSO_MAX_ESTACAO_MM = 1
ZERO_FALSO_REDE_P75_MM = 20

# Limiares
# 50 e 100 mm em 24h são os cortes dos avisos de chuvas intensas do INMET
# (50 a 100 = perigo, acima de 100 = grande perigo).
LIMIARES_INMET = [50, 100]
LIMIARES_TESTADOS = [30, 50, 75, 100, 125, 150]
JANELAS_HORAS = [24, 72]

# 15/02/2022: usei os valores do relatório da Defesa Civil de Petrópolis
# ("Eventos chuvosos de 15 de fevereiro de 2022") para conferir os dados do Cemaden.
DATA_EVENTO_2022 = "2022-02-15"
DEFESA_CIVIL_15FEV2022_MM = {
    "Rua Araruama/Quitandinha": 133.1,
    "Rua Amazonas/Quitandinha": 111.0,
}

# Links para download (INMET e Atlas). O Cemaden é baixado na mão pelo PED.
URL_INMET = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip"
# tento da versão mais nova para a mais velha, a primeira que funcionar fica
URLS_ATLAS = [
    "https://atlasdigital.mdr.gov.br/arquivos/BD_Atlas_1991_2025.xlsx",
    "https://atlasdigital.mdr.gov.br/arquivos/BD_Atlas_1991_2024.xlsx",
    "https://atlasdigital.mdr.gov.br/arquivos/BD_Atlas_1991_2023.xlsx",
    "http://atlasdigital.mdr.gov.br/arquivos/BD_Atlas_1991_2022.xlsx",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (projeto academico UCP)"}

# Pastas
RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "entrada"
ENTRADA_INMET = ENTRADA / "inmet"
ENTRADA_ATLAS = ENTRADA / "atlas"
ENTRADA_CEMADEN = ENTRADA / "cemaden"
TRATADOS = RAIZ / "dados" / "tratados"
TABELAS = RAIZ / "resultados" / "tabelas"
FIGURAS = RAIZ / "resultados" / "figuras"

for pasta in [ENTRADA_INMET, ENTRADA_ATLAS, ENTRADA_CEMADEN, TRATADOS, TABELAS, FIGURAS]:
    pasta.mkdir(parents=True, exist_ok=True)
