# Roda o projeto inteiro, do download até os gráficos
# Autor: Marcelo Pereira
# Projeto: Chuva nos bairros e desastres em Petrópolis (2014 a 2025)
#
# Como usar:
#   python executar.py                 baixa INMET e Atlas (se ainda não tiver) e processa tudo
#   python executar.py --sem-download  usa só o que já está em dados/entrada
#
# Os CSVs do Cemaden já precisam estar em dados/entrada/cemaden.
# Saídas: dados/tratados, resultados/tabelas e resultados/figuras.
import argparse
import json

from src import analise, chuva, config, desastres, download, figuras


def salvar(df, pasta, nome):
    df.to_csv(pasta / nome, index=False, encoding="utf-8-sig")


def main(baixar=True):
    if baixar:
        download.executar()

    # 1) leitura e limpeza
    print("\nTratamento (pode levar um ou dois minutos)")
    horaria, diaria, mensal, resumo, descartados = chuva.carregar()
    eventos, info_atlas = desastres.carregar()
    n_cem = (resumo["fonte"] == "Cemaden").sum()
    print(f"  {n_cem} estações do Cemaden e 1 do INMET | {len(eventos)} desastres "
          f"| Atlas até {info_atlas['ultimo_ano_na_base']}")
    print(f"  {descartados} registros marcados como suspeitos pelo Cemaden foram descartados")
    print(f"  {int(diaria['zero_falso'].sum())} dias de 'zero falso' descartados")

    # 2) análises
    print("\nAnálise")
    disp = analise.disponibilidade(diaria)
    ext = analise.extremos_por_estacao(diaria, resumo)
    por_regiao = analise.extremos_por_regiao(ext)
    cal = analise.calendario(mensal)
    dias_comparados, comparacao = analise.inmet_x_central(diaria)
    tab_2022, horas_2022 = analise.evento_15fev2022(diaria, horaria, resumo)
    chuva_desastres = analise.chuva_nos_desastres(diaria, eventos)
    lim = analise.limiares(diaria, eventos)
    ind = analise.indicadores(resumo, diaria, ext, eventos, info_atlas, comparacao)
    print(ind.to_string(index=False))

    # 3) salvar tudo
    T, D = config.TABELAS, config.TRATADOS
    salvar(resumo, D, "estacoes.csv")
    salvar(diaria.drop(columns=["p75_rede"]), D, "chuva_diaria.csv")
    salvar(mensal, D, "chuva_mensal.csv")
    salvar(eventos, D, "desastres.csv")
    salvar(ind, T, "indicadores.csv")
    salvar(disp, T, "disponibilidade_por_ano.csv")
    salvar(ext, T, "chuva_forte_por_estacao.csv")
    salvar(por_regiao, T, "chuva_forte_por_regiao.csv")
    salvar(cal, T, "calendario_por_regiao.csv")
    salvar(dias_comparados, T, "inmet_x_area_central_diario.csv")
    salvar(comparacao, T, "inmet_x_area_central_resumo.csv")
    salvar(tab_2022, T, "evento_15fev2022.csv")
    salvar(horas_2022, T, "evento_15fev2022_horario.csv")
    salvar(chuva_desastres, T, "chuva_nos_desastres.csv")
    salvar(lim, T, "limiares.csv")
    (T / "info_atlas.json").write_text(json.dumps(info_atlas, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4) gráficos do relatório
    figuras.gerar(disp, ext, cal, horas_2022, chuva_desastres)
    print("\nPronto. Resultados em resultados/. Para abrir o painel: streamlit run app.py")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sem-download", action="store_true")
    main(baixar=not p.parse_args().sem_download)
