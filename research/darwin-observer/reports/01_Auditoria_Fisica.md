# Relatório 1 - Auditoria física

Data: 17/10/2026. Fonte primária: walteryanko/yanko-process-lab, commit f4444d4c238291b8633743930249ee387ad94541. O arquivo model.ts foi recuperado, preservado em vendor e comparado numericamente com a transcrição Python do Oracle-KF v0.1. O projeto é independente; o núcleo estável original não foi alterado.

## Identidade do processo

CSTR de hidrólise de óxido de propileno. Estados x = [CA, CB, CC, CM, T, Tt]. Medições y = [T,Tt]. A + B -> C; metanol é inerte. Concentrações em kmol/m³; temperaturas em K; vazões molares em kmol/h; tempo em horas. mw significa vazão molar, não kg/h. Não foram usadas concentrações como medições operacionais.

## Equações preservadas

v0 = FA/rhoA + FB/rhoB + FM/rhoM; D = v0/V.

r = k0 exp[-E/(R T)] CA.

dCA/dt = FA/V - D CA - r; dCB/dt = FB/V - D CB - r.

dCC/dt = r - D CC; dCM/dt = FM/V - D CM.

q = mw cpB (Ta - T) [1 - exp(-UA/(mw cpB))].

dT/dt = [q - (FA cpA + FB cpB + FM cpM)(T-T0) + (-Delta H) r V] / [V sum(Ci cpi)].

dTt/dt = [mw cpB (Ta-Tt) - q] / (rhoB Vt cpB).

A temperatura Tt não realimenta o balanço do reator. Essa assimetria térmica histórica foi mantida; substituí-la por q = UA(Tt-T) mudaria o modelo e sua observabilidade. Os termos químicos mantêm a direção estequiométrica [-1,-1,+1,0]. Os invariantes reacionais CA+CC e CB+CC têm somente transporte na derivada.

## Duas variantes completas

| Grandeza | Tabelado primário | Histórico completo | Unidade |
| --- | --- | --- | --- |
| cpA / cpB / cpC / cpM | 146,5 / 75,4 / 192,6 / 81,6 | 146,538 / 75,3624 / 192,5928 / 81,642 | kJ/(kmol K) |
| rhoA / rhoB / rhoM | 14,8 / 55,3 / 24,7 | 0,923 / 3,45 / 1,54 × CUNIT | kmol/m³ |
| V / Vt | 1,89 / 1,1 | 1.891825668 / 1.100109490 | m³ |
| UA | 30.385,6 | 30385.608555456 | kJ/(h K) |
| E | 75.362,4 | 75.362,4 | kJ/kmol |
| R | 8,314 | 8,3191716 | kJ/(kmol K) |
| k0 | 16,96 × 10^12 | 16,96 × 10^12 | 1/h |
| -Delta H | 91.556,9 | 83.736 | kJ/kmol |
| Arrhenius | T em K | T em K + 0,1833333333 | K |

Na variante histórica, CUNIT = 0,45359237/0,028316846592; todas as densidades, capacidades, volumes, vazões, temperaturas e constantes foram convertidas conjuntamente. Não foi criado um híbrido entre a entalpia histórica e os demais valores tabelados.

A variante principal, também usada no checkpoint Oracle-KF, tem equilíbrio [  0.366134  33.768061   2.539426   3.63395  340.303489 319.202323]. A variante histórica completa tem equilíbrio [  0.607025  33.989102   2.295765   3.628487 332.333618 314.397585]. A diferença de cerca de 8 K não é um erro de solver: nasce das fontes físicas diferentes. A variante NAKE calibrada, documentada no relatório recuperado, usou entalpia efetiva de -84.138,654 kJ/kmol; ela não foi usada como planta desta campanha.

## Integração e regressões verificadas

Planta: RK4 com seis subpassos por Ts = 0,015 h. Observadores: RK4 com três subpassos. O teste independente usa DOP853 com tolerâncias apertadas. Há testes contra derivadas e passos do Oracle-KF e contra a transformação SI histórica recuperada. Os resíduos de equilíbrio ficam abaixo de 1e-9 nas unidades de cada balanço. Os testes não executam MATLAB/Simulink.

O UKF novo inclui Q antes de calcular a covariância da medição linear e usa atualização de Joseph. Essa escolha evita a inconsistência existente na variante inicial do Multiverse-MPC, que não incluía Q na covariância de observação. A implementação Oracle-KF v0.1 recuperada já possui a atualização linear com Q. Todos os comparadores desta campanha compartilham o mesmo integrador, Q, R e prior inicial, salvo a dimensão de parâmetros do UKF adaptativo.

## Ativos recuperados e limites

Recuperados: código público do ProcessLab; checkpoint Oracle-KF v0.1; dissertação de Brandão (2019), equações 53-55 e Tabela 1; arquivos modeloCT.m e NMPC_Fmincon.m; núcleo Python histórico; relatórios RSI-ProcessLab, AIRE-NMPC e NAKE. RSI registra o núcleo químico invisível; AIRE registra discrepâncias de conversão e configuração dos filtros; NAKE registra uma calibração distinta. Esses resultados anteriores não foram somados aos dados novos. Não foi recuperado nesta execução o aplicativo desktop completo ProcessLab Studio nem executado seu instalador.

O NMPC deriva diretamente do controlador público: p = 57, m = 6, Ts = 0,015 h, Qe = 0,8 e Rdu = 0,2, com busca por coordenadas. A origem MATLAB/SQP foi preservada para auditoria, mas não se afirma identidade entre os solvers. O limite térmico do estudo é 344 K e os limites de mw são 22,7 a 1.366,2 kmol/h; não constituem certificação de uma planta real.
