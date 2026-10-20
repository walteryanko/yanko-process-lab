# PG Estimator Benchmark v0.1 — resultados exploratórios

Episódios previstos: 320; concluídos: 320; falhas: 0.
IAE só é apresentado para malha fechada. Unidade de CC: kmol/m³ (= mol/L); IAE: kmol h/m³.
Térmico soft significa penalização QR=1000, não restrição rígida.
Oito sementes por célula; IC bootstrap pareado exploratório. Tempos incluem execução no runner, não Windows.

|Cenário|Térmico|Ruído|Método|n/falhas|RMSE CC|IAE CC|T pico K|T acima h|Obs ms|
|---|---|---|---|---:|---:|---:|---:|---:|---:|
|OL_FA|open|contaminated|EKF|8/0|0.0271277|—|341.731|0|0.240871|
|OL_FA|open|contaminated|GM_EKF|8/0|0.0177937|—|341.731|0|0.848747|
|OL_FA|open|contaminated|MHE5|8/0|0.0271175|—|341.731|0|3.02637|
|OL_FA|open|contaminated|UKF_RK4|8/0|0.0271301|—|341.731|0|0.0611123|
|OL_FA|open|gaussian|EKF|8/0|0.0172147|—|341.731|0|0.24688|
|OL_FA|open|gaussian|GM_EKF|8/0|0.0173299|—|341.731|0|0.858662|
|OL_FA|open|gaussian|MHE5|8/0|0.0172146|—|341.731|0|2.98831|
|OL_FA|open|gaussian|UKF_RK4|8/0|0.0172184|—|341.731|0|0.0583256|
|REG_FA15|none|contaminated|EKF|8/0|0.0269404|0.323655|344.877|0.2129|0.267902|
|REG_FA15|none|contaminated|GM_EKF|8/0|0.0175542|0.319302|344.537|0.0821921|0.893213|
|REG_FA15|none|contaminated|MHE5|8/0|0.0269055|0.32364|344.874|0.207061|3.02461|
|REG_FA15|none|contaminated|UKF_RK4|8/0|0.0269404|0.323606|344.877|0.207489|0.0697719|
|REG_FA15|none|gaussian|EKF|8/0|0.0170475|0.31651|344.561|0.0785052|0.26498|
|REG_FA15|none|gaussian|GM_EKF|8/0|0.017234|0.317917|344.558|0.0794234|0.881816|
|REG_FA15|none|gaussian|MHE5|8/0|0.017051|0.316598|344.56|0.0784831|2.97426|
|REG_FA15|none|gaussian|UKF_RK4|8/0|0.0170495|0.316528|344.56|0.0782258|0.0709658|
|REG_FA15|soft|contaminated|EKF|8/0|0.0269555|0.325866|344.871|0.207189|0.2627|
|REG_FA15|soft|contaminated|GM_EKF|8/0|0.0175542|0.319301|344.537|0.082193|0.884815|
|REG_FA15|soft|contaminated|MHE5|8/0|0.0269202|0.325835|344.868|0.201394|3.03248|
|REG_FA15|soft|contaminated|UKF_RK4|8/0|0.0269555|0.325822|344.871|0.201669|0.0702661|
|REG_FA15|soft|gaussian|EKF|8/0|0.0170475|0.316511|344.561|0.0785061|0.263765|
|REG_FA15|soft|gaussian|GM_EKF|8/0|0.017234|0.31792|344.558|0.0794245|0.885987|
|REG_FA15|soft|gaussian|MHE5|8/0|0.017051|0.316599|344.56|0.078484|2.95958|
|REG_FA15|soft|gaussian|UKF_RK4|8/0|0.0170495|0.316527|344.56|0.0782246|0.0708374|
|SERVO_P10|none|contaminated|EKF|8/0|0.0280995|0.374608|341.447|0|0.263025|
|SERVO_P10|none|contaminated|GM_EKF|8/0|0.0191464|0.368103|341.297|0|0.880889|
|SERVO_P10|none|contaminated|MHE5|8/0|0.0280714|0.374297|341.443|0|3.03519|
|SERVO_P10|none|contaminated|UKF_RK4|8/0|0.0280998|0.374592|341.446|0|0.071455|
|SERVO_P10|none|gaussian|EKF|8/0|0.0186505|0.365297|341.292|0|0.263646|
|SERVO_P10|none|gaussian|GM_EKF|8/0|0.0188024|0.366423|341.296|0|0.88385|
|SERVO_P10|none|gaussian|MHE5|8/0|0.0186507|0.365293|341.291|0|2.98737|
|SERVO_P10|none|gaussian|UKF_RK4|8/0|0.018653|0.365305|341.291|0|0.0690841|
|SERVO_P10|soft|contaminated|EKF|8/0|0.0280995|0.374608|341.447|0|0.263452|
|SERVO_P10|soft|contaminated|GM_EKF|8/0|0.0191464|0.368103|341.297|0|0.881341|
|SERVO_P10|soft|contaminated|MHE5|8/0|0.0280714|0.374297|341.443|0|3.02797|
|SERVO_P10|soft|contaminated|UKF_RK4|8/0|0.0280998|0.374592|341.446|0|0.0692196|
|SERVO_P10|soft|gaussian|EKF|8/0|0.0186505|0.365297|341.292|0|0.263318|
|SERVO_P10|soft|gaussian|GM_EKF|8/0|0.0188024|0.366423|341.296|0|0.885558|
|SERVO_P10|soft|gaussian|MHE5|8/0|0.0186507|0.365293|341.291|0|2.98143|
|SERVO_P10|soft|gaussian|UKF_RK4|8/0|0.018653|0.365305|341.291|0|0.0692735|

## Limitações
Simulação sintética com planta nominal, receitas conhecidas e covariâncias históricas.
GM_EKF não reproduz o DDR-EKF publicado. MHE não herda automaticamente garantias teóricas de outro algoritmo.
Não há sintonia posterior com os testes. Falhas e uso de fallback devem acompanhar qualquer ranking.
As trajetórias reais dos métodos divergem em malha fechada; o ruído exógeno permanece pareado.
Os valores médios de T pico não substituem o pior episódio; consulte metrics.csv.
A rotina MHE possui limite de avaliações, que pode interromper a solução antes da convergência.
Não foram testados sensores ausentes, erros de parâmetros da planta ou inventários iniciais incertos nesta campanha.
