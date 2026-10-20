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
