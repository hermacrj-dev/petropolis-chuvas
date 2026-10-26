# Como obter os dados

## Cemaden (manual)

1. Cadastro gratuito em https://ped.cemaden.gov.br
2. Obtenção de Dados > Dados Históricos.
3. UF: RJ. Município: Petrópolis. Tipo de estação: Pluviométrica.
4. Escolher a estação. Intervalo: 01/01/2013 a 31/12/2025. Formato: CSV.
5. Repetir para cada estação (o PED aceita uma por pedido).
6. Salvar o CSV na pasta da região correspondente em `dados/entrada/cemaden/`.

Se a mesma estação tiver mais de um arquivo, pode deixar todos: o código une os registros e
descarta os repetidos. Uma estação nova, que não esteja na lista abaixo, pode ser colocada em
qualquer pasta de região que faça sentido.

| Região | Estações |
|---|---|
| 1_area_central | Alto da Serra, Independência2, Morin, Mosela, Rua Amazonas/Quitandinha, Rua Araruama/Quitandinha |
| 2_correas_nogueira_araras | Araras, CIEP Brizolão137, Nogueira |
| 3_itaipava_e_vales | Estrada da Cachoeira, Estrada do Cantagalo, Itaipava, Vale do Cuiabá, Vale do Cuiabá2, Vila Constância, Vila Rica |
| 4_pedro_do_rio_e_posse | CIEP Brizolão 281, Pedro do Rio |

A estação Itaipava2 (330390622A) não veio nos arquivos (um dos pedidos voltou vazio) e ficou fora do estudo.

## INMET e Atlas (automático)

O `executar.py` baixa os dois. Se o Atlas falhar, baixar a planilha em
https://atlasdigital.mdr.gov.br e salvar em `dados/entrada/atlas/`.
