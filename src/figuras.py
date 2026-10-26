# Gráficos para o relatório (salvos em resultados/figuras)
# Autor: Marcelo Pereira
# Usei a mesma cor para cada região em todos os gráficos. O INMET fica sempre em
# laranja e com triângulo, para dar para diferenciar mesmo sem ver a cor.

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from src import config

matplotlib.use("Agg")  # salva as imagens sem abrir janela

CORES_REGIAO = {
    "Área central (1º distrito)": "#2a78d6",
    "Corrêas, Nogueira e Araras": "#1baf7a",
    "Itaipava e vales": "#eda100",
    "Pedro do Rio e Posse": "#e87ba4",
    "Estação oficial (INMET)": "#eb6834",
}
TEXTO, TEXTO2, GRADE = "#0b0b0b", "#52514e", "#e6e5e1"
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
ORDEM_REGIOES = list(CORES_REGIAO)

plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRADE, "axes.labelcolor": TEXTO2,
                     "xtick.color": TEXTO2, "ytick.color": TEXTO2})


def titulo(ax, texto, subtitulo=None):
    ax.set_title(texto, loc="left", fontsize=12, color=TEXTO, pad=22 if subtitulo else 8)
    if subtitulo:
        ax.text(0, 1.02, subtitulo, transform=ax.transAxes, fontsize=9, color=TEXTO2, va="bottom")


def limpar(ax, grade="y"):
    for lado in ["top", "right"]:
        ax.spines[lado].set_visible(False)
    if grade:
        ax.grid(axis=grade, color=GRADE, linewidth=0.8)
        ax.set_axisbelow(True)


def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(config.FIGURAS / nome, dpi=160)
    plt.close(fig)


def ordenar_por_regiao(tab):
    tab = tab.copy()
    tab["ordem"] = tab["regiao"].map({r: i for i, r in enumerate(ORDEM_REGIOES)})
    return tab.sort_values(["ordem", "estacao"])


def disponibilidade(disp):
    # mapa de calor: estação x ano, cor = % de dias válidos
    t = disp.pivot_table(index=["regiao", "estacao"], columns="ano", values="pct_dias_validos")
    t = t.reset_index()
    t = ordenar_por_regiao(t).set_index("estacao").drop(columns=["regiao", "ordem"])
    fig, ax = plt.subplots(figsize=(9, 6.2))
    im = ax.imshow(t.values, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(t.shape[1]), t.columns.astype(str))
    ax.set_yticks(range(t.shape[0]), t.index)
    ax.set_xticks(np.arange(-0.5, t.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, t.shape[0]), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="both", length=0)
    for lado in ax.spines.values():
        lado.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("% de dias com dado válido")
    cb.outline.set_visible(False)
    titulo(ax, "Quanto cada estação funcionou, ano a ano",
            "Células claras indicam estação parada, com falhas ou marcando zero em dia de chuva")
    salvar(fig, "01_disponibilidade_das_estacoes.png")


def mapa(ext):
    fig, ax = plt.subplots(figsize=(7.5, 7.5))
    for regiao, g in ext.groupby("regiao"):
        inmet = regiao == "Estação oficial (INMET)"
        ax.scatter(g["longitude"], g["latitude"], s=60 + g["dias_acima_50mm_por_ano"] * 90,
                   color=CORES_REGIAO.get(regiao, "#8a8984"), alpha=0.85,
                   edgecolor="white", linewidth=2, marker="^" if inmet else "o", label=regiao, zorder=3)
    # algumas estações ficam muito perto uma da outra e os nomes se sobrepunham,
    # então ajustei a posição do texto delas na mão
    deslocar = {"Rua Araruama/Quitandinha": (-12, 9, "right"), "Rua Amazonas/Quitandinha": (-14, -7, "right"),
                "Morin": (12, 10, "left"), "Alto da Serra": (12, -9, "left"), "Independência2": (14, -4, "left"),
                "Mosela": (12, 0, "left"), config.NOME_INMET: (-10, 0, "right"),
                "Vila Constância": (-10, 0, "right"), "Vila Rica": (-10, 0, "right")}
    for _, r in ext.iterrows():
        dx, dy, ha = deslocar.get(r["estacao"], (9, 0, "left"))
        ax.annotate(f"{r['estacao']}  {r['dias_acima_50mm_por_ano']:.1f}", (r["longitude"], r["latitude"]),
                    xytext=(dx, dy), textcoords="offset points", fontsize=7.5, color=TEXTO2,
                    va="center", ha=ha)
    ax.set_xlim(ext["longitude"].min() - 0.1, ext["longitude"].max() + 0.08)
    ax.set_aspect("equal")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    limpar(ax, grade="both")
    leg = ax.legend(frameon=False, fontsize=8, loc="upper left", markerscale=0.6)
    for h in leg.legend_handles:
        h.set_sizes([60])
    titulo(ax, "Dias com mais de 50 mm de chuva por ano, por estação",
            "Quanto maior o círculo, mais frequente a chuva forte. Sul (embaixo) = área central")
    salvar(fig, "02_mapa_chuva_forte.png")


def extremos(ext):
    t = ext.sort_values("dias_acima_50mm_por_ano")
    fig, ax = plt.subplots(figsize=(8, 6.2))
    cores = [CORES_REGIAO.get(r, "#8a8984") for r in t["regiao"]]
    ax.barh(t["estacao"], t["dias_acima_50mm_por_ano"], color=cores, height=0.7)
    for y, v in enumerate(t["dias_acima_50mm_por_ano"]):
        ax.text(v + 0.05, y, f"{v:.1f}", va="center", fontsize=8, color=TEXTO2)
    limpar(ax, grade="x")
    ax.set_xlabel("dias por ano com mais de 50 mm")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in CORES_REGIAO.values()]
    ax.legend(handles, CORES_REGIAO.keys(), frameon=False, fontsize=8, loc="lower right")
    titulo(ax, "A chuva forte se concentra na área central",
            "Dias por ano com mais de 50 mm, considerando só os dias com dado válido")
    salvar(fig, "03_chuva_forte_por_estacao.png")


def calendario(cal):
    t = cal.pivot(index="regiao", columns="mes", values="chuva_media_mm")
    t = t.reindex([r for r in ORDEM_REGIOES if r in t.index])
    fig, ax = plt.subplots(figsize=(9, 3.4))
    im = ax.imshow(t.values, cmap="Blues", aspect="auto", vmin=0)
    ax.set_xticks(range(12), MESES)
    ax.set_yticks(range(len(t)), t.index)
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = t.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if v > np.nanmax(t.values) * 0.55 else TEXTO)
    ax.set_xticks(np.arange(-0.5, 12), minor=True)
    ax.set_yticks(np.arange(-0.5, len(t)), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="both", length=0)
    for lado in ax.spines.values():
        lado.set_visible(False)
    titulo(ax, "Chuva média de cada mês por região (mm)", "Novembro a março concentram a chuva em todas as regiões")
    salvar(fig, "04_calendario_da_chuva.png")


def evento_2022(horas):
    # chuva acumulada ao longo do dia 15/02/2022, uma linha por estação
    if horas.empty:
        return
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    destaque = {"Rua Araruama/Quitandinha": "#2a78d6", "Rua Amazonas/Quitandinha": "#6aa3e6",
                config.NOME_INMET: "#eb6834"}
    for nome, g in horas.groupby("estacao"):
        cor = destaque.get(nome, "#c3c2b7")
        ax.plot(g["hora_local"], g["acumulado_mm"], color=cor, linewidth=2.2 if nome in destaque else 1.2,
                zorder=3 if nome in destaque else 2)
        ultimo = g.iloc[-1]
        if nome in destaque or ultimo["acumulado_mm"] > 30:
            ax.text(ultimo["hora_local"], ultimo["acumulado_mm"], f"  {nome} ({ultimo['acumulado_mm']:.0f} mm)",
                    fontsize=7.5, color=TEXTO2, va="center")
    limpar(ax)
    ax.set_ylabel("chuva acumulada no dia (mm)")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Hh"))
    inicio, fim = horas["hora_local"].min(), horas["hora_local"].max()
    ax.set_xlim(inicio, fim + (fim - inicio) * 0.35)
    titulo(ax, "15 de fevereiro de 2022: a chuva caiu na área central",
            "Chuva acumulada por hora nas estações com dado. Pico do Couto em laranja")
    salvar(fig, "05_evento_15_fev_2022.png")


def desastres(tab):
    # um ponto para a área central e um para o INMET em cada desastre
    if tab.empty:
        return
    t = tab.sort_values("data_evento").reset_index(drop=True)
    rotulos = [f"{d:%d/%m/%Y}" for d in t["data_evento"]]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    y = np.arange(len(t))
    for i, r in t.iterrows():
        vals = [v for v in [r["central_24h_mm"], r["inmet_24h_mm"]] if np.isfinite(v)]
        if len(vals) == 2:
            ax.plot(vals, [i, i], color=GRADE, linewidth=2, zorder=1)
    ax.scatter(t["central_24h_mm"], y, s=70, color="#2a78d6", edgecolor="white", linewidth=1.5,
               label="Maior valor na área central (Cemaden)", zorder=3)
    ax.scatter(t["inmet_24h_mm"], y, s=70, color="#eb6834", marker="^", edgecolor="white", linewidth=1.5,
               label="Pico do Couto (INMET)", zorder=3)
    for lim in config.LIMIARES_INMET:
        ax.axvline(lim, color="#8a8984", linestyle="--", linewidth=1)
        ax.text(lim, -0.75, f" {lim} mm", fontsize=7.5, color=TEXTO2, va="bottom")
    for i, r in t.iterrows():
        # avisa quando uma das fontes não tinha dado no dia
        if np.isfinite(r["central_24h_mm"]) and not np.isfinite(r["inmet_24h_mm"]):
            ax.text(r["central_24h_mm"] + 4, i, "INMET sem dado", fontsize=7.5, color=TEXTO2, va="center")
        if not np.isfinite(r["central_24h_mm"]):
            ax.text(max(r["inmet_24h_mm"], 0) + 4, i, "nenhuma estação da área central funcionando",
                    fontsize=7.5, color=TEXTO2, va="center")
    ax.set_yticks(y, rotulos)
    ax.set_ylim(len(t) - 0.5, -1)
    limpar(ax, grade="x")
    ax.set_xlabel("maior chuva em 24 horas (mm), do dia anterior ao seguinte")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.13), ncol=2)
    titulo(ax, "Chuva nos dias de desastre", "Desastres registrados no Atlas Digital de Desastres")
    salvar(fig, "06_chuva_nos_desastres.png")


def gerar(disp, ext, cal, horas_2022, chuva_desastres):
    disponibilidade(disp)
    mapa(ext)
    extremos(ext)
    calendario(cal)
    evento_2022(horas_2022)
    desastres(chuva_desastres)
