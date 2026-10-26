# Dicionário de dados

Bases geradas por `executar.py` em `dados/tratados/`. Autor: Marcelo Pereira.

## estacoes.csv
Uma linha por estação (18 do Cemaden e 1 do INMET).

| Campo | Descrição |
|---|---|
| codigo | Código da estação (Cemaden: ex. 330390617A; INMET: A610) |
| estacao | Nome da estação |
| regiao | Região do município (ou "Estação oficial (INMET)") |
| latitude, longitude | Coordenadas da estação |
| fonte | Cemaden ou INMET |
| dias_validos | Dias do período com dado válido |
| primeiro_registro, ultimo_registro | Primeira e última data com registro |
| pct_dias_validos | Percentual de dias válidos no período |

## chuva_diaria.csv
Uma linha por estação e dia (horário de Brasília), de 01/01/2014 a 31/12/2025.

| Campo | Descrição |
|---|---|
| data | Dia |
| codigo, estacao, regiao, fonte | Identificação da estação |
| chuva_dia_mm | Chuva total do dia (vazio se o dia não for válido) |
| horas_com_registro | Horas do dia com algum registro |
| max_3h_mm | Maior chuva em 3 horas seguidas, encerradas no dia |
| max_24h_mm | Maior acumulado de 24 horas encerrado no dia |
| max_72h_mm | Maior acumulado de 72 horas encerrado no dia |
| zero_falso | Verdadeiro se a estação marcou menos de 1 mm num dia em que a maior parte da rede passou de 20 mm |
| valido | Dia usado nas análises (20 ou mais horas com registro, sem zero falso e fora de mês reprovado) |
| ano, mes | Ano e mês |

Acumulados só são calculados com ao menos 80% das horas da janela registradas.

## chuva_mensal.csv
Uma linha por estação e mês.

| Campo | Descrição |
|---|---|
| chuva_mes_mm | Soma da chuva dos dias válidos |
| dias_validos, dias | Dias válidos e dias do mês |
| dias_acima_50mm | Dias com mais de 50 mm |
| pct_dias_validos | Percentual de dias válidos |
| total_baixo_demais | Verdadeiro se o total ficou abaixo de 20% do registrado pela rede no mês (estação marcando zero) |
| valido | Mês usado nas médias (80% ou mais de dias válidos e total compatível com a rede) |

## desastres.csv
Uma linha por desastre em Petrópolis no período (Atlas Digital de Desastres).

| Campo | Descrição |
|---|---|
| data_evento | Data do desastre, lida no protocolo do registro |
| registros | Quantos registros do Atlas formam o evento |
| tipo | Tipologia (ex.: Chuvas Intensas, Enxurradas, Movimento de Massa) |
| obitos, desabrigados, desalojados, desaparecidos | Danos humanos do registro oficial (maior valor entre os registros do dia) |
