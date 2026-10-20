---
title: "Relatório técnico estendido: PG Information and Control Frontier — núcleo parcial"
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


# Auditoria da recuperação

# Recovery audit and historical status

Reference date: 20 October 2026. Repository default main was f4444d4c238291b8633743930249ee387ad94541.
New campaign starts from d2610a0723cbbaf00d3f4559242ba0efafb67771, which preserves the Darwin/thesis sources.

| Material | Recovery | Scope |
|---|---|---|
| Dissertation, Dissertacao_WalterYanko.pdf | Text read, pp.38–42 | Original balances, sensors, heat exchange and parameter table. 92-page PDF; not all pages reread. |
| modeloCT.m | Full original source recovered | Literal six-state historical dynamics |
| modeloFun_KF.m, NMPC_Fmincon.m, model/observer archive | Present in traced Git tree | Some prior audit content and NMPC reconstruction read; original MATLAB runtime not executed |
| Simulink package | Filename located, bytes unavailable locally | No Simulink execution |
| Relatorio_CSTR_Propilenoglicol.pdf | Relevant physical and attribution pages read | Historical values, units, seeds and caveats established |
| ICAC_Manuscrito_PT.pdf | Full five-page manuscript read | Historical twin and decision claims |
| research/icac-information-decision | Absent from live branch listing; commit search found no ICAC match | Code and full raw reproduction unavailable |
| PG C01–C14 | Timeline in Relatorio_Campanhas_PG_EB_Arioston.pdf read | Some C02/C03/C04/C12 code survives on beyond branch; no full 14-campaign replay |
| Darwin complete/thesis | Code and source manifest recovered from Git | Existing outputs are inherited evidence, not new execution |
| Darwin reduced branch | Audit-only checkpoint recovered | It explicitly reports zero new trajectories; not a completed reduced-model campaign |
| PG_Darwin_Reduced_Pilot_v0.1 | Report read; package identified | Independent PI/EKF pilot, tabulated variant; not equivalent to historical NMPC |
| PG Model Fidelity v0.8 | Current RESULTADOS.md v8 read | 1792 reported episodes, oracle parameter interpolation; not causal online identification |
| New frontier | Independent implementation with parity test | Its numbers are not substitutions for the historical protocols |

| Historical result | Reported value | New exact reproduction | Divergence / status |
|---|---|---|---|
| ICAC twin product gap | 0.426449 kmol/m3 | Not reproduced at that historical endpoint | Construction/protocol raw files inaccessible; new .4/.8 twin experiments use declared different initial conditions |
| Instantaneous lower bound | 0.213225 kmol/m3 | Analytic half-gap rule verified; rounded historical scalar inherited | 0.426449/2=0.2132245 before rounding |
| Nominal predictor hidden mismatch IAE | 0.951143 kmol h/m3 | Not rerun | Original 6 h, 400-step protocol differs from new 0.9 h episodes |
| Estimator-only correction IAE | 0.850912 | Not rerun | Source: PG report pp.55–57; 20 seeds 270201–270220 |
| Estimator+predictor correction IAE | 0.358768 | Not rerun | Same historical mismatch contrast; no new historical validation claim |
| ICAC B1 relative IAE | -14.60% | Not rerun | Manuscript reports six holdout seeds, different horizon/objective; not pooled with new data |

## Physical changes
The table's reaction heat is -91556.90 kJ/kmol; the executable uses -36000 Btu/lbmol,
converted in the recovered archive to -83736 kJ/kmol. M0 uses the latter. The historical
Fahrenheit +460 Arrhenius convention becomes Kelvin +0.183333333333.
Replacing it silently by exact absolute temperature would change the benchmark.

M1H adds a Kirchhoff correction with an ASSUMED reference enthalpy at nominal T.
This is thermodynamically consistent within the chosen ideal-mixture model but is not
a physically calibrated reconciliation. M1J adds a reciprocal lumped jacket, with
conductance selected to match the original nominal stationary coil duty.
M2L and M2Q use declared synthetic slopes/curvatures of species Cp(T). They are
sensitivity/falsification families, not measured property correlations.

The initial test run had 17 passes and one failed effect-size expectation. The full record
and scientific interpretation are preserved in initial_test_failure.md.

## Unexecuted central requirements
Exact historical C08/ICAC replay; all C01–C14 raw audits; validated physical-property M1;
full continuous 57-step/6-move strong baseline; fully tuned MHE; CPU timing on the target
Ryzen; prospective Lie-derivative symbolic rank sweep; independent human theoretical review.
These gaps prohibit labeling the entire requested v1.0 FINAL complete.

## Mixture admissibility gap

The benchmark uses constant volume and feed-based volumetric outflow without a separately validated mixture equation of state or partial-molar-volume constraint. Positive concentrations are admissible to M0 but do not alone certify real-liquid composition admissibility. Nonideal mixture enthalpy, reaction volume change and exact composition-volume constraints remain uncalibrated. Their influence must be assessed before making a physical impossibility claim.

# Revisão bibliográfica crítica

# Critical literature review — 20 October 2026

This is a targeted, source-verified review, not an exhaustive systematic review.
No worldwide novelty claim is justified by this search. Publisher metadata, author-hosted
manuscripts and institutional records were preferred. Paywalls and inaccessible pages were recorded.

| Topic | Verified antecedent | Relation and limit of the present contribution |
|---|---|---|
| Nonlinear observability | Hermann and Krener (1977), DOI 10.1109/TAC.1977.1101601 | Local rank conditions are established. Here exact PG symmetry is proved directly; finite numerical rank is not called structural proof. IEEE page had a robot gate. |
| Reactor indistinguishability | Schaum, Moreno, Díaz-Salgado and Alvarez, IFAC DYCOPS 2007 | Nonmonotone kinetics already produce concentration ambiguity with thermal sensing. Our PG construction instead uses calorimetric compensation and shared dilution. |
| Identifiability | Villaverde, Barreiro and Papachristodoulou (2016), DOI 10.1371/journal.pcbi.1005153 | State augmentation and Lie-derivative identifiability are established; this campaign does not invent that analysis. |
| Empirical reduction/information | Lall, Marsden and Glavaski (2002), DOI 10.1002/rnc.657 | Trajectory sensitivity and empirical reduction have long precedents. Our finite-horizon singular spectra are diagnostic, not an exact global Gramian theorem. |
| MHE | Rao, Rawlings and Mayne (2003), DOI 10.1109/TAC.2002.808470 | Constrained deterministic estimation has stability conditions. The six-step implementation here does not establish those conditions or represent a fully tuned best-in-class MHE. |
| Output-feedback MPC | Rawlings, Mayne and Diehl, second-edition textbook, author site | Standard foundations and implementation reference. State error, model error and constraints interact; new guarantees are not inferred from trajectory plots. |
| Regret under measurements | Goel and Hassibi, PMLR 144 (2021), 1270–1280 | Prior regret-optimal linear control compares to an offline benchmark. Here the comparator knows the initial chemical world but uses the same finite action class; these regret definitions are different. |
| Decision-focused prediction | Elmachtoub and Grigas (2022), DOI 10.1287/mnsc.2020.3922 | Prediction error and decision loss need not align. No novelty is claimed for that principle. Our setting is dynamic inferential control. |
| Dual control | Klenske and Hennig, JMLR 17(127), 2016 | Actions may change learning. The present scenario controller does not optimize future observation distributions, so it is not a full dual controller. |
| Belief MPC, recent | Cao et al., arXiv:2604.24663 (2026), preprint | Linear dynamics, bilinear sensing and input-dependent Kalman covariance. Its favorable synthetic results do not establish gains for this nonlinear reactor. |
| Latent-risk planning, recent | Enwerem, Baras and Belta, arXiv:2604.03868 v2 (2026), preprint | Measured state with latent parameters, CVaR and MPPI. Our ambiguity is chemical state with thermal observations; no CVaR guarantee is imported. |
| Reactor physics | Brandão dissertation (2019), pp. 30–32; recovered modeloCT.m | Original six-state equations and sensors. Table/coded enthalpies differ; M0 follows code and preserves its Arrhenius offset. |
| Reaction enthalpy correction | Fogler, UMich living example 12-4 | The public code contains a temperature correction from reaction Cp difference. It supports checking Kirchhoff consistency, not importing its different operating point or enthalpy as a calibrated replacement. |

Searches also covered set-membership nonlinear MPC (Canale, DOI 10.1002/rnc.2878;
publisher full text was inaccessible), inferential control, information-constrained control,
value of chemical sampling and chemical-reactor observability. Coverage of the entire
2025–2026 literature and full-text comparisons remains incomplete.

## Claim-by-claim originality assessment

1. Two invisible chemical modes in the constant-Cp PG model: case-specific construction,
   already present in recovered internal ICAC material; not a new discovery of this campaign.
2. Persistence under a reciprocal jacket and consistent temperature-dependent reaction
   enthalpy: explicit extension of that construction; potentially useful audit result.
3. Dimension controlled by the span of species heat-capacity functions: candidate compact
   structural characterization. Priority not established; compare against general quotient
   systems, reaction invariants and structural-identifiability literature before claiming novelty.
4. Half-separation estimation bound and convex regret bound: elementary consequences of
   known inequalities, not independent major theoretical novelty.
5. Controller superiority: must be determined by paired test and confirmation data, including
   adverse regimes, stronger continuous baselines, safety and computation.
6. Publication: a reproducible negative or mixed result may be valuable. Submission readiness
   still requires recovered historical replay, better physical properties, stronger baselines and
   independent expert review.

All bibliography entries are in manuscripts/references.bib. Preprints are explicitly labeled.

## Additional physical source check

Chan and Seider (University of Pennsylvania, July 2004) use excess-water first-order kinetics and nonideal-liquid thermodynamics in a related batch teaching case. These assumptions differ from a calibrated CSTR model. A 2026 microchannel-kinetics paper at https://www.mdpi.com/2227-9717/14/9/1491 was located, but the publisher returned HTTP 429; its parameters were not imported. This is an access limitation, not evidence against alternative kinetics.

# Configuração congelada

~~~json
{
  "version": "1.0-computational-core",
  "date": "2026-10-20",
  "status": "frozen before new simulations",
  "scope": "Historical M0 benchmark and explicitly hypothetical reconciliations; no industrial validation",
  "development_seeds": [
    11,
    12
  ],
  "validation_seeds": [
    101,
    102,
    103
  ],
  "test_seeds": [
    4100,
    4101,
    4102,
    4103,
    4104,
    4105,
    4106,
    4107,
    4108,
    4109,
    4110,
    4111,
    4112,
    4113,
    4114,
    4115,
    4116,
    4117,
    4118,
    4119
  ],
  "confirmation_seeds": [
    8100,
    8101,
    8102,
    8103,
    8104,
    8105,
    8106,
    8107,
    8108,
    8109,
    8110,
    8111,
    8112,
    8113,
    8114,
    8115,
    8116,
    8117,
    8118,
    8119
  ],
  "dt_h": 0.015,
  "steps": 60,
  "horizon": 14,
  "grid_points_per_move": 5,
  "move_blocks": [
    3,
    11
  ],
  "qmin": 0.05,
  "qmax": 3,
  "slew": 0.4,
  "study_T_limit": 344.2611111111,
  "primary_contrasts": [
    [
      "P2_regret",
      "B1_ukf"
    ],
    [
      "P3_adaptive_regret",
      "B2_both"
    ],
    [
      "B2_both",
      "B2_estimator"
    ]
  ],
  "primary_metric": "paired trajectory IAE",
  "uncertainty": "20 independent paired noise seeds within each fixed scenario; seed-cluster bootstrap across finite scenario suite",
  "success_rule": "exploratory target >=10% IAE improvement with 95% paired CI above zero, no material increase in thermal severity, confirmation; multiplicity Holm for three primary contrasts",
  "information": "Only current T,Tt, past actions and measured current feeds. No future disturbances. Exact-inventory and chemical variants separately labeled.",
  "runtime_budget": "one CPU worker; 60 min job ceiling; pilot predicts cost; do not silently trim seeds",
  "model_variants": "M0 historical. M1H Kirchhoff with assumed reaction-enthalpy reference at nominal T; M1J adds nominally matched lumped jacket; M2L/Q synthetic cp(T) slopes/curvatures, not measured properties.",
  "gaps": "ICAC branch absent at recovery; C01-C14 raw code not retrieved; historical scalar values not automatically reproduced."
}
~~~
# Registro de testes

~~~
test_01_historical_rhs_parity (test_science.ScientificTests.test_01_historical_rhs_parity) ... ok
test_02_conserved_reaction_inventories (test_science.ScientificTests.test_02_conserved_reaction_inventories) ... ok
test_03_energy_accounting (test_science.ScientificTests.test_03_energy_accounting) ... ok
test_04_equilibrium (test_science.ScientificTests.test_04_equilibrium) ... ok
test_05_positivity (test_science.ScientificTests.test_05_positivity) ... ok
test_06_independent_integration (test_science.ScientificTests.test_06_independent_integration) ... ok
test_07_jacobian_step_consistency (test_science.ScientificTests.test_07_jacobian_step_consistency) ... ok
test_08_twins_constant_cp_and_jacket (test_science.ScientificTests.test_08_twins_constant_cp_and_jacket) ... ok
test_09_variable_cp_falsifies_specific_twin (test_science.ScientificTests.test_09_variable_cp_falsifies_specific_twin) ... ok
test_10_rank_has_two_exact_null_directions (test_science.ScientificTests.test_10_rank_has_two_exact_null_directions) ... ok
test_11_causal_prefix (test_science.ScientificTests.test_11_causal_prefix) ... ok
test_12_inventory_reconstruction (test_science.ScientificTests.test_12_inventory_reconstruction) ... ok
test_13_constraints (test_science.ScientificTests.test_13_constraints) ... ok
test_14_failed_optimization_fallback (test_science.ScientificTests.test_14_failed_optimization_fallback) ... ok
test_15_regret_exact (test_science.ScientificTests.test_15_regret_exact) ... ok
test_16_zero_conflict_not_impossible_state_error (test_science.ScientificTests.test_16_zero_conflict_not_impossible_state_error) ... ok
test_17_seed_separation (test_science.ScientificTests.test_17_seed_separation) ... ok
test_18_reproducible_and_metric_independent (test_science.ScientificTests.test_18_reproducible_and_metric_independent) ... ok

----------------------------------------------------------------------
Ran 18 tests in 11.990s

OK

~~~
# Verificação independente de métricas

~~~json
{
  "trajectories_checked": 5720,
  "trajectories_expected": 5720,
  "max_iae_error": 9.8879238130678e-17,
  "max_rmse_error": 9.8879238130678e-17,
  "pass_all": true
}
~~~
# Todos os cenários: médias por método

| scenario | method | IAE | RMSE CC | Tmax | Thermal integral | fallback | Decision ms | samples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| combined | B0 PI | 0.093429 | 0.12106 | 335.19 | 0 | 0 | 0.011068 | 0 |
| combined | B1 continuous | 0.22045 | 0.13055 | 332.33 | 0 | 0 | 4.9675 | 0 |
| combined | B1 ukf | 0.23055 | 0.13057 | 332.35 | 0 | 0 | 1.6601 | 0 |
| combined | B2 both | 0.079746 | 0.076413 | 337.06 | 0 | 0 | 1.9027 | 0 |
| combined | B2 estimator | 0.25361 | 0.077038 | 332.33 | 0 | 0 | 1.6709 | 0 |
| combined | B3 assumed inventory | 0.25434 | 0.12063 | 332.33 | 0 | 0 | 1.682 | 0 |
| combined | B3 known inventory | 0.2805 | 0.13184 | 332.33 | 0 | 0 | 1.6737 | 0 |
| combined | B4 mhe | 0.19172 | 0.11811 | 332.58 | 0 | 0 | 1.7129 | 0 |
| combined | B5 true state | 0.25117 | 0 | 332.33 | 0 | 0 | 1.6657 | 0 |
| combined | P1 expected | 0.23055 | 0.13057 | 332.35 | 0 | 0 | 4.3434 | 0 |
| combined | P2 regret | 0.2325 | 0.13086 | 332.33 | 0 | 0 | 4.2769 | 0 |
| combined | P3 adaptive regret | 0.078689 | 0.076353 | 337.17 | 0 | 0 | 4.9517 | 0 |
| combined | P4 hybrid | 0.080989 | 0.076408 | 337.05 | 0 | 0 | 6.5361 | 0 |
| combined | P5 delayed | 0.24352 | 0.12469 | 332.33 | 0 | 0 | 1.6656 | 4 |
| combined | P5 event | 0.23268 | 0.11023 | 332.34 | 0 | 0 | 1.6665 | 3.2 |
| combined | P5 frequent | 0.22634 | 0.10136 | 332.34 | 0 | 0 | 1.6624 | 8 |
| combined | P5 initial | 0.23052 | 0.11112 | 332.34 | 0 | 0 | 1.6696 | 1 |
| combined | P5 noisy | 0.23078 | 0.119 | 332.37 | 0 | 0 | 1.6611 | 4 |
| combined | P5 periodic | 0.22186 | 0.10568 | 332.33 | 0 | 0 | 1.6588 | 4 |
| correlated noise | B0 PI | 0.012351 | 0.018987 | 333.33 | 0 | 0 | 0.010863 | 0 |
| correlated noise | B1 continuous | 0.0056224 | 0.01913 | 332.77 | 0 | 0 | 5.0819 | 0 |
| correlated noise | B1 ukf | 0.0017832 | 0.019368 | 332.46 | 0 | 0 | 1.9438 | 0 |
| correlated noise | B2 both | 0.0088977 | 0.025513 | 333.22 | 0 | 0 | 1.9538 | 0 |
| correlated noise | B2 estimator | 0.0010672 | 0.025383 | 332.41 | 0 | 0 | 1.9229 | 0 |
| correlated noise | B3 assumed inventory | 0.0022236 | 0.018095 | 332.6 | 0 | 0 | 1.9298 | 0 |
| correlated noise | B3 known inventory | 0.0022236 | 0.018095 | 332.6 | 0 | 0 | 1.9374 | 0 |
| correlated noise | B4 mhe | 0.0012654 | 0.020191 | 332.4 | 0 | 0 | 1.9705 | 0 |
| correlated noise | B5 true state | 0 | 0 | 332.33 | 0 | 0 | 1.9173 | 0 |
| correlated noise | P1 expected | 0.0017832 | 0.019368 | 332.46 | 0 | 0 | 5.0096 | 0 |
| correlated noise | P2 regret | 0.0011856 | 0.01923 | 332.42 | 0 | 0 | 5.008 | 0 |
| correlated noise | P3 adaptive regret | 0.0077582 | 0.025376 | 333.2 | 0 | 0 | 5.0854 | 0 |
| correlated noise | P4 hybrid | 0.0082111 | 0.02542 | 333.27 | 0 | 0 | 6.749 | 0 |
| correlated noise | P5 delayed | 0.0021283 | 0.019508 | 332.48 | 0 | 0 | 1.9207 | 4 |
| correlated noise | P5 event | 0.0019023 | 0.021342 | 332.47 | 0 | 0 | 1.9474 | 2 |
| correlated noise | P5 frequent | 0.0019023 | 0.019926 | 332.47 | 0 | 0 | 1.9193 | 8 |
| correlated noise | P5 initial | 0.0019023 | 0.021948 | 332.47 | 0 | 0 | 1.9256 | 1 |
| correlated noise | P5 noisy | 0.0062162 | 0.046467 | 332.83 | 0 | 0 | 1.9155 | 4 |
| correlated noise | P5 periodic | 0.0019023 | 0.021342 | 332.47 | 0 | 0 | 1.9254 | 4 |
| dropout | B0 PI | 0.0066846 | 0.011372 | 332.93 | 0 | 0 | 0.010994 | 0 |
| dropout | B1 continuous | 0.0032454 | 0.011315 | 332.61 | 0 | 0 | 5.0065 | 0 |
| dropout | B1 ukf | 0.0016471 | 0.011311 | 332.44 | 0 | 0 | 1.9513 | 0 |
| dropout | B2 both | 0.0069945 | 0.015851 | 332.89 | 0 | 0 | 1.9614 | 0 |
| dropout | B2 estimator | 0.0014342 | 0.015842 | 332.44 | 0 | 0 | 1.9311 | 0 |
| dropout | B3 assumed inventory | 0.0023341 | 0.011488 | 332.58 | 0 | 0 | 1.9369 | 0 |
| dropout | B3 known inventory | 0.0023341 | 0.011488 | 332.58 | 0 | 0 | 1.9301 | 0 |
| dropout | B4 mhe | 0.0016341 | 0.012176 | 332.43 | 0 | 0 | 1.974 | 0 |
| dropout | B5 true state | 0 | 0 | 332.33 | 0 | 0 | 1.9117 | 0 |
| dropout | P1 expected | 0.0016471 | 0.011311 | 332.44 | 0 | 0 | 5.0001 | 0 |
| dropout | P2 regret | 0.0014446 | 0.011322 | 332.37 | 0 | 0 | 4.9714 | 0 |
| dropout | P3 adaptive regret | 0.006065 | 0.015834 | 332.89 | 0 | 0 | 5.1153 | 0 |
| dropout | P4 hybrid | 0.0064323 | 0.01583 | 332.91 | 0 | 0 | 6.7783 | 0 |
| dropout | P5 delayed | 0.0018754 | 0.012641 | 332.46 | 0 | 0 | 1.9105 | 4 |
| dropout | P5 event | 0.0018621 | 0.01493 | 332.45 | 0 | 0 | 1.9474 | 2 |
| dropout | P5 frequent | 0.0018621 | 0.014337 | 332.45 | 0 | 0 | 1.925 | 8 |
| dropout | P5 initial | 0.0018621 | 0.015276 | 332.45 | 0 | 0 | 1.9134 | 1 |
| dropout | P5 noisy | 0.0079265 | 0.042957 | 332.98 | 0 | 0 | 1.9146 | 4 |
| dropout | P5 periodic | 0.0018621 | 0.015099 | 332.45 | 0 | 0 | 1.9271 | 4 |
| feed | B0 PI | 0.11611 | 0.011236 | 336.78 | 0 | 0 | 0.011034 | 0 |
| feed | B1 continuous | 0.0601 | 0.011873 | 332.6 | 0 | 0 | 4.4467 | 0 |
| feed | B1 ukf | 0.059356 | 0.011877 | 332.44 | 0 | 0 | 1.6282 | 0 |
| feed | B2 both | 0.062922 | 0.015899 | 332.93 | 0 | 0 | 1.6332 | 0 |
| feed | B2 estimator | 0.059966 | 0.015842 | 332.43 | 0 | 0 | 1.6238 | 0 |
| feed | B3 assumed inventory | 0.059774 | 0.01203 | 332.57 | 0 | 0 | 1.6175 | 0 |
| feed | B3 known inventory | 0.059774 | 0.01203 | 332.57 | 0 | 0 | 1.6278 | 0 |
| feed | B4 mhe | 0.059336 | 0.012883 | 332.42 | 0 | 0 | 1.666 | 0 |
| feed | B5 true state | 0.058536 | 0 | 332.33 | 0 | 0 | 1.619 | 0 |
| feed | P1 expected | 0.059356 | 0.011877 | 332.44 | 0 | 0 | 4.0911 | 0 |
| feed | P2 regret | 0.059297 | 0.011886 | 332.36 | 0 | 0 | 4.0733 | 0 |
| feed | P3 adaptive regret | 0.061435 | 0.015872 | 332.89 | 0 | 0 | 4.1172 | 0 |
| feed | P4 hybrid | 0.061734 | 0.015885 | 332.91 | 0 | 0 | 5.4782 | 0 |
| feed | P5 delayed | 0.059577 | 0.013194 | 332.45 | 0 | 0 | 1.6263 | 4 |
| feed | P5 event | 0.059646 | 0.015444 | 332.44 | 0 | 0 | 1.6282 | 2.95 |
| feed | P5 frequent | 0.059627 | 0.014792 | 332.44 | 0 | 0 | 1.6157 | 8 |
| feed | P5 initial | 0.059538 | 0.015748 | 332.44 | 0 | 0 | 1.6128 | 1 |
| feed | P5 noisy | 0.06455 | 0.04317 | 332.95 | 0 | 0 | 1.6277 | 4 |
| feed | P5 periodic | 0.059526 | 0.015551 | 332.44 | 0 | 0 | 1.6069 | 4 |
| heat transfer | B0 PI | 0.031443 | 0.02292 | 332.52 | 0 | 0 | 0.010955 | 0 |
| heat transfer | B1 continuous | 0.066754 | 0.023863 | 332.33 | 0 | 0 | 5.6066 | 0 |
| heat transfer | B1 ukf | 0.099788 | 0.024558 | 332.36 | 0 | 0 | 1.9339 | 0 |
| heat transfer | B2 both | 0.028001 | 0.014626 | 333.88 | 0 | 0 | 1.9685 | 0 |
| heat transfer | B2 estimator | 0.080227 | 0.015783 | 332.38 | 0 | 0 | 1.9372 | 0 |
| heat transfer | B3 assumed inventory | 0.099235 | 0.027171 | 332.36 | 0 | 0 | 1.9485 | 0 |
| heat transfer | B3 known inventory | 0.099235 | 0.027171 | 332.36 | 0 | 0 | 1.9461 | 0 |
| heat transfer | B4 mhe | 0.10036 | 0.019822 | 332.36 | 0 | 0 | 1.9809 | 0 |
| heat transfer | B5 true state | 0.10619 | 0 | 332.33 | 0 | 0 | 1.9214 | 0 |
| heat transfer | P1 expected | 0.099788 | 0.024558 | 332.36 | 0 | 0 | 5.0249 | 0 |
| heat transfer | P2 regret | 0.10264 | 0.024602 | 332.42 | 0 | 0 | 5.0064 | 0 |
| heat transfer | P3 adaptive regret | 0.030407 | 0.014657 | 333.89 | 0 | 0 | 5.1265 | 0 |
| heat transfer | P4 hybrid | 0.028128 | 0.014611 | 333.87 | 0 | 0 | 6.9223 | 0 |
| heat transfer | P5 delayed | 0.10219 | 0.024936 | 332.37 | 0 | 0 | 1.9242 | 4 |
| heat transfer | P5 event | 0.10081 | 0.026159 | 332.37 | 0 | 0 | 1.9413 | 2 |
| heat transfer | P5 frequent | 0.099087 | 0.024549 | 332.38 | 0 | 0 | 1.9444 | 8 |
| heat transfer | P5 initial | 0.10025 | 0.026281 | 332.38 | 0 | 0 | 1.9207 | 1 |
| heat transfer | P5 noisy | 0.097939 | 0.048393 | 332.6 | 0 | 0 | 1.9294 | 4 |
| heat transfer | P5 periodic | 0.099536 | 0.025589 | 332.38 | 0 | 0 | 1.9199 | 4 |
| inventory minus | B0 PI | 0.060143 | 0.12003 | 332.93 | 0 | 0 | 0.01109 | 0 |
| inventory minus | B1 continuous | 0.059577 | 0.12016 | 332.61 | 0 | 0 | 4.9699 | 0 |
| inventory minus | B1 ukf | 0.060464 | 0.12022 | 332.44 | 0 | 0 | 1.9265 | 0 |
| inventory minus | B2 both | 0.060547 | 0.12106 | 332.93 | 0 | 0 | 1.9689 | 0 |
| inventory minus | B2 estimator | 0.060307 | 0.12125 | 332.44 | 0 | 0 | 1.9313 | 0 |
| inventory minus | B3 assumed inventory | 0.05916 | 0.12362 | 332.58 | 0 | 0 | 1.9335 | 0 |
| inventory minus | B3 known inventory | 0.038648 | 0.052411 | 336.44 | 0 | 0 | 1.9291 | 0 |
| inventory minus | B4 mhe | 0.060639 | 0.11986 | 332.43 | 0 | 0 | 1.9684 | 0 |
| inventory minus | B5 true state | 0.042257 | 0 | 335.36 | 0 | 0 | 1.9219 | 0 |
| inventory minus | P1 expected | 0.060464 | 0.12022 | 332.44 | 0 | 0 | 5.0301 | 0 |
| inventory minus | P2 regret | 0.061292 | 0.12032 | 332.37 | 0 | 0 | 5.0333 | 0 |
| inventory minus | P3 adaptive regret | 0.059661 | 0.12109 | 332.89 | 0 | 0 | 5.0872 | 0 |
| inventory minus | P4 hybrid | 0.059649 | 0.12109 | 332.91 | 0 | 0 | 6.7786 | 0 |
| inventory minus | P5 delayed | 0.046639 | 0.082444 | 334.92 | 0 | 0 | 1.9384 | 4 |
| inventory minus | P5 event | 0.041422 | 0.014626 | 335.82 | 0 | 0 | 1.934 | 2 |
| inventory minus | P5 frequent | 0.04162 | 0.014029 | 335.87 | 0 | 0 | 1.9336 | 8 |
| inventory minus | P5 initial | 0.041773 | 0.014942 | 335.86 | 0 | 0 | 1.9181 | 1 |
| inventory minus | P5 noisy | 0.046597 | 0.044115 | 335.41 | 0 | 0 | 1.9186 | 4 |
| inventory minus | P5 periodic | 0.041773 | 0.014806 | 335.86 | 0 | 0 | 1.9242 | 4 |
| inventory plus | B0 PI | 0.063136 | 0.12246 | 332.93 | 0 | 0 | 0.011024 | 0 |
| inventory plus | B1 continuous | 0.061569 | 0.12231 | 332.61 | 0 | 0 | 4.9639 | 0 |
| inventory plus | B1 ukf | 0.060387 | 0.12225 | 332.44 | 0 | 0 | 1.9212 | 0 |
| inventory plus | B2 both | 0.061797 | 0.12223 | 332.93 | 0 | 0 | 1.9459 | 0 |
| inventory plus | B2 estimator | 0.060544 | 0.12204 | 332.44 | 0 | 0 | 1.9178 | 0 |
| inventory plus | B3 assumed inventory | 0.061691 | 0.11896 | 332.58 | 0 | 0 | 1.9379 | 0 |
| inventory plus | B3 known inventory | 0.043535 | 0.052254 | 332.78 | 0 | 0 | 1.9344 | 0 |
| inventory plus | B4 mhe | 0.060212 | 0.12274 | 332.43 | 0 | 0 | 1.9682 | 0 |
| inventory plus | B5 true state | 0.044461 | 0 | 332.72 | 0 | 0 | 1.9173 | 0 |
| inventory plus | P1 expected | 0.060387 | 0.12225 | 332.44 | 0 | 0 | 5.01 | 0 |
| inventory plus | P2 regret | 0.059559 | 0.12216 | 332.37 | 0 | 0 | 5.0058 | 0 |
| inventory plus | P3 adaptive regret | 0.062655 | 0.12219 | 332.89 | 0 | 0 | 5.0882 | 0 |
| inventory plus | P4 hybrid | 0.062747 | 0.1222 | 332.91 | 0 | 0 | 6.7788 | 0 |
| inventory plus | P5 delayed | 0.049122 | 0.081439 | 332.67 | 0 | 0 | 1.9307 | 4 |
| inventory plus | P5 event | 0.046292 | 0.01508 | 332.7 | 0 | 0 | 1.9371 | 2 |
| inventory plus | P5 frequent | 0.046106 | 0.014498 | 332.71 | 0 | 0 | 1.9223 | 8 |
| inventory plus | P5 initial | 0.046297 | 0.015474 | 332.7 | 0 | 0 | 1.9196 | 1 |
| inventory plus | P5 noisy | 0.049212 | 0.043957 | 332.65 | 0 | 0 | 1.9229 | 4 |
| inventory plus | P5 periodic | 0.046297 | 0.015302 | 332.7 | 0 | 0 | 1.9171 | 4 |
| kinetic | B0 PI | 0.089428 | 0.076605 | 333.28 | 0 | 0 | 0.010903 | 0 |
| kinetic | B1 continuous | 0.16428 | 0.081211 | 332.33 | 0 | 0 | 5.6893 | 0 |
| kinetic | B1 ukf | 0.19263 | 0.083904 | 332.33 | 0 | 0 | 1.9316 | 0 |
| kinetic | B2 both | 0.044861 | 0.015328 | 333.99 | 0 | 0 | 1.9864 | 0 |
| kinetic | B2 estimator | 0.23438 | 0.016884 | 332.33 | 0 | 0 | 1.9402 | 0 |
| kinetic | B3 assumed inventory | 0.19998 | 0.094075 | 332.33 | 0 | 0 | 1.9439 | 0 |
| kinetic | B3 known inventory | 0.19998 | 0.094075 | 332.33 | 0 | 0 | 1.9537 | 0 |
| kinetic | B4 mhe | 0.17914 | 0.073232 | 332.33 | 0 | 0 | 1.994 | 0 |
| kinetic | B5 true state | 0.30114 | 0 | 332.33 | 0 | 0 | 1.9346 | 0 |
| kinetic | P1 expected | 0.19263 | 0.083904 | 332.33 | 0 | 0 | 5.0584 | 0 |
| kinetic | P2 regret | 0.1836 | 0.083579 | 332.33 | 0 | 0 | 5.0384 | 0 |
| kinetic | P3 adaptive regret | 0.043723 | 0.015313 | 333.85 | 0 | 0 | 5.1591 | 0 |
| kinetic | P4 hybrid | 0.044135 | 0.015359 | 333.96 | 0 | 0 | 6.7849 | 0 |
| kinetic | P5 delayed | 0.19173 | 0.083329 | 332.33 | 0 | 0 | 1.9354 | 4 |
| kinetic | P5 event | 0.18559 | 0.080046 | 332.33 | 0 | 0 | 1.9537 | 2 |
| kinetic | P5 frequent | 0.18104 | 0.073214 | 332.33 | 0 | 0 | 1.9446 | 8 |
| kinetic | P5 initial | 0.18559 | 0.080069 | 332.33 | 0 | 0 | 1.9402 | 1 |
| kinetic | P5 noisy | 0.18674 | 0.09073 | 332.4 | 0 | 0 | 1.9305 | 4 |
| kinetic | P5 periodic | 0.18511 | 0.076543 | 332.33 | 0 | 0 | 1.9375 | 4 |
| nominal | B0 PI | 0.0066351 | 0.011301 | 332.93 | 0 | 0 | 0.011745 | 0 |
| nominal | B1 continuous | 0.0032395 | 0.011244 | 332.61 | 0 | 0 | 4.9795 | 0 |
| nominal | B1 ukf | 0.0016471 | 0.01124 | 332.44 | 0 | 0 | 1.9157 | 0 |
| nominal | B2 both | 0.0075155 | 0.01487 | 332.93 | 0 | 0 | 1.936 | 0 |
| nominal | B2 estimator | 0.0014342 | 0.014862 | 332.44 | 0 | 0 | 1.9084 | 0 |
| nominal | B3 assumed inventory | 0.0023341 | 0.011423 | 332.58 | 0 | 0 | 1.9167 | 0 |
| nominal | B3 known inventory | 0.0023341 | 0.011423 | 332.58 | 0 | 0 | 1.9209 | 0 |
| nominal | B4 mhe | 0.0016341 | 0.012091 | 332.43 | 0 | 0 | 1.9743 | 0 |
| nominal | B5 true state | 0 | 0 | 332.33 | 0 | 0 | 1.9177 | 0 |
| nominal | P1 expected | 0.0016471 | 0.01124 | 332.44 | 0 | 0 | 5.0063 | 0 |
| nominal | P2 regret | 0.0014446 | 0.011249 | 332.37 | 0 | 0 | 5.0092 | 0 |
| nominal | P3 adaptive regret | 0.006065 | 0.014836 | 332.89 | 0 | 0 | 5.061 | 0 |
| nominal | P4 hybrid | 0.0064323 | 0.014847 | 332.91 | 0 | 0 | 6.7574 | 0 |
| nominal | P5 delayed | 0.0018754 | 0.012597 | 332.46 | 0 | 0 | 1.9256 | 4 |
| nominal | P5 event | 0.0018621 | 0.014873 | 332.45 | 0 | 0 | 1.9273 | 2 |
| nominal | P5 frequent | 0.0018621 | 0.014288 | 332.45 | 0 | 0 | 1.9205 | 8 |
| nominal | P5 initial | 0.0018621 | 0.015221 | 332.45 | 0 | 0 | 1.9188 | 1 |
| nominal | P5 noisy | 0.0079265 | 0.042936 | 332.98 | 0 | 0 | 1.9126 | 4 |
| nominal | P5 periodic | 0.0018621 | 0.015065 | 332.45 | 0 | 0 | 1.9141 | 4 |
| outside prior | B0 PI | 0.16836 | 0.24254 | 333.56 | 0 | 0 | 0.011088 | 0 |
| outside prior | B1 continuous | 0.3054 | 0.2526 | 332.33 | 0 | 0 | 5.6969 | 0 |
| outside prior | B1 ukf | 0.29077 | 0.25234 | 332.33 | 0 | 0 | 1.9137 | 0 |
| outside prior | B2 both | 0.086894 | 0.23862 | 336.25 | 0 | 0 | 1.9354 | 0 |
| outside prior | B2 estimator | 0.35094 | 0.23936 | 332.33 | 0 | 0 | 1.9265 | 0 |
| outside prior | B3 assumed inventory | 0.29908 | 0.22306 | 332.33 | 0 | 0 | 1.9287 | 0 |
| outside prior | B3 known inventory | 0.42095 | 0.18713 | 332.33 | 0 | 0.016667 | 1.935 | 0 |
| outside prior | B4 mhe | 0.26574 | 0.24633 | 332.33 | 0 | 0 | 1.9742 | 0 |
| outside prior | B5 true state | 0.43887 | 0 | 332.33 | 0 | 0 | 1.9088 | 0 |
| outside prior | P1 expected | 0.29077 | 0.25234 | 332.33 | 0 | 0 | 5.0011 | 0 |
| outside prior | P2 regret | 0.2806 | 0.25143 | 332.33 | 0 | 0 | 5.0472 | 0 |
| outside prior | P3 adaptive regret | 0.086411 | 0.23866 | 336.17 | 0 | 0 | 5.0162 | 0 |
| outside prior | P4 hybrid | 0.087971 | 0.23863 | 336.24 | 0 | 0 | 6.3957 | 0 |
| outside prior | P5 delayed | 0.4036 | 0.21264 | 332.33 | 0 | 0 | 1.9226 | 4 |
| outside prior | P5 event | 0.39926 | 0.13483 | 332.33 | 0 | 0 | 1.9519 | 2.75 |
| outside prior | P5 frequent | 0.39555 | 0.12249 | 332.33 | 0 | 0 | 1.9163 | 8 |
| outside prior | P5 initial | 0.39926 | 0.13602 | 332.33 | 0 | 0 | 1.9224 | 1 |
| outside prior | P5 noisy | 0.38486 | 0.14055 | 332.33 | 0 | 0 | 1.9275 | 4 |
| outside prior | P5 periodic | 0.39402 | 0.12843 | 332.33 | 0 | 0 | 1.9112 | 4 |
| properties | B0 PI | 0.062622 | 0.037479 | 332.37 | 0 | 0 | 0.010864 | 0 |
| properties | B1 continuous | 0.16316 | 0.02852 | 332.33 | 0 | 0 | 5.7274 | 0 |
| properties | B1 ukf | 0.16004 | 0.029004 | 332.33 | 0 | 0 | 1.9301 | 0 |
| properties | B2 both | 0.059327 | 0.11611 | 334.88 | 0 | 0 | 1.9112 | 0 |
| properties | B2 estimator | 0.23345 | 0.1103 | 332.33 | 0 | 0 | 1.929 | 0 |
| properties | B3 assumed inventory | 0.1653 | 0.027922 | 332.33 | 0 | 0 | 1.9289 | 0 |
| properties | B3 known inventory | 0.1653 | 0.027922 | 332.33 | 0 | 0 | 1.9371 | 0 |
| properties | B4 mhe | 0.13801 | 0.021633 | 332.33 | 0 | 0 | 1.9963 | 0 |
| properties | B5 true state | 0.098074 | 0 | 332.33 | 0 | 0 | 1.9282 | 0 |
| properties | P1 expected | 0.16004 | 0.029004 | 332.33 | 0 | 0 | 5.0264 | 0 |
| properties | P2 regret | 0.1636 | 0.029499 | 332.33 | 0 | 0 | 5.0197 | 0 |
| properties | P3 adaptive regret | 0.05938 | 0.11559 | 334.89 | 0 | 0 | 4.9843 | 0 |
| properties | P4 hybrid | 0.059247 | 0.11624 | 334.89 | 0 | 0 | 6.5861 | 0 |
| properties | P5 delayed | 0.16186 | 0.02469 | 332.33 | 0 | 0 | 1.9301 | 4 |
| properties | P5 event | 0.15953 | 0.026844 | 332.33 | 0 | 0 | 1.9478 | 2.1 |
| properties | P5 frequent | 0.15961 | 0.026353 | 332.33 | 0 | 0 | 1.9265 | 8 |
| properties | P5 initial | 0.156 | 0.027853 | 332.33 | 0 | 0 | 1.9359 | 1 |
| properties | P5 noisy | 0.15497 | 0.049409 | 332.37 | 0 | 0 | 1.9237 | 4 |
| properties | P5 periodic | 0.15573 | 0.028028 | 332.33 | 0 | 0 | 1.9435 | 4 |
| saturation | B0 PI | 0.0066351 | 0.011301 | 332.93 | 0 | 0 | 0.011305 | 0 |
| saturation | B1 continuous | 0.0032395 | 0.011244 | 332.61 | 0 | 0 | 4.7753 | 0 |
| saturation | B1 ukf | 0.0016471 | 0.01124 | 332.44 | 0 | 0 | 1.7314 | 0 |
| saturation | B2 both | 0.0084796 | 0.014867 | 332.96 | 0 | 0 | 1.7539 | 0 |
| saturation | B2 estimator | 0.0014342 | 0.014862 | 332.44 | 0 | 0 | 1.7346 | 0 |
| saturation | B3 assumed inventory | 0.0023341 | 0.011423 | 332.58 | 0 | 0 | 1.753 | 0 |
| saturation | B3 known inventory | 0.0023341 | 0.011423 | 332.58 | 0 | 0 | 1.7386 | 0 |
| saturation | B4 mhe | 0.0016341 | 0.012091 | 332.43 | 0 | 0 | 1.7843 | 0 |
| saturation | B5 true state | 0 | 0 | 332.33 | 0 | 0 | 1.7351 | 0 |
| saturation | P1 expected | 0.0016471 | 0.01124 | 332.44 | 0 | 0 | 4.4495 | 0 |
| saturation | P2 regret | 0.0014446 | 0.011249 | 332.37 | 0 | 0 | 4.4191 | 0 |
| saturation | P3 adaptive regret | 0.0064252 | 0.014832 | 332.92 | 0 | 0 | 4.5354 | 0 |
| saturation | P4 hybrid | 0.0067396 | 0.014836 | 332.92 | 0 | 0 | 6.0592 | 0 |
| saturation | P5 delayed | 0.0018754 | 0.012597 | 332.46 | 0 | 0 | 1.7321 | 4 |
| saturation | P5 event | 0.0018621 | 0.014873 | 332.45 | 0 | 0 | 1.7648 | 2 |
| saturation | P5 frequent | 0.0018621 | 0.014288 | 332.45 | 0 | 0 | 1.7525 | 8 |
| saturation | P5 initial | 0.0018621 | 0.015221 | 332.45 | 0 | 0 | 1.7249 | 1 |
| saturation | P5 noisy | 0.0091172 | 0.042937 | 333.06 | 0 | 0 | 1.7299 | 4 |
| saturation | P5 periodic | 0.0018621 | 0.015065 | 332.45 | 0 | 0 | 1.7363 | 4 |
| servo | B0 PI | 0.04255 | 0.011002 | 336.18 | 0 | 0 | 0.011136 | 0 |
| servo | B1 continuous | 0.048797 | 0.010804 | 335.88 | 0 | 0 | 5.4046 | 0 |
| servo | B1 ukf | 0.052975 | 0.010779 | 335.93 | 0 | 0 | 1.9322 | 0 |
| servo | B2 both | 0.053552 | 0.014356 | 335.96 | 0 | 0 | 1.9601 | 0 |
| servo | B2 estimator | 0.052413 | 0.014344 | 335.92 | 0 | 0 | 1.9263 | 0 |
| servo | B3 assumed inventory | 0.053005 | 0.011009 | 335.91 | 0 | 0 | 1.9374 | 0 |
| servo | B3 known inventory | 0.053005 | 0.011009 | 335.91 | 0 | 0 | 1.9433 | 0 |
| servo | B4 mhe | 0.05283 | 0.011523 | 335.93 | 0 | 0 | 1.9762 | 0 |
| servo | B5 true state | 0.052263 | 0 | 335.93 | 0 | 0 | 1.9264 | 0 |
| servo | P1 expected | 0.052975 | 0.010779 | 335.93 | 0 | 0 | 5.043 | 0 |
| servo | P2 regret | 0.053178 | 0.010787 | 335.94 | 0 | 0 | 5.0253 | 0 |
| servo | P3 adaptive regret | 0.052755 | 0.014329 | 335.94 | 0 | 0 | 5.1425 | 0 |
| servo | P4 hybrid | 0.052382 | 0.014329 | 335.94 | 0 | 0 | 6.8483 | 0 |
| servo | P5 delayed | 0.053079 | 0.012217 | 335.93 | 0 | 0 | 1.9334 | 4 |
| servo | P5 event | 0.053164 | 0.01452 | 335.93 | 0 | 0 | 1.9539 | 2.15 |
| servo | P5 frequent | 0.052768 | 0.013963 | 335.93 | 0 | 0 | 1.9342 | 8 |
| servo | P5 initial | 0.053164 | 0.014861 | 335.93 | 0 | 0 | 1.93 | 1 |
| servo | P5 noisy | 0.055595 | 0.042776 | 335.92 | 0 | 0 | 1.9257 | 4 |
| servo | P5 periodic | 0.053164 | 0.014746 | 335.93 | 0 | 0 | 1.9279 | 4 |
| unreachable | B0 PI | 0.50345 | 0.012917 | 362.54 | 13.148 | 0 | 0.010953 | 0 |
| unreachable | B1 continuous | 0.65883 | 0.007955 | 344.31 | 0.0037276 | 0.21417 | 23.584 | 0 |
| unreachable | B1 ukf | 0.66176 | 0.0080068 | 344.11 | 2.7001e-05 | 0 | 1.7908 | 0 |
| unreachable | B2 both | 0.6638 | 0.010598 | 344.14 | 0.00015598 | 0 | 1.8204 | 0 |
| unreachable | B2 estimator | 0.66135 | 0.010663 | 344.1 | 9.6588e-05 | 0 | 1.7828 | 0 |
| unreachable | B3 assumed inventory | 0.66147 | 0.0086399 | 344.14 | 0.00025534 | 0 | 1.7792 | 0 |
| unreachable | B3 known inventory | 0.66147 | 0.0086399 | 344.14 | 0.00025534 | 0 | 1.7834 | 0 |
| unreachable | B4 mhe | 0.66171 | 0.0085724 | 344.02 | 0 | 0 | 1.8196 | 0 |
| unreachable | B5 true state | 0.6621 | 0 | 343.91 | 0 | 0 | 1.771 | 0 |
| unreachable | P1 expected | 0.66176 | 0.0080068 | 344.11 | 2.7001e-05 | 0 | 4.6204 | 0 |
| unreachable | P2 regret | 0.66176 | 0.0080068 | 344.11 | 2.7001e-05 | 0 | 4.5877 | 0 |
| unreachable | P3 adaptive regret | 0.6638 | 0.010598 | 344.14 | 0.00015598 | 0 | 4.6753 | 0 |
| unreachable | P4 hybrid | 0.6638 | 0.010598 | 344.14 | 0.00015598 | 0 | 6.507 | 0 |
| unreachable | P5 delayed | 0.66178 | 0.014746 | 344.11 | 2.0583e-05 | 0 | 1.7833 | 4 |
| unreachable | P5 event | 0.66179 | 0.012642 | 344.11 | 0 | 0 | 1.8096 | 2 |
| unreachable | P5 frequent | 0.6618 | 0.012081 | 344.11 | 6.4189e-06 | 0 | 1.7721 | 8 |
| unreachable | P5 initial | 0.66176 | 0.01284 | 344.11 | 2.7001e-05 | 0 | 1.7771 | 1 |
| unreachable | P5 noisy | 0.66171 | 0.042325 | 344.12 | 5.9959e-05 | 0 | 1.7749 | 4 |
| unreachable | P5 periodic | 0.66172 | 0.012806 | 344.12 | 2.7001e-05 | 0 | 1.7809 | 4 |
