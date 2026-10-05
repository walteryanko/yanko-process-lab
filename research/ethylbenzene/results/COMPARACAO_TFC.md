# Houve melhoria frente ao TFC?

Há melhorias e pioras frente a uma referência **PI + FKE reconstruída no mesmo protocolo novo**. A superioridade sobre a execução histórica do TFC ainda não está demonstrada: sua sintonia numérica, estado inicial completo, matrizes P/Q/R e amostragem não foram recuperados. O ganho de 14,8% informado no estudo anterior é contra o **UKF novo + NMPC MIMO**, não contra o PI do TFC.

## Números publicados, preservados

| Perturbação | Malha | IAE | ITAE | ISE |
|---|---|---:|---:|---:|
| benzene_50 | Fechada: PI + FKE | 0.1476 | 0.3368 | 0.0102 |
| benzene_50 | Aberta | 0.0906 | 0.5625 | 0.0016 |
| recycle_minus50 | Fechada: PI + FKE | 0.1467 | 0.3291 | 0.0102 |
| recycle_minus50 | Aberta | 0.3678 | 2.1230 | 0.0267 |

Fonte: Tabelas 4.3-4.4 do PDF do autor, p. 57. No benzeno, os valores publicados de IAE e ISE fechados são **62,9% e 537,5% maiores** que os abertos; somente ITAE melhora. Isso contradiz a discussão do texto e foi preservado. No reciclo, as três métricas publicadas melhoram em malha fechada.

Tabela 4.2: MAE=0,00001626 e RMSE=0,000514 para xEB; janela e condições não estão integralmente especificadas. As frações FKE da Tabela 4.1 também foram incorporadas: [0,0050; 0,6631; 0,2795; 0,0523].

## Comparação controlada com PI + FKE reconstruído

Todos recebem a mesma planta reduzida, equilíbrio, viés inicial, medição de temperatura, ruído, sementes 9001–9003, períodos e limites de atuação. O FKE tem Jacobiana exata e Q constante=64×Q0, escolhido em validação independente. A receita de relé do TFC aplicada em ensaio nominal separado produziu Kcu=45,878237, Tu=0,15 h, Kc=20,853744 e Ti=0,125 h. São parâmetros novos, não recuperados do TFC. A válvula equipercentual tem rangeabilidade 50, capacidade 2, taxa máxima 0,12 por amostra e anti-windup explicitamente introduzido.

Ganho = média de três razões pareadas, 100×(1−IAE_evento_novo/IAE_evento_PI). Positivo significa redução de erro; negativo significa piora. Janelas: 3–10 h nos servos e 5–10 h nos demais casos. A comparação de mesmo atuador/objetivo usa **SISO sem restrição térmica**. MIMO e a nova restrição térmica alteram o projeto.

| Cenário | UKF validado / físico SISO | LSTM-UKF / físico SISO |
|---|---:|---:|
| benzene_50 | +16.36% | +19.77% |
| recycle_minus50 | +97.91% | +98.00% |
| servo_up | -11.29% | -11.77% |
| servo_down | -7.12% | -6.76% |
| thermal_loss | +56.20% | -67.76% |
| kinetics_noise | -0.07% | -0.09% |

O ganho próximo de 98% no reciclo inclui a dificuldade do PI reconstruído, que oscila nesse caso. Depende da sintonia e do modelo efetivo adotados. Nos servos os dois NMPC físicos SISO pioram; no caso cinético a diferença é inferior a 0,1% e não sustenta uma conclusão robusta com apenas três sementes. LSTM-UKF SISO piora também na perda térmica.

## Todas as combinações SISO sem restrição nos dois casos históricos

| Estimador | Preditor NMPC | Benzeno +50% | Reciclo −50% |
|---|---|---:|---:|
| UKF Q0 | physical | +20.34% | +97.72% |
| UKF Q0 | neural | +20.95% | -66.84% |
| UKF validado | physical | +16.36% | +97.91% |
| UKF validado | neural | +16.22% | -67.00% |
| LSTM-UKF | physical | +19.77% | +98.00% |
| LSTM-UKF | neural | +20.36% | -67.36% |
| NAKE-BB | physical | -80.23% | +88.09% |
| NAKE-BB | neural | -108.09% | +8.89% |
| LSTM-NAKE | physical | -72.49% | +86.08% |
| LSTM-NAKE | neural | -99.59% | +88.48% |

A predição blackbox SISO com UKF/LSTM-UKF piora cerca de 67% no reciclo. NAKE-BB e LSTM-NAKE SISO pioram no benzeno. Portanto aprendizagem não demonstra superioridade universal. Os 240 grupos por cenário, preditor, estimador, modo e restrição, com temperatura e contagem de sementes que melhoram, estão em `improvement_vs_pi.csv/json`.

## Temperatura e integrabilidade

Sem restrição, o PI reconstruído atinge 182,38 °C no benzeno e 201,03 °C no reciclo. UKF validado / NMPC físico SISO atinge 182,34 °C e 165,65 °C. A redução de IAE não garante cumprir o limite assumido de 165 °C. O PI histórico não possuía esse limite. Compará-lo com NMPC restrito mede também uma exigência nova; a auditoria térmica anterior mantém 128/360 execuções restritas com ultrapassagem real simulada.

As integrais novas 0–10 h e as publicadas estão lado a lado em `tfc_control_comparison.csv/json`. Não se calcula ganho causal entre elas: a partida histórica difere do início novo em equilíbrio, e ruído/sintonia/amostragem não coincidem.

## Observadores

| Observador novo | MAE 0–5 h | RMSE 0–5 h | RMSE 5–10 h |
|---|---:|---:|---:|
| UKF Q0 | 0.0022359 | 0.0046601 | 0.0003726 |
| UKF validado | 0.0022434 | 0.0046580 | 0.0003539 |
| LSTM-UKF | 0.0022433 | 0.0046595 | 0.0003284 |
| NAKE-BB | 0.0022283 | 0.0046523 | 0.0003681 |
| LSTM-NAKE | 0.0022306 | 0.0046486 | 0.0003324 |
| FKE reconstruído | 0.0022294 | 0.0046375 | 0.0003539 |

A estimação nova usa verdade e medições comuns, sem influência do controlador. O viés inicial domina a janela 0–5 h. Seu RMSE é maior que o RMSE original publicado; os protocolos diferentes impedem atribuir a diferença somente ao estimador. Nenhum ganho sobre a Tabela 4.2 é reivindicado.

## Curvas originais e auditoria

`tfc_digitized.csv` contém digitalização das Figuras 4.4, 4.7 e 4.8, não séries brutas recuperadas. Máscaras, calibragem, hashes de PNGs e resolução estão em `tfc_digitization.json`. Incerteza vertical nominal de dois pixels: ±0,0040 / ±0,0021 / ±0,0018 em xEB. Sobreposições longas não são interpoladas. A legenda da Figura 4.8 é ambígua; cores e rótulos são preservados.

As planilhas originais são varreduras estáticas, não registros temporais do PI/FKE. Não foi localizado o Simulink executável deste reator de cinco estados. A planta Aspen completa continua fora do escopo.

18/18 testes PI + FKE e 15/15 testes de estimação FKE concluídos. Todas as 7.200 amostras PI foram reintegradas, com erro de estados/integrais igual a zero; trajetórias verdadeiras de estimação coincidem exatamente com as dos outros filtros. Nove testes numéricos do módulo, incluindo FKE/Jacobiana e reversão de PI saturado. Q e covariâncias nos NPZ usam **unidades físicas dos estados ao quadrado**; o escalonamento normalizado é apenas interno.

Reprodução: `baseline.py`, `historical.py`, `report.py`; dados e código versionados, trajetórias separadas. Não houve sintonia usando pontuação dos testes de controle.
