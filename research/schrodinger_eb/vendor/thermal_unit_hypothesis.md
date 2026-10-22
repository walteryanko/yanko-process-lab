# Auditoria térmica adicional: hipótese de unidades e evidência de h/T

**Resultado:** dividir os três coeficientes térmicos de alimentação por 4,184 gera uma semelhança interessante entre taxas de capacidade térmica, mas **não confirma mistura kJ/kcal**. A inspeção do backup Aspen recuperado revelou uma explicação muito mais específica: os quatro valores publicados como capacidades caloríficas coincidem numericamente com **entalpia molar armazenada dividida pela temperatura em °C**, dentro do arredondamento da tabela.

O benchmark principal continua congelado, usando a equação literal reconstruída. Nenhuma constante do modelo ou resultado de controle foi alterado para esta auditoria.

## 1. Teste da hipótese kJ/kcal solicitado

No equilíbrio reconstruído a 160°C:

| Quantidade | Coeficientes publicados | Alimentações divididas por 4,184 |
|---|---:|---:|
| Σ fᵢρᵢCpᵢ, kcal/(h K) | 581766,446 | 139045,518 |
| fsaídaρ₁Cp₁, kcal/(h K) | 136679,891 | 136679,891 |
| Diferença relativa entrada/saída | +325,642% | +1,731% |
| Q exigido pelo equilíbrio, kcal/h | 21828692,029 | 1416089,123 |
| Q exigido, MW | 25,369791 | 1,645810 |
| Mudança artificial de Q ao trocar °C por K sem corrigir referências, MW | 141,297623 | 0,750994 |

O fator 4,184 reduz a discrepância numérica, mas produz Q muito diferente do dever do Aspen recuperado. Além disso, igualdade entre taxas agregadas de capacidade térmica não é um critério suficiente de consistência para misturas reativas com composição e temperatura diferentes. Por isso, a hipótese de simples erro kJ/kcal permanece **não confirmada** e não deve ser aplicada como correção factual.

## 2. Evidência extraída do backup final do Aspen

Fonte: `original_tfc/recovered/TFC/AspenSimFiles/Ethylbenzene_walter/Ethylbenzene.bkp`, registros `DSET STREAM MATERIAL ... STR_MAIN @L_115` de ETHYL, BENZ, REFLUX1 e R1OUT.

| Corrente | T armazenada (°C) | h molar (kcal/kmol) | h/T (kcal/(kmol °C)) | Valor no TFC |
|---|---:|---:|---:|---:|
| Etileno fresco | 46,8500000 | 11071,4549 | 236,317074 | 236,32 |
| Benzeno fresco | 46,8500000 | 12452,7783 | 265,801031 | 265,80 |
| Reciclo da coluna 1 | 45,2200671 | 12367,7849 | 273,502135 | 273,50 |
| Saída do reator 1 | 160,8500000 | 11832,1872 | 73,560380 | 73,56 |

As diferenças são inferiores a 13 partes por milhão e todas ficam dentro do arredondamento publicado. A interpretação dos campos como entalpia molar foi confirmada por duas identidades independentes presentes no próprio arquivo:

1. dividir h molar pela massa molar recupera a entalpia mássica armazenada;
2. multiplicar h molar pela vazão molar, com a conversão temporal, recupera o fluxo de entalpia armazenado.

Exemplo: 12452,7783/78,11364 = 159,418743 cal/g, exatamente o campo de entalpia mássica do benzeno. Essa confirmação evita depender apenas da interpretação de identificadores numéricos do formato Aspen.

A unidade não foi escolhida apenas por plausibilidade: o registro textual de convergência `CONV_PLT` do mesmo arquivo identifica explicitamente `MASS ENTHALPY`, `CAL/GM` para a corrente R2IN. Isso ancora a leitura dos campos de entalpia das correntes em calorias; cal/mol e kcal/kmol são numericamente equivalentes.

**Inferência forte, não histórico de edição comprovado:** os coeficientes térmicos do TFC aparentam ter sido obtidos por h/T°C. O backup não registra como a tabela foi construída, portanto não é possível afirmar a intenção do autor. A coincidência numérica, entretanto, é muito mais específica do que a hipótese de conversão kJ/kcal.

## 3. Por que h/T não é capacidade calorífica

Uma capacidade calorífica apropriada para a derivada energética é uma derivada termodinâmica, por exemplo Cp=(∂h/∂T) a pressão e composição fixas. Já h/T depende do zero adotado para a entalpia e da origem numérica da escala de temperatura. Mesmo quando h/T reproduz h exatamente num ponto, não reproduz sua inclinação local.

Logo, usar o número 73,56 como capacidade acumulativa do reator pode reproduzir um valor de entalpia estacionário e ainda assim produzir constante de tempo térmica incorreta. Ajustar Q não resolve essa diferença de derivada. Não foram recuperados valores explicitamente identificados como Cp/Cv derivados para essas quatro correntes no resumo final; eles precisam ser exportados ou recalculados com o mesmo pacote termodinâmico e condições de fase.

## 4. Dever térmico do Aspen confirmado por duas vias

As vazões molares armazenadas das três alimentações são 630,6; 630,6; 969,4 kmol/h. A saída do reator é 1606,15065 kmol/h. Usando as entalpias da tabela:

`Qremovido = Σ Fin hin − Fout hout`

`Qremovido = 7.819.436,976 kcal/h = 9,087923 MW`.

O registro do próprio bloco `RCSTR CSTR1 RES_Q` contém −2.172.065,83 cal/s, equivalente a **−9,087923 MW**, confirmando o balanço por uma segunda leitura independente. O sinal negativo é remoção na convenção do bloco; o modelo reconstruído usa Q positivo para remoção.

Portanto:

- **9,087923 MW**: dever armazenado no Aspen associado ao TFC recuperado, a 160,85°C;
- aproximadamente **10,29 MW**: referência relacionada de Luyben, não o valor exato deste backup;
- **25,369791 MW**: Q calculado para o equilíbrio da reconstrução literal a 160°C;
- **1,645810 MW**: resultado do teste hipotético de dividir apenas os coeficientes de alimentação por 4,184.

Esses valores não devem ser intercambiados em uma alegação de segurança térmica.

## 5. Implicação para a calibração de Q

As próprias entalpias de corrente do Aspen já fecham o dever térmico armazenado **sem acrescentar separadamente geração de calor de reação**. Assim, usar coeficientes que são h/T para representar essas mesmas entalpias e simultaneamente acrescentar um termo explícito de entalpia de reação exige cuidado para não contar efeitos químicos duas vezes.

A reconstrução também usa fR1=fE+fB+fC1 e densidade molar fixa, enquanto o Aspen fornece vazão molar de saída e contração da mistura. A diferença entre deveres não pode ser atribuída apenas a um fator de unidade. Ela pode reunir referência de entalpia, derivada térmica, composição/densidade e contabilidade de reação. O Q ajustado estacionariamente é compatível com compensação desses efeitos; faltam o código final e dados dinâmicos para decompor causalmente o erro histórico.

O próximo experimento adequado é reconstruir entalpias de espécie e Cp(T,x) consistentemente, conservar massa/inventário, recalibrar o estado estacionário e **comparar as derivadas e trajetórias térmicas**. Isso deve formar uma planta alternativa explicitamente identificada, preservando o benchmark literal para auditoria histórica.

## Reprodução

`python research/experiments/thermal_unit_hypothesis.py`

O script lê o backup original, verifica as duas identidades de entalpia, calcula as duas hipóteses de coeficientes e grava `results/thermal_unit_hypothesis.json`. Não modifica o modelo principal.
