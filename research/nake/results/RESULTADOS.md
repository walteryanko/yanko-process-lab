# NAKE x UKF - resultados simulados

Equilíbrio calibrado: T=332.3 K; Tt=314.490675 K; CC=2.280915 kmol/m³.
Entalpia efetiva: -84138.653537 kJ/kmol. Calibração em um ponto, não parâmetro físico recuperado.

360 execuções; 0 divergências. 19 testes numéricos aprovados localmente.

| Regime | UKF ref. | UKF ressint. | NAKE-Q | NAKE dinâmica | NAKE híbrido | Ganho híbrido |
|---|---:|---:|---:|---:|---:|---:|
| Nominal | 0.006908 | 0.007042 | 0.006993 | 0.007841 | 0.007833 | -11.2% |
| Partida | 0.007106 | 0.007120 | 0.007194 | 0.008000 | 0.008203 | -15.2% |
| Degraus na alimentação | 0.006794 | 0.006910 | 0.006889 | 0.008303 | 0.008520 | -23.3% |
| Degraus na refrigeração | 0.006900 | 0.007033 | 0.007016 | 0.007980 | 0.007956 | -13.1% |
| UA: -12% | 0.009541 | 0.007751 | 0.007152 | 0.008570 | 0.009520 | -22.8% |
| Cinética: +10% | 0.038815 | 0.037860 | 0.030385 | 0.022919 | 0.021026 | +44.5% |
| Ruído dos sensores: ×3 | 0.010683 | 0.011304 | 0.018122 | 0.015720 | 0.019293 | -70.7% |
| Perda de sensores | 0.008634 | 0.010338 | 0.010483 | 0.015567 | 0.015215 | -47.2% |
| Fora do treino: combinado | 0.073351 | 0.066627 | 0.047973 | 0.035864 | 0.030331 | +54.5% |

RMSE de CC em kmol/m³. Ganho calculado contra o UKF ressintonizado. Média por semente; regimes igualmente ponderados.
Média macro: UKF ressintonizado 0.017998; NAKE híbrido 0.014211; redução 21.0%.

A versão híbrida ganha nos testes de cinética e combinação fora do treino, mas piora em outros regimes. Q não substitui uma adaptação de R. Calibração de incerteza é preliminar: cobertura, NEES e NIS são fornecidos, sem garantia estatística geral.

Verificação histórica independente: RMSE nos 24 pontos não nominais: tabelado 8.2473 K; calibrado 0.5268 K; máximo calibrado 1.9780 K. Seleção da raiz mais próxima do ponto histórico: diagnóstico de melhor caso, não previsão por continuação.

Código e pesos reais; rede MLP de estatísticas causais, não LSTM. Sem dados da planta real, ensaio MATLAB ou comparação fechada NMPC nesta execução. Ver README e protocol.json.