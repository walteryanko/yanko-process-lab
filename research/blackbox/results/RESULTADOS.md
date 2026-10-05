# IA black-box no NMPC e no NAKE - malha fechada

240 execuções; 229 completas; 11 interrompidas. Três sementes independentes por combinação.

P/U = NMPC físico+UKF; P/N=físico+NAKE-BB; N/U=neural+UKF; N/N=neural+NAKE-BB.
IAE calculado com CC real da planta simulada. Unidades: kmol h/m³. Média de trajetórias completas; `*` indica que alguma semente foi interrompida.

## Sem restrição de 344 K

| Caso | P/U | P/N | N/U | N/N |
|---|---:|---:|---:|---:|
| Servo +10% | 0.553141 | 0.554039 | 0.546717 | 0.547424 |
| FA -10% | 0.505276 | 0.507449 | 0.496255 | 0.498092 |
| FB +10% | 0.540408 | 0.535564 | 0.529515 | 0.524891 |
| T0 -10% °F | 0.628069 | 0.610795 | 0.609157 | 0.598012 |
| Ta -20% °F | 0.626429 | 0.609083 | 0.609705 | 0.597327 |
| FA -15% | 0.471039 | 0.487965 | 0.468754 | 0.493749 |
| T0 -30% °F | 0.630493 | 0.616778 | 0.619001 | 0.609591 |
| Servo -20% | 1.020369 | 1.045568 | 1.039206 | 1.071191 |
| Servo +20% / limite | 0.218587 | 0.225297 | 0.230115 | 0.240714 |
| Partida fria | -* | 0.666490* | -* | -* |

## Com restrição de 344 K

| Caso | P/U | P/N | N/U | N/N |
|---|---:|---:|---:|---:|
| Servo +10% | 0.553141 | 0.554039 | 0.546716 | 0.547423 |
| FA -10% | 0.505276 | 0.507449 | 0.496255 | 0.498093 |
| FB +10% | 0.540406 | 0.535563 | 0.529515 | 0.524891 |
| T0 -10% °F | 0.628069 | 0.610795 | 0.609157 | 0.598013 |
| Ta -20% °F | 0.626429 | 0.609083 | 0.609705 | 0.597327 |
| FA -15% | 0.471039 | 0.487965 | 0.468754 | 0.493749 |
| T0 -30% °F | 0.630496 | 0.616779 | 0.619004 | 0.609592 |
| Servo -20% | 1.020367 | 1.045566 | 1.039207 | 1.071190 |
| Servo +20% / limite | 0.554073 | 0.559633 | 0.548431 | 0.554240 |
| Partida fria | 0.765983 | 0.812931 | 0.952346 | 0.932910 |

## Limites da comparação

Dados sintéticos no modelo com entalpia efetiva calibrada em um ponto; sem dados industriais ou execução MATLAB/Simulink.
A Figura39 e a partida exigem hipóteses explícitas de reconstrução. A penalidade térmica histórica foi substituída por desigualdades na predição.
Uma restrição satisfeita na predição não garante que T real da planta ruidosa respeite344K. Ver Tmax e duração das violações em summary.csv.
Resultados interrompidos no evento355.4K têm IAE parcial e não entram no cálculo de ganhos.
Falhas declaradas de SLSQP: 86; ações de fallback: 83; reparos de covariância: 0.
A versão NAKE-BB usa dinâmica neural e adaptação causal de Q por inovações. Não aprende o ganho K e não é a versão grey-box anterior nem uma reprodução de KalmanNet.

## Diagnóstico adicional com margem térmica de 4 K

24 execuções em partida e servo térmico; 24 completas. Temperatura máxima 341.634243 K; violações de344K 0.
Falhas SQP 148; fallback de resfriamento máximo 146. Esses eventos ocorreram na partida.
A margem vem do máximo térmico de57passos da validação independente (3.710K), arredondado para4K. A ausência de violações observadas inclui a política de fallback e não constitui garantia geral. Ver metrics_margin.csv e relatório.
