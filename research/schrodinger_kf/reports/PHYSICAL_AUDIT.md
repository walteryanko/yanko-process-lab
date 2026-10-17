# Auditoria física e proveniência

## Variante escolhida

Fonte principal: `walteryanko/yanko-process-lab`, commit
`f4444d4c238291b8633743930249ee387ad94541`.
Os arquivos `model.ts`, `observer.ts`, `controller.ts` e `matrix.ts` foram
recuperados e preservados em `vendor/processlab/`, com a licença original.
O código selecionado é a transcrição literal **TABLED** da branch main.
Sua origem histórica é a dissertação de Walter Yanko de Aragão Brandão (2019),
[registro UFCG](https://dspace.sti.ufcg.edu.br/handle/riufcg/12684).
O portal não respondeu durante esta sessão; a auditoria direta usa o código
recuperado, não uma alegação de releitura integral do PDF.

O arquivo MATLAB original `pg_modeloCT.m` e a referência SI histórica foram
recuperados do commit `88c40e65204fa6aa5bed02cc64fb15be79a53bb1`.
O primeiro foi preservado byte a byte, inclusive sua codificação original.
MATLAB/Simulink não foram executados. A implementação histórica Python foi
inspecionada e seu equilíbrio recalculado. A versão calibrada NAKE foi
inspecionada no commit `f9ad5c7743094681eb66a78b47936eae0cf5cb48`.

## Unidades reais

| Grandeza | Unidade | Valor TABLED |
|---|---|---|
| CA, CB, CC, CM | kmol/m³ | variáveis |
| T, Tt, T0, Ta | K | variáveis; 297 e 289 nas entradas |
| FA, FB, FM | kmol/h | 36,3; 453,6; 45,4 |
| mw (refrigerante) | **kmol/h**, não kg/h | 453,6 |
| CpA, CpB, CpC, CpM | kJ/(kmol·K) | 146,5; 75,4; 192,6; 81,6 |
| ρA, ρB, ρM | kmol/m³ | 14,8; 55,3; 24,7 |
| UA | kJ/(h·K) | 30385,6 |
| q = −ΔH | kJ/kmol | **91556,9**, exotérmico positivo |
| V, Vt | m³ | 1,89; 1,1 |
| E | kJ/kmol | 75362,4 |
| R | kJ/(kmol·K) | 8,314 |
| k0 | h⁻¹ | 16,96×10¹² |
| Δt | h | 0,015 = 54 s |

O subscrito m de mw não significa vazão mássica: o produto mw·CpB só
possui a unidade correta com vazão molar nesta convenção.
Tempo está em horas; converter apenas Δt para segundos corromperia o modelo.

## Equações preservadas

v=FA/ρA+FB/ρB+FM/ρM, D=v/V, r=k0 exp(−E/(RT))CA.

    dCA/dt = FA/V − D CA − r
    dCB/dt = FB/V − D CB − r
    dCC/dt = r − D CC
    dCM/dt = FM/V − D CM
    Qcool = mw CpB (Ta−T) [1−exp(−UA/(mw CpB))]
    dT/dt = [Qcool − (FA CpA+FB CpB+FM CpM)(T−T0) + q r V] / [V Σ Ci Cpi]
    dTt/dt = [mw CpB(Ta−Tt)−Qcool] / [ρB Vt CpB]

O mesmo Qcool aparece com sinais opostos nos dois balanços. Tt não entra
no balanço de T. Não se substituiu a transferência histórica por UA(Tt−T).
As identidades para CA+CC e CB+CC cancelam a reação. CM é inerte.

## Variantes mantidas separadas

TABLED calcula T*=340,303489 K, aproximadamente 8 K acima do equilíbrio
historicamente citado de 332,3 K. A tradução fiel do MATLAB tem
−ΔH=83736 kJ/kmol e preserva T_F+460 como T_K+0,183333; seus Cp, R,
volumes, densidades e alimentações vêm de conversões mais precisas.
A variante NAKE ajusta o calor efetivo para forçar T*=332,3 K.
Essa calibração não prova recuperação de um parâmetro histórico.
Nenhum desses coeficientes foi misturado na campanha TABLED.
Os três conjuntos e equilíbrios estão quantificados em `physical_audit.json`.

O checkpoint Oracle-KF usa os mesmos coeficientes TABLED e UKF RK4; o
Multiverse v0.1 usa a mesma física, embora seu texto a contraste com a
variante histórica. Ambos foram lidos. O relatório RSI-ProcessLab foi
consultado e sua análise da assimetria e da direção não observável foi
confirmada por derivação e testes novos; seus resultados de RSI não são
atribuídos a esta campanha.

## Integração, limites e resíduos

A planta usa RK4 com subpasso máximo 0,001 h. Os filtros usam 0,0025 h,
comparado a DOP853 e ao código TypeScript; não é Euler oculto. O baseline
histórico separado mantém Euler. O controlador usa o mesmo RK4 dos filtros.
Guardas rejeitam concentrações negativas e temperaturas fora de [150,600] K.
Esse intervalo é um domínio numérico; os limites de estudo 344 K e de parada
355,4 K são distintos. mw permanece em [22,7;1366,2] kmol/h.

O ruído de processo é discreto e aditivo, com Q publicado de main. Portanto,
uma trajetória estocástica não conserva exatamente os invariantes químicos
da solução determinística. Os resíduos da dinâmica são avaliados separando
esse incremento conhecido. Não se ajusta a física para absorver os erros
de observação. Rejeições de amostras, falhas e fallbacks são contabilizados.

## Escalonamento

O custo OT usa s=[1,40,3,4,10,10], em kmol/m³ e K respectivamente: ordens
de grandeza de concentração e excursões térmicas de engenharia. É uma
escolha explícita de métrica, não um ajuste escondido da física. A sensibilidade
a ε é medida em desenvolvimento. A ponte usa escalas de desvio padrão da
previsão, que definem sua referência Browniana; isso é diferente do custo OT.

## Observabilidade

Para δCA=0 e Σ Cp_i δCi=0, estados com as mesmas temperaturas têm reação
e capacidade térmica iguais. Sob entradas idênticas, δc(t)=δc(0)exp(−∫Ddt),
enquanto δT=δTt=0. Há pelo menos duas direções exatas invisíveis em composição.
No equilíbrio sem excitação pode haver perda adicional de posto local.
Os dois Gramians, parado e excitado, são publicados. A diminuição do erro
por lavagem não deve ser confundida com identificação pelos sensores.
