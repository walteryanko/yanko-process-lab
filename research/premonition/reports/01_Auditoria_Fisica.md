# 1. Auditoria física e matemática

YCS Premonition-MPC Lab v1.0. Referência do projeto: 18/10/2026. Pesquisa exclusivamente computacional. O modelo primário é a transformação SI do arquivo MATLAB modeloCT.m recuperado do ProcessLab; a tabela da dissertação e a variante calibrada são mantidas separadas.

Fontes: repositório walteryanko/yanko-process-lab; main f4444d4c238291b8633743930249ee387ad94541; histórico b55a46cd182c70100b50ff5e6c98ba82ed96a5a8; referência independente 88c40e65204fa6aa5bed02cc64fb15be79a53bb1. A dissertação de Brandão (UFCG, 2019) foi recuperada e consultada nas equações 33–55 e seções 4.1.1.5, 4.3.2.3 e 5.3.2.3. Seu PDF não é redistribuído neste pacote.

Convenções: x=[CA,CB,CC,CM,T,Tt]; u=[FA,FB,FM,mw,T0,Ta]. Concentrações em kmol/m³, temperaturas em K, vazões em kmol/h, tempo em h. Δt=0,015 h (54 s). O modelo assume fase líquida e volume constante. Extrapolações acima do domínio físico de fase não constituem previsões industriais.

v=FA/ρA+FB/ρB+FM/ρM; D=v/V; k=k0 exp[−E/(R(T+δ))]; r=k CA. Balanços: dCA/dt=(FA−vCA)/V−r; dCB/dt=(FB−vCB)/V−r; dCC/dt=r−DCC; dCM/dt=(FM−vCM)/V.

Q=mw CpB (Ta−T)[1−exp(−UA/(mw CpB))]; Ccap=V Σ Ci Cpi; Fcp=FA CpA+FB CpB+FM CpM. dT/dt=[Q−Fcp(T−T0)+H r V]/Ccap; dTt/dt=[mw CpB(Ta−Tt)−Q]/(ρB Vt CpB). A assimetria é preservada: Tt não realimenta Q. Alterar isso criaria outro modelo.

| Variante | H kJ/kmol | R kJ/(kmol K) | δ K | T nominal K |
| --- | --- | --- | --- | --- |
| original_MATLAB_SI | 83736 | 8.31917 | 0.183333 | 332.334 |
| tabled | 91556.9 | 8.314 | 0 | 340.303 |
| calibrated_332_3 | 84138.7 | 8.314 | 0 | 332.3 |

| Parâmetro | Valor SI | Parâmetro | Valor SI |
| --- | --- | --- | --- |
| cpA | 146.538 | cpB | 75.3624 |
| cpC | 192.593 | cpM | 81.6426 |
| rhoA | 14.785 | rhoB | 55.2637 |
| rhoM | 24.6684 | E | 75362.4 |
| R | 8.31917 | k0 | 1.696e+13 |
| heat | 83736 | V | 1.89183 |
| Vt | 1.10011 | UA | 30385.6 |
| offset | 0.183333 |  |  |

δ=0,183333333 K preserva T_F+460. O R convertido é 8,3191716, não 8,314. O calor de reação histórico é 83.736 kJ/kmol, enquanto a tabela usa 91.556,9. Nenhum ajuste foi aplicado ao primário. O nominal calculado é 0.607025, 33.9891, 2.29576, 3.62849, 332.334, 314.398.

344 K é o limite de estudo mantido no ProcessLab. A conversão exata de 160 °F seria 344,261111 K; essa diferença é explicitada, não ocultada. A dissertação associa 355,4 K à restrição prática por possibilidade de evaporação do óxido de propileno. Esses valores não são pontos de bifurcação nem certificação de segurança.

O UKF conserva α=0,001, β=2, κ=0, predição Euler e Q/R extraídos do Simulink, convertidos para SI. P0 e estado inicial são próprios da campanha em torno do equilíbrio, não uma reprodução da partida. A atualização linear T/Tt usa Joseph e regularização SPD. Ablações RK4, adaptativa e EKF foram executadas com as mesmas trajetórias.

O C0 preserva P=57, M=6, Qe=0,8, RΔu=0,2 e a busca coordenada do controller.ts público. Há substituição explícita da variante tabelada pelo primário histórico e um guard comum. Não se declara equivalência binária ao fmincon/MATLAB. O fonte arquivado de NMPC_Fmincon.m é referência, com o aviso de direitos autorais preservado.

Oracle-KF v0.1, NAKE, Schrödinger-KF e os checkpoints Quantum/Multiverse foram auditados. Usam família tabelada/calibrada ou modelos treinados incompatíveis com o primário histórico; não foram transplantados. RSI aponta para a pesquisa beyond na fonte recuperada. Não se atribuem ganhos a esses métodos nesta entrega.

Testes: balanços e invariantes; comparação com pg_reference.py; RK4 versus DOP853; Jacobiano analítico versus diferenças centrais; espectro completo versus forma reduzida; guard, fallback, causalidade, separação de sementes e JSON estrito. O resultado automatizado completo está em results/tests_final.log e results/tests.xml.
