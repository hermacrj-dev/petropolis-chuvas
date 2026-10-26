# Painel: Chuva nos bairros e desastres em Petrópolis
# Autor: Marcelo Pereira
# Para abrir: streamlit run app.py (depois de rodar o executar.py).
# As contas que dependem do filtro de época ficam em src/painel.py.

import altair as alt
import pandas as pd
import streamlit as st

from src import analise, config, painel

CORES = {
    "Área central (1º distrito)": "#2a78d6",
    "Corrêas, Nogueira e Araras": "#1baf7a",
    "Itaipava e vales": "#eda100",
    "Pedro do Rio e Posse": "#e87ba4",
}
ESCALA_REGIAO = alt.Scale(domain=list(CORES), range=list(CORES.values()))
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
CINZA = "#8a8984"
CENTRAL = config.REGIAO_CENTRAL


def numero(valor, casas=1):
    # número no formato brasileiro (vírgula decimal)
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.set_page_config(page_title="Chuva e desastres em Petrópolis", layout="wide")


@st.cache_data
def carregar():
    return painel.carregar()


try:
    diaria, mensal, estacoes, desastres, evento_2022 = carregar()
except FileNotFoundError:
    st.error("As bases ainda não existem. Rode primeiro: python executar.py")
    st.stop()

# ----- Filtros (barra lateral) -----
st.sidebar.header("Filtros")
anos = st.sidebar.slider("Anos", config.ANO_INICIO, config.ANO_FIM, (config.ANO_INICIO, config.ANO_FIM))
epoca = st.sidebar.radio("Época do ano", list(painel.EPOCAS))
meses = painel.EPOCAS[epoca]

diaria_f = painel.filtrar(diaria, anos, meses)
mensal_f = painel.filtrar(mensal, anos, meses)
eventos_f = painel.filtrar(desastres, anos, meses, col_data="data_evento")
est = painel.por_estacao(diaria_f, estacoes, anos, meses)
regioes = painel.media_regioes(est)

cem_f = diaria_f[diaria_f["fonte"] == "Cemaden"]
cobertura_rede = cem_f["valido"].mean() * 100 if len(cem_f) else 0
st.sidebar.metric("Dias com dado na rede, neste filtro", f"{numero(cobertura_rede, 0)}%")
st.sidebar.caption("Os pluviômetros do Cemaden ficaram parados por longos períodos, principalmente entre "
                   "2019 e 2022. Por isso as comparações usam \"dias por ano de dado válido\" e os vãos "
                   "aparecem em cinza nos gráficos. Os desastres do Atlas vão até 2022.")

if est["poucos_dados"].all():
    st.warning("Nenhuma estação tem dados suficientes nesse filtro. Escolha um período maior.")
    st.stop()

# ----- Topo da página -----
st.title("Chuva nos bairros e desastres em Petrópolis")
st.caption(f"18 pluviômetros do Cemaden e desastres do Atlas Digital de Desastres no Brasil. "
           f"Filtro: {anos[0]} a {anos[1]}, {epoca.lower()}.")
st.warning("**Este painel mostra o histórico. Não é previsão do tempo nem alerta de risco.** "
           "Para receber alertas, envie seu CEP por SMS para **40199**. Em emergência, ligue **199** "
           "(Defesa Civil) ou **193** (Bombeiros).", icon="⚠️")

abas = st.tabs(["Visão geral", "Regiões", "Quando chove", "Chuva e desastres", "Qualidade dos dados"])

# ----- Aba 1: visão geral -----
with abas[0]:
    taxa_central = regioes.loc[regioes["regiao"] == CENTRAL, "dias_50_por_ano"]
    taxa_central = float(taxa_central.iloc[0]) if len(taxa_central) else float("nan")
    taxa_demais = est[~est["poucos_dados"] & (est["regiao"] != CENTRAL)]["dias_50_por_ano"].mean()
    maior = painel.maior_chuva(diaria_f)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dias por ano com mais de 50 mm na área central", numero(taxa_central))
    c1.caption(f"{numero(taxa_central / taxa_demais)} vezes as demais regiões ({numero(taxa_demais)})"
               if taxa_demais > 0 else "Sem dias acima de 50 mm nas demais regiões")
    if maior is not None:
        c2.metric("Maior chuva em 24 horas", f"{numero(maior['max_24h_mm'], 0)} mm")
        c2.caption(f"{maior['estacao']}, {maior['data']:%d/%m/%Y}"
                   + (" (temporal de abril de 2025, depois do fim do Atlas)" if maior["data"].year == 2025 and maior["data"].month == 4 else ""))
    c3.metric("Desastres registrados", len(eventos_f))
    c3.caption(f"{int(eventos_f['obitos'].sum())} óbitos no registro oficial" if len(eventos_f)
               else "Nenhum no filtro (o Atlas vai até 2022)")
    c4.metric("Dias com dado na rede", f"{numero(cobertura_rede, 0)}%")
    c4.caption("O resto são dias com estação parada ou com defeito")

    st.subheader("Chuva forte ano a ano, por região")
    serie = painel.serie_anual(diaria_f, meses)
    # cada trecho sem lacuna vira uma linha separada, assim o gráfico mostra o vão
    serie = serie.sort_values(["regiao", "ano"])
    serie["trecho"] = serie.groupby("regiao")["dias_50_por_estacao"].transform(lambda s: s.isna().cumsum())
    linhas = alt.Chart(serie.dropna(subset=["dias_50_por_estacao"])).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("dias_50_por_estacao:Q", title="dias com mais de 50 mm (por estação)"),
        color=alt.Color("regiao:N", scale=ESCALA_REGIAO, title=None, legend=alt.Legend(orient="bottom")),
        detail="trecho:N",
        tooltip=[alt.Tooltip("regiao:N", title="Região"), alt.Tooltip("ano:O", title="Ano"),
                 alt.Tooltip("dias_50_por_estacao:Q", title="Dias > 50 mm", format=".1f"),
                 alt.Tooltip("cobertura_pct:Q", title="% de dias com dado", format=".0f")],
    )
    lacunas = alt.Chart(serie[serie["dias_50_por_estacao"].isna()]).mark_point(
        shape="cross", size=70, color=CINZA, filled=True).encode(
        x="ano:O", y=alt.datum(0),
        tooltip=[alt.Tooltip("regiao:N", title="Região"), alt.Tooltip("ano:O", title="Ano"),
                 alt.Tooltip("cobertura_pct:Q", title="% de dias com dado", format=".0f")],
    )
    st.altair_chart((linhas + lacunas).properties(height=320), width="stretch")
    st.caption("Cruz cinza no zero = região com menos de 25% dos dias com dado naquele ano (vão nos dados, "
               "não ausência de chuva). A linha é interrompida nesses anos.")

    st.subheader("Pluviômetros com mais chuva forte")
    barras = est.copy()
    barras["situacao"] = barras["poucos_dados"].map({True: "poucos dados neste filtro", False: "ok"})
    st.altair_chart(
        alt.Chart(barras).mark_bar(cornerRadiusEnd=4).encode(
            y=alt.Y("estacao:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220, labelOverlap=False)),
            x=alt.X("dias_50_por_ano:Q", title="dias por ano com mais de 50 mm"),
            color=alt.Color("regiao:N", scale=ESCALA_REGIAO, legend=None),
            opacity=alt.condition(alt.datum.poucos_dados, alt.value(0.3), alt.value(1)),
            tooltip=[alt.Tooltip("estacao:N", title="Estação"), alt.Tooltip("regiao:N", title="Região"),
                     alt.Tooltip("dias_50_por_ano:Q", title="Dias > 50 mm por ano", format=".1f"),
                     alt.Tooltip("maior_24h_mm:Q", title="Maior chuva em 24 h (mm)", format=".0f"),
                     alt.Tooltip("data_maior_24h:N", title="Data"),
                     alt.Tooltip("anos_de_dado:Q", title="Anos de dado", format=".1f"),
                     alt.Tooltip("situacao:N", title="Situação")],
        ).properties(height=alt.Step(22)), width="stretch")
    st.caption("Barras claras = estações com poucos dados neste filtro (menos de 25% dos dias), pouco confiáveis. "
               "As cores seguem as regiões.")

# ----- Aba 2: regiões -----
with abas[1]:
    opcoes = {
        "Dias por ano com mais de 50 mm": ("dias_50_por_ano", ".1f", "média das estações"),
        "Chuva por ano (mm)": ("chuva_por_ano_mm", ".0f", "média das estações"),
        "Maior chuva em 24 horas (mm)": ("maior_24h_mm", ".0f", "maior valor da região"),
    }
    escolha = st.selectbox("Comparar as regiões por", list(opcoes))
    coluna, formato, como = opcoes[escolha]

    st.subheader("Cada região e suas estações")
    pontos_est = est.dropna(subset=[coluna]).copy()
    pontos_est["situacao"] = pontos_est["poucos_dados"].map({True: "poucos dados neste filtro", False: "ok"})
    eixo_y = alt.Y("regiao:N", sort=list(CORES), title=None, axis=alt.Axis(labelLimit=260))
    barras = alt.Chart(regioes).mark_bar(opacity=0.25, height=34).encode(
        y=eixo_y, x=alt.X(f"{coluna}:Q", title=escolha),
        color=alt.Color("regiao:N", scale=ESCALA_REGIAO, legend=None),
        tooltip=[alt.Tooltip("regiao:N", title="Região"),
                 alt.Tooltip(f"{coluna}:Q", title=f"Região ({como})", format=formato)])
    rotulos = regioes.assign(texto=regioes[coluna].map(lambda v: numero(v, int(formato[1]))))
    valor_regiao = alt.Chart(rotulos).mark_text(align="left", dx=6, dy=-24, fontSize=13, fontWeight="bold").encode(
        y=eixo_y, x=f"{coluna}:Q", text="texto:N",
        color=alt.Color("regiao:N", scale=ESCALA_REGIAO, legend=None))
    pontos = alt.Chart(pontos_est).mark_circle(size=110, stroke="white", strokeWidth=1).encode(
        y=eixo_y, x=f"{coluna}:Q",
        color=alt.Color("regiao:N", scale=ESCALA_REGIAO, legend=None),
        opacity=alt.condition(alt.datum.poucos_dados, alt.value(0.3), alt.value(1)),
        tooltip=[alt.Tooltip("estacao:N", title="Estação"),
                 alt.Tooltip(f"{coluna}:Q", title=escolha, format=formato),
                 alt.Tooltip("cobertura_pct:Q", title="% dos dias com dado", format=".0f"),
                 alt.Tooltip("situacao:N", title="Situação")],
    )
    st.altair_chart((barras + pontos + valor_regiao).properties(height=alt.Step(70)), width="stretch")
    st.caption(f"Barra clara = {como}; cada bolinha é um pluviômetro da região (passe o mouse para ver o nome). "
               "Bolinhas apagadas = estações com poucos dados neste filtro, que ficam fora da média.")

    st.subheader("Resumo por região")
    tabela_reg = regioes.copy()
    tabela_reg["o"] = tabela_reg["regiao"].map({r: i for i, r in enumerate(CORES)})
    tabela_reg = tabela_reg.sort_values("o")
    tabela_reg = pd.DataFrame({
        "Região": tabela_reg["regiao"],
        "Estações": tabela_reg["estacoes"],
        "Dias > 50 mm por ano": tabela_reg["dias_50_por_ano"].map(numero),
        "Dias > 100 mm por ano": tabela_reg["dias_100_por_ano"].map(lambda v: numero(v, 2)),
        "Chuva por ano (mm)": tabela_reg["chuva_por_ano_mm"].map(lambda v: numero(v, 0)),
        "Maior chuva em 24 h (mm)": tabela_reg["maior_24h_mm"].map(lambda v: numero(v, 0)),
        "% dos dias com dado": tabela_reg["cobertura_pct"].map(lambda v: numero(v, 0)),
    })
    st.dataframe(tabela_reg, hide_index=True, width="stretch")
    st.caption("Médias das estações com dados suficientes no filtro. A maior chuva em 24 horas é o maior "
               "valor entre as estações da região.")

# ----- Aba 3: quando chove -----
with abas[2]:
    st.subheader("Chuva de cada mês, por região")
    medida = st.radio("Mostrar", ["Chuva média do mês (mm)", "Dias com mais de 50 mm no mês"], horizontal=True)
    campo = "chuva_media_mm" if medida.startswith("Chuva") else "dias_acima_50mm"
    cal = analise.calendario(mensal_f[mensal_f["fonte"] == "Cemaden"])
    cal["mes_nome"] = cal["mes"].map(lambda x: MESES[x - 1])
    base = alt.Chart(cal).encode(
        x=alt.X("mes_nome:N", sort=MESES, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("regiao:N", sort=list(CORES), title=None, axis=alt.Axis(labelLimit=260)))
    calor_mes = base.mark_rect(stroke="white", strokeWidth=2).encode(
        color=alt.Color(f"{campo}:Q", scale=alt.Scale(scheme="blues"), title=None),
        tooltip=[alt.Tooltip("regiao:N", title="Região"), alt.Tooltip("mes_nome:N", title="Mês"),
                 alt.Tooltip(f"{campo}:Q", title=medida, format=".1f"),
                 alt.Tooltip("estacoes:Q", title="Estações usadas")])
    texto = base.mark_text(fontSize=11).encode(
        text=alt.Text(f"{campo}:Q", format=".0f" if campo == "chuva_media_mm" else ".1f"),
        color=alt.condition(f"datum.{campo} > {cal[campo].max() * 0.55}", alt.value("white"), alt.value("#0b0b0b")))
    st.altair_chart((calor_mes + texto).properties(height=250), width="stretch")
    st.caption("Média dos meses com dado de cada estação, depois média das estações da região.")

    st.subheader("Mês a mês, ano a ano")
    regiao_escolhida = st.selectbox("Região", list(CORES))
    r = mensal_f[(mensal_f["regiao"] == regiao_escolhida) & mensal_f["valido"]]
    r = r.groupby(["ano", "mes"]).agg(chuva_mm=("chuva_mes_mm", "mean"), estacoes=("codigo", "nunique")).reset_index()
    grade = pd.MultiIndex.from_product([range(anos[0], anos[1] + 1), meses], names=["ano", "mes"]).to_frame(index=False)
    grade = grade.merge(r, on=["ano", "mes"], how="left")
    grade["mes_nome"] = grade["mes"].map(lambda x: MESES[x - 1])
    grade["situacao"] = grade["chuva_mm"].isna().map({True: "sem dados", False: "com dados"})
    base = alt.Chart(grade).encode(
        x=alt.X("mes_nome:N", sort=MESES, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("ano:O", title=None),
        tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("mes_nome:N", title="Mês"),
                 alt.Tooltip("chuva_mm:Q", title="Chuva no mês (mm)", format=".0f"),
                 alt.Tooltip("estacoes:Q", title="Estações com dado"),
                 alt.Tooltip("situacao:N", title="Situação")])
    vazio = base.transform_filter("datum.chuva_mm == null").mark_rect(
        stroke="white", strokeWidth=2, color="#3a3a3a")
    cheio = base.transform_filter("datum.chuva_mm != null").mark_rect(stroke="white", strokeWidth=2).encode(
        color=alt.Color("chuva_mm:Q", scale=alt.Scale(scheme="blues"), title="mm"))
    st.altair_chart((vazio + cheio).properties(height=alt.Step(24)), width="stretch")
    st.caption("Quadrados cinza escuro = nenhuma estação da região com o mês completo (vão nos dados). "
               "Novembro a março concentram a chuva em todas as regiões.")

# ----- Aba 4: chuva e desastres -----
with abas[3]:
    st.subheader("Quanto choveu na área central nos dias de desastre")
    if eventos_f.empty:
        st.info("Nenhum desastre registrado no Atlas dentro desse filtro. O Atlas disponível vai até 2022.")
    else:
        tab = analise.chuva_nos_desastres(diaria_f, eventos_f)
        tab["dia"] = tab["data_evento"].dt.strftime("%d/%m/%Y")
        tab["rotulo"] = [f"{v:.0f} mm, {e}" if pd.notna(v) else "sem estação da área central funcionando"
                         for v, e in zip(tab["central_24h_mm"], tab["estacao_do_maximo"])]
        tab["x_rotulo"] = tab[["central_24h_mm", "central_72h_mm"]].max(axis=1).fillna(0)
        ordem = tab["dia"].tolist()
        dica = [alt.Tooltip("dia:N", title="Data"), alt.Tooltip("tipo:N", title="Tipo"),
                alt.Tooltip("central_24h_mm:Q", title="Chuva em 24 h (mm)", format=".0f"),
                alt.Tooltip("central_72h_mm:Q", title="Chuva em 72 h (mm)", format=".0f"),
                alt.Tooltip("obitos:Q", title="Óbitos"), alt.Tooltip("desalojados:Q", title="Desalojados")]
        eixo_y = alt.Y("dia:N", sort=ordem, title=None)
        b72 = alt.Chart(tab).mark_bar(color="#9cc3f0", height=22).encode(
            y=eixo_y, x=alt.X("central_72h_mm:Q", title="chuva acumulada (mm)", scale=alt.Scale(domainMin=0)),
            tooltip=dica)
        b24 = alt.Chart(tab).mark_bar(color="#2a78d6", height=22).encode(y=eixo_y, x="central_24h_mm:Q", tooltip=dica)
        rot = alt.Chart(tab).mark_text(align="left", dx=6, fontSize=12, color="#d9d9d6").encode(
            y=eixo_y, x="x_rotulo:Q", text="rotulo:N")
        regras = alt.Chart(pd.DataFrame({"x": config.LIMIARES_INMET, "t": ["50 mm", "100 mm"]}))
        linhas_lim = regras.mark_rule(strokeDash=[4, 4], color=CINZA).encode(x="x:Q")
        nomes_lim = regras.mark_text(align="left", dx=3, dy=-6, color=CINZA, fontSize=11).encode(
            x="x:Q", y=alt.value(0), text="t:N")
        grafico = (b72 + b24 + linhas_lim + nomes_lim + rot).properties(height=alt.Step(44))
        st.altair_chart(grafico, width="stretch")
        st.caption("Barra escura = maior chuva em 24 horas; barra clara = em 72 horas. Considera o maior valor "
                   "entre as estações da área central, do dia anterior ao seguinte ao desastre. "
                   "Linhas tracejadas: 50 e 100 mm, os cortes dos avisos de chuvas intensas.")

        tabela = tab[["dia", "tipo", "obitos", "desabrigados", "desalojados", "central_24h_mm",
                      "central_72h_mm", "estacao_do_maximo"]].rename(columns={
            "dia": "Data", "tipo": "Tipo", "obitos": "Óbitos", "desabrigados": "Desabrigados",
            "desalojados": "Desalojados", "central_24h_mm": "Chuva 24 h (mm)",
            "central_72h_mm": "Chuva 72 h (mm)", "estacao_do_maximo": "Estação com mais chuva"})
        for col in ["Chuva 24 h (mm)", "Chuva 72 h (mm)"]:
            tabela[col] = tabela[col].map(lambda v: "sem dado" if pd.isna(v) else f"{v:.0f}")
        tabela["Estação com mais chuva"] = tabela["Estação com mais chuva"].fillna("nenhuma funcionando")
        st.dataframe(tabela, hide_index=True, width="stretch")

        st.subheader("A partir de quanto chover o risco aumenta?")
        lim = analise.limiares(diaria_f, eventos_f)
        lim = lim[lim["fonte"] == "Área central (Cemaden)"]
        c1, c2 = st.columns(2)
        janela = c1.radio("Acumulado", ["24h", "72h"], horizontal=True,
                          format_func=lambda x: "24 horas" if x == "24h" else "72 horas (3 dias)")
        limiar = c2.select_slider("Limiar (mm)", options=config.LIMIARES_TESTADOS, value=100)
        lj = lim[lim["medida"] == janela]
        linha = lj[lj["limiar_mm"] == limiar].iloc[0]

        k1, k2, k3 = st.columns(3)
        k1.metric("Desastres em que a chuva passou do limiar",
                  f"{int(linha['desastres_captados'])} de {int(linha['desastres_com_dado'])}")
        k2.metric("Vezes que choveu acima do limiar", int(linha["episodios_acima"]))
        k3.metric("Dessas vezes, quantas tiveram desastre",
                  f"{int(linha['episodios_com_desastre'])} ({linha['precisao']:.0%})"
                  if linha["episodios_acima"] else "nenhuma")

        curvas = lj.melt(id_vars="limiar_mm", value_vars=["recall", "precisao"], var_name="indicador", value_name="valor")
        curvas["indicador"] = curvas["indicador"].map({"recall": "Desastres captados (recall)",
                                                       "precisao": "Chuvas fortes que viraram desastre (precisão)"})
        graf = alt.Chart(curvas).mark_line(point=True, strokeWidth=2).encode(
            x=alt.X("limiar_mm:Q", title="limiar (mm)"),
            y=alt.Y("valor:Q", title=None, axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("indicador:N", title=None, legend=alt.Legend(orient="bottom", labelLimit=400),
                            scale=alt.Scale(range=["#2a78d6", "#eda100"])),
            tooltip=[alt.Tooltip("limiar_mm:Q", title="Limiar (mm)"), alt.Tooltip("indicador:N", title=""),
                     alt.Tooltip("valor:Q", title="Valor", format=".0%")])
        marca = alt.Chart(pd.DataFrame({"x": [limiar]})).mark_rule(color=CINZA, strokeDash=[4, 4]).encode(x="x:Q")
        st.altair_chart((graf + marca).properties(height=260), width="stretch")
        st.write("Quase todos os desastres aconteceram com chuva acima de 50 mm na área central, mas a maior "
                 "parte das chuvas fortes passa sem desastre registrado. Subindo o limiar, os alarmes falsos "
                 "caem, mas desastres começam a escapar. A chuva é o gatilho; o dano depende também de onde "
                 "ela cai e da ocupação das encostas.")

# ----- Aba 5: qualidade dos dados -----
with abas[4]:
    st.subheader("Quanto cada pluviômetro funcionou")
    disp = cem_f.groupby(["regiao", "estacao", "ano"])["valido"].mean().mul(100).reset_index(name="pct")
    ordem_est = (est.assign(o=est["regiao"].map({r: i for i, r in enumerate(CORES)}))
                 .sort_values(["o", "estacao"])["estacao"].tolist())
    base = alt.Chart(disp).encode(
        x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("estacao:N", sort=ordem_est, title=None, axis=alt.Axis(labelLimit=220)))
    quadros = base.mark_rect(stroke="white", strokeWidth=1.5).encode(
        color=alt.Color("pct:Q", title="% dias com dado", scale=alt.Scale(scheme="blues", domain=[0, 100])),
        tooltip=[alt.Tooltip("estacao:N", title="Estação"), alt.Tooltip("regiao:N", title="Região"),
                 alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("pct:Q", title="% dias com dado", format=".0f")])
    numeros = base.mark_text(fontSize=9).encode(
        text=alt.Text("pct:Q", format=".0f"),
        color=alt.condition("datum.pct > 55", alt.value("white"), alt.value("#0b0b0b")))
    st.altair_chart((quadros + numeros).properties(height=alt.Step(22)), width="stretch")
    st.caption("Células claras = estação parada, com falha ou marcando zero em dia de chuva (\"zero falso\"). "
               "Os vãos foram tratados assim: o dia só vale com 20 das 24 horas registradas, e as "
               "comparações entre estações usam dias por ano de dado válido.")

    st.subheader("A chuva forte da área central é real?")
    val = painel.validacao_central(diaria_f, painel.dias_no_filtro(anos, meses)[1])
    c1, c2, c3 = st.columns(3)
    if val["comparaveis"]:
        c1.metric("Dias de chuva forte confirmados por outra estação central",
                  f"{numero(val['confirmados'] / val['comparaveis'] * 100, 0)}%")
        c1.caption(f"{val['confirmados']} de {val['comparaveis']} dias com outra estação central "
                   f"marcando 25 mm ou mais")
    if val["dias_em_comum"]:
        c2.metric("Chuva por ano na época escolhida, área central", f"{numero(val['anual_central'], 0)} mm")
        c3.metric("Chuva por ano na época escolhida, demais regiões", f"{numero(val['anual_demais'], 0)} mm")
        c2.caption(f"Só nos {val['dias_em_comum']} dias em que as duas tinham dado")
    st.write("Sim. A maior parte dos dias de chuva forte aparece em mais de uma estação da área central ao mesmo "
             "tempo, e a diferença para o resto do município se mantém quando se comparam só os mesmos dias. "
             "Ela combina com o relevo: a área central fica na borda da Serra do Mar, onde o ar úmido que vem "
             "do litoral sobe e chove mais. Estudos sobre Petrópolis também registram essa diferença dentro do "
             "município ([Nascimento et al., 2021](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1139959/1/"
             "Chuvas-de-alta-intensidade-e-volume-no-municipio-de-Petropolis-RJ-2021.pdf)).")
    st.markdown("**Conferência com a Defesa Civil (15/02/2022)**")
    conf = evento_2022.dropna(subset=["defesa_civil_mm"])[["estacao", "chuva_dia_mm", "defesa_civil_mm"]]
    st.dataframe(conf.rename(columns={"estacao": "Estação", "chuva_dia_mm": "Calculado aqui (mm)",
                                      "defesa_civil_mm": "Relatório da Defesa Civil (mm)"}),
                 hide_index=True)

    st.subheader("E a estação oficial do INMET?")
    inm = painel.inmet_resumo(diaria_f)
    if inm["dias_fortes"]:
        pct = inm["inmet_tambem"] / inm["dias_fortes"] * 100
        st.write(f"A estação automática do INMET fica no Pico do Couto, a 1.777 m, longe dos bairros. "
                 f"Dos {inm['dias_fortes']} dias com mais de 50 mm na área central, ela também passou de 50 mm "
                 f"em só {inm['inmet_tambem']} ({numero(pct, 0)}%). Em 15/02/2022 marcou 3 mm. Ela não representa "
                 f"a chuva dos bairros e por isso fica fora das análises deste painel.")

    with st.expander("Fontes, tratamento e limitações"):
        st.markdown("""
**Fontes**
- Chuva nos bairros: rede de pluviômetros do Cemaden, plataforma PED (ped.cemaden.gov.br). Dados da rede observacional do CEMADEN/MCTI.
- Estação oficial: INMET, estação automática Pico do Couto (A610), portal.inmet.gov.br/dadoshistoricos.
- Desastres: Atlas Digital de Desastres no Brasil, atlasdigital.mdr.gov.br (base disponível até 2022).

**Tratamento**
- Horários convertidos de UTC para o horário de Brasília.
- Dia válido: pelo menos 20 das 24 horas com registro.
- Descartados os registros marcados como suspeitos pelo Cemaden e os dias em que a estação marcou menos de 1 mm enquanto a maior parte da rede registrava chuva forte.
- Acumulados de 24 e 72 horas, porque os deslizamentos dependem também da chuva dos dias anteriores.

**Limitações**
- Muitas falhas na rede entre 2019 e 2022; estações com poucos dados no filtro aparecem destacadas.
- Só aparecem os desastres reconhecidos oficialmente.

Projeto de extensão do curso de Ciência de Dados e Business Intelligence da Universidade Católica de Petrópolis. Autor: Marcelo Pereira.
""")
