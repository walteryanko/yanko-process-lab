# YCS Ethylbenzene Schrödinger-KF Laboratory 1.0

Laboratório local para o primeiro reator de produção de etilbenzeno por alquilação de benzeno. Não é desidrogenação para estireno. Python 3.11+, CPU-first. Release reexecutada em 22/10/2026.

## Resultado entregue

2.240 execuções de estimação, 176 avaliações de desenvolvimento, 40 simulações de controle, 3 validações de fallback e 35 testes automatizados aprovados. Na campanha principal, 100 sementes por cenário, N=128, M4 teve RMSE de CEB 16,6% maior que UKF no cenário gaussiano e 13,6% maior na condição de baixa informação térmica. M3 apresentou forte subdispersão. Não se estabeleceu posterior persistentemente bimodal no CSTR nem melhoria estatisticamente clara no controle. M5 mantém EnKF porque a ablação não justificou a ponte.

## Windows

1. Extraia todo o ZIP em uma pasta com permissão de escrita.
2. Instale Python 3.11+ x64, incluindo o launcher `py`.
3. Execute `INICIAR_LAB.bat`: instala dependências e abre http://127.0.0.1:8765.
4. Para explorar resultados sem instalação, abra `YCS_Ethylbenzene_Laboratory.html` ou `VER_RESULTADOS.bat`. Novas simulações precisam do motor Python.
5. `TESTAR.bat` executa testes; `REPRODUZIR.bat` cria uma cópia datada, preservando os resultados entregues.

Internet é necessária apenas para a instalação inicial. Não há GPU, serviço pago nem chave de API. As dependências suportam Windows, mas esta release foi executada em Linux; desempenho e instalação em Windows ainda precisam de validação nativa. O orçamento de 16 GB orientou o desenho, sem certificação no notebook de destino.

```bash
python -m venv .venv
# Ative o ambiente virtual pelo procedimento do seu sistema.
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m eblab.server
python -m eblab.experiments --out results/novo --trials 100 --steps 60 --particles 128
```

Defina OPENBLAS_NUM_THREADS=1 e OMP_NUM_THREADS=1. Campanhas usam quatro processos; `--workers 1` reduz carga simultânea. Uma pasta que já contenha runs.jsonl não é sobrescrita.

## Modelo e arquitetura

Fonte: walteryanko/yanko-process-lab, commit `16aaafb63572d62e0e3341e26d8317b0651bdde0`, branch research/ethylbenzene-combinations. Originais intactos em vendor/.

- Estado: [CE, CB, CEB, CDEB, T_C], kmol/m³ e °C. Medição: apenas T_C.
- Entrada: [fE, fB, fReciclo, Q, TE, TB, TReciclo]. Vazões m³/h; Q kcal/h positivo para remoção.
- Amostragem 0,025 h = 90 s, configuração da pesquisa EB recuperada. Os 54 s do propilenoglicol não foram transplantados.
- Planta DOP853, rtol=1e-10, atol=1e-12; filtros RK4 com oito subpassos.
- Q efetivo nominal 25,2414 MW não equivale ao dever Aspen de 9,0879 MW. Os coeficientes térmicos publicados apresentam evidências de h/T, não Cp derivativo. Esta é uma limitação central do modelo reconstruído.

| Método | Implementação |
|---|---|
| M0 | UKF α=0,35, β=2, κ=0, paridade com original verificada sem projeções |
| M1 | EnKF com observações perturbadas e covariância amostral |
| M2 | Bootstrap PF, log-pesos, reamostragem sistemática se ESS < N/2 |
| M3 | Transformação baricêntrica entrópica, log-Sinkhorn, custo com escalas físicas |
| M4 | Schrödinger–Föllmer, referência browniana δ0 e alvo posterior KDE |
| M5 | Alternância EnKF/M4; gatilho desativado pela ablação |

M3 não é M4. A ponte M4 gera a posterior em tempo auxiliar; não é uma ponte física entre duas marginais arbitrárias. Veja reports/mathematics.md.

## Dados e reprodução

results/primary contém 1.200 execuções (100 sementes × 2 cenários × 6 filtros). robust/naive comparam informação de ruído; physics_fixed/physics_joint separam estado e parâmetros; q64 usa somente as primeiras 20 sementes; no_observations usa 100 sementes por cenário. Não comparar o agregado q64 com 100 sementes sem pareamento.

results/studies contém seleção, testes sintéticos, observabilidade, PF 4.096/8.192 e custo N=64..1.024. results/control contém quatro braços × 10 sementes. analysis.json verifica 600 datasets, 2.240 trajetórias, RMSE recalculado e balanços de inventário independentes da cinética. JSONL contém métricas por seed; CSV é tabular; NPZ guarda planta, entradas, medições, ruído, estimativas, covariâncias e intervalos. demo_*.json preserva partículas e planos dos primeiros seeds.

```bash
python -m eblab.studies development --out results/repro/studies
python -m eblab.studies synthetic --out results/repro/studies
python -m eblab.studies observability --out results/repro/studies
python -m eblab.studies reference --out results/repro/studies
python scripts/run_campaigns.py --out results/repro --workers 4
python -m eblab.studies scaling --out results/repro/studies
python -m eblab.control --out results/repro/control
python -m eblab.control --forced --trials 3 --out results/repro/fallback_validation
```

Configuração congelada: ε=0,1, h=0,1, 64 passos, limiar M5 infinito. Scripts analyze.py, build_dashboard.py e report.py operam sobre results/ da release; use uma cópia isolada para outra campanha. O script reproduce.py faz essa cópia e reproduz toda a ciência. Relatórios requerem requirements-reports.txt.

Os sete painéis exibem dados reais. Projeções 2D/3D não representam toda a distribuição de cinco estados. Uma nova trajetória altera a demonstração, preservando os benchmarks. O ZIP inclui dados volumosos; a branch Git contém fontes e resumos leves. Se web/data.js estiver ausente no Git, execute `python scripts/bootstrap_demo.py`.

Não se reivindicam originalidade absoluta, observabilidade global, dominância universal, estabilidade garantida do NMPC ou validação industrial. A termodinâmica reduzida, N finito, horizonte 1,5 h, domínio condicionado e posterior aproximada restringem as conclusões.
