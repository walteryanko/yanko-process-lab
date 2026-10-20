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
