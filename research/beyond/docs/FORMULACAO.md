# Formulação e limites de informação

## Informação útil depende da decisão

Seja \(\xi=(x_0,\theta)\) a condição desconhecida e \(b_t\) uma distribuição ou conjunto compatível com o histórico térmico e as entradas aplicadas. A escolha de operação z e política causal \(\pi\) deve considerar

$$
\min_{z,\pi}\ \mathbb E_{\xi\sim b_0}\!
\left[\int_0^H \ell(x,u,z)\,dt+c_{\rm trans}+c_{\rm amostra}\right],
\quad \dot x=f(x,u,\theta),\quad u=\pi(y_{0:t},u_{0:t-1},z),
$$

sob limites de estados, atuadores, velocidade, recursos e risco. Um conjunto viável de pontos estacionários não é um conjunto invariante, e tampouco comprova a viabilidade das trajetórias entre os pontos.

Uma medida operacional de falta de informação é o arrependimento

$$
\mathcal R(b,z)=\min_{\pi}\mathbb E_b[J(\xi,z,\pi)]
 -\mathbb E_b[\min_{\pi}J(\xi,z,\pi)] .
$$

O valor de um experimento a é a redução esperada desse arrependimento, descontados sua perturbação produtiva, riscos, tempo e custo. A matriz de Fisher é um instrumento local de projeto, não essa definição de valor.

A implementação desta campanha aproxima partes do problema: mapas locais de sensibilidade; simulação de políticas fixas; identificação MAP com prior comum; e escolha entre 17 decisões estacionárias de refrigeração para uma mesma qualidade futura. O arrependimento dessas 17 decisões não é arrependimento do controlador dinâmico ótimo nem lucro industrial. A otimização conjunta global sobre todas as políticas não foi resolvida.

## Três formas de reduzir erro

Reduzir a covariância de parâmetros mediante observações, reduzir a sensibilidade da qualidade a esses parâmetros e dissipar a influência de inventários iniciais são mecanismos diferentes. A comparação usa as mesmas escalas físicas de prior e ruído em toda a paisagem. A covariância posterior local é \(P=(I+F)^{-1}\), em coordenadas previamente normalizadas. A variância de qualidade é \(gPg^T\), com g propagado até a variável de decisão.

Para evitar favorecer artificialmente uma fase final de oscilação, o ensaio espectral também avalia uma qualidade estacionária futura no mesmo ponto nominal para todos os sinais. Parâmetros térmicos e inventários iniciais entram como perturbações desconhecidas na matriz completa. Não se calcula informação química fingindo que essas perturbações são conhecidas.

Sensibilidades estacionárias usam \(\partial x_{ss}/\partial\theta=-f_x^{-1}f_\theta\). Perto de singularidades, uma sensibilidade grande pode sinalizar proximidade de bifurcação ou invalidade da aproximação linear para o tamanho do prior. Nenhum mapa local é promovido a incerteza global certificada.

## Contraexemplo exato no PG

Considere duas condições iniciais com a mesma concentração A, as mesmas temperaturas e

$$
\delta C_A=\delta T=\delta T_t=0,\qquad
c_{pB}\delta C_B+c_{pC}\delta C_C+c_{pM}\delta C_M=0 .
$$

Essas condições mantêm a mesma capacidade térmica total e a mesma taxa de reação. Para toda entrada comum admissível, a diferença química obedece

$$
\delta c(t)=\delta c(0)\exp\!\left[-\int_0^t D(s)\,ds\right].
$$

Os dois registros térmicos são idênticos. Uma política que observa somente esses registros aplica as mesmas ações aos dois reatores. Há dois modos químicos estruturalmente invisíveis. A excitação pode identificar outras direções, mas não esses modos.

Para uma especificação \(|C_C-C_C^\star|\leq\epsilon\), uma condição necessária de garantia simultânea é \(|\delta C_C(t)|\leq2\epsilon\). A largura inicial de 0,5 kmol/m³ e a banda de ±2% da qualidade nominal produzem um limite inferior de 0,239973 h sob a maior diluição permitida; na alimentação nominal, 0,256463 h. São aproximadamente 14,4 e 15,4 minutos. Nem refrigeração perfeita nem um estimador mais complexo removem esse obstáculo informacional. A restrição de velocidade da alimentação pode tornar a espera necessária ainda maior.

Esquecer não é identificar: a distribuição do inventário original não precisa contrair na direção invisível, embora a qualidade atual se torne menos dependente dele. Se os mesmos volumes e alimentações médias mantêm \(\int D\,dt\), não é possível melhorar a separação final dos gêmeos apenas reordenando as entradas. Pode-se alterar a ambiguidade acumulada e o custo transitório.

## Coordenadas úteis à decisão

O quociente \(z=(C_A,H,I,T,T_t)\), com \(H=\sum_j c_{pj}C_j\) e \(I=C_A+C_C\), fecha uma dinâmica de cinco estados e preserva a qualidade \(C_C=I-C_A\). Uma direção química irrelevante ao objetivo é removida. O estado I continua não observado termicamente; reduzi-lo a uma constante conhecida seria adicionar informação.

A covariância inicial do modelo reduzido é a projeção \(LP_0L^T\) do mesmo prior. A equivalência das trajetórias foi verificada numericamente; não foi demonstrado um novo controlador reduzido superior. No EB, as duas coordenadas invariantes seguem balanços de renovação. Não se confundiu posto estequiométrico dois com dois parâmetros cinéticos individualmente identificáveis.

## Controlabilidade inferencial como condição de interseção

Para cada condição \(\xi\) de uma classe observacional, denote por \(\Pi_\epsilon(\xi,z)\) as políticas causais que atendem à especificação com os limites físicos. Uma garantia comum exige

$$
\bigcap_{\xi\in\mathcal E(y,z)}\Pi_\epsilon(\xi,z)\ne\varnothing .
$$

Mudar z pode ajudar de três maneiras: separar registros relevantes, diminuir a dispersão da qualidade dentro da classe ou ampliar a interseção de políticas aceitáveis. Pode também piorar a margem térmica e eliminar essa interseção. Esta é uma formulação útil de uma condição necessária; não se apresenta como novo teorema universal de suficiência.

O atlas numérico usa 51 rampas para alvos constantes de refrigeração. A significa que encontrou uma ação comum; B significa que encontrou ações individuais mas nenhuma comum nessa família; C da família significa apenas que a busca restrita falhou. Não é prova de inviabilidade física absoluta. Separadamente, o PG tem o limite exato \(C_C\le C_A+C_C\le\max(F_A/v)=3,666796\) kmol/m³, quando o inventário inicial também satisfaz essa desigualdade. Uma referência acima desse teto exemplifica impossibilidade física demonstrada.

## Observabilidade aparente produzida por entalpia inconsistente

No EB, seja N a matriz estequiométrica e R a derivada das taxas em relação às quatro concentrações, num equilíbrio com entrada fixa. O bloco químico linearizado é \(A_c=-DI+NR\). Se as entalpias satisfazem Hess, existe um vetor de entalpias de espécies h tal que \(\Delta H^T=h^TN\). Para qualquer \(v\in\ker(NR)\),

$$
A_cv=-Dv,\qquad \Delta H^TRv=h^TNRv=0.
$$

Na equação histórica do EB, os termos de alimentação e saída de energia não dependem das concentrações. Portanto \((v,0)\) é um modo não observado pela temperatura na linearização. Como o posto de NR é dois, esse núcleo tem dimensão dois e o posto observável é no máximo três. Uma entalpia fora do espaço estequiométrico pode produzir um acoplamento térmico espúrio e elevar o posto local para quatro.

A ablação foi verificada em doze equilíbrios entre 150 e 162 °C e alimentação de 0,9 a 1,1 do nominal. O quarto valor singular do registro térmico normalizado passa de aproximadamente 0,00118 para 9e-14 no nominal; o autovalor correspondente de Fisher era somente 1,4e-6. Assim, aumentar o posto formal não significava informação prática útil. A correção de Hess não reconcilia o restante do balanço de energia. Tampouco a análise linearizada prova indistinguibilidade não linear sob excitação. Fjeld, Asbjørnsen e Åström (1974) e Dochain, Couenne e Jallut (2009) são antecedentes diretos a revisar antes de alegar originalidade.

No PG, o posto linearizado nominal é três, embora o núcleo químico global demonstrado tenha dimensão dois. No equilíbrio, a derivada térmica em relação à capacidade calorífica total se anula porque o numerador do balanço é zero. Uma direção adicional pode ficar invisível somente nessa linearização. Não se extrapola esse posto local para todas as trajetórias excitadas.
