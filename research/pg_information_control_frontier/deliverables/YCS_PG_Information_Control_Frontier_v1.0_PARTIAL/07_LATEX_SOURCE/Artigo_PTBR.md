---
title: "Limites de Informação e Decisão no Controle Preditivo Inferencial de um Reator Não Linear de Propilenoglicol"
author: "Walter Yanko de Aragão Brandão"
date: "20 October 2026"
lang: "pt-BR"
fontsize: 11pt
geometry: margin=24mm
colorlinks: true
---

# Resumo

Este estudo computacional investiga limites de informação e decisão em um modelo recuperado de reator de propilenoglicol de seis estados. Existe uma classe química exatamente indistinguível de dimensão dois sob capacidades caloríficas constantes e cinética de primeira ordem. Acrescentar realimentação térmica da camisa não a elimina. O posto funcional das capacidades caloríficas caracteriza uma ambiguidade suficiente remanescente; exemplos com propriedades dependentes de temperatura examinam a separabilidade prática. A suíte principal executou 5320 trajetórias, com 400 trajetórias de confirmação em sementes independentes e 18 verificações de grade. Na diluição nominal, separação inicial de produto de 0,8 kmol/m3 implica limite inferior de 0.060376 kmol h/m3 para o pior IAE entre dois mundos em 0,9 h. Há conflito decisório positivo em 51 dos 80 casos finitos examinados. Os ganhos médios adicionais por ambiguidade foram 0,63% e 0,66%, com intervalos pareados incluindo zero; compartilhar a correção com o preditor reduziu IAE em 39,91% frente à correção somente do estimador. Não se demonstrou superioridade sobre todo NMPC contínuo. As alternativas físicas não foram calibradas, e os números históricos ICAC não foram reproduzidos independentemente. Trata-se de manuscrito parcial de pesquisa, ainda não validado para submissão.
# Introdução

O controle inferencial de qualidade depende da informação carregada pelos sensores e das previsões usadas na escolha das ações. Reduzir o RMSE de concentração não garante diminuir a perda de controle em malha fechada. Este estudo audita um CSTR de propilenoglicol de seis estados antes de testar maior complexidade. Separam-se duas perguntas: existe ambiguidade química demonstrável quando somente temperaturas são medidas? Representar essa ambiguidade melhora o controle contra comparadores igualmente informados?

O manuscrito interno ICAC já descrevia gêmeos calorimétricos e conflitos de decisão. Seus percentuais permanecem evidência histórica. A branch e o arquivo completo de reprodução ICAC não estavam disponíveis. O presente manuscrito registra um núcleo computacional independente, com pendências explícitas para publicação.

# Trabalhos relacionados

Observabilidade e identificabilidade não lineares distinguem perda de informação de dificuldade numérica [@hermann1977; @villaverde2016]. Ambiguidade de concentração em reatores já aparece em estudos de cinética não monotônica e controle por saída [@schaum2007]. Sensibilidades empíricas revelam direções fracas sem demonstrar observabilidade estrutural global [@lall2002].

MHE com restrições e MPC por realimentação de saída possuem fundamentação consolidada [@rao2003; @rawlings2017]. Regret sob medições possui antecedentes com comparadores diferentes, em sistemas lineares [@goel2021]. Predição orientada à decisão e controle dual também antecedem a campanha [@elmachtoub2022; @klenske2016]. Preprints recentes investigam medições dependentes de entrada e risco de parâmetros latentes [@cao2026; @enwerem2026]. A contribuição candidata aqui é a classificação específica pela capacidade calorífica, com proveniência rastreável e experimentos de decisão no PG.

# Modelo físico do processo

As fontes são a dissertação de Brandão e seu modelo MATLAB recuperado [@brandao2019]. A reação é A+B para C; metanol M é tratado como inerte. O volume é constante, com saída regulada pelo nível. Usam-se kmol/m3, kelvin, horas e kJ:
$$v=F_A/\rho_A+F_B/\rho_B+F_M/\rho_M,\quad D=v/V,\quad
r=k_0\exp[-E/(R(T+0.183333333333))]C_A.$$
Os balanços são
$$\dot C_A=F_A/V-DC_A-r,\qquad\dot C_B=F_B/V-DC_B-r,$$
$$\dot C_C=-DC_C+r,\qquad\dot C_M=F_M/V-DC_M.$$
Definindo $W=\sum_i c_{p,i}C_i$ e $F_{cp}=F_Ac_{p,A}+F_Bc_{p,B}+F_Mc_{p,M}$:
$$Q=m_wc_{p,B}(T_a-T)[1-e^{-UA/(m_wc_{p,B})}],$$
$$\dot T=\frac{Q+F_{cp}(T_0-T)-\Delta H_r rV}{VW},\qquad
\dot T_t=\frac{m_wc_{p,B}(T_a-T_t)-Q}{\rho_BV_tc_{p,B}}.$$
Somente $T,T_t$ são medidas. A entrada otimizada é $m_w=q\,453.59237$ kmol/h; as alimentações atuais são conhecidas, sem antecipação de perturbações. Preserva-se a assimetria histórica: $T_t$ não aparece em $Q$.

A entalpia executável é -83736 kJ/kmol, enquanto a tabela da dissertação informa -91556.90. A conversão imperial arredondada e o deslocamento de Arrhenius são convenções preservadas para reprodução. O exemplo público de Fogler contém correção da entalpia com temperatura, mas utiliza outras condições operacionais [@fogler_examples]; não autoriza substituir constantes sem calibração.

Um caso didático relacionado utiliza cinética de primeira ordem com água em excesso e líquido não ideal [@chan2004]. Isso sustenta a aproximação cinética como benchmark, mas impede tratar apenas a calorimetria ideal como validação da equivalência física de inventários reais.

O benchmark de volume constante calcula a vazão volumétrica de saída pelas densidades das alimentações, mas não impõe equação de estado dependente da composição nem fechamento por volumes molares parciais a cada inventário candidato. Positividade representa admissibilidade no modelo, não admissibilidade física completa da mistura líquida. Restrições exatas adicionais de composição e volume intersectariam o subespaço invisível e poderiam reduzi-lo. Variação de volume pela reação e entalpia não ideal permanecem fora das reconciliações testadas.

## Alternativas físicas explícitas

M1H introduz consistência de Kirchhoff:
$\Delta H_r(T)=\Delta H_r(T_r)+\int_{T_r}^T(c_{p,C}-c_{p,A}-c_{p,B})\,d\theta$,
assumindo a entalpia histórica na temperatura nominal $T_r=332.333618020$ K. Essa referência não é conhecida independentemente. M1J acrescenta $Q=G(T_t-T)$ com armazenamento térmico da camisa. Escolhe-se $G=m_{w0}c_{p,B}[\exp(UA/(m_{w0}c_{p,B}))-1]$ para igualar a remoção estacionária nominal. Não se confunde UA de uma serpentina com condutância de uma camisa perfeitamente misturada.

M2L e M2Q adotam $c_{p,i}(T)=a_i+b_i(T-T_r)+c_i(T-T_r)^2$, com $a_i$ históricos. As inclinações relativas são (0.0015,0.0002,0.0025,0.0010) por K; as curvaturas relativas são (0.000010,0.000002,0.000016,-0.000003) por K ao quadrado. M2L anula as curvaturas. Entalpias sensíveis e de reação são integradas consistentemente. São modelos sintéticos de sensibilidade, sem calibração de propriedades; nenhum constitui o M1 fisicamente validado solicitado na missão integral.

# Arquiteturas de estimação e controle

B1 combina UKF de seis estados e preditor nominal. B2_estimator acrescenta fatores logarítmicos de cinética e troca térmica ao UKF, preservando o preditor nominal. B2_both transmite esses fatores estimados ao preditor. Nenhum recebe parâmetros verdadeiros. B0 é um PI documentado sobre concentração inferida, com ganhos 4 e 2 e antiwindup; não é reprodução de uma cascata histórica otimamente sintonizada.

B3_assumed_inventory impõe inventários iniciais nominais. B3_known_inventory recebe os inventários verdadeiros uma única vez e dispõe de informação adicional. Os estados reduzidos são $(C_C,T,T_t)$, com totais propagados pelos balanços de alimentação e diluição. B4 é MHE determinístico de seis passos, prior aproximado de chegada, sem variáveis de ruído de processo e orçamento de 18 avaliações. B5 usa estado atual verdadeiro somente como oráculo diagnóstico, mantendo parâmetros nominais no preditor.

P1 minimiza custo médio de três representantes. P2 minimiza seu maior regret. P3 combina essa regra com adaptação causal de parâmetros. P4 aplica ação robusta quando os representantes discordam em pelo menos 0,2 unidade nominal de refrigeração; caso contrário utiliza política nominal adaptada. Os representantes são o ponto do UKF e compensações calorimétricas de produto de mais/menos $0.4e^{-\int Ddt}$. Não constituem conjunto envolvente certificado nem amostragem posterior completa.

As variantes P5 mantêm controle nominal e acrescentam amostra inicial; quatro amostras periódicas; coleta por evento com cota quatro; atraso de três passos; ruído ampliado; ou até oito amostras frequentes. O desvio padrão de composição é 0,03 kmol/m3, ampliado para 0,15 no caso ruidoso. Inovações atrasadas são transportadas aproximadamente pela diluição, com incremento explícito de variância. Não há suavizador completo de medições fora de sequência. Pedidos por evento usam largura da crença e desacordo decisório disponíveis, sem observações futuras.

A política padrão enumera até 25 sequências de dois blocos: primeira ação por três passos, segunda por onze. Incrementos pertencem a cinco pontos entre -0,4 e 0,4. Todos compartilham $0.05\le q\le3$ e variação máxima 0,4; no cenário de saturação, o mesmo teto reduzido 1,3 vale para todos. A restrição amostrada é $T\le344.261111$ K. Ausência de plano conjuntamente viável ativa contingência explícita de menor violação prevista. Isso não estabelece segurança garantida.

O custo adimensional é
$$J=\sum_{j=1}^{14}\left[0.8\left(\frac{C_{C,j}-r_k}{2.295764605}\right)^2+
1000\left(\frac{\max(T_j-344.261111,0)}{160/1.8}\right)^2\right]
+0.2[(q_1-q_{\rm prev})^2+(q_2-q_1)^2].$$
Esse objetivo difere do IAE. B1_continuous otimiza o mesmo problema de dois blocos por SLSQP, iniciado na solução da grade. É um comparador local; não equivale ao NMPC histórico completo de horizonte 57 e seis movimentos.

# Metodologia experimental

O protocolo congelado prevê 14 cenários, 19 métodos e 20 sementes pareadas por combinação. Cada trajetória contém 60 intervalos de 0,015 h, totalizando 0,9 h. Incluem-se nominal, servo, erros cinético e térmico, inventários com sinais opostos, perturbação de alimentação, erro de capacidade calorífica, ruído correlacionado, perda de medição, saturação, perturbações combinadas, estado fora do conjunto inicial e referência inalcançável. As variantes físicas estruturais são analisadas separadamente do benchmark de controle M0.

Os desvios padrão iniciais do UKF são (0,15;0,8;0,4;0,3;0,5;0,5). A diagonal de Q é (2e-6;2e-5;2e-6;1e-7;0,015;0,006). Os ruídos térmicos possuem desvios (1,385;1,062)/1,8 K. Fatores adaptativos têm variância inicial 0,15 ao quadrado, variância de processo 1e-5 e limites [-0,5;0,5]. Usam-se alpha=0,5 e beta=2. Nenhuma sintonia utiliza desfechos reservados.

As sementes principais são 4100–4119; a confirmação 8100–8119 cobre quatro cenários declarados e cinco métodos. As sementes 101–103 avaliam uma grade mais densa; a semente 11 serve ao piloto de custo. Os ruídos são pareados entre métodos. O bootstrap reamostra sementes; para a suíte finita, cada semente é primeiro agregada entre cenários. A incerteza descreve essa suíte, sem representar uma população industrial. Três contrastes primários recebem ajuste de Holm; os demais permanecem exploratórios.

A planta usa RK4 com 12 subpassos, comparado ao DOP853 do SciPy com rtol 2e-11 e atol 1e-12. Predição usa três subpassos e filtro quatro. Estados físicos não são recortados. Reparos de positividade e covariância do estimador são contabilizados. Métricas escalares são recalculadas independentemente das trajetórias salvas. Os tempos pertencem a CPU Linux hospedada, sem certificação no Ryzen de destino.

# Parâmetros e condição inicial

| Parameter | Value | Unit |
| --- | --- | --- |
| V | 1.8918 | m3 |
| Vt | 1.1001 | m3 |
| UA | 30386 | kJ/(h K) |
| CpA | 146.54 | kJ/(kmol K) |
| CpB | 75.362 | kJ/(kmol K) |
| CpC | 192.59 | kJ/(kmol K) |
| CpM | 81.643 | kJ/(kmol K) |
| E | 75362 | kJ/kmol |
| R | 8.3192 | kJ/(kmol K) |
| k0 | 1.696e+13 | 1/h |
| DeltaH | -83736 | kJ/kmol |
| FA | 36.287 | kmol/h |
| FB | 453.59 | kmol/h |
| FM | 45.359 | kmol/h |
| mw0 | 453.59 | kmol/h |
| T0 | 297.04 | K |
| Ta | 288.71 | K |

Equilíbrio nominal: 0.607024732, 33.989102107, 2.295764605, 3.628486671, 332.333618020, 314.397585330.

# Escopo matemático e demonstrações

Os resultados seguintes descrevem a classe de modelos explicitada, sem estabelecer validação de uma instalação industrial. O tempo é medido em horas. Os mundos comparados compartilham alimentações conhecidas, parâmetros, referência, restrições de atuação e temperaturas iniciais medidas. As condições químicas iniciais pertencem ao domínio positivo aberto admitido pelo benchmark de seis estados, sem impor uma equação de estado validada da mistura. Restrições exatas adicionais de admissibilidade devem ser intersectadas com a classe construída e podem reduzir sua dimensão. Supõem-se existência e unicidade das soluções no horizonte considerado. As entradas podem depender causalmente das temperaturas medidas. As afirmações de informação exata usam medições sem ruído ou acoplamento com a mesma realização aditiva de ruído.

## Proposição 1: classe de equivalência calorimétrica

Considere $\dot c=F/V-D(t)c+\nu r$, com $\nu=(-1,-1,1,0)^T$ e $r=k(T)C_A$. Suponha que a composição afete a dinâmica térmica somente por $C_A$ e $W(T,c)=\sum_i c_{p,i}(T)C_i$. A troca térmica pode ser qualquer função localmente Lipschitz de $T,T_t,u$, independente das demais coordenadas químicas. A entalpia de reação pode depender da temperatura.

Para capacidades caloríficas constantes, dois estados iniciais que satisfaçam
$$\delta C_A=0,\quad\delta T=\delta T_t=0,\qquad
c_{p,B}\delta C_B+c_{p,C}\delta C_C+c_{p,M}\delta C_M=0$$
produzem temperaturas idênticas sob toda entrada comum admissível, enquanto ambas as trajetórias permanecerem no domínio físico. Suas diferenças químicas obedecem a
$$\delta c(t)=e^{-\int_0^tD(s)\,ds}\delta c(0).$$

Demonstração. A igualdade de $C_A,T$ implica igualdade das taxas de reação. A subtração dos balanços de espécies deixa somente diluição homogênea. A combinação calorimétrica das diferenças permanece nula; portanto as derivadas térmicas coincidem. A unicidade das soluções completa a demonstração. Em realimentação causal, históricos idênticos produzem ações seguintes idênticas. Existem duas direções químicas independentes nesse núcleo. Os seis estados livres não podem ser reconstruídos integralmente; o subsistema que produz temperaturas possui no máximo quatro coordenadas $(C_A,W,T,T_t)$. A construção é suficiente para demonstrar indistinguibilidade; não caracteriza necessariamente todos os pares indistinguíveis.

O resultado permanece com troca térmica recíproca entre camisa e reator. Portanto a ausência de realimentação de $T_t$ não explica, isoladamente, a ambiguidade química bidimensional.

## Proposição 1b: posto funcional das capacidades caloríficas

Defina
$$\mathcal S=\operatorname{span}\{(c_{p,B}(T),c_{p,C}(T),c_{p,M}(T)):T\in\mathcal I\}.$$
Toda diferença com $\delta C_A=0$ e $(\delta C_B,\delta C_C,\delta C_M)\in\mathcal S^\perp$ admite a construção anterior. A dimensão desse conjunto é $3-\dim\mathcal S$.

Demonstração. A diferença de capacidade térmica é nula em toda temperatura de $\mathcal I$. As diferenças de espécies recebem o mesmo fator escalar de diluição. A demonstração anterior permanece válida, inclusive com entalpia de reação e entalpias sensíveis da alimentação dependentes de temperatura. Capacidades constantes dão posto um. Funções afins por espécie têm posto no máximo dois, deixando ao menos uma direção invisível. Funções quadráticas independentes podem eliminar esse núcleo específico. Sua eliminação NÃO demonstra observabilidade não linear completa: podem restar outras simetrias, estados singulares e baixa sensibilidade.

Uma consequência para instrumentação: uma medição química escalar $a^Tc$ resolve o produto na classe de equivalência apenas se
$$\ker(a^T|_{\mathcal N})\subseteq\ker(e_C^T|_{\mathcal N}),$$
onde $\mathcal N$ é o subespaço químico invisível. Medir $C_C$ satisfaz o requisito; medir uma concentração arbitrária pode não satisfazê-lo. Conhecer $C_A+C_C$ também permite obter produto quando $C_A$ é identificado, mas seu valor inicial é informação adicional.


## Proposição 1c: entrada constante não informativa e teste local no quociente

Para M0 sob entradas constantes, defina $A=C_A$, $W=\sum c_{p,i}C_i$,
$q=F_A/V$, $c=F_{cp}/V$, $n=c_{p,C}-c_{p,A}-c_{p,B}$,
$a(T)=[Q(T)+F_{cp}(T_0-T)]/V$ e $b(T)=-\Delta H_r k(T)$.
Então
$\dot A=q-(D+k)A,\quad\dot W=c-DW+nkA,\quad
g=\dot T=(a+bA)/W.$
Num ponto com $\dot A=0$ e $a+bA=0$, perturbações suficientemente pequenas e arbitrárias em B, C e M mantêm A e ambas as temperaturas constantes sob a mesma entrada fixa. Elas alteram W e decaem por diluição. Há, portanto, três direções químicas invisíveis nesse experimento sem excitação, embora apenas duas pertençam à família calorimétrica válida para todas as entradas. A excitação pode distinguir a direção adicional. Não se trata de simetria tridimensional válida para toda entrada.

Um teste local suficiente usa os gradientes de $T,T_t,L_fT,L_f^2T$ no quociente $(A,W,T,T_t)$. O menor dois por dois referente a $(A,W)$ é
$\det\begin{bmatrix}g_A&g_W\\(L_fg)_A&(L_fg)_W\end{bmatrix}
=-\frac{b[bq+(D+k)a]}{W^3}
+\frac{(a+bA)[-ba_T+bc+ab_T-ank]}{W^4}.$
Obtém-se a expressão diferenciando
$L_fg=\frac{bq+Da-bkA}{W}
+\frac{(a+bA)(a_T+b_TA-c-nkA)}{W^2}.$
Menor não nulo é condição suficiente de posto quatro nesse teste local do quociente. Ele se anula no equilíbrio nominal com entrada constante. O valor zero isolado não demonstra inobservabilidade; a construção explícita de trajetórias invariantes acima demonstra esse caso particular. O sistema de seis estados continua com posto máximo quatro sob a simetria válida para todas as entradas. As avaliações de precisão arbitrária são cálculos locais de apoio, não um teorema global de posto.

## Proposição 2: limites de estimação e rastreamento

Se duas concentrações possíveis no instante $t$ têm separação $\Delta(t)$, qualquer estimador com o mesmo histórico informacional fornece a mesma estimativa nos dois mundos:
$$\max_i|\hat C_C(t)-C_C^{(i)}(t)|\geq\Delta(t)/2.$$
A desigualdade triangular demonstra o resultado. O ponto médio atinge o limite quando somente esses dois valores são possíveis.

A mesma desigualdade vale substituindo a estimativa por uma referência comum. A integração fornece
$$\max_i\operatorname{IAE}_i(H)\geq\frac12\int_0^H\Delta(t)\,dt.$$
Com diluição constante e separação inicial $\Delta_0$, o lado direito é $\Delta_0(1-e^{-DH})/(2D)$. Esse é um limite do pior erro de rastreamento, não do regret em relação a um controlador informado do estado. O oráculo também pode enfrentar perda transitória inevitável. A queda do limite por diluição representa renovação física do inventário, não informação fornecida pelo sensor.

Para entrada fixa em malha aberta e registros gaussianos com mesma covariância conhecida $\Sigma$, a divergência KL é $\frac12(\mu_1-\mu_2)^T\Sigma^{-1}(\mu_1-\mu_2)$. O risco esperado absoluto no problema de dois mundos é limitado inferiormente por $\Delta(1-\mathrm{TV})/2$. Pinsker fornece $\Delta\max(0,1-\sqrt{\mathrm{KL}/2})/2$. A fórmula não se transfere automaticamente para realimentação adaptativa ruidosa em que as ações modificam a separação química. Não se reivindica aqui um limite estocástico industrial.

## Proposição 3: ambiguidade de estado e conflito decisório

Considere custos contínuos $J_i$ em um conjunto comum, compacto e não vazio de sequências admissíveis $\mathcal U$. Escreva $J_i^*=\min_{\mathcal U}J_i$. Então
$$\mathcal R^*=\min_{u\in\mathcal U}\max_i[J_i(u)-J_i^*]$$
é zero se, e somente se, os conjuntos de minimizadores possuem interseção não vazia. Se não possuem, $\mathcal R^*>0$.

Demonstração. Os regrets são não negativos. Um minimizador comum os anula. Reciprocamente, continuidade e compacidade garantem que o mínimo do máximo seja atingido. Se ele é zero, a decisão minimiza todos os custos. Logo, minimizadores sem interseção implicam valor estritamente positivo. Uma separação química grande pode coexistir com regret nulo quando todos os mundos preferem a mesma ação, inclusive saturação comum.

Quando as restrições dependem do mundo, os ótimos individuais devem respeitar seus conjuntos declarados e a decisão robusta pertence à interseção. Interseção vazia significa inviabilidade, não regret finito. O cálculo numérico marca explicitamente a ausência de candidatos conjuntamente viáveis.


## Proposição 3b: quando representar a ambiguidade não altera a ação de custo esperado

Nos gêmeos exatos de PG com a mesma alimentação conhecida, a vazão de refrigeração não altera a diluição. Para qualquer plano comum, escreva $C_C(t;u,\delta)=C_C(t;u,0)+d(t)\delta$, onde $d(t)=e^{-\int_0^tD(s)ds}$ independe do plano de refrigeração. Suponha offsets com média zero, representantes fisicamente admissíveis, restrições dependentes apenas das temperaturas e ações comuns e custo de tracking quadrático ponderado, acrescido de custos térmicos e de atuação comuns. Então
$\mathbb E_\delta J_\delta(u)=J_0(u)+\mathbb E[\delta^2]\sum_j w_jd(t_j)^2.$
O último termo independe de $u$. Logo, os conjuntos de minimizadores das políticas nominal e de custo esperado são exatamente iguais, tanto na grade quanto na classe contínua.

Demonstração. Expanda os quadrados e tome a média. O termo cruzado se anula pela média zero; os demais custos e restrições são compartilhados. É um caso de equivalência de certeza, não um teorema universal de robustez. Perdas não quadráticas, diluição dependente da ação, truncamento assimétrico de crenças, restrições físicas adicionais ou mudança da política informacional podem invalidá-lo. No P1 de três representantes simétricos, a proposição prevê benefício de controle nulo, exceto por exclusões de admissibilidade e desempates numéricos. Ela refuta a ideia de que apenas incluir esses mundos necessariamente melhora este NMPC quadrático.

## Proposição 4: limite quantitativo condicional

Para dois custos $\mu$-fortemente convexos no mesmo conjunto convexo, com minimizadores $u_1^*,u_2^*$,
$$\mathcal R^*\geq\frac{\mu}{8}\|u_1^*-u_2^*\|^2.$$
Convexidade forte e otimalidade de primeira ordem fornecem $J_i(u)-J_i(u_i^*)\geq\mu\|u-u_i^*\|^2/2$. Pelo menos uma distância é maior ou igual à metade da distância entre minimizadores. Isso demonstra o limite. A convexidade também impede ganho por randomização sob o máximo dos custos esperados. Essas condições NÃO foram demonstradas para a otimização não linear de PG; nenhum regret numérico do PG é certificado por essa expressão.

Sob indistinguibilidade exata durante todo o horizonte, uma política causal determinística e sem ruído realiza a mesma sequência em todos os mundos. Se suas sequências pertencem a $\mathcal U$, seu pior regret é pelo menos o valor minimax nesse conjunto. Uma grade finita fornece resultado exato somente dentro da grade. Se os custos ótimos individuais forem mantidos nos ótimos contínuos, restringir apenas as decisões fornece limite superior do minimax contínuo. Aqui tanto as decisões quanto os ótimos individuais são restritos à grade; o resultado não possui, em geral, relação unilateral de limite com o regret minimax contínuo. Não é limite inferior válido para todo controlador físico. Se medições futuras distinguirem os mundos, regret de sequências abertas não equivale ao valor da política adaptativa ótima.

## Antecedentes e contribuição possível

Observabilidade, detectabilidade, limites de risco de dois pontos, minimax regret e estimação orientada à decisão já são conhecidos. As demonstrações são especializações elementares, sem pretensão de uma lei universal nova. A contribuição específica candidata é a classificação pelo posto funcional de Cp, aplicada ao modelo PG rastreável, e a ligação auditada entre formulação física, instrumentação e decisão. Ainda são necessárias revisão abrangente de originalidade e propriedades físicas calibradas.

# Resultados numéricos

As comparações abaixo provêm da execução. Melhoria positiva favorece o primeiro método. O IC da suíte reamostra 20 sementes pareadas e é condicional aos cenários escolhidos.

| Candidate | Baseline | Gain (%) | IAE diff. | CI lower | CI upper | Holm p |
| --- | --- | --- | --- | --- | --- | --- |
| P2 regret | B1 ukf | 0.63459 | 0.0008501 | -0.0010082 | 0.0028354 | 0.41857 |
| P3 adaptive regret | B2 both | 0.65721 | 0.00057897 | -0.00020713 | 0.0014596 | 0.41857 |
| B2 both | B2 estimator | 39.912 | 0.058515 | 0.056526 | 0.060461 | 3.1106e-22 |

## Experimentos físicos e informacionais

| variant | Max dT (K) | Product decay error |
| --- | --- | --- |
| M0 historical | 5.6843e-14 | 5.8647e-12 |
| M1H Kirchhoff hypothesis | 0 | 5.8634e-12 |
| M1J mixed jacket hypothesis | 0 | 5.8616e-12 |
| M2L linear cp hypothesis | 1.0307e-05 | 3.3766e-07 |
| M2Q quadratic cp hypothesis | 9.3374e-06 | 3.1641e-07 |

## Posto local dependente da entrada e gêmeos remanescentes com propriedades afins

| T | determinant | Derivative error | Rank 4 test |
| --- | --- | --- | --- |
| 315 | 3.1461 | 3.1924e-58 | True |
| 325 | 60.576 | 1.0753e-57 | True |
| 332.33 | 8.1092e-58 | 1.8484e-57 | False |
| 340 | -893.84 | 5.2572e-57 | True |
| 348 | -5623.8 | 4.4607e-57 | True |


| Unexcited dT | Excited dT | Affine twin dT | Affine rank | Quadratic rank |
| --- | --- | --- | --- | --- |
| 0 | 0.037972 | 0 | 2 | 3 |

## Métricas absolutas selecionadas

| scenario | method | IAE | RMSE CC | Tmax | fallback |
| --- | --- | --- | --- | --- | --- |
| combined | B1 continuous | 0.22045 | 0.13055 | 332.33 | 0 |
| combined | B1 ukf | 0.23055 | 0.13057 | 332.35 | 0 |
| combined | B2 both | 0.079746 | 0.076413 | 337.06 | 0 |
| combined | B2 estimator | 0.25361 | 0.077038 | 332.33 | 0 |
| combined | B4 mhe | 0.19172 | 0.11811 | 332.58 | 0 |
| combined | P2 regret | 0.2325 | 0.13086 | 332.33 | 0 |
| combined | P3 adaptive regret | 0.078689 | 0.076353 | 337.17 | 0 |
| inventory plus | B1 continuous | 0.061569 | 0.12231 | 332.61 | 0 |
| inventory plus | B1 ukf | 0.060387 | 0.12225 | 332.44 | 0 |
| inventory plus | B2 both | 0.061797 | 0.12223 | 332.93 | 0 |
| inventory plus | B2 estimator | 0.060544 | 0.12204 | 332.44 | 0 |
| inventory plus | B4 mhe | 0.060212 | 0.12274 | 332.43 | 0 |
| inventory plus | P2 regret | 0.059559 | 0.12216 | 332.37 | 0 |
| inventory plus | P3 adaptive regret | 0.062655 | 0.12219 | 332.89 | 0 |
| kinetic | B1 continuous | 0.16428 | 0.081211 | 332.33 | 0 |
| kinetic | B1 ukf | 0.19263 | 0.083904 | 332.33 | 0 |
| kinetic | B2 both | 0.044861 | 0.015328 | 333.99 | 0 |
| kinetic | B2 estimator | 0.23438 | 0.016884 | 332.33 | 0 |
| kinetic | B4 mhe | 0.17914 | 0.073232 | 332.33 | 0 |
| kinetic | P2 regret | 0.1836 | 0.083579 | 332.33 | 0 |
| kinetic | P3 adaptive regret | 0.043723 | 0.015313 | 333.85 | 0 |
| nominal | B1 continuous | 0.0032395 | 0.011244 | 332.61 | 0 |
| nominal | B1 ukf | 0.0016471 | 0.01124 | 332.44 | 0 |
| nominal | B2 both | 0.0075155 | 0.01487 | 332.93 | 0 |
| nominal | B2 estimator | 0.0014342 | 0.014862 | 332.44 | 0 |
| nominal | B4 mhe | 0.0016341 | 0.012091 | 332.43 | 0 |
| nominal | P2 regret | 0.0014446 | 0.011249 | 332.37 | 0 |
| nominal | P3 adaptive regret | 0.006065 | 0.014836 | 332.89 | 0 |

## Confirmação independente

| Candidate | Baseline | Gain (%) | CI lower | CI upper |
| --- | --- | --- | --- | --- |
| P2 regret | B1 ukf | 1.6012 | -0.0009961 | 0.00542 |
| P3 adaptive regret | B2 both | 0.39846 | -0.0004547 | 0.0010219 |
| B2 both | B2 estimator | 59.47 | 0.087979 | 0.093852 |
| B2 estimator | B1 ukf | -10.663 | -0.018306 | -0.011301 |
| B2 both | B1 ukf | 55.148 | 0.07268 | 0.079613 |
| P3 adaptive regret | B1 ukf | 55.327 | 0.07309 | 0.07969 |

## Resultados adversos preservados

| scenario | Candidate | Gain (%) | CI lower | CI upper |
| --- | --- | --- | --- | --- |
| correlated noise | B0 PI | -592.59 | -0.012046 | -0.0090047 |
| saturation | P5 noisy | -453.52 | -0.011561 | -0.0035668 |
| saturation | B2 both | -414.81 | -0.0099462 | -0.00387 |
| correlated noise | B2 both | -398.96 | -0.010116 | -0.0040413 |
| dropout | P5 noisy | -381.22 | -0.0093647 | -0.0033412 |
| nominal | P5 noisy | -381.22 | -0.0093315 | -0.0032564 |
| correlated noise | P4 hybrid | -360.46 | -0.0095007 | -0.0035447 |
| nominal | B2 both | -356.27 | -0.0083201 | -0.0034261 |
| correlated noise | P3 adaptive regret | -335.06 | -0.0088984 | -0.0031583 |
| dropout | B2 both | -324.64 | -0.0077757 | -0.0030081 |
| saturation | P4 hybrid | -309.17 | -0.0078871 | -0.0026648 |
| dropout | B0 PI | -305.83 | -0.0063577 | -0.003696 |

## Interpretação dos resultados executados

P2 apresentou ganho médio adicional de 0.635% frente a B1; diferença absoluta pareada de IAE 0.000850, com IC95% [-0.001008, 0.002835] kmol h/m3. P3 acrescentou 0.657% frente ao preditor adaptado, com IC95% [-0.000207, 0.001460] em unidades absolutas de IAE. Ambos incluem zero. A confirmação independente também não estabeleceu benefício adicional. A meta exploratória de 10% para controle por ambiguidade não foi atingida.

Compartilhar as estimativas paramétricas causais com o preditor reduziu o IAE médio de 0.146611 para 0.088095, redução de 39.91%. É atribuição dentro desta suíte e destes modelos, não demonstração de controlador universal novo. A adaptação somente do estimador piorou o IAE frente a B1, apesar de RMSE médio menor.

P1 e B1 possuem IAE exatamente igual em toda a suíte principal, consistente com a proposição de custo esperado. A grade de nove pontos produziu diferenças médias adversas para P2 nos três cenários de sensibilidade, com apenas três sementes; não resgatou a hipótese positiva.

A referência informada do estado tem RMSE zero, porém IAE médio 0.146790, contra 0.133960 de B1. Ela mantém preditor nominal e objetivo quadrático de horizonte finito; portanto não é limite inferior certificado do IAE atingível. É contraexemplo explícito à suposição de que RMSE menor garante tracking melhor.

Uma amostra química inicial reduziu o IAE médio de inventory-plus em 23.33%. Quatro amostras periódicas deram o mesmo IAE nesse cenário e RMSE discretamente menor. Na suíte completa com mismatch, as políticas de amostragem implementadas não melhoraram o IAE médio. Isso é desempenho realizado dos algoritmos, não valor ótimo negativo da informação gratuita: uma política otimamente projetada poderia ignorar informação opcional adicional.

O PI fixo obteve tracking médio favorável, mas alcançou temperatura amostrada máxima de 362.542 K, excedendo o limite do estudo em 18.281 K. Seu ganho bruto de IAE falha no critério de segurança. B1_continuous registrou falha do solver em 1.530% das decisões e acionou a contingência prevista. Ausência de aborto de trajetória não equivale à ausência de falhas do otimizador ou de violações térmicas.

Os dados não estabelecem vencedor uniforme nem ganho substancial adicional de engenharia por representar ambiguidade. Sustentam um resultado informacional específico do modelo, a ablação útil da correção do preditor e a falsificação de interpretações simplistas de desempenho.

# Ablação, falsificação e interpretação

As comparações com a mesma informação separam decisão pontual e por representantes, correção somente do estimador e compartilhamento com o preditor, além de grade mais densa. Inventário exato e amostragem química fornecem informação adicional; seu eventual ganho não pode ser atribuído apenas à sofisticação algorítmica.

O resultado estrutural persiste ao substituir a serpentina assimétrica por camisa recíproca mantendo capacidades caloríficas constantes. A dependência sintética de propriedades pode desfazer a compensação específica entre duas espécies, mas as diferenças térmicas podem permanecer pequenas diante do ruído. O mapa numérico utiliza uma grade de estados iniciais, não pontos estacionários fisicamente viáveis. Para ruído gaussiano independente, a Fisher correspondente é o produto da sensibilidade transposta pela sensibilidade; seus valores singulares não certificam cobertura posterior.

A proposição do custo esperado fornece um caso nulo mais forte: gêmeos exatos e simétricos acrescentam apenas um termo de variância independente do plano ao custo quadrático. P1 não possui vantagem teórica na ação sobre a política pontual nessas condições. A auditoria suplementar verifica a identidade em nove combinações de horizonte e referência.

Regret positivo na grade demonstra conflito nessa classe. Seu valor minimax não limita inferiormente todo controlador causal. Um oráculo informado do estado pode reduzir perda, mas referências inalcançáveis e limites de refrigeração permanecem. Preserva-se a expectativa experimental inicialmente refutada: diferença térmica de 9.516165278e-7 K não ultrapassou o corte arbitrário 1e-6 K. A verificação de implementação foi substituída por identidade exata de capacidade térmica, sem exigir resultado favorável na separabilidade científica.

# Limitações e condição para publicação

Os números históricos 0.951143, 0.850912, 0.358768 e 14.60% possuem fontes documentais identificadas, mas seus protocolos não foram reexecutados. O NMPC de dois blocos, PI fixo e MHE curto desta campanha não representam os melhores baselines disponíveis. Permanecem horizontes maiores, otimização contínua de seis movimentos, sintonia sistemática em desenvolvimento, outras variáveis químicas medidas e stress tests fechados nas famílias físicas.

Além do menor explícito de Lie no quociente M0, não foram concluídos mapas completos de derivadas de Lie, calibração de limites estatísticos práticos, dinâmica real de analisadores, segurança entre amostras, margens rigorosas de recuperação e tempos no Ryzen. A covariância atribuída ao MHE vem da aproximação UKF de chegada; sua cobertura é apenas diagnóstica. Não se informa NEES completo porque os históricos de covariância completa não foram salvos. Tempos decisórios excluem parte da programação das amostras; tempos totais dos episódios estão registrados. Não se afirma produção dentro de especificação nem perda econômica, pois não foram definidos limites comerciais ou preços. Trata-se de simulação, sem ensaio industrial.

O artigo ainda não está pronto para submissão como demonstração de um controlador superior. O caminho defensável é a classificação estrutural e a auditoria reproduzível de decisão, após validação de propriedades físicas, revisão mais abrangente de originalidade e revisão técnica independente.

# Conclusões

O modelo recuperado impõe um limite informacional específico que não desaparece com a troca da arquitetura do estimador. Realimentação da camisa é insuficiente para removê-lo quando as capacidades caloríficas são constantes. A importância para o controle depende do objetivo, da viabilidade e da classe de ações. Os dados documentam as comparações executadas e seus casos negativos, sustentando uma contribuição computacional delimitada e mantendo explícita a incompletude da missão integral.

# Auditoria das conclusões

| Questão | Classe de evidência | Conclusão |
| --- | --- | --- |
| Q1 | Demonstrada matematicamente | M0 possui classe química bidimensional indistinguível; seis estados livres não são completamente observáveis. |
| Q2 | Parcialmente sustentada | A ambiguidade com Cp constante persiste com entalpia consistente e camisa recíproca; M1 físico calibrado permanece ausente. |
| Q3 | Demonstrada matematicamente | O núcleo suficiente é ortogonal ao espaço funcional de CpB, CpC e CpM, com diferença em CA igual a zero. |
| Q4 | Demonstrada matematicamente | Metade da separação limita o erro instantâneo no problema de dois mundos; o limite integrado é distinto. |
| Q5 | Sustentada experimentalmente | Custos na classe finita determinam quando a ambiguidade altera ações; não há certificado de ótimo contínuo global. |
| Q6 | Sustentada experimentalmente | Contraexemplos executados contradizem a confiabilidade geral: menor RMSE, inclusive zero, pode acompanhar IAE maior. |
| Q7 | Sustentada experimentalmente | O compartilhamento com o preditor reduziu IAE médio em 39,91% contra correção somente do estimador, com confirmação independente. |
| Q8 | Inconclusiva | Ganhos adicionais de 0,63%/0,66% possuem IC incluindo zero; a meta exploratória de 10% não foi atingida. |
| Q9 | Sustentada experimentalmente | Regimes adversos são preservados nas tabelas e em contrasts.csv. |
| Q10 | Parcialmente sustentada | Somente os esquemas declarados de medição de CC foram testados; frequência globalmente ótima não foi estabelecida. |
| Q11 | Demonstrada matematicamente | Os limites para gêmeos exatos independem da arquitetura do estimador sob as hipóteses declaradas. |
| Q12 | Parcialmente sustentada | A prova transfere para a mesma estrutura de diluição, cinética e calorimetria; ganhos numéricos não se generalizam automaticamente. |

# Figuras dos dados executados

![Figure 1. Physical process and available information](figures/Figure_01.png)

![Figure 2. Distinct chemical inventories, identical historical thermal outputs](figures/Figure_02.png)

![Figure 3. Finite-horizon sensitivity map (initial-state grid, not equilibrium map)](figures/Figure_03.png)

![Figure 4. Singular spectra; a numerical floor does not prove observability](figures/Figure_04.png)

![Figure 5. One shared measurement stream: estimation error and two-world bound](figures/Figure_05.png)

![Figure 6. Estimation error and tracking loss across fixed scenarios](figures/Figure_06.png)

![Figure 7. World-conditioned and minimax-regret actions (finite action class)](figures/Figure_07.png)

![Figure 8. Decision ambiguity versus prior width and prediction horizon](figures/Figure_08.png)

![Figure 9. Servo tracking; paired seed 4100](figures/Figure_09.png)

![Figure 10. Regulatory response to known current feed disturbance; paired seed 4100](figures/Figure_10.png)

![Figure 11. Concentration and temperature under hidden kinetic mismatch](figures/Figure_11.png)

![Figure 12. Actuation and sampled thermal constraint under combined perturbations](figures/Figure_12.png)

![Figure 13. Finite-suite contrasts: positive differences favor the candidate](figures/Figure_13.png)

![Figure 14. Value of additional chemical measurements: inventory-plus scenario](figures/Figure_14.png)

![Figure 15. Tracking, sampled safety, effort and computing trade-offs](figures/Figure_15.png)

![Figure 16. Regime map: favorable and adverse mean differences](figures/Figure_16.png)
# Referências

