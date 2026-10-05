# Etilbenzeno: resultados simulados

20 configurações; 720 ensaios de controle; 75 ensaios de observadores. Primeiro reator do TFC, reconstruído.

Equilíbrio: T=160.876134 C, xEB=0.281108; Q efetivo=25.241426 MW. Limite de pesquisa assumido: 165 C.

Ganho de IAE após evento: média das razões pareadas vs UKF validado + NMPC físico, no mesmo modo. Positivo=melhora. MIMO acrescenta objetivo térmico e atuador, portanto seu efeito inclui essa mudança de projeto.

## Restrição ativada

| Estimador | Preditor | Modo | IAE média evento | Ganho vs UKF val. | Tmax C | Runs >165 C | Fallbacks |
|---|---|---|---:|---:|---:|---:|---:|
| UKF Q0 | physical | siso | 0.0703227 | +18.24% | 183.997 | 10/18 | 20 |
| UKF Q0 | physical | mimo | 0.0303816 | -20.26% | 182.684 | 3/18 | 0 |
| UKF Q0 | neural | siso | 0.1357533 | -1308.68% | 183.990 | 10/18 | 22 |
| UKF Q0 | neural | mimo | 0.0304025 | -21.22% | 182.685 | 3/18 | 0 |
| UKF validado | physical | siso | 0.1065005 | +0.00% | 169.226 | 9/18 | 88 |
| UKF validado | physical | mimo | 0.0261590 | +0.00% | 169.301 | 3/18 | 12 |
| UKF validado | neural | siso | 0.1706095 | -1328.45% | 169.195 | 10/18 | 86 |
| UKF validado | neural | mimo | 0.0260540 | -0.08% | 169.323 | 3/18 | 9 |
| LSTM-UKF | physical | siso | 0.0866662 | +12.45% | 173.445 | 10/18 | 44 |
| LSTM-UKF | physical | mimo | 0.0223004 | +12.60% | 172.282 | 3/18 | 0 |
| LSTM-UKF | neural | siso | 0.1567232 | -1323.10% | 173.436 | 10/18 | 54 |
| LSTM-UKF | neural | mimo | 0.0223240 | +11.77% | 172.274 | 3/18 | 0 |
| NAKE-BB | physical | siso | 0.0990403 | -72.29% | 173.572 | 10/18 | 56 |
| NAKE-BB | physical | mimo | 0.0228215 | -8.44% | 172.320 | 3/18 | 0 |
| NAKE-BB | neural | siso | 0.1308144 | -706.58% | 173.567 | 9/18 | 59 |
| NAKE-BB | neural | mimo | 0.0229571 | -15.56% | 172.322 | 3/18 | 0 |
| LSTM-NAKE | physical | siso | 0.0972932 | -87.30% | 172.277 | 10/18 | 52 |
| LSTM-NAKE | physical | mimo | 0.0223296 | -7.07% | 171.456 | 3/18 | 0 |
| LSTM-NAKE | neural | siso | 0.0962635 | -67.36% | 172.285 | 10/18 | 52 |
| LSTM-NAKE | neural | mimo | 0.0224786 | -14.46% | 171.458 | 3/18 | 0 |

## Restrição desativada

| Estimador | Preditor | Modo | IAE média evento | Ganho vs UKF val. | Tmax C | Runs >165 C | Fallbacks |
|---|---|---|---:|---:|---:|---:|---:|
| UKF Q0 | physical | siso | 0.0309353 | -277.02% | 188.913 | 18/18 | 0 |
| UKF Q0 | physical | mimo | 0.0303815 | -124.49% | 182.684 | 3/18 | 0 |
| UKF Q0 | neural | siso | 0.0957184 | -1602.75% | 188.889 | 18/18 | 0 |
| UKF Q0 | neural | mimo | 0.0304023 | -125.55% | 182.685 | 3/18 | 0 |
| UKF validado | physical | siso | 0.0224099 | +0.00% | 183.749 | 18/18 | 0 |
| UKF validado | physical | mimo | 0.0224796 | +0.00% | 169.379 | 3/18 | 0 |
| UKF validado | neural | siso | 0.0874669 | -1332.77% | 183.634 | 18/18 | 0 |
| UKF validado | neural | mimo | 0.0224831 | -0.75% | 169.369 | 3/18 | 0 |
| LSTM-UKF | physical | siso | 0.0237938 | -46.38% | 184.937 | 18/18 | 0 |
| LSTM-UKF | physical | mimo | 0.0223006 | +2.30% | 172.282 | 3/18 | 0 |
| LSTM-UKF | neural | siso | 0.0887544 | -1373.82% | 184.835 | 18/18 | 0 |
| LSTM-UKF | neural | mimo | 0.0223241 | +1.33% | 172.275 | 3/18 | 0 |
| NAKE-BB | physical | siso | 0.0272900 | -116.46% | 183.625 | 18/18 | 0 |
| NAKE-BB | physical | mimo | 0.0228232 | -17.64% | 172.320 | 3/18 | 0 |
| NAKE-BB | neural | siso | 0.0586416 | -760.21% | 183.499 | 18/18 | 0 |
| NAKE-BB | neural | mimo | 0.0229589 | -24.71% | 172.322 | 3/18 | 0 |
| LSTM-NAKE | physical | siso | 0.0275449 | -120.23% | 184.301 | 18/18 | 0 |
| LSTM-NAKE | physical | mimo | 0.0223289 | -12.63% | 171.456 | 3/18 | 0 |
| LSTM-NAKE | neural | siso | 0.0265576 | -101.65% | 184.176 | 18/18 | 0 |
| LSTM-NAKE | neural | mimo | 0.0224778 | -20.05% | 171.458 | 3/18 | 0 |

## Estimação sem controle

| Caso | UKF Q0 | UKF validado | LSTM-UKF | NAKE-BB | LSTM-NAKE |
|---|---:|---:|---:|---:|---:|
| Nominal | 0.0003726 | 0.0003539 | 0.0003284 | 0.0003681 | 0.0003324 |
| Benzeno +50% | 0.0003026 | 0.0003288 | 0.0003215 | 0.0005207 | 0.0004874 |
| Reciclo -50% | 0.0003068 | 0.0003893 | 0.0003651 | 0.0005687 | 0.0004058 |
| Perda térmica 20% | 0.0114197 | 0.0013178 | 0.0013620 | 0.0012615 | 0.0024211 |
| Cinética, ruído e perda de sensor | 0.0205873 | 0.0204468 | 0.0204401 | 0.0205795 | 0.0204272 |

RMSE de xEB após 5 h. Mesmas trajetórias por caso/semente. Redes e Q fixo selecionados em validação independente. Não há ganho universal de aprendizagem.

A comparação com as tabelas e curvas originais e com 18 ensaios PI + FKE reconstruídos está em [COMPARACAO_TFC.md](COMPARACAO_TFC.md). Os ganhos nesta página usam o UKF novo, não o controle original do TFC.

Originais conferidos: TFC.zip, PDF do TFC, Luyben 2011 e exportação Aspen. Não executado no Aspen/MATLAB. Capacidade/densidade constantes e Q efetivo são aproximações do reator reduzido; a planta completa não está reproduzida. Ver README, manifesto, protocolo e auditoria.
