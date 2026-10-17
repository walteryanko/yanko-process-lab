# Relatório 3 - Experimentos reproduzíveis

## Protocolo e inventário

Executados: 1.800 episódios principais de teste, com sete estimadores por episódio (12.600 avaliações); 240 episódios de treinamento/validação; 50 episódios de calibração; 600 episódios de diagnóstico cego; 100 sementes de controle em quatro malhas (400 trajetórias); 3.300 avaliações de ablação e 40 desafios exploratórios. As condições são sintéticas. O número de métodos não transforma uma trajetória em várias amostras independentes.

As sementes e as regras de separação estão em configs/protocol.json e nos registros. Pilotos de quatro episódios foram usados antes do congelamento: revelaram sensibilidade da previsão aberta à inicialização e motivaram o prefixo causal de 0,30 h. Nenhum resultado de piloto foi incluído nas médias finais. O único erro de software encontrado na suíte inicial foi uma operação np.r_ não suportada no compilador; o controlador foi corrigido antes de executar o benchmark de controle. Os registros iniciais e finais foram preservados.

## A e B - estimação e recuperação de estrutura

Unidade do RMSE: kmol/m³. Métrica principal inclui a partida inteira, inclusive a incerteza inicial. O CSV também contém RMSE após 20 passos, os seis estados, cobertura, NIS, previsão térmica a dez passos e tempos. A previsão a dez passos é condicional à sequência de entradas fornecida no benchmark; não usa medições futuras. Ela não foi calculada para os baselines adaptativo/RBF/Neural e seus campos ficam explicitamente vazios.

| Cenário | UKF | Adaptativo | Darwin | Redução % | IC diferença UKF-Darwin |
| --- | --- | --- | --- | --- | --- |
| A_mild | 0.01616 | 0.01636 | 0.01575 | 2.5 | -0.00005 / 0.00085 |
| A_rich | 0.02213 | 0.01753 | 0.01578 | 28.7 | 0.00519 / 0.00744 |
| A_weak | 0.01617 | 0.01664 | 0.01618 | -0.1 | -0.00011 / 0.00010 |
| B_activation | 0.15959 | 0.05642 | 0.01526 | 90.4 | 0.13298 / 0.15553 |
| B_curvature | 0.03030 | 0.02669 | 0.03018 | 0.4 | 0.00008 / 0.00018 |
| B_rate | 0.07269 | 0.01652 | 0.01569 | 78.4 | 0.05511 / 0.05895 |
| C_UA | 0.01859 | 0.01535 | 0.01447 | 22.2 | 0.00317 / 0.00503 |
| C_bias | 0.04271 | 0.04947 | 0.01241 | 70.9 | 0.02902 / 0.03148 |
| C_drift | 0.01329 | 0.05274 | 0.01306 | 1.7 | 0.00018 / 0.00029 |
| C_dropout | 0.01438 | 0.01496 | 0.01438 | 0.0 | 0.00000 / 0.00000 |
| C_noise | 0.02003 | 0.02872 | 0.02003 | 0.0 | 0.00000 / 0.00000 |
| D_composition | 0.01904 | 0.01884 | 0.01515 | 20.4 | 0.00295 / 0.00484 |
| D_feed | 0.01937 | 0.01687 | 0.01492 | 23.0 | 0.00345 / 0.00549 |
| D_flow | 0.02289 | 0.01851 | 0.01572 | 31.3 | 0.00557 / 0.00873 |
| D_legacy | 0.03663 | 0.09891 | 0.03952 | -7.9 | -0.00351 / -0.00226 |
| D_noise | 0.02298 | 0.02510 | 0.01958 | 14.8 | 0.00244 / 0.00442 |
| H0 | 0.01317 | 0.01364 | 0.01317 | 0.0 | 0.00000 / 0.00000 |
| X_saturation | 0.02117 | 0.01715 | 0.01566 | 26.0 | 0.00396 / 0.00701 |

[[FIG:01_estimation_intervals.png]]

No A_rich, o expoente escondido é 0,4 e o estimado é 0.398398. O intercepto é 0.000731. A forma aceita é UA_eff = 30385,6 exp(0.000731) (mw/453,6)^(0.398398). A biblioteca foi fixada antes do teste; o mecanismo verdadeiro foi usado somente para calcular o erro de recuperação depois.

| Condição | Modelo escolhido | Erro funcional UA % | Precisão de termos | Explicações plausíveis |
| --- | --- | --- | --- | --- |
| A_mild | UA_power | 0.052 | 1.00 | UA_power |
| A_rich | UA_power | 0.062 | 1.00 | UA_power, UA_sqrt |
| A_weak | UA_sqrt | 4.784 | 0.00 | UA_sqrt, UA_linear, UA_power, UA_reciprocal, UA_quadratic |

A recuperação funcional não estabelece unicidade: UA_sqrt continua plausível em A_rich. A_weak admite cinco explicações próximas e não apresenta ganho químico detectável. A precisão de termos é uma métrica da representação desta biblioteca; funções diferentes podem aproximar a mesma curva dentro de uma faixa restrita.

[[FIG:03_trace.png]]

Em B_rate e B_activation, a mudança cabe na família de Arrhenius usada pelos candidatos. O ganho grande frente ao UKF nominal não é o ganho contra o melhor comparador: em B_rate, Darwin versus UKF adaptativo melhora 5.0%, com IC pareado [0.00041876237371889257, 0.0012590625339814734]. Em A_rich, essa comparação dá 10.0%. B_curvature deliberadamente está fora da família cinética simples: o sistema selecionou feed_temperature, explicação fisicamente errada para a causa injetada. O ganho químico foi pequeno; esse caso falsifica a interpretação de que uma boa validação de saída identifica automaticamente o mecanismo.

## C - sensor ou física, sem revelar o rótulo

| Condição | Acertos | Abstenções | Falsas equações | Detecções |
| --- | --- | --- | --- | --- |
| C_UA | 100 | 0 | 0 | 100 |
| C_bias | 100 | 0 | 0 | 100 |
| C_drift | 100 | 0 | 0 | 100 |
| C_dropout | 100 | 0 | 0 | 0 |
| C_noise | 56 | 44 | 0 | 91 |
| H0 | 99 | 1 | 0 | 0 |

Cada linha tem 100 episódios independentes. As falhas começam presentes no episódio; a deriva cresce linearmente. São medidas adicionais de detecção de presença persistente, não uma distribuição de atrasos após todos os tipos possíveis de changepoint. A detecção de intermitência usa disponibilidade e é separada da estatística de média: por isso o cenário C_dropout tem zero detecções da estatística, mas 100 diagnósticos de sensor.

Foram 555/600 classificações corretas, 45 abstenções e nenhuma classificação incorreta entre as respostas conclusivas. Essa separação perfeita entre classes conclusivas pertence somente ao gerador e às magnitudes testadas. Não houve falsa aceitação de equação física em 500 episódios sem alteração física: 0/500, com limite superior de Wilson de 0.76% (95%). Zero observado não é risco zero.

[[FIG:04_blind.png]]

## D - transferência e limites

Modelos de A_rich foram congelados e transferidos para nova alimentação, vazão, composição e ruído. A transferência entre condições da mesma variante geralmente melhora a média. Em D_legacy, a planta usa todos os parâmetros históricos e o observador mantém os tabelados: o RMSE aumenta 7.9%. Esse experimento testa transporte direto incompatível, não refutação de uma lei de UA isolada com toda a física histórica recalibrada.

## E - separação entre estimação e previsão de controle

| Malha | IAE | RMSE rastreio | Produção kmol | Violações/100 | IAE ganho % |
| --- | --- | --- | --- | --- | --- |
| adaptive_nominal | 0.09810 | 0.13907 | 27.094 | 0 | -1.6 |
| darwin_corrected | 0.02577 | 0.03595 | 28.186 | 0 | 73.3 |
| darwin_nominal | 0.09672 | 0.13787 | 27.112 | 0 | -0.1 |
| nominal | 0.09659 | 0.13769 | 27.114 | 0 | 0.0 |

Darwin com NMPC nominal muda a estimação, mas não reduz o IAE de forma convincente. O maior efeito vem de usar o modelo corrigido no horizonte de controle: redução média de 73.3% do IAE em relação à malha nominal; diferença pareada com IC 95% [0.06987729337709941, 0.07173015540188787]. Todas as malhas tiveram 0/100 episódios acima de 344 K; o limite superior de Wilson por malha é 3.7%. A viabilidade prevista foi 100% nesta campanha. Os tempos de solver refletem esta máquina Linux, incluindo contenda entre processos; não garantem latência no notebook Windows.

[[FIG:02_structure_control.png]]

O funcional usa rastreamento e esforço, não lucro. Produção acumulada é integral de v0 CC e não receita ou produto vendável. O funcional econômico comercial original não foi recuperado como um objetivo diretamente aplicável a esta variante. Não se inventaram preços, custos ou melhorias econômicas.

## Ablações e falsificação

ablations.csv contém remoção do detector, ranking sem holdout, remoção do veto físico, ausência de termos simbólicos, ausência de adaptação, atualização online após detecção e desligamento do monitor de perda. As ablações de remoção de veto também relaxam a política de aceitação ao escolher diretamente um candidato, portanto não isolam perfeitamente um único efeito causal. O espaço funcional continua fisicamente limitado: remover o veto não cria expressões singulares arbitrárias. Resultados iguais não demonstram que o veto seja dispensável em outros espaços de busca.

O braço online compara ativação após detecção, modelo previamente ativado com monitor e monitor de perda desligado. As proteções duras de domínio permanecem. Os eventos reais estão em online_events.json. O controlador também tem testes explícitos de inviabilidade e retorno à refrigeração máxima. Na campanha E as reversões não foram necessárias; o caso negativo de teste assegura execução do caminho de fallback, não sua eficácia universal.

O gerador adversarial amostrou 40 condições, com dt de 0,0075, 0,015 ou 0,03 h, alterações de intensidade, ruído e forma de UA. O pior caso é registrado em adversarial.json. Nenhum modelo foi reajustado após esse desafio. X_saturation usa outras 100 sementes finais. A proposta de busca adversarial é amostragem aleatória dirigida pelo erro relativo, não um agente de otimização adversarial treinado.
