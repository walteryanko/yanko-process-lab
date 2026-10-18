# Darwin Observer nos cenários da dissertação

Comparação executada em 18/10/2026 para Walter Yanko de Aragão Brandão. A fonte é a dissertação **Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares** (UFCG, 2019) e seu código MATLAB/Simulink recuperado.

## Abrir os resultados

- `reports/thesis/Comparacao_Darwin_Dissertacao.pdf`: 56 páginas, com os 19 cenários, todos os seis estados, temperaturas, perturbações, variável manipulada, referências e RMSE/IAE.
- `reports/thesis/Graficos_Darwin_Dissertacao.html`: galeria local das 50 figuras. Extraia todo o pacote antes de abrir; as imagens ficam em `figures/`.
- `reports/thesis/Metricas_RMSE_IAE_por_cenario.csv`: médias e IC95% por cenário, condição, método e variável; delimitador ponto e vírgula, vírgula decimal, UTF-8.
- `artifacts/thesis/metrics.csv`: as 1.800 execuções individuais, com sementes, erros, violações térmicas, tempos e caminhos das trajetórias.
- `artifacts/thesis/summary.csv` e `paired_comparisons.csv`: agregações e diferenças pareadas.
- `artifacts/thesis/trajectories/`: resultados NPZ brutos das execuções, incluídos no pacote completo.

## Resultado

O Darwin **reteve H0 e coincidiu numericamente com o UKF RK4**. Nenhuma correção física obteve validação independente suficiente; o melhor candidato teve ganho de 4,49%, abaixo dos 10% exigidos, e IC95% da diferença de perda incluindo zero. Esta campanha não injeta um defeito estrutural oculto: diferenças contra o UKF Euler não podem ser atribuídas à descoberta simbólica.

São 8 cenários em malha aberta e 11 sob NMPC, estes executados com e sem a penalização térmica original. Três observadores × 30 combinações cenário/condição × 20 sementes = 1.800 execuções. Nenhuma falha de simulação ou de otimização foi observada. A comparação é uma reconstrução física, não uma repetição bit a bit das curvas MATLAB: SLSQP substitui fmincon e as sementes são novas. Não foram digitalizados números das curvas PID/cascata ou EKF para simular resultados desses métodos.

O limite original é 160 °F = 344,2611 K. “Com restrição” significa a **penalização suave QR=1000** do código recuperado, e não uma desigualdade rígida. Violações são reportadas sem arredondar o limiar para 344 K. Os percentuais de perturbação das temperaturas são aplicados em °F antes da conversão para SI.

RMSE de estimação e IAE de estimação usam `estimativa − verdade da planta` para cada estado. RMSE de controle e IAE de controle usam `CC da planta − referência`. Todos usam a janela completa, incluindo a partida. RMSE é `sqrt(mean(error**2))`; IAE é a integral trapezoidal de `abs(error)`. A fórmula impressa como RMSE na Equação 61 da dissertação difere dessa definição convencional.

As curvas mostram a primeira semente predefinida de cada cenário, sem seleção pela aparência. As tabelas agregam 20 realizações independentes; o bootstrap pareado usa 2.000 reamostragens. As iniciais químicas são conhecidas pela receita ou pelo equilíbrio; os resultados não provam observabilidade global nem validação industrial.

## Reproduzir

Python 3.11 ou superior. Dependências em `requirements.txt` (inclui CasADi 3.7.2). Na pasta do projeto:

```bash
python -m pip install -r requirements.txt
python -m darwin.thesis_experiments --stage fit
# Opcional, no Linux com gcc: acelera o custo sem alterar as equações.
python -m darwin.thesis_experiments --stage compile
python -m darwin.thesis_experiments --stage run --n 20 --workers 4
python -m darwin.thesis_reporting --stage all
python -m pytest -q
```

O comando `run` atual já inclui os 19 cenários. Não execute `scripts/complete_thesis_steady.py` numa reprodução nova: esse script registra o adendo histórico da primeira execução, quando a Figura 28 foi incluída após os outros 18 casos. `protocol_initial_18_cases.json` e `protocol_addendum.json` preservam a sequência auditável original.

No Windows, `REPRODUZIR_DISSERTACAO.bat` prepara o ambiente e usa CasADi diretamente, sem exigir gcc. É mais lento que o custo C compilado utilizado nesta máquina Linux. Os resultados foram testados em Linux/Python 3.12; a execução real no Windows não foi validada nesta entrega.

Os comandos substituem `artifacts/thesis` e os relatórios correspondentes; copie a pasta antes se quiser preservar a campanha entregue. O protocolo e as sementes são fixos, mas pequenas diferenças de plataforma/solver podem ocorrer. As versões do sistema e os hashes estão em `artifacts/thesis/runtime.json` e no manifesto do pacote.

## Proveniência e verificação

- Fonte e decisões: `artifacts/thesis/source_provenance.json`.
- Parâmetros históricos: `vendor/thesis_original/`.
- Casos/eventos/unidades: `darwin/thesis_cases.py`.
- NMPC com referência futura conhecida e sem antecipação de perturbações: `darwin/thesis_control.py`.
- Separação entre planta avaliadora e entradas operacionais: `darwin/thesis_experiments.py`.
- Comissionamento: `discovery.json`, `calibration.json`, diretório `commissioning/`.
- Equivalência efetivamente observada: `equivalence_check.json`.
- Testes: 36 aprovados, incluindo balanços, equivalência histórica, causalidade, gradiente do custo, eventos entre amostras e exportação do laboratório.

Durante a verificação foi detectado um gzip preexistente corrompido no exportador v1.0. O CSV foi regenerado a partir dos modelos congelados e das 100 sementes originais, sem reajuste; o maior desvio numérico nas médias de RMSE de CC foi 2,60×10⁻¹¹. Isso não altera o protocolo nem os resultados novos da dissertação. A reparação está em `legacy_export_repair.json`.
