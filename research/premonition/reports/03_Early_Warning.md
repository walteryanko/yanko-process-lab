# 3. Early Warning Signals e detecção

A hipótese foi separada em dois alvos: B usa desaparecimento do equilíbrio frio em T0=295,5196437 K; C/D usa primeiro cruzamento de T>344 K nos próximos 20 passos. Um modelo de probabilidade de bifurcação foi treinado separadamente, com horizonte de 80 passos. A janela de antecedência térmica é 18 min; a de bifurcação, 72 min.

Na campanha B, 80 trajetórias de treino, 40 de calibração e 100 de teste usam apenas medições térmicas ruidosas, entrada corrente e UKF causal. A rampa média progride de 294,8 K até além da dobra, ou para antes dela em controles negativos. Ruído de processo atua na alimentação. A data do evento é a perda do equilíbrio da família congelada nas entradas médias; a transição observada é registrada separadamente em T>T_dobra+3 K.

| Detector B | Eventos | Antecipados | Recall | Falsos/h | Antecedência min |
| --- | --- | --- | --- | --- | --- |
| thermal_342 | 50 | 0 | 0 | 0 | n/a |
| EWS | 50 | 0 | 0 | 0.00692281 | n/a |
| spectral | 50 | 50 | 1 | 0 | 37.35 |
| hybrid_probability | 50 | 50 | 1 | 0 | 36.9 |

No teste B houve 50 perdas de equilíbrio e 50 mudanças de ramo observadas; 0 episódios cruzaram 344 K. Logo, o êxito do detector espectral nessa campanha não representa previsão de perigo térmico. O modelo e a alimentação corrente são conhecidos; não é previsão apenas por uma temperatura isolada.

EWS: regressão linear removida em janela causal; AR(1), variância residual, assimetria, energia de baixa frequência e −ln(φ)/Δt para 0<φ<1. Fora desse intervalo, a taxa é indefinida. O EWS térmico D2 usa escore φ+0,12 ln(variância). O detector de modelo usa a abscissa reativa e considera estado quase estacionário no alvo térmico; valores fora do equilíbrio são indicadores congelados, não certificados de estabilidade.

D4: regressão logística padronizada. D5: 55 árvores de boosting com profundidade 2, taxa 0,06, folhas com pelo menos 60 amostras; calibração sigmoidal em trajetórias separadas. As probabilidades são condicionadas à mistura sintética e à política geradora. Não são probabilidades de acidente. Modelos são JSON legíveis, sem pickle.

Para C/D: 160 trajetórias de treino, 80 de calibração, 100 de teste final e 100 adversariais. Modelos e limiares foram congelados antes de usar as sementes finais 300000–300099 e 400000–400099. Sementes do piloto e da avaliação exploratória foram excluídas da avaliação final. Nenhum limiar foi reajustado após o teste final.

Critério de alerta: somente o início de um alerta antes do evento, dentro do horizonte, recebe crédito. Alarmes persistentes iniciados antes da janela não ganham crédito retroativo. Os últimos horizontes incompletos, o período após o primeiro evento e a inicialização de 31 amostras são censurados. Precisão usa inícios de alerta; recall usa eventos por trajetória. Há registro separado de alertas redundantes.

| Detector térmico | Eventos | Antecipados | Precisão | Recall | Falsos/h | Lead min |
| --- | --- | --- | --- | --- | --- | --- |
| D0 | 51 | 45 | 0.965517 | 0.882353 | 0.0174383 | 3.6 |
| D1 | 51 | 34 | 1 | 0.666667 | 0 | 4.5 |
| D2 | 51 | 36 | 0.506849 | 0.705882 | 0.31389 | 2.7 |
| D3 | 51 | 8 | 0.140845 | 0.156863 | 0.531869 | 13.95 |
| D4 | 51 | 49 | 0.933333 | 0.960784 | 0.0435958 | 6.3 |
| D5 | 51 | 50 | 0.982143 | 0.980392 | 0.00871916 | 7.2 |
| D5_noEWS | 51 | 51 | 0.981818 | 1 | 0.00871916 | 7.2 |

| Conjunto | Modelo | Brier | ECE | AP | Prevalência por amostra |
| --- | --- | --- | --- | --- | --- |
| test | D4 | 0.0700311 | 0.0378373 | 0.660953 | 0.133403 |
| test | D5 | 0.0639263 | 0.0107399 | 0.658133 | 0.133403 |
| test | D5_noEWS | 0.0640318 | 0.00720184 | 0.648936 | 0.133403 |
| falsification | D4 | 0.0869419 | 0.0831565 | 0.627223 | 0.129517 |
| falsification | D5 | 0.0845957 | 0.0671608 | 0.603956 | 0.129517 |
| falsification | D5_noEWS | 0.0737987 | 0.014996 | 0.625388 | 0.129517 |

As curvas de calibração reportam frequências empíricas, Brier, ECE e precision-recall. Os intervalos de recall são binomiais exatos. Intervalos de efeitos pareados são calculados por reamostragem de trajetórias, não pela falsa independência de pontos temporais.

Sensibilidade B: janelas 24/64/128, ruído dobrado, ruído colorido, rampas rápidas/lentas e resfriamento oscilante, 12 trajetórias por condição. As rampas lentas têm duração ampliada para atingir o mesmo ponto final. Na oscilação, a dobra é recalculada para a vazão corrente. O estudo adicional de subamostragem é um piloto descritivo de quatro trajetórias e não valida desempenho estatístico.

![02_recovery](figures/02_recovery.png)

![03_ews_trace](figures/03_ews_trace.png)

![04_detection](figures/04_detection.png)

![05_calibration](figures/05_calibration.png)
