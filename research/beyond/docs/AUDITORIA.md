# Auditoria dos modelos e dos antecedentes

## Escopo e procedência

Esta investigação usa os reatores estudados por Walter Yanko de Aragão Brandão. Não substitui PG ou EB por um CSTR genérico. A execução nova ocorreu em Python; MATLAB, Simulink, Octave e Aspen não estavam disponíveis para executar os arquivos históricos. Foram recuperados os modelos, os arquivos nativos e os relatórios anteriores. Recuperação de um arquivo não equivale à validação de sua execução no software original.

O repositório walteryanko/yanko-process-lab foi inspecionado nas branches main, research/nake-calibrated-equilibrium e research/ethylbenzene-combinations. A nova branch research/beyond-conventional-operation-20261010 parte do commit 16aaafb63572d62e0e3341e26d8317b0651bdde0. Main estava em f4444d4c238291b8633743930249ee387ad94541 e a branch NAKE em f9ad5c7743094681eb66a78b47936eae0cf5cb48. Os resultados anteriores permanecem preservados.

| Material recuperado | Uso nesta investigação |
|---|---|
| Dissertação de 2019 e código MATLAB do PG | Equações, unidades, seis estados, custo original e cadeia de medição |
| Codigo_CSTR_Reproduzivel.zip e Relatorio_CSTR_Propilenoglicol.pdf | Fonte SI fiel, C0, C2, C3, diagnósticos e resultados anteriores |
| LBE_NMPC_SG_CSTR_Codigo_e_Relatorio.zip e relatório LBE | Modelo híbrido, controle econômico e limitações da proteção térmica |
| TFC_WALTER_FINAL_imprimir e TFC.zip | Reações EB, FiltroKalman.slx, backups Aspen e arquivos auxiliares |
| Pesquisa_Etilbenzeno_2026.zip, relatório e artigo EB | Reconstrução de cinco estados, estimadores, PI, cascata, NMPC e auditoria térmica |
| ICAC e MOSAIC v1.0 | Antecedentes de ambiguidade, oráculos, comutação, amostras químicas e resultados negativos |

Os hashes SHA256 e tamanhos dos 13 pacotes/PDFs materializados constam de provenance/recovered_sources.json. As cópias executáveis essenciais estão em vendor; os documentos acadêmicos integrais não são redistribuídos na branch pública. O Google Drive também contém a dissertação final em DISSERTACAO_WALTER. A orientação registrada no PG é de Heleno Bispo da Silva Júnior; Arioston Araújo de Morais Júnior aparece na banca e nos agradecimentos. No TFC, Arioston é o orientador. Nenhuma coautoria ou nova contribuição pessoal é atribuída por esta investigação.

## Quatro níveis de modelo

| Nível | PG | EB |
|---|---|---|
| Histórico | MATLAB/Simulink e dissertação de 2019; variantes de atuação devem ser diferenciadas | TFC e modelo Aspen, incluindo reciclos e separação |
| Reconstrução usada | Tradução SI da família que manipula refrigeração, com seis estados e trocador assimétrico | Primeiro reator, cinco estados, reciclo de entrada fixado e equação térmica literal |
| Variante reconciliada | Nenhuma nova planta reconciliada foi criada | Fechamento de Hess é apenas ablação; a reconciliação termodinâmica completa não foi concluída |
| Planta experimental | Não houve experimento físico | Não houve experimento físico nem execução do fluxograma completo |

O modelo PG arredondado de estudos antigos no GitHub não foi silenciosamente confundido com a tradução fiel mais recente. A variante do Drive em que FA/CA ocupam a cadeia de atuação/controle também não é intercambiável com a família arquivada de refrigeração/CC. As novas manipulações de alimentação são graus de liberdade operacionais declarados, comparados separadamente com a malha histórica SISO.

## Modelo PG

Os estados são \(x=(C_A,C_B,C_C,C_M,T,T_t)\). A reação é \(A+B\to C\), e M é inerte. Quantidade está em kmol, volume em m³, tempo em h, temperatura em K e energia em kJ. A conversão exata usa \(1\ {\rm lbmol}=0{,}45359237\ {\rm kmol}\), \(1\ {\rm ft^3}=0{,}028316846592\ {\rm m^3}\) e o pequeno deslocamento de 0,183333 K que preserva a expressão histórica \(T_F+460\).

Com \(D=v/V\), \(r=k(T)C_A\) e \(c_f=(F_A,F_B,0,F_M)/v\),

$$
\dot c=D(c_f-c)+(-1,-1,1,0)^T r,\qquad
v=F_A/\rho_A+F_B/\rho_B+F_M/\rho_M .
$$

O calor do trocador é \(q=m_w c_{pB}(T_a-T)[1-\exp(-UA/(m_wc_{pB}))]\). O balanço do reator usa q diretamente; o de \(T_t\) recebe q, mas \(T_t\) não realimenta \(\dot T\). Essa assimetria foi preservada. Um trocador simétrico convencional alteraria justamente a geometria de observação em investigação.

| Grandeza nominal | Valor |
|---|---:|
| \(C_A,C_B,C_C,C_M\), kmol/m³ | 0,607025; 33,989102; 2,295765; 3,628487 |
| \(T,T_t\), K | 332,333618; 314,397585 |
| \(F_A,m_w\), kmol/h | 36,287390; 453,592370 |
| Tempo de residência, h | 0,151336 |
| Produção nominal, kmol/h | 28,699053 |
| Remoção de calor nominal, kJ/h | 878251,455 |
| Limite principal | 160 °F = 344,261111 K |
| Limite posterior separado | 180 °F = 355,372222 K |

O limite de 180 °F não foi usado para aceitar trajetórias nesta campanha. A temperatura inferior de 290 K é apenas um limite do domínio de estudo. As faixas de FA, refrigeração e velocidades de atuação estão codificadas em models.py e no protocolo. FB, FM e T de alimentação são entradas conhecidas e ficam fixas nos ensaios novos; não foi simulada incerteza arbitrária em todos os feeds.

## Modelo EB

Os estados são as concentrações de etileno, benzeno, EB e DEB e a temperatura em °C. Arrhenius usa K. Tempo está em h, volume em m³ e energia em kcal. O volume é 200 m³.

$$
E+B\to EB,\quad E+EB\to DEB,\quad B+DEB\to 2EB .
$$

A matriz estequiométrica tem posto dois. A terceira coluna é a diferença entre a primeira e a segunda. Os invariantes de reação são \(B+EB+DEB\) e \(E+EB+2DEB\). Os três termos cinéticos foram mantidos; não se eliminou DEB para favorecer a produção desejada. A referência controlada é fração molar de EB, não concentração.

| Grandeza nominal | Valor |
|---|---:|
| \(C_E,C_B,C_{EB},C_{DEB}\), kmol/m³ | 0,037381; 4,632416; 1,966908; 0,372448 |
| Temperatura, °C | 160 |
| Vazões de E, B e reciclo, m³/h | 82,59918; 57,95784; 88,92402 |
| Tempo de residência, h | 0,871532 |
| Fração molar de EB | 0,280620 |
| Formação líquida de EB no R1, kmol/h | 451,188946 |
| Dever reconstruído, MW | 25,369791 |
| Envelope exploratório novo, °C | 140,85 a 165 |

A saída líquida de EB subtrai o EB trazido pelo reciclo; DEB exportado é reportado separadamente. A seletividade usada é formação líquida EB dividida pela soma dessa formação com a saída de DEB. Não é seletividade global da fábrica. O efeito posterior sobre reciclos e destilação não foi simulado.

A válvula histórica tem característica de igual porcentagem \(F_E=F_{\max}50^{s-1}\). Os baselines recuperados continuam usando essa conversão. As novas políticas usam a vazão como coordenada invertível da válvula, dentro de uma faixa mais estreita, com um limite adicional de velocidade em vazão. O segundo atuador é um dever térmico idealizado, herdado dos estudos exploratórios MIMO; sua existência, capacidade e dinâmica não foram certificadas. O piso de 140,85 °C apenas respeita a direção necessária de troca com vapor a 414 K. Não demonstra área de troca suficiente.

## Discrepância termodinâmica do EB

A auditoria anterior já identificara que os quatro valores usados como capacidades caloríficas coincidem com entalpia molar dividida por temperatura em °C, dentro de aproximadamente 13 ppm. \(h/T\) não substitui \(\partial h/\partial T\). O backup Aspen fecha a remoção de 9,087923 MW tanto pelo balanço de entalpias das correntes quanto pelo registro RES_Q do bloco, a 160,85 °C. A reconstrução literal requer 25,369791 MW a 160 °C. São modelos/estados diferentes; ajustar um escalar Q não valida suas derivadas.

A hipótese anterior de dividir os coeficientes de alimentação por 4,184 exige 1,645810 MW e não reconcilia o backup. Também há diferenças de densidade, contração e contabilidade das entalpias de reação. A presente pesquisa preserva essa conclusão. Não apresentou um modelo termodinâmico reconciliado como se fosse factual.

O teste novo deliberadamente incorreto troca a referência numérica °C por K sem transformar as entalpias e depois reajusta Q no ponto nominal. Ele absorve 141,297623 MW de deslocamento estático, mas muda \(\partial T_{ss}/\partial F_E\) de 1,514969 para 4,138456 °C por (m³/h). Isso mostra por que uma calibração estacionária pode esconder uma derivada errada. Não é uma planta física alternativa.

Os valores históricos \(\Delta H=(-27150,-26950,-205{,}5)\) kcal/kmol têm residual de ciclo de 5,5 kcal/kmol. O fechamento \(\Delta H_3=-200\) é testado isoladamente. Corrigir esse pequeno residual não corrige as capacidades caloríficas nem valida a seletividade inferida.

## Auditoria dos resultados anteriores

C2 era uma recomendação de compromisso no PG, não vencedor universal. C3 liderava uma agregação normalizada e C5 uma média absoluta; a reconstrução original vencia episódios históricos. A cobertura nominal de 95% de C2 ficou em aproximadamente 88% em cenários de mismatch, portanto não é garantia probabilística. A propagação determinística dos inventários de C3 depende de informação inicial favorável.

No EB, os estudos recentes já mostravam forte desempenho de cascata PI com feedforward e falsificavam supostos ganhos de NMPC obtidos com temperaturas incompatíveis com remoção de calor para vapor. Os ganhos finais de PI/FKE de 2016 não foram recuperados inequivocamente: B0R é uma reconstrução, não reprodução certificada do TFC.

ICAC e MOSAIC já haviam ensaiado ambiguidade de decisão, oráculos, comutação e medições químicas esparsas, sem dominância universal. O núcleo invisível do PG e sua dissipação por diluição também já estavam documentados. Esses resultados são antecedentes internos, não novas descobertas desta campanha.

Foram reexecutados C0, C2 e C3 no PG e B0R, cascata e NMPC com envelope no EB, com o mesmo simulador, entradas medidas, limites externos e cenários pareados. O adaptador acrescenta os mesmos limites de amplitude/velocidade e uma proteção térmica heurística aos baselines. Logo, essa comparação é uma adaptação sob condições comuns; os valores não devem ser atribuídos retroativamente à execução original MATLAB/Aspen. LSTM, NAKE e MHE foram recuperados/auditados nos arquivos anteriores, mas não receberam novo treinamento integral nesta campanha.
