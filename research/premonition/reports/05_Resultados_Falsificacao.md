# 5. Resultados e falsificação

Os resultados sustentam a existência de múltiplos equilíbrios e dobras no modelo PG histórico. Também mostram que prever perda de um equilíbrio e prever ultrapassagem térmica são tarefas diferentes. O detector de modelo antecipou transições da campanha B; o EWS estatístico simples falhou nesse teste mesmo havendo desaceleração observável em perturbações controladas.

| Detector sob ruído adversarial | Eventos | Antecipados | Falsos alertas | Falsos/h | Lead min |
| --- | --- | --- | --- | --- | --- |
| D0 | 50 | 40 | 6 | 0.0518068 | 3.15 |
| D1 | 50 | 33 | 0 | 0 | 4.5 |
| D2 | 50 | 40 | 107 | 0.923887 | 2.7 |
| D3 | 50 | 8 | 107 | 0.923887 | 11.25 |
| D4 | 50 | 48 | 30 | 0.259034 | 6.3 |
| D5 | 50 | 50 | 18 | 0.15542 | 6.75 |
| D5_noEWS | 50 | 50 | 5 | 0.0431723 | 6.75 |

Contribuição incremental dos EWS: os intervalos pareados do Brier completo menos sem EWS são [-0.002698000929127468, 0.000977476642441162] no teste e [-0.012176687187964151, 0.006686848827867454] no adversarial. A decisão deve considerar esses intervalos e os falsos alertas; um valor médio isolado não demonstra superioridade.

| C4 menos C0 | Diferença média | IC95 inferior | IC95 superior |
| --- | --- | --- | --- |
| IAE | 0.000850992 | 0.000262935 | 0.00151209 |
| RMSE_CC | -6.90283e-05 | -0.000151289 | -1.07371e-05 |
| tracking_RMSE | 0.000323088 | 4.99722e-05 | 0.000630554 |
| production_kmol | -0.0131226 | -0.0213098 | -0.00630836 |
| cooling_kmol | 2.17125 | 1.20589 | 3.34373 |
| effort | 0.0067474 | 0.0036635 | 0.010389 |
| peak_T | -0.232347 | -0.358015 | -0.127785 |
| violation_h | 0 | 0 | 0 |
| violation_Kh | -0.0103822 | -0.0212463 | -0.0027771 |
| thermal_event | 0 | 0 | 0 |
| cost | 0.000998321 | -0.000269152 | 0.00228924 |
| economic_proxy | -0.0142082 | -0.0227741 | -0.00699215 |
| feasible_fraction | 0 | 0 | 0 |

| Política | Eventos evitados | Eventos causados | Pares | C0 sem evento | Ações nesses pares |
| --- | --- | --- | --- | --- | --- |
| C1 | 0 | 0 | 100 | 60 | 0 |
| C2 | 0 | 0 | 100 | 60 | 0 |
| C3 | 0 | 0 | 100 | 60 | 409 |
| C4 | 0 | 0 | 100 | 60 | 212 |
| C4_noEWS | 0 | 0 | 100 | 60 | 158 |
| conservative | 0 | 0 | 100 | 60 | 0 |
| oracle_offline | 1 | 9 | 100 | 60 | 0 |

As diferenças em intensidade de violação, IAE e proxy econômico devem ser lidas conjuntamente. Um IC bootstrap [0,0] quando não há discordância observada não prova equivalência. Para C4, o intervalo binomial exato da frequência de discordância é [0.0, 0.03621669264517641].

Os intervalos são exploratórios, obtidos com 2.000 reamostragens pareadas; não foram corrigidos para multiplicidade. Eventos raros são apresentados com seus denominadores. Desempenho no conjunto sintético não estima frequências de falha industrial.

Covariância e observabilidade: a cobertura média de 95% para CC no teste final foi 0.824562; no adversarial, 0.689688. Cobertura baixa denuncia excesso de confiança do filtro sob erro estrutural. results/CD/uncertainty_and_pairs.json contém estratificação por erro químico e antecedência condicionada a ambos detectarem.

Intervenções em pares nos quais C0 não teve evento são um indicador de custo preventivo potencialmente desnecessário. Não se afirma que seriam desnecessárias em qualquer planta ou horizonte. O controlador C4 pode alterar o evento que o classificador pretendia prever; isso exige distinguir risco anterior à ação e desfecho após a ação.

Falhas e resultados negativos preservados: D2 pode confundir ruído colorido com resiliência; D3 pode falhar para eventos térmicos sem bifurcação; probabilidades podem perder calibração sob nova política; limitador físico não vence falta de capacidade de resfriamento; a referência offline pode perder desempenho por efeitos não convexos e orçamento local.

Casos individuais estão em results/CD/failure_cases.json e no Failure Explorer. O arquivo dead_detector.json documenta uma probabilidade deliberadamente inválida sem desativação do guard. Todos os episódios de controle, inclusive falhas, são preservados. A interface identifica contrafactuais como simulações pareadas.

![08_failure](figures/08_failure.png)
