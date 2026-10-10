# Síntese da investigação

Esta investigação testou se modificar a operação facilita o controle de composição sem medição química contínua nos modelos PG e EB recuperados. A resposta é condicional: houve ganho informacional e menor erro em parte do domínio PG, mas nenhum regime seguro e dominante nos dois processos.

Os quatro experimentos principais foram executados e aprofundados segundo os resultados. A periodicidade perdeu para um estacionário encontrado com recursos comparáveis. Com a mesma referência química e o mesmo PI, o erro PG caiu 41,8%, acompanhado de 2,24% menos produção e violações térmicas. No EB, a melhora praticamente desapareceu. Uma pequena inconsistência de Hess acrescentava uma direção de observabilidade local espúria.

O pacote reúne auditoria, revisão crítica, formulação, hipóteses, código, dados brutos, figuras, baselines, resultados negativos e reprodução. A contribuição mais madura é metodológica. As novas evidências são de simulação Python; MATLAB, Aspen e planta real não foram executados. A autoria científica e qualquer submissão precisam de revisão dos pesquisadores.

| Evidência executada | Quantidade |
|---|---:|
| Projetos de excitação e ajustes MAP | 44 e 192 |
| Candidatos periódicos e linhas de mapa | 144 e 376 |
| Malhas principais rotuladas e rodada de qualidade comum | 2304 e 216 |
| Baselines recuperados reexecutados | 180 |
| Malhas com amostra atrasada e supervisão | 192 e 120 |
| Testes científicos e verificações DOP853 | 15 e 10 |

As contagens não são tamanhos de amostras independentes. As diferenças e intervalos pareados estão no capítulo de resultados. Os limites históricos e exploratórios permanecem separados.

\clearpage
\tableofcontents



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

\clearpage

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


# Revisão crítica e lacunas científicas

## Escopo da busca

A busca internacional foi encerrada em 10 de outubro de 2026. Abrangeu os termos propostos, seus sinônimos e cadeias de referências sobre operação periódica, resposta não linear em frequência, invariantes, observadores térmicos, controle auto-otimizante, identificação ativa segura, amostragem e valor da informação. É uma revisão dirigida, não uma revisão sistemática com cobertura exaustiva. O registro de fontes distingue texto integral, resumo do editor, repositório institucional e preprint. Não se infere ineditismo da ausência de um resultado na busca.

A questão operacional tem antecedentes fortes. Há inclusive um artigo de 2013 sobre oscilações em um CSTR de propilenoglicol [R01]. Nele, a vazão de saída é um grau de liberdade relevante; isso não equivale ao benchmark de volume fixo aqui preservado. A resposta não linear em frequência já serve para estudar mecanismos e ganhos periódicos [R02-R05]. Os trabalhos recentes de metanol [R06-R08] reforçam que os ganhos dependem do sistema, da cinética e do regime; não justificam transferir conclusões ou parâmetros para PG/EB.

A conexão entre invariantes, observabilidade e controlabilidade remonta pelo menos a Fjeld, Asbjørnsen e Åström [R09]. Extensões de reação/fluxo e controladores em coordenadas de avanço são anteriores a esta campanha [R10, R11, R22]. Modelagem por entalpia já foi associada ao projeto de observadores [R12]. Portanto, nem “controlar em coordenadas de reação” nem “usar temperatura para inferir química” constitui, isoladamente, novidade.

Escolher variáveis e condições operacionais para reduzir perda econômica também se relaciona ao controle auto-otimizante [R13]. A contribuição potencial precisa demonstrar o efeito adicional da informação incompleta sobre decisões, mantendo qualidade, recursos, atuadores e riscos comparáveis. Projeto de experimento voltado à decisão tem antecedentes recentes [R20, R21], ainda em preprint no recorte consultado. A formulação em termos de arrependimento é compatível com essa literatura; não foi inventada aqui.

## Lacunas e testes por experimento

**Experimento 1.** NFR e excitação multivariável já são conhecidos [R02-R05]. A lacuna específica era saber se sinais admissíveis melhoram decisões de composição nestes modelos, com inventários e parâmetros térmicos desconhecidos. Hipótese: algum sinal supera entrada constante e excitação convencional no erro futuro e no arrependimento, sem violar limites. O mínimo executado foi a triagem Fisher seguida de MAP não linear e decisões comuns com sementes novas. Potencial publicável: protocolo aplicado e resultados negativos, condicionado a distinguir valor decisório de precisão paramétrica; não uma nova espectroscopia.

**Experimento 2.** Operação periódica, fases de entradas e restrições de recursos têm literatura consolidada [R01-R08, R15]. A lacuna local era um comparador estacionário com os mesmos recursos reais após limitação de velocidade. Hipótese: existe ciclo seguro que domina esse comparador. O teste mínimo foi simular ciclos até fechamento e buscar um estacionário com consumo igual ou menor. A hipótese não foi sustentada na família examinada. O resultado negativo é útil, mas não prova impossibilidade de toda operação periódica.

**Experimento 3.** Baixa perda sob incerteza e seleção de variáveis são próximas de controle auto-otimizante [R13]. Faltava um mapa conjunto de produtividade, sensibilidade química e ambiguidade para os benchmarks preservados. Hipótese: há regiões produtivas menos sensíveis, independentemente de serem mais observáveis. O teste mínimo foi derivação implícita, prior físico fixo e posterior separado. A confirmação é local; publicar exige demonstrar utilidade em malha fechada e não apenas um mapa colorido.

**Experimento 4.** Projeto de experimento e controle sob informação incompleta antecedem a proposta [R13, R16, R20, R21]. A diferença pretendida é escolher o regime para reduzir o conjunto de decisões conflitantes, incluindo transições. Hipótese: trocar somente o regime melhora uma política congelada em cenários novos. O teste mínimo foi pareamento por sementes, referência comum e registro de riscos/custos. PG mostrou compromisso favorável ao tracking, mas inseguro em parte dos casos; EB não confirmou o ganho com a mesma qualidade. Há material metodológico, sem princípio universal validado.

**Experimento 5.** Dissipação de invariantes por renovação é conhecida [R09-R11] e já aparecia no acervo interno. A lacuna é quantificar seu custo sob recursos iguais. Hipótese: reordenar a alimentação acelera a redução da ambiguidade terminal. Gêmeos exatos e três sinais com a mesma renovação refutaram essa possibilidade para os modos demonstrados. A eventual contribuição está no limite operacional explícito e na comparação causal, não em redescobrir a diluição.

**Experimento 6.** Controle por histórico e dados tem antecedentes, incluindo DeePC [R17]. Testou-se somente uma política térmica compacta com filtro e integral, que ignora a estimativa química disponível em paralelo. Hipótese: decisões úteis dispensam reconstrução de todos os estados. Os testes sustentam utilidade local, mas não suficiência global da memória nem superioridade sobre NMPC. Um artigo de nova arquitetura não se justifica.

**Experimento 7.** Horários de amostragem robustos já foram estudados [R18]; ICAC/MOSAIC também são antecedentes internos. A lacuna aqui é o efeito causal de uma amostra atrasada no controle futuro. Hipótese: a seleção por variância supera um horário fixo. O mínimo foi escolher espécie/instante sem acessar verdade online, então atualizar o filtro no passado e refazer a propagação. A seleção não dominou universalmente. A contribuição possível é expor a diferença entre valor estatístico e valor decisório, incluindo atraso.

**Experimento 8.** Restrições impostas por invariantes à observação são clássicas [R09]. Faltavam contraexemplos explícitos ligados à banda de qualidade e a ações comuns. Hipótese: gêmeos indistinguíveis impedem uma garantia imediata. No PG há prova e limite temporal; no EB há pares aproximados e distância do registro completo. O caso EB não é prova de impossibilidade estrutural. O limite PG é uma aplicação rigorosa, com antecedente interno reconhecido.

**Experimento 9.** Avanços e invariantes já produzem representações úteis a estimação/controle [R10, R11, R22]. A lacuna local era uma redução que preservasse a qualidade sem favorecer o prior inicial. Hipótese: um quociente de cinco estados PG reproduz a qualidade do modelo de seis. A igualdade foi verificada com covariância projetada. Ainda não há evidência de ganho computacional ou de controle que justifique uma nova contribuição algorítmica.

**Experimento 10.** Modelagem por entalpia [R12] e reconciliação termodinâmica [R23] são antecedentes. A lacuna encontrada é o efeito de inconsistências térmicas sobre a suposta informação química. O mínimo executado foi fechar Hess, comparar o núcleo químico/temperatura e perturbar deliberadamente uma referência de entalpia, com refit nominal. Ambos revelaram artefatos que a calibração estática não elimina. Esta é uma candidata forte a nota metodológica, mas a originalidade internacional da proposição precisa de revisão adicional.

**Experimento 11.** Bandas mortas e regiões de controle já integram ferramentas de controle preditivo [R19]. A lacuna local era verificar se esperar ou moderar atuação ajuda diante do núcleo invisível, contabilizando produção perdida. Hipótese: uma política conservadora domina a correção contínua quando a informação é frágil. O mínimo comparou espera, zona morta e gate com as mesmas realizações. Não houve dominância universal; a covariância do filtro não é certificado de confiança.

**Experimento 12.** Viabilidade e aprendizagem ativa segura têm fundamentos anteriores [R16, R24]. A lacuna operacional é separar insuficiência de informação de impossibilidade física, sem chamar falha numérica de prova. O mínimo foi uma família de ações comuns para gêmeos e limites analíticos PG, acrescida de cenários adversos. O atlas é local; não é um núcleo global de viabilidade. A classificação explícita dos níveis de evidência pode sustentar a metodologia experimental.

## O que a revisão permite afirmar

Não foi demonstrado um fenômeno físico novo. Há uma campanha nova nestas reconstruções, com controles de confusão que alteram as conclusões: recursos reais dos ciclos, mesma qualidade, priors iguais, temperaturas históricas e consistência estequiométrica da informação. O antecedente internacional mais próximo da candidata H26 combina [R09] e [R12]; [R23] mostra que conciliar propriedades com leis físicas também é trabalho estabelecido. A demonstração específica de posto espúrio no EB é evidência adicional, não autorização para anunciar um novo princípio geral.



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


# Cobertura executada e limites

## Sequência de pesquisa

A recuperação e a auditoria precederam os novos experimentos. O protocolo inicial foi escrito localmente antes das simulações, sem registro externo ou alegação de pré-registro imutável. A triagem executou os experimentos 1 a 4. O aprofundamento escolheu informação com efeito em decisões, operação sob incerteza e falsificação termodinâmica, porque a periodicidade não havia superado o comparador estacionário.

Erros de avaliação foram encontrados e corrigidos: a limitação de velocidade deslocava as médias dos sinais periódicos; e o RMSE de um piloto de malha fechada alinhava incorretamente uma estimativa atual com a próxima verdade. As tabelas iniciais permanecem em results/pilot_v0, explicitamente excluídas das conclusões. A campanha de malha fechada foi repetida com o alinhamento correto e todas as trajetórias foram salvas. Também foi corrigido um excesso de velocidade no primeiro movimento de um sinal de esquecimento recentrado; a versão final usa modulação suave de média exatamente zero. Um erro de solução estacionária na identificação foi convertido em indicador de falha, sem apagar o cenário.

| Experimento | Execução efetiva | Limite que permanece |
|---|---|---|
| 1 Espectroscopia | 44 projetos, harmônicos, Fisher com perturbações desconhecidas e 192 ajustes MAP | Não identifica todo estado nem todos os mecanismos; amplitude segura apenas nos casos aceitos |
| 2 Periodicidade | 144 candidatos, partidas completas, igualdade de médias e comparador estacionário com recursos iguais ou menores | Não houve busca funcional global de toda forma de onda |
| 3 Baixa sensibilidade | 376 linhas de mapa, derivadas implícitas, prior fixo e produção mínima | Local e dependente do prior; não substitui análise global |
| 4 Região operacional | O1 a O4, PI congelado, estimador nominal, transições, supervisor e referências químicas iguais em rodada nova | Otimização conjunta global e segurança invariante não demonstradas |
| 5 Esquecimento | Gêmeos exatos, renovação acumulada e políticas de espera | Não identifica o inventário original |
| 6 Controle por saída | Memória compacta de temperatura e integral, sem composição online | Não foi treinado DeePC, rede recorrente nem política geral de custo futuro |
| 7 Amostra esparsa | Escolha de instante/espécie, precisão de 2%, atrasos e 192 malhas com atualização causal | Não há preço laboratorial real; um assay não corrige toda a cinética |
| 8 Gêmeos | Contraexemplo exato PG e pares EB com distância do registro térmico inteiro | No EB, aproximação numérica em entrada fixa; não impossibilidade universal |
| 9 Coordenadas | Quociente exato PG, conservação EB e prior projetado | Sem demonstração de superioridade de um novo controlador reduzido |
| 10 Termodinâmica | Fontes Aspen, refutação de ajuste escalar e ablação de Hess | Cp verdadeiro e planta reconciliada ausentes |
| 11 Inação | Zona morta, espera, gate de covariância e oráculo de estado | Covariância não calibrada universalmente; espera pode custar produção |
| 12 Adversários | Cinética, calor, inventários, bias, congelamento, perdas de amostra e cenários fora do domínio | Não exaustivo; sem prova geral de núcleo de viabilidade |

## Comparações realizadas

A campanha principal tem 2304 execuções rotuladas, incluindo pontos coincidentes O1 a O4 no EB e O2/O3 no PG. Isso não significa 2304 realizações estatisticamente independentes. As comparações de regiões usam 12 clusters de sementes, agrupando cinco famílias de cenário por semente. Os baselines recuperados somam 180 trajetórias; a rodada com a mesma referência química soma 216. A identificação usa 16 sementes da família ajustada e oito com bias de sensor não modelado. Amostragem e supervisão têm 12 sementes novas cada.

O oráculo de estado usa estados reais na política nominal, e é explicitamente rotulado. A identificação inclui um oráculo de parâmetros verdadeiros na escolha entre as 17 ações futuras. Não se implementou um oráculo global de controle ótimo com modelo e estado perfeitos; não se deve tratar um desses comparadores limitados como ótimo físico absoluto.

Os baselines históricos retêm seus ajustes recuperados; as políticas novas tiveram uma pequena busca comum de ganho na condição nominal. Isso é adequado para testar uma intervenção de região com algoritmo congelado, mas não é um campeonato com orçamento de tuning idêntico para todas as arquiteturas. Não foi promovida uma nova arquitetura vencedora.

## Integridade das métricas

IAE, ISE e ITAE usam integração discreta uniforme. A normalização de IAE é pela qualidade nominal e horizonte; não é a porcentagem de tempo fora da especificação. A produção considera a saída do modelo, e a energia é calor removido, não consumo elétrico certificado. O quadrado da vazão de refrigeração é apenas um substituto de esforço de bombeamento, sem curva real de bomba. Desgaste é aproximado pela variação total normalizada dos atuadores.

Na campanha inicial de regiões, cada ponto tem sua própria referência estacionária de qualidade. Essa diferença é explicitada e motivou a rodada adicional com qualidade exatamente igual. Os pontos com maior alimentação não recebem crédito como se o ganho viesse exclusivamente de informação. O custo de transição aparece nas trajetórias que começam no mesmo estado nominal.

Os intervalos bootstrap de 95% são pareados, com 4000 reamostragens de sementes inteiras. São intervalos exploratórios sem correção de multiplicidade. Ruídos gaussianos independentes e intervalos paramétricos sintéticos são hipóteses de estudo, não distribuições industriais estimadas.

Nenhuma violação foi eliminada para melhorar uma média. Candidatos periódicos inválidos não participam da lista admissível, mas permanecem nos dados brutos. Falha de uma busca estacionária ou de uma família finita de ações não prova inviabilidade global. Os testes independentes DOP853 verificam dez trajetórias selecionadas, incluindo os piores picos de temperatura e os melhores ciclos encontrados; não constituem certificado de segurança contínua.

## O que falta para publicação e aplicação

A revisão internacional é dirigida, com busca encerrada em 10 de outubro de 2026; não é uma revisão sistemática exaustiva nem cobre o restante do mês. Algumas fontes foram verificadas por resumo do editor e outras em texto integral. A ausência de um artigo localizado não demonstra ineditismo.

Há material para uma comunicação metodológica e um manuscrito exploratório. Antes de submissão, são necessários: revisão humana da argumentação e autoria; comparação mais ampla de antecedentes; revisão do desenho estatístico; e, para qualquer afirmação física sobre o EB, exportação/reconstrução termodinâmica consistente. Nenhuma submissão, atribuição de coautoria ou contato com terceiros foi realizado. O formato final do COBEQ 2027 não foi presumido nem inventado.

A verificação final da contabilidade de calor passou a usar os parâmetros reais salvos da planta simulada, incluindo a deriva temporal do supervisor. Os valores anteriores, calculados com parâmetros nominais sobre as mesmas trajetórias, foram preservados em pilot_v0 e excluídos. Estados, entradas, qualidade, produção, violações e decisões não mudaram. Esse acesso à verdade ocorre somente na avaliação offline, não nos controladores.


# Resultados e recomendação científica

## Conclusão principal

Modificar a operação alterou a informação e o desempenho do controle nos modelos recuperados, mas não produziu uma solução segura e dominante nos dois reatores. A conclusão mais forte é metodológica: a escolha de regime só pode receber crédito após separar aquisição de informação, redução de sensibilidade, dissipação de inventários, mudança de especificação e consumo de recursos.

O PG apresentou ganhos de inferência e menor erro com o mesmo PI térmico. Parte das condições mais favoráveis ao erro violou o limite histórico de 160 °F sob mismatch. O EB apresentou ganhos locais pequenos de informação, sem melhora clara de tracking quando a referência química foi mantida igual. Sua reconstrução continua termodinamicamente não reconciliada. Nenhuma nova trajetória é recomendada para planta real.

## Excitação e informação química

Foram avaliados 44 projetos térmicos, com amplitude, velocidade e tempo de observação documentados. As matrizes incluem inventário inicial e parâmetros térmicos desconhecidos. O alvo comparável é uma qualidade estacionária futura comum, evitando que a fase final do ciclo favoreça um sinal.

| Modelo | Desvio posterior sem excitação | Melhor senoide de alimentação | Redução local |
|---|---:|---:|---:|
| PG | 0,053965 kmol/m³ | 0,008416 kmol/m³, período de aproximadamente 4 residências | 84,4% |
| EB | 0,013264 em fração molar | 0,012321, período de aproximadamente 1 residência | 7,1% |

Esses números são previsões locais sob o prior adotado. Não são RMSE observado nem prova de identificação individual de todas as constantes. As correlações e desvios posteriores por parâmetro estão nos dados brutos. No PG, dois modos químicos permanecem exatamente invisíveis para qualquer entrada comum. No EB, três taxas de reação e efeitos térmicos continuam fortemente confundidos.

![Informação prevista para a mesma qualidade futura e escalas físicas fixas.](figures/spectra_information.png){width=95%}

A validação não linear fez 192 ajustes MAP: 16 sementes com a família correta e oito com bias térmico não modelado, quatro sinais e dois reatores. Somente temperaturas e entradas foram fornecidas ao ajuste. A decisão posterior escolhe entre 17 alvos de refrigeração; um oráculo de parâmetros calcula o arrependimento dessa família finita.

| Modelo e sinal | RMSE da qualidade futura | Arrependimento médio |
|---|---:|---:|
| PG constante | 0,016685 | 0,105895 |
| PG degrau | 0,010745 | 0,002931 |
| PG PRBS | 0,018125 | 0,033725 |
| PG senoide | 0,006019 | 0,004239 |
| EB constante | 0,010388 | 1,496401 |
| EB senoide | 0,009379 | 0,811008 |

No PG, a diferença de arrependimento senoide menos constante foi -0,101655, IC bootstrap pareado de 95% [-0,183124; -0,034132]. A redução média de 96,0% se refere a esse custo estacionário particular, não a IAE dinâmico nem a lucro. O degrau teve arrependimento médio ainda menor; não se demonstrou superioridade da senoide sobre a excitação convencional.

No EB, a redução média de 45,8% teve IC da diferença [-1,695583; 0,190828], incluindo zero. Além disso, alguns testes de degrau/PRBS infringiram o envelope térmico e não podem ser promovidos como projetos seguros. Os oito casos com bias fora da família ajustada permanecem separados no arquivo de contrastes. Não se usa convergência numérica do MAP como certificado de identificabilidade.

![Predição e decisão podem ordenar os projetos de excitação de maneiras diferentes.](figures/decision_value.png){width=93%}

## Periodicidade sob recursos comparáveis

A varredura examinou 144 candidatos senoidais, quadrados suavizados e multissenoidais, com amplitudes, fases e duty cycles variados. Foram aceitos 68 de 72 no PG e 45 de 72 no EB. A partida inteira foi verificada, e os últimos quatro ciclos foram usados depois de atingir fechamento periódico. A referência estacionária é o melhor ponto encontrado numa grade de alimentação e temperatura, com recursos iguais ou menores.

| Resultado máximo na família admissível | PG | EB |
|---|---:|---:|
| Ganho de produção sobre nominal | +0,1637% | +0,0305% |
| Ganho sobre estacionário comparável | -12,6217% | -0,8982% |
| Produção do ciclo correspondente, kmol/h | 28,7460 | 451,3268 |
| Produção do estacionário comparador, kmol/h | 32,8984 | 455,4171 |

O comparador é o melhor encontrado, não um ótimo global certificado. Isso basta para refutar a dominância dos ciclos examinados: existe uma alternativa estacionária melhor. Não basta para provar que toda periodicidade possível é inútil. Nenhuma melhora simultânea robusta de produção, seletividade e informação foi demonstrada.

Um piloto parecia produzir ganho PG de cerca de 5,4%, mas o limitador de velocidade deslocava a alimentação média. Esse resultado foi invalidado, arquivado e repetido após a correção. Calor removido, média e quadrado do atuador e variação total são reportados separadamente. No PG, a seletividade é identicamente um porque o modelo não contém reação secundária; não há base para anunciar melhoria de seletividade química.

![Todos os ciclos admissíveis ficaram abaixo de um estacionário encontrado com recursos comparáveis.](figures/periodic_comparison.png){width=95%}

## Paisagem de sensibilidade e operação

O mapa contém 376 linhas. As seleções exigem pelo menos 90% da produção nominal e margem térmica nominal de 2 K. O1 maximiza uma função econômica substituta; O2 reduz sensibilidade; O3 reduz incerteza posterior da qualidade; O4 combina critérios. Os pesos são declarados no código e não representam preços industriais.

| Modelo e região | Temperatura | Alimentação relativa | Produção, kmol/h | Sensibilidade relativa |
|---|---:|---:|---:|---:|
| PG nominal | 332,334 K | 1,0000 | 28,6991 | 0,13111 |
| PG O1 | 342,064 K | 1,1714 | 37,7523 | 0,06046 |
| PG O2 e O3 | 342,064 K | 0,8286 | 26,8989 | 0,03805 |
| PG O4 | 342,064 K | 1,1286 | 36,4043 | 0,05595 |
| EB nominal | 160 °C | 1,0000 | 451,1889 | 0,04981 |
| EB O1 a O4 | 161,714 °C | 0,8714 | 416,5168 | 0,04051 |

No PG, há regiões menos sensíveis, mas próximas do teto histórico. No EB, as quatro seleções coincidem para esses pesos e essa grade. A variação de preços substitutos muda a seleção. Menor desvio posterior pode decorrer de menor sensibilidade da qualidade, mesmo sem maior informação medida; O3 não deve ser interpretado como “máxima observabilidade”.

![Mapa PG com o ponto nominal marcado em vermelho. A sensibilidade usa escala logarítmica.](figures/landscape_PG.png){width=95%}

![Mapa EB da reconstrução do primeiro reator.](figures/landscape_EB.png){width=95%}

A campanha inicial de malha fechada contém 2304 execuções rotuladas. Para cada região, há cinética, parâmetros térmicos, incerteza combinada, falhas de sensor e casos fora do domínio. Os ganhos foram escolhidos na condição nominal e congelados. As comparações principais usam 12 clusters de sementes; regiões coincidentes não contam como evidência independente.

Com alimentação nominal PG e referência própria de cada região, 340 K reduziu o IAE normalizado em 41,0% e aumentou produção em 10,3%, mas a fração de trajetórias com violação térmica subiu de 8,3% a 15,0%. Isso não é um ganho operacional aceitável. No EB, a região O2 reduziu erro em 13,8%, com 7,8% menos produção e 12,9% menos alimentação. Essa comparação ainda mudava a qualidade desejada.

## Verificação com a mesma referência de composição

Para remover esse fator de confusão, uma rodada exploratória adicional usou 216 trajetórias, três famílias adversas e 12 sementes inéditas. A vazão de alimentação foi resolvida para que a qualidade estacionária nominal fosse exatamente a mesma em todas as regiões. O PI, suas memórias e os limites permaneceram os mesmos.

| Mudança em relação ao nominal | PG a 337 K | PG a 340 K | EB a 162 °C |
|---|---:|---:|---:|
| IAE normalizado | -30,85% | -41,82% | -0,26% |
| Produção média | -1,59% | -2,24% | -0,12% |
| Alimentação média | -8,33% | -11,98% | -0,72% |
| Calor removido | -25,08% | -40,61% | -1,67% |
| Trajetórias com violação | 4/36 | 3/36 | 0/36 |
| Violações no nominal pareado | 3/36 | 3/36 | 0/36 |

No PG a 340 K, o IAE normalizado caiu de 0,033747 para 0,019633. A diferença foi -0,014114, IC95% [-0,022466; -0,007626]. A produção caiu 0,638944 kmol/h, IC95% [-0,886668; -0,348401]. A média de passos com violação aumentou de 1,333 para 2,778, embora a diferença não seja estatisticamente resolvida neste pequeno conjunto. Houve picos acima de 355 K; o limite aceito continua 344,261 K. Portanto, nem o nominal nem a alternativa estão certificados para essa incerteza.

No EB a 162 °C, a diferença de IAE foi -0,000135, IC95% [-0,000890; 0,000626]. O efeito é compatível com zero. A 158 °C também não apareceu melhora clara. Esta rodada enfraquece a hipótese de um princípio operacional compartilhado que melhore tracking sem trocar controlador.

A redução de calor removido não é automaticamente economia de utilidades: depende de nível térmico, bomba e rede energética, ausentes dos modelos. Também não se pode declarar os recursos iguais nesta comparação; eles estão explicitamente alterados. A vantagem PG é um compromisso operacional específico.

![Efeitos com qualidade nominal comum e intervalos pareados.](figures/same_quality.png){width=95%}

## Baselines e combinações

Nos baselines recuperados, foram executadas 180 trajetórias com adaptadores e limites comuns. No subconjunto PG com inventário incerto e mismatch combinado, a 340 K, os IAE normalizados médios foram 0,03197 para C0, 0,02257 para C2, 0,02097 para C3 e 0,02232 para o PI térmico direto. No nominal, foram 0,07987, 0,03850, 0,03556 e 0,03826. São seis sementes e horizonte reduzido; C3 mantém uma hipótese favorável sobre invariantes, explicitada no adaptador.

No EB desse subconjunto, B0R, cascata e NMPC com envelope tiveram erros médios 0,04637, 0,04274 e 0,04369, contra 0,04552 do PI direto. Não houve uma nova arquitetura dominante. Não se repetiu treinamento integral de todos os modelos LSTM/NAKE/MHE recuperados. Tempos de execução são de um host compartilhado e incluem diagnósticos; não certificam uso em tempo real.

O supervisor adaptativo foi testado em 120 trajetórias com deriva paramétrica. No PG, a alternativa fixa a 337 K reduziu erro, mas a troca adaptativa violou restrições em parte dos casos. No EB, o supervisor preservou mais produção que a alternativa fixa, sem demonstrar superioridade universal. Os ensaios combinando periodicidade e mudança de região não mostraram ganho adicional limpo: alteraram médias de recurso e, em alguns casos, pioraram o erro. Nenhuma combinação foi promovida.

As transições começam no mesmo estado nominal e incluem rampas de quatro tempos de residência. Algumas transições PG foram admissíveis nas oito sementes examinadas; O1/O4 violaram limites em outras. Dois pontos estacionários admissíveis não certificam o caminho entre eles.

## Esquecimento e amostras químicas

Os gêmeos PG produziram registros térmicos idênticos sob sete tipos de entrada. A diferença inicial de 0,5 kmol/m³ segue exatamente a diluição acumulada, com erro numérico máximo de aproximadamente 1,2e-10. Aos 0,6 h, três sinais com renovação acumulada 3,964700 terminaram na mesma separação de 0,00948686 kmol/m³. Antecipar alimentação mudou a ambiguidade integrada em aproximadamente -0,53%; não revelou o inventário original.

O limite necessário de 14,4 minutos, usando a maior diluição permitida, estabelece um obstáculo informacional para garantir imediatamente a banda de ±2% a ambos os gêmeos. A escolha de regime pode reduzir a dependência do inventário, mas não reconstruí-lo retrospectivamente pela temperatura.

No EB, um par plausível começou com diferença de fração molar 0,12234 e terminou em 0,01999 após uma hora. O maior desvio térmico foi 0,0268 °C, contra desvio de ruído de 0,1 °C. A distância quadrática do registro inteiro foi 0,9405; sob hipóteses gaussianas independentes e probabilidades iguais, o erro ótimo de discriminação ainda é aproximadamente 31,4%. Isso é evidência prática para essa entrada fixa, não impossibilidade estrutural sob toda excitação.

A seleção de uma amostra química atrasada foi separada do protocolo estritamente térmico. Em 192 malhas, o benefício não foi universal. No PG, com atraso de meia residência, o IAE médio passou de 0,06530 sem amostra a 0,06453 com seleção por variância, enquanto amostrar em um quarto da campanha deu 0,06393. Com atraso de duas residências, a amostra selecionada piorou o IAE para 0,06637. No EB, o ganho foi pequeno e persistiram violações nas políticas inferenciais. Não se calculou benefício líquido monetário sem um custo laboratorial fornecido.

## Termodinâmica e observabilidade espúria

A discrepância entre o dever literal EB de 25,3698 MW e o backup Aspen de 9,0879 MW não foi resolvida por mudança de unidade ou ajuste escalar. A falsificação de referência de entalpia mostrou que refazer Q no nominal pode preservar o equilíbrio e, simultaneamente, mudar o ganho térmico de alimentação em 173,2%.

Um resultado adicional apareceu na análise de posto. O residual de Hess de apenas 5,5 kcal/kmol elevava o posto local do registro térmico de três para quatro. Corrigi-lo removeu a direção adicional em todos os doze equilíbrios testados. No nominal, seu autovalor de Fisher era aproximadamente 1,4e-6, portanto praticamente sem valor sob o prior/ruído adotado. É possível tornar um modelo aparentemente mais observável introduzindo uma inconsistência física. O diagnóstico por posto deve ser acompanhado da prova estrutural, de escalas e do valor real da informação.

Esse resultado não significa que o modelo com Hess fechado seja uma planta reconciliada. Não prova uma impossibilidade global para o EB excitado. Seu interesse está na auditoria de informação, com antecedentes clássicos reconhecidos.

![A ablação de Hess remove uma direção local com informação prática desprezível.](figures/hess_observability.png){width=90%}

## Classificação da contribuição e maturidade

| Classe | Avaliação nesta campanha |
|---|---|
| A Novo fenômeno físico | Não estabelecido; todos os novos resultados são simulados ou matemáticos |
| B Formulação matemática | Interseção de políticas admissíveis e separação dos mecanismos são úteis; novidade internacional não demonstrada |
| C Metodologia de operação | Candidata local no PG, limitada por margem térmica e compromissos de recursos |
| D Estratégia inferencial | Não apareceu uma arquitetura nova dominante |
| E Limite informacional | Limite PG rigoroso e ablação local de Hess EB; invariantes têm antecedentes internos e clássicos |
| F Metodologia experimental | Contribuição mais madura: comparadores com recursos e qualidade explícitos, gêmeos, oráculos e falhas preservadas |
| G Resultado negativo | Forte no escopo testado: periodicidade não domina estacionário; ganho EB desaparece com qualidade igual; combinações não promovidas |

A recomendação é desenvolver uma comunicação metodológica sobre seleção de regime sob informação incompleta e falsificações físicas. Um manuscrito exploratório acompanha o pacote, sem autoria nova atribuída e sem declaração de ineditismo. Antes de submissão são necessárias revisão humana e ampliação dos antecedentes, além da reconciliação EB para alegações sobre processo físico. A preparação para COBEQ 2027 depende do regulamento efetivo; nenhum formato ou aceite foi presumido.

\clearpage

## Respostas às dez perguntas

**P1.** Sim, no PG houve informação adicional útil sobre direções identificáveis e melhora da decisão futura; o núcleo invisível permaneceu. No EB, a melhora decisória não foi estatisticamente clara.

**P2.** Não frente ao estacionário com recursos comparáveis na família examinada. Os pequenos ganhos sobre o nominal não bastam.

**P3.** Sim, regiões localmente menos sensíveis foram encontradas nos dois modelos, condicionadas ao prior e ao domínio.

**P4.** Não existe equivalência geral. No PG os critérios selecionaram pontos diferentes; no EB coincidiram para certos pesos.

**P5.** Há candidatas no PG, mas não uma alternativa aprovada sob todos os limites. No EB, o ganho não persistiu claramente com a mesma qualidade.

**P6.** Sim, condicionalmente: o mesmo PI teve menor erro PG após mudança de regime. Perdas produtivas e violações impedem anunciá-lo como solução segura.

**P7.** O modelo PG permitiu aumentar produção usando uma política que não usa composição estimada, mas isso envolveu mudança da qualidade/regime e risco térmico. Não houve ganho simultâneo gratuito demonstrado.

**P8.** Há uma formulação compartilhada para distinguir informação, sensibilidade e renovação. Não houve validação de uma melhoria operacional comum aos dois processos.

**P9.** A ablação de Hess revelou observabilidade local espúria no EB. O falso ganho periódico por alteração da média e o teste de renovação igual também foram falsificações decisivas.

**P10.** Há potencial real de comunicação metodológica, com resultados negativos reproduzíveis. Ainda não há base para reivindicar um novo princípio universal ou uma tecnologia industrial pronta.


# Hipóteses adicionais e decisões de investigação

As hipóteses abaixo foram formuladas durante a campanha, a partir dos resultados da triagem. São exploratórias, não hipóteses confirmatórias previamente registradas. Uma conexão matemática conhecida não recebe automaticamente status de descoberta original.

| ID | Hipótese falsificável | Menor teste e resultado | Decisão |
|--------|----------------------------|------------------------------|------------------------|
| H13 | Reordenar a alimentação, mantendo a renovação acumulada, reduz a incerteza terminal do PG | Três sinais de 0,6 h; separação terminal igual a 0,00948686 kmol/m³ | Refutada para os modos invariantes; a ambiguidade integrada muda menos de 1% |
| H14 | Ajustar Q no nominal torna uma equação térmica independente da referência de temperatura | Mudança deliberadamente incorreta de referência, seguida de refit; ganho térmico de alimentação muda 173% | Refutada; diagnóstico de derivadas é necessário |
| H15 | É possível remover um estado químico sem perder a qualidade controlada | Quociente de cinco coordenadas, mesmo prior projetado; erro de qualidade abaixo de 5e-14 | Sustentada numericamente; antecedente geral são coordenadas invariantes |
| H16 | O melhor projeto de Fisher também minimiza o arrependimento de controle | MAP e 17 decisões futuras, sementes novas; senoide prevê melhor, degrau tem menor arrependimento médio PG | Refutada como regra de ordenação universal |
| H17 | A pequena inconsistência de Hess explica a maior parte da baixa informação do EB | 24 ensaios espectrais com e sem fechamento do ciclo | Não sustentada; efeito pequeno na incerteza do alvo futuro sob o prior usado |
| H18 | Um ponto robusto local continua seguro ao se deslocar até ele | Transições de quatro tempos de residência, estados iniciais comuns e mismatch | Refutada para algumas escolhas PG; pontos bons não certificam caminhos |
| H19 | Excitação periódica e região robusta produzem ganhos adicionais quando combinadas | PI térmico fixo, nominal/alternativa com/sem modulação | Não promovida; qualidade média piora e as médias de recursos diferem |
| H20 | Uma amostra escolhida para reduzir variância também melhora mais o controle que um horário fixo | Atualização química com atraso e replay causal em 12 sementes novas | Não sustentada universalmente; no PG a seleção piora com atraso de dois tempos de residência |
| H21 | Aumentar a precisão térmica remove todos os modos desconhecidos do PG | Produto da Fisher pela direção invisível e prova de equivalência | Refutada estruturalmente; ruído menor não cria a informação ausente |
| H22 | Uma política compacta de memória pode ser útil sem reconstruir composição | PI de temperatura filtrada e integral, sem usar o estado químico calculado em paralelo | Sustentada como candidato local; não resolve aliasing nem domina baselines |
| H23 | O ponto econômico e o robusto são necessariamente diferentes | Mapas O1 a O4 e variação de pesos econômicos | Refutada; no EB coincidem para os pesos iniciais, e mudam quando os pesos mudam |
| H24 | Uma inovação térmica alta identifica unicamente erro cinético | Equação do residual: calor, entalpia, remoção e bias podem gerar o mesmo escalar | Refutada como diagnóstico único; falta identificação causal multissinal |
| H25 | O benefício de escolher outra região persiste com a mesma qualidade nominal | Nova campanha com 216 trajetórias e sementes 70000 a 70011 | PG melhora tracking com menor produção e risco residual; EB não mostra diferença clara |
| H26 | Uma violação de Hess pode aumentar artificialmente o posto de observabilidade térmica | Doze equilíbrios EB em duas variantes, com escalas idênticas; posto local quatro passa a três ao fechar Hess | Sustentada nesta linearização; a direção adicional tem informação prática desprezível |

H13 e H14 são as duas experiências autônomas curtas principais. H15 a H25 ampliam a interpretação sem acrescentar uma nova arquitetura por estética. Foram descartadas, sem execução, propostas de usar caos intencional próximo de bifurcações, deslocamentos rápidos entre ramos e controle extremo com cortes de alimentação além da autoridade declarada: a triagem já mostrou perda de margem térmica e não havia um conjunto seguro certificado que justificasse aprofundá-las. Não se conclui que tais técnicas sejam impossíveis em outros equipamentos.

O antecedente interno mais próximo de H13, H15, H21 e H24 já estava nos relatórios CSTR/ICAC/MOSAIC. A novidade possível aqui é o protocolo comparativo e sua evidência adicional, não a descoberta retrospectiva dessas propriedades.

Na verificação final de H13, a primeira versão de degraus limitados e recentrados excedia a velocidade permitida no primeiro movimento. Ela foi excluída e preservada em pilot_v0. A versão final usa uma senoide de amplitude relativa 0,06, média exatamente zero e máximo de 0,837 do limite de velocidade, incluindo a partida. O resultado terminal permanece o mesmo.


# Referências verificadas


Os identificadores abaixo são usados também no manuscrito. Datas são de publicação, não de atualização do mecanismo de busca.

R01. Pérez-Polo, M. F.; Pérez-Molina, M. Increasing the reactant conversion through induced oscillations in a continuous stirred tank reactor by using PI control. *Journal of Process Control*, 23, 778-792, 2013. DOI [10.1016/j.jprocont.2013.03.007](https://doi.org/10.1016/j.jprocont.2013.03.007). Verificação: resumo do editor.

R02. Nikolić, D.; Seidel-Morgenstern, A.; Petkovska, M. Nonlinear frequency response analysis of forced periodic operation of non-isothermal CSTR using single input modulations. Part I: Modulation of inlet concentration or flow-rate. *Chemical Engineering Science*, 2014. DOI [10.1016/j.ces.2014.06.013](https://doi.org/10.1016/j.ces.2014.06.013). Verificação: editor e registro institucional; paginação omitida por divergência de registros.

R03. Nikolić, D.; Seidel-Morgenstern, A.; Petkovska, M. Periodic Operation with Modulation of Inlet Concentration and Flow Rate. Part I: Nonisothermal CSTR. *Chemical Engineering & Technology*, 39, 2020-2028, 2016. DOI [10.1002/ceat.201600185](https://doi.org/10.1002/ceat.201600185). Verificação: editor.

R04. Živković, L. A.; Vidaković-Koch, T.; Petkovska, M. Computer-Aided Nonlinear Frequency Response Method for Investigating the Dynamics of Chemical Engineering Systems. *Processes*, 8, 1354, 2020. DOI [10.3390/pr8111354](https://doi.org/10.3390/pr8111354). Texto integral consultado pelo repositório PSE/LAPSE.

R05. Felischak, M.; Kaps, L.; Hamel, C.; Nikolić, D.; Petkovska, M.; Seidel-Morgenstern, A. Analysis and experimental demonstration of forced periodic operation of an adiabatic stirred tank reactor: Simultaneous modulation of inlet concentration and total flow-rate. *Chemical Engineering Journal*, 410, 128197, 2021. DOI [10.1016/j.cej.2020.128197](https://doi.org/10.1016/j.cej.2020.128197). Verificação: editor. Há corrigendum: [10.1016/j.cej.2021.132930](https://doi.org/10.1016/j.cej.2021.132930), 2022; nenhum ganho numérico desse estudo é reutilizado aqui.

R06. Leipold, J.; Nikolić, D.; Seidel-Morgenstern, A.; Kienle, A. Optimization of methanol synthesis under forced periodic operation in a non-isothermal fixed-bed reactor. *Computers & Chemical Engineering*, 2025, 109040. DOI [10.1016/j.compchemeng.2025.109040](https://doi.org/10.1016/j.compchemeng.2025.109040). Verificação: editor e Max Planck.

R07. Kaps, L. et al. Forced Periodic Reactor Operation Applied to Methanol Synthesis. *ChemCatChem*, 2026, e202501403. DOI [10.1002/cctc.202501403](https://doi.org/10.1002/cctc.202501403). Primeiro acesso online publicado em 14/12/2025; verificação: editor.

R08. Leipold, J.; Kienle, A. Forced periodic operation of chemical reactors: Origins of performance improvement demonstrated for methanol synthesis. *Chemical Engineering Science*, publicação online em 2026, 124639. DOI [10.1016/j.ces.2026.124639](https://doi.org/10.1016/j.ces.2026.124639). Verificação: resumo do editor e instituição; não confundir ano online com ano do fascículo.

R09. Fjeld, M.; Asbjørnsen, O. A.; Åström, K. J. Reaction invariants and their importance in the analysis of eigenvectors, state observability and controllability of the continuous stirred tank reactor. *Chemical Engineering Science*, 29, 1917-1926, 1974. DOI [10.1016/0009-2509(74)85009-8](https://doi.org/10.1016/0009-2509(74)85009-8). Verificação: editor e Universidade de Lund.

R10. Srinivasan, B.; Amrhein, M.; Bonvin, D. Reaction and flow variants/invariants in chemical reaction systems with inlet and outlet streams. *AIChE Journal*, 44, 1858-1867, 1998. DOI [10.1002/aic.690440815](https://doi.org/10.1002/aic.690440815). Verificação: editor.

R11. Amrhein, M.; Bhatt, N.; Srinivasan, B.; Bonvin, D. Extents of reaction and flow for homogeneous reaction systems with inlet and outlet streams. *AIChE Journal*, 2010. DOI [10.1002/aic.12125](https://doi.org/10.1002/aic.12125). Verificação: editor.

R12. Dochain, D.; Couenne, F.; Jallut, C. Enthalpy based modelling and design of asymptotic observers for chemical reactors. *International Journal of Control*, 82, 1389-1403, 2009. DOI [10.1080/00207170802236085](https://doi.org/10.1080/00207170802236085). Verificação: resumo do editor; acesso integral não obtido.

R13. Skogestad, S. Plantwide control: the search for the self-optimizing control structure. *Journal of Process Control*, 10, 487-507, 2000. DOI [10.1016/S0959-1524(00)00023-8](https://doi.org/10.1016/S0959-1524(00)00023-8). Texto integral do manuscrito do autor consultado na NTNU.

R14. Luyben, W. L. Design and control of the ethylbenzene process. *AIChE Journal*, 2011. DOI [10.1002/aic.12289](https://doi.org/10.1002/aic.12289). Verificação: editor e PDF no acervo TFC. O fluxograma completo não é intercambiável com o R1 isolado.

R15. Benner, P.; Seidel-Morgenstern, A.; Zuyev, A. Analysis of switching strategies for the optimization of periodic chemical reactions with controlled flow-rate. Preprint, 2019. [arXiv:1909.02287](https://arxiv.org/abs/1909.02287). Verificação: repositório dos autores.

R16. Lew, T.; Sharma, A.; Harrison, J.; Bylard, A.; Pavone, M. Safe Active Dynamics Learning and Control: A Sequential Exploration-Exploitation Framework. Preprint, 2020. [arXiv:2008.11700](https://arxiv.org/abs/2008.11700). A identificação consultada é a versão preprint; não se pressupõe equivalência de hipóteses de segurança com nossos reatores.

R17. Coulson, J.; Lygeros, J.; Dörfler, F. Data-Enabled Predictive Control: In the Shallows of the DeePC. Trabalho de 2019; preprint de 2018. [arXiv:1811.05890](https://arxiv.org/abs/1811.05890). Verificação: arXiv/ETH. DeePC não foi implementado nesta campanha.

R18. Yu, H.; Yue, H.; Halling, P. Robust Sampling Time Design for Biochemical Systems. *IFAC-PapersOnLine*, 51(18), 215-220, 2018. DOI [10.1016/j.ifacol.2018.09.302](https://doi.org/10.1016/j.ifacol.2018.09.302). Verificação: editor e [repositório Strathclyde](https://strathprints.strath.ac.uk/63696/).

R19. Hedengren, J. D.; Asgharzadeh Shishavan, R.; Powell, K. M.; Edgar, T. F. Nonlinear modeling, estimation and predictive control in APMonitor. *Computers & Chemical Engineering*, 70, 133-148, 2014. DOI [10.1016/j.compchemeng.2014.04.013](https://doi.org/10.1016/j.compchemeng.2014.04.013). Verificação: página do autor e referências oficiais APMonitor.

R20. Wan, B.; Liu, M.; Grigas, P.; Shen, Z.-J. M. Decision-Focused Sequential Experimental Design: A Directional Uncertainty-Guided Approach. Preprint de 05/02/2026. [arXiv:2602.05340](https://arxiv.org/abs/2602.05340). Não tratado como artigo revisado por pares nem como validação química.

R21. Go, J.; Qian, X.; Yoon, B.-J. Goal-driven Bayesian Optimal Experimental Design for Robust Decision-Making Under Model Uncertainty. Preprint de 25/05/2026. [arXiv:2605.26093](https://arxiv.org/abs/2605.26093). Verificação: arXiv; aplicação não constitui demonstração nos reatores PG/EB.

R22. Marquez Ruiz, A.; Mendez Blanco, C.; Özkan, L. Constrained Control and Estimation of Homogeneous Reaction Systems Using Extent-Based Linear Parameter Varying Models. *Industrial & Engineering Chemistry Research*, 59, 2242-2251, 2020. DOI [10.1021/acs.iecr.9b04412](https://doi.org/10.1021/acs.iecr.9b04412). Verificação: editor e registro dos autores na TU Eindhoven.

R23. Salike, S.; Bhatt, N. Thermodynamically consistent estimation of Gibbs free energy from data: data reconciliation approach. *Bioinformatics*, 36, 1219-1225, 2020; online em 04/10/2019. DOI [10.1093/bioinformatics/btz741](https://doi.org/10.1093/bioinformatics/btz741). Texto integral consultado. A reconciliação de Gibbs é antecedente metodológico; não fornece os Cp faltantes do EB.

R24. Saint-Pierre, P. Approximation of the viability kernel. *Applied Mathematics and Optimization*, 29, 187-209, 1994. DOI [10.1007/BF01204182](https://doi.org/10.1007/BF01204182). Verificação: editor. O atlas finito deste trabalho não implementa uma aproximação certificada desse núcleo.

R25. Brandão, W. Y. de A. *Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares*. Dissertação, UFCG, 2019. Fonte primária recuperada no acervo do usuário; orientação de Heleno Bispo da Silva Júnior, participação de Arioston Araújo de Morais Júnior na banca/agradecimentos.

R26. Brandão, W. Y. de A. *Uso de sensores virtuais como observadores de estado aplicados na dinâmica e controle de processos químicos lineares e não lineares*. Trabalho final de curso, UFPB, 2016. Fonte primária recuperada; orientação de Arioston Araújo de Morais Júnior.


# Figuras complementares

![Ganhos e fases empíricos dos registros amostrados.](figures/frequency_response.png){width=95%}

![Fronteira de Pareto para três critérios locais.](figures/pareto.png){width=95%}

![Campanha inicial com referências próprias por região.](figures/control_tradeoffs.png){width=95%}

![Dissipação e indistinguibilidade química.](figures/chemical_twins.png){width=95%}

