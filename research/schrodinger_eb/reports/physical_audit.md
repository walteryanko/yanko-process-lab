# Auditoria física do reator de etilbenzeno do TFC

Data: 2026-10-10. Fonte primária local: `upload/TFC_WALTER_FINAL_imprimir(1).pdf`, páginas impressas 42–57 (iguais à posição da página neste PDF). Equações e tabelas foram verificadas visualmente nas páginas 44–46; figuras nas páginas 53 e 55. Esta auditoria não afirma ter reproduzido o arquivo Simulink original.

## 1. Escopo e nomes de correntes

O equipamento observado é o **primeiro reator**, não toda a planta. As alimentações são etileno fresco `fE`, benzeno fresco `fB` e reciclo da primeira coluna `fC1`. A saída do reator é `fR1`. A Tabela 3.3 estabelece explicitamente:

`fR1 = fE + fB + fC1`.

Portanto `fC1` não é uma vazão de refrigerante e `fR1` não é o reciclo. No benchmark “−50% no reciclo” deve-se alterar `fC1`; a saída acompanha a soma para preservar a hipótese de volume constante. Manipular independentemente quatro vazões sem acrescentar balanço de inventário viola a própria definição do modelo.

## 2. Reações, taxas e estequiometria

Com a ordem de espécies `[E,B,EB,DEB]`, o TFC contém corretamente:

1. `E + B -> EB`;
2. `EB + E -> DEB`;
3. `DEB + B -> 2 EB`.

O coeficiente **2** da transalquilação é indispensável e está presente no documento (pp. 43–44).

`r1=k1 CE CB`, `r2=k2 CE CEB`, `r3=k3 CB CDEB`;

`ki=Ai exp[-Ei/(R TK)]`, sendo `TK=T°C+273.15`.

A matriz estequiométrica, por colunas de reações, é

```
S = [[-1,-1, 0],
     [-1, 0,-1],
     [ 1,-1, 2],
     [ 0, 1,-1]].
```

As taxas líquidas são `rE=-r1-r2`, `rB=-r1-r3`, `rEB=r1-r2+2r3`, `rDEB=r2-r3`.

As colunas obedecem `S3=S1-S2`, de modo que `rank(S)=2`. Duas quantidades químicas conservadas são:

- anéis aromáticos: `zA=CB+CEB+CDEB`;
- grupos etila equivalentes: `zE=CE+CEB+2CDEB`.

As duas seguem balanços lineares de entrada/saída independentes das taxas de reação. Isso permite restrições multiestado consistentes, sem aprender novamente a estequiometria. É uma hipótese técnica a testar, não um ganho de controle já demonstrado.

## 3. Balanços exatamente transcritos

```
V dCE/dt   = fE rhoE + fC1 CE,C1 - fR1 CE + V(-r1-r2)
V dCB/dt   = fB rhoB + fC1 CB,C1 - fR1 CB + V(-r1-r3)
V dCEB/dt  = fC1 CEB,C1 - fR1 CEB + V(r1-r2+2r3)
V dCDEB/dt = -fR1 CDEB + V(r2-r3)

rho1 cv1 V dT/dt =
  fE rhoE cpE TE + fB rhoB cpB TB + fC1 rhoC1 cpC1 TC1
  -fR1 rho1 cp1 T + V sum_i[ri(-DeltaHi)] - Q.
```

Na página 44 o lado esquerdo usa `cv1`; o termo de saída usa `cp1`. Na tabela consta `cv1=73.56`; não se explicita separadamente `cp1`, logo adotar `cp1=cv1` é uma hipótese de reprodução a registrar. `Q>0` significa remoção de calor. O equilíbrio líquido constante e a cinética de fase líquida são aproximações do modelo; não se deve extrapolar para inferência de pressão ou vaporização sem equações adicionais.

## 4. Constantes do TFC e correção de unidades

| Parâmetro | Valor publicado | Unidade e observação |
|---|---:|---|
| V | 200 | m³ |
| rho1 | 8.09685 | kmol/m³ |
| rhoE | 7.63446 | kmol/m³ |
| rhoB | 10.8803 | kmol/m³ |
| rhoC1 | 10.9014 | kmol/m³ |
| cv1 | 73.56 | kcal/(kmol °C), conforme tabela |
| cpE | 236.32 | kcal/(kmol °C), conforme tabela |
| cpB | 265.80 | kcal/(kmol °C), conforme tabela |
| cpC1 | 273.50 | kcal/(kmol °C), conforme tabela |
| TE; TB; TC1 | 46.85; 46.85; 45.22 | °C |
| CE,C1; CB,C1; CEB,C1 | 0.001198; 10.8982; 0.002015 | kmol/m³ |
| fE; fB; fC1 | 82.59918; 57.95784; 88.92402 | m³/h |
| fR1 | 229.48104 | m³/h, soma calculada |
| DeltaH1; DeltaH2; DeltaH3 | −27150; −26950; −205.5 | kcal/kmol |
| A1; A2; A3 | 1.528e6; 2.778e7; 1000 | unidade corrigida: m³/(kmol s) |
| E1; E2; E3 | 17000; 20000; 15000 | cal/mol |
| R | 1.987 | deve ser cal/(mol K), não kcal/(mol K) |
| C iniciais | 0, 0, 0, 0 | kmol/m³, Tabela 3.3 |
| T inicial | 46.85 | °C |

O rótulo de `R` na Tabela 3.3 traz kcal/mol/K, mas o valor 1.987 exige cal/mol/K para combinar com as energias de ativação publicadas. A Tabela 3.4 rotula o prefator com minuto⁻¹ e omite m³. O artigo primário de Luyben explicita segundo⁻¹; o modelo em horas requer multiplicador **3600** nas taxas. Essa correção também é corroborada quantitativamente pela composição estacionária.

As entalpias satisfazem aproximadamente a identidade de Hess: `DeltaH1-DeltaH2=-200`, comparado a `DeltaH3=-205.5` kcal/kmol. A diferença é 5.5 kcal/kmol. Deve ser registrada como pequena inconsistência/possível arredondamento ou diferença de referência térmica, e não ser silenciosamente corrigida no baseline.

## 5. Auditoria numérica independente de equilíbrio

Fixando a temperatura em 160°C, valor aproximado da Figura 4.3, resolvendo os quatro balanços e usando os parâmetros publicados:

| Interpretação de Ai | xE | xB | xEB | xDEB |
|---|---:|---:|---:|---:|
| valores diretamente no modelo horário | 0.277886 | 0.715284 | 0.006795 | 0.000036 |
| valores por minuto, multiplicados por 60 | 0.145197 | 0.683688 | 0.150353 | 0.020763 |
| valores por segundo, multiplicados por 3600 | 0.005333 | 0.660910 | 0.280620 | 0.053137 |
| Matlab/Simulink na Tabela 4.1 | 0.0051 | 0.6607 | 0.2811 | 0.0531 |

Na terceira interpretação, as concentrações calculadas são `[0.03738085,4.63241640,1.96690815,0.37244803]` kmol/m³. As frações são definidas por `xi=Ci/sum(C)`, não por `Ci/rho1`. A soma dos Ci vale 7.00915 kmol/m³, que difere da densidade molar fixa usada no balanço térmico. Isso identifica outra aproximação que requer auditoria.

Este resultado é uma **reconstrução próxima do equilíbrio**, não uma reprodução exata do Simulink. O TFC não oferece a temperatura exata, o valor ajustado de Q nem a implementação que gerou a Tabela 4.1. Não se deve calibrar muitos parâmetros contra quatro números arredondados e chamar o ajuste de validação.

## 6. O que a calibração de Q pode estar compensando

O texto da página 46 informa que Q foi ajustado para aproximar Matlab e Aspen; não fornece o valor ajustado. Sob a equação literal em °C, `cp1=cv1` e o equilíbrio de 160°C calculado acima:

**Atualização após recuperar o backup Aspen:** a investigação em `thermal_unit_hypothesis.md` verificou que os quatro coeficientes publicados como capacidades caloríficas coincidem com h/T em Celsius dentro de 13 ppm. Não são valores independentemente verificados de derivada calorífica. O dever efetivo armazenado no Aspen é 9,087923 MW, confirmado pelos fluxos de entalpia e pelo registro do bloco. Essa evidência é mais específica do que a hipótese inicial de simples inconsistência de unidades.

- geração reacional: 16.873878 milhões de kcal/h;
- entalpia sensível de entrada: 26.823596 milhões de kcal/h;
- termo de saída: 21.868783 milhões de kcal/h;
- Q exigido pelo equilíbrio: **21.828692 milhões de kcal/h**, ou **25.369791 MW**.

Esse Q é calculado nesta pesquisa, não recuperado do TFC. O coeficiente térmico de entrada é 581766.446 kcal/(h K), versus 136679.891 na saída. Trocar a referência numérica de Celsius para Kelvin, sem modificar as entalpias de referência de forma consistente, muda o Q necessário em 121.575393 milhões de kcal/h. Isso mostra por que não se deve interpretar o Q ajustado como medição física de trocador.

Para a interpretação física alternativa, usar entalpias de espécie consistentes com uma referência comum e propriedades térmicas verificadas, mais transferência `Q=UA(T-Tsteam)`. Essa alternativa precisa de calibração/validação dinâmica independente; substituí-la agora mudaria a planta usada na comparação histórica. A hipótese de que Q compensa erro cinético, térmico ou dinâmica omitida não é identificável usando um único ponto estacionário. Exige residual temporal, variação de temperatura e medição/estimativa independente do dever térmico.

## 7. Informação química no sinal térmico

As duas alquilações liberam calor quase igual por mol de etileno consumido (27150 e 26950 kcal/kmol). Portanto a geração de calor observa fortemente o consumo total de etileno e tende a separar menos diretamente a formação desejada de EB e a indesejada de DEB. A transalquilação tem pequeno calor líquido. Isso é uma explicação física para investigar condicionamento ruim de certas combinações de estados, mas não substitui cálculo de observabilidade.

A análise independente de observabilidade desta pesquisa acrescentou uma ablação de consistência de Hess: usar DeltaH3=−200, mantendo o ponto nominal pelo reajuste correspondente de Q. Nessa ablação, o posto diferencial local em equilíbrio cai de 4 para 3. A pequena diferença de entalpia do modelo literal cria uma direção informativa muito fraca. Isso não constitui teorema de indistinguibilidade não linear global: fora do equilíbrio, derivadas e perturbações finitas podem recuperar informação. A conclusão pertinente é fragilidade do condicionamento da inferência térmica, não ausência absoluta de informação.

Perto de uma única temperatura, `Ai` e `Ei` aparecem pela combinação `ln(ki)=ln(Ai)-Ei/(RT)`. Estimar simultaneamente ambos sem excitação térmica torna o problema mal condicionado. Um fator multiplicativo local por reação, ou um único parâmetro de transferência térmica, é mais defensável que ajustar seis parâmetros de Arrhenius de uma só vez.

## 8. Baseline histórico e lacunas que impedem reprodução exata

Tabela 4.1:

| Grandeza | Luyben | Aspen | Matlab | FKE |
|---|---:|---:|---:|---:|
| xE | 0.0039 | 0.0039 | 0.0051 | 0.0050 |
| xB | 0.6568 | 0.6572 | 0.6607 | 0.6631 |
| xEB | 0.2891 | 0.2888 | 0.2811 | 0.2795 |
| xDEB | 0.0501 | 0.0500 | 0.0531 | 0.0523 |

Tabela 4.2 reporta erro da **composição**, sem unidade declarada: MAE=1.626e−5 e RMSE=0.000514. A Figura 4.5 usa composição molar. Não assumir que esses valores sejam erros de concentração em kmol/m³. A razão RMSE/MAE=31.6113 implica N≥1000 pela desigualdade RMSE≤√N MAE. É compatível com erro muito concentrado em poucas amostras ou diferença de normalização; não é impossível matematicamente. Faltam amostragem, séries e implementação para decidir.

Para este reator, o PDF não fornece números de Q/R/P0 do FKE, passo h, covariância inicial completa, semente, sinal de ruído, Jacobiana numérica/código, nem Kc/Ti do PI. Os ruídos especificados nas seções anteriores pertencem a outros processos. O método de sintonia é relé em malha fechada seguido de Ziegler-Nichols, mas Ku/Tu também não estão tabulados. Não há constante de tempo da válvula.

Para a válvula são recuperáveis: característica igual porcentagem, rangeabilidade 50, falha fecha, densidade 0.214175 g/cm³, ΔP=1 psi, vazão nominal 363.673 gal/min, abertura nominal 0.785175. A conversão de gal/min confirma 82.599 m³/h, portanto o rótulo ft³/h na p55 é inconsistente. A curva estática implica `fmax≈191.4066 m³/h` e `Cvmax≈390.0108` sob a equação líquida usada no TFC. “100% acima da capacidade” é recomendação de dimensionamento; a seleção comercial pode fornecer razão efetiva 2.317 em vez de exatamente 2. Uma curva estática não comprova dinâmica de atuador.

## 9. Revisão das métricas históricas

| Perturbação | Malha | IAE | ITAE | ISE |
|---|---|---:|---:|---:|
| +50% fB | fechada | 0.1476 | 0.3368 | 0.0102 |
| +50% fB | aberta | 0.0906 | 0.5625 | 0.0016 |
| −50% fC1 | fechada | 0.1467 | 0.3291 | 0.0102 |
| −50% fC1 | aberta | 0.3678 | 2.123 | 0.0267 |

Os gráficos incluem partida em t=0; o distúrbio ocorre em t=5 h e o horizonte termina em 10 h. Assim, maior erro inicial/overshoot em malha fechada pode piorar IAE e ISE, enquanto menor erro tardio melhora ITAE. O ruído do valor estimado também pode contribuir. Essa é uma hipótese compatível com os números e figuras, não a reprodução da trajetória. A frase do TFC que afirma superioridade em todos os critérios é mais ampla que os próprios números para +50% fB. Não corrigir números nem afirmar troca de colunas sem as séries.

## 10. Verificação com Luyben e limites da fonte

Luyben, W. L. (2011), *Design and control of the ethyl benzene process*, AIChE Journal 57(3), 655–670. DOI: https://doi.org/10.1002/aic.12289 . A página oficial confirma o artigo; o PDF oficial retornou 403 e o link de texto integral redirecionou ao resumo. Foi lida uma reprodução do artigo original em https://www.scribd.com/document/484990103/AIChEJournalVolume57issue32011doi10-1002-aic-12289WilliamL-Luyben-Designandcontroloftheethylbenzeneprocess1-pdf .

Na reprodução, pp. 656–657 confirmam taxas em kmol/(m³ s), as três reações, 200 m³, primeiro reator aproximadamente 434 K e 20 atm, e resfriamento por geração de vapor. Os parâmetros de troca são U=203 cal/(s m² K), A=602 m² e vapor a 414 K; dever informado 2.46e6 cal/s (~10.29 MW). Essa base física difere do Q ajustado inferido da equação literal do TFC. O modelo de planta considera reconversão do DEB no segundo reator; portanto menor DEB na saída do primeiro não é automaticamente menor custo global.

## 11. Verificação posterior com os arquivos recuperados

A busca pelos originais recuperou `TFC.zip` e o backup `AspenSimFiles/Ethylbenzene_walter/Ethylbenzene.bkp`. O agente de recuperação verificou nesse backup as taxas e a estequiometria acima. As vazões molares de saída são `[6.25720598,1055.62916,463.900029,80.364254]` kmol/h, total 1606.15065 kmol/h; correspondem a `x=[0.00389578,0.65724169,0.28882722,0.05003532]`, reproduzindo os números Aspen da Tabela 4.1. Esta é conferência dos resultados armazenados no backup, não uma nova execução de Aspen nesta sessão.

Os arquivos de Matlab/Simulink recuperados são exemplos de temperatura/FK e não o código final de cinco estados do reator. Q ajustado, passo, covariâncias e ganhos finais continuam ausentes. O arquivo `aspeneb.bkp` corresponde a uma versão anterior diferente e não deve substituir o backup associado ao TFC final.

**Conclusão verificável:** é possível construir um benchmark fiel à topologia e às equações, corrigindo unidades documentadas e declarando os ajustes. Foi confirmado o equilíbrio Aspen armazenado. Não é possível certificar identidade com as trajetórias FKE+PI de 2016 sem o código final. A prioridade técnica continua sendo auditar o modelo térmico antes de atribuir eventuais ganhos à IA ou a um estimador novo.
