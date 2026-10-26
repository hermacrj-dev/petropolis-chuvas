# Chuva nos bairros e desastres em Petrópolis (2014 a 2025)

**Autor:** Marcelo Pereira
**Curso:** Ciência de Dados e Business Intelligence, Universidade Católica de Petrópolis
**Disciplina:** Projetos e Atividades de Extensão

Neste projeto eu juntei os 18 pluviômetros do Cemaden espalhados por Petrópolis e os
desastres registrados no Atlas Digital de Desastres para responder três perguntas:

1. Onde chove mais forte na cidade?
2. Em que meses a chuva forte se concentra?
3. Quanto chovia nos dias de desastre, e a partir de quantos milímetros o risco aumenta?

O resultado é um painel web em Streamlit, feito para qualquer pessoa consultar. Todas as
abas podem ser filtradas por anos e por época do ano (ano inteiro, período chuvoso ou seco).

> O painel é histórico. Não é previsão do tempo nem alerta de risco.
> Para receber alertas: SMS 40199 (envie seu CEP). Defesa Civil: 199.

## Principais achados

- Na área central (1º distrito), cada estação registra em média **8,2 dias por ano com
  mais de 50 mm**, cerca de 3,6 vezes as outras regiões (2,3). As estações com mais chuva
  forte são Independência2, Morin e Alto da Serra.
- Essa diferença é real e não erro de equipamento: 77% dos dias de chuva forte numa estação
  central aparecem também em outra estação central, e comparando só os dias em que todas as
  regiões tinham dado, a área central recebe cerca de 2.250 mm por ano contra 1.280 mm no
  restante do município. Isso combina com o relevo (borda da Serra do Mar).
- A maior chuva em 24 horas da série foi em 05/04/2025: 306 mm no Alto da Serra, confirmada
  pelo Morin (200 mm) e pela imprensa. Esse temporal não está no Atlas, que vai até 2022.
- Os totais de 15/02/2022 calculados aqui batem com o relatório da Defesa Civil
  (Rua Araruama: 134,1 mm contra 133,1 mm; Rua Amazonas: 111,2 mm contra 111,0 mm).
- Todos os desastres com dado na área central tiveram mais de 50 mm em 24 horas. Com o
  limiar de 100 mm, 5 de 6 desastres foram captados (recall 0,83), mas só 15% das chuvas
  acima disso tiveram desastre registrado (precisão 0,15). A chuva forte é necessária, mas
  sozinha não explica o desastre.
- A rede do Cemaden tem muitas falhas, principalmente entre 2019 e 2022 (só 43% dos dias
  com dado no total). Por isso as comparações são feitas por "dias por ano de dado válido",
  e os vãos aparecem marcados no painel.
- A estação oficial do INMET, no Pico do Couto, não representa a chuva dos bairros: nos dias
  de chuva forte na área central, ela também passou de 50 mm em só 17%. Ela entra no projeto
  apenas como comparação.

## Como rodar

Precisa do [uv](https://docs.astral.sh/uv/), que instala o Python e as bibliotecas. Dentro da pasta do projeto:

```
uv venv --python 3.11
uv pip install -r requirements.txt
```

Esses dois comandos criam o ambiente `.venv` (uma vez só). Depois:

```
uv run python executar.py
uv run streamlit run app.py
```

O `executar.py` baixa o INMET e o Atlas (se ainda não estiverem na pasta), trata os dados,
faz as análises e salva tabelas e gráficos. O `app.py` abre o painel no navegador, com as abas
Visão geral, Regiões, Quando chove, Chuva e desastres e Qualidade dos dados.

## Fontes

| Fonte | O que tem | Como consegui |
|---|---|---|
| Cemaden | Chuva a cada 10 minutos em 18 pluviômetros de Petrópolis | Pedido no PED (ped.cemaden.gov.br), um por estação. Passo a passo em `docs/como_obter_os_dados.md` |
| INMET, estação A610 | Chuva por hora no Pico do Couto | Download automático (portal.inmet.gov.br/dadoshistoricos) |
| Atlas Digital de Desastres | Desastres reconhecidos em cada município | Download automático (atlasdigital.mdr.gov.br) |

## Estrutura

```
executar.py               roda o projeto do início ao fim
app.py                    painel (Streamlit)
src/config.py             anos, limiares, regiões e pastas
src/download.py           download do INMET e do Atlas
src/chuva.py              leitura e limpeza do Cemaden e do INMET
src/desastres.py          leitura do Atlas
src/analise.py            análises
src/figuras.py            gráficos do relatório
src/painel.py             contas do painel que dependem do filtro de época
dados/entrada/cemaden/    um CSV por estação, separados em pastas por região
dados/entrada/inmet/      CSVs do INMET (o código baixa)
dados/entrada/atlas/      planilha do Atlas (o código baixa)
dados/tratados/           bases tratadas (geradas pelo código)
resultados/tabelas/       tabelas com os resultados
resultados/figuras/       gráficos
docs/                     dicionário de dados e como obter os dados
```

## Documentação

- `docs/dicionario_de_dados.md`: o que tem em cada base tratada e em cada coluna.
- `docs/como_obter_os_dados.md`: como baixar de novo os dados do Cemaden.

## Sobre o repositório

Os CSVs do Cemaden estão no repositório (cerca de 280 MB) porque não têm download
automático. As bases tratadas, as tabelas e as figuras também vão, porque o painel lê
delas. Os dados brutos do INMET e do Atlas ficam fora (`.gitignore`), porque o
`executar.py` baixa de novo.

## Citação dos dados

Dados da rede observacional do CEMADEN/MCTI. INMET, Banco de Dados Meteorológicos.
Ministério da Integração e do Desenvolvimento Regional, Atlas Digital de Desastres no Brasil.
