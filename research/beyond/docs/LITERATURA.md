# Revisão crítica e lacunas científicas

## Escopo da busca

A busca internacional foi encerrada em 10 de outubro de 2026. Abrangeu os termos propostos, seus sinônimos e cadeias de referências sobre operação periódica, resposta não linear em frequência, invariantes, observadores térmicos, controle auto-otimizante, identificação ativa segura, amostragem e valor da informação. É uma revisão dirigida, não uma revisão sistemática com cobertura exaustiva. O registro de fontes distingue texto integral, resumo do editor, repositório institucional e preprint. Não se infere ineditismo da ausência de um resultado na busca.

A questão operacional tem antecedentes fortes. Há inclusive um artigo de 2013 sobre oscilações em um CSTR de propilenoglicol [R01]. Nele, a vazão de saída é um grau de liberdade relevante; isso não equivale ao benchmark de volume fixo aqui preservado. A resposta não linear em frequência já serve para estudar mecanismos e ganhos periódicos [R02–R05]. Os trabalhos recentes de metanol [R06–R08] reforçam que os ganhos dependem do sistema, da cinética e do regime; não justificam transferir conclusões ou parâmetros para PG/EB.

A conexão entre invariantes, observabilidade e controlabilidade remonta pelo menos a Fjeld, Asbjørnsen e Åström [R09]. Extensões de reação/fluxo e controladores em coordenadas de avanço são anteriores a esta campanha [R10, R11, R22]. Modelagem por entalpia já foi associada ao projeto de observadores [R12]. Portanto, nem “controlar em coordenadas de reação” nem “usar temperatura para inferir química” constitui, isoladamente, novidade.

Escolher variáveis e condições operacionais para reduzir perda econômica também se relaciona ao controle auto-otimizante [R13]. A contribuição potencial precisa demonstrar o efeito adicional da informação incompleta sobre decisões, mantendo qualidade, recursos, atuadores e riscos comparáveis. Projeto de experimento voltado à decisão tem antecedentes recentes [R20, R21], ainda em preprint no recorte consultado. A formulação em termos de arrependimento é compatível com essa literatura; não foi inventada aqui.

## Lacunas e testes por experimento

**Experimento 1.** NFR e excitação multivariável já são conhecidos [R02–R05]. A lacuna específica era saber se sinais admissíveis melhoram decisões de composição nestes modelos, com inventários e parâmetros térmicos desconhecidos. Hipótese: algum sinal supera entrada constante e excitação convencional no erro futuro e no arrependimento, sem violar limites. O mínimo executado foi a triagem Fisher seguida de MAP não linear e decisões comuns com sementes novas. Potencial publicável: protocolo aplicado e resultados negativos, condicionado a distinguir valor decisório de precisão paramétrica; não uma nova espectroscopia.

**Experimento 2.** Operação periódica, fases de entradas e restrições de recursos têm literatura consolidada [R01–R08, R15]. A lacuna local era um comparador estacionário com os mesmos recursos reais após limitação de velocidade. Hipótese: existe ciclo seguro que domina esse comparador. O teste mínimo foi simular ciclos até fechamento e buscar um estacionário com consumo igual ou menor. A hipótese não foi sustentada na família examinada. O resultado negativo é útil, mas não prova impossibilidade de toda operação periódica.

**Experimento 3.** Baixa perda sob incerteza e seleção de variáveis são próximas de controle auto-otimizante [R13]. Faltava um mapa conjunto de produtividade, sensibilidade química e ambiguidade para os benchmarks preservados. Hipótese: há regiões produtivas menos sensíveis, independentemente de serem mais observáveis. O teste mínimo foi derivação implícita, prior físico fixo e posterior separado. A confirmação é local; publicar exige demonstrar utilidade em malha fechada e não apenas um mapa colorido.

**Experimento 4.** Projeto de experimento e controle sob informação incompleta antecedem a proposta [R13, R16, R20, R21]. A diferença pretendida é escolher o regime para reduzir o conjunto de decisões conflitantes, incluindo transições. Hipótese: trocar somente o regime melhora uma política congelada em cenários novos. O teste mínimo foi pareamento por sementes, referência comum e registro de riscos/custos. PG mostrou compromisso favorável ao tracking, mas inseguro em parte dos casos; EB não confirmou o ganho com a mesma qualidade. Há material metodológico, sem princípio universal validado.

**Experimento 5.** Dissipação de invariantes por renovação é conhecida [R09–R11] e já aparecia no acervo interno. A lacuna é quantificar seu custo sob recursos iguais. Hipótese: reordenar a alimentação acelera a redução da ambiguidade terminal. Gêmeos exatos e três sinais com a mesma renovação refutaram essa possibilidade para os modos demonstrados. A eventual contribuição está no limite operacional explícito e na comparação causal, não em redescobrir a diluição.

**Experimento 6.** Controle por histórico e dados tem antecedentes, incluindo DeePC [R17]. Testou-se somente uma política térmica compacta com filtro e integral, que ignora a estimativa química disponível em paralelo. Hipótese: decisões úteis dispensam reconstrução de todos os estados. Os testes sustentam utilidade local, mas não suficiência global da memória nem superioridade sobre NMPC. Um artigo de nova arquitetura não se justifica.

**Experimento 7.** Horários de amostragem robustos já foram estudados [R18]; ICAC/MOSAIC também são antecedentes internos. A lacuna aqui é o efeito causal de uma amostra atrasada no controle futuro. Hipótese: a seleção por variância supera um horário fixo. O mínimo foi escolher espécie/instante sem acessar verdade online, então atualizar o filtro no passado e refazer a propagação. A seleção não dominou universalmente. A contribuição possível é expor a diferença entre valor estatístico e valor decisório, incluindo atraso.

**Experimento 8.** Restrições impostas por invariantes à observação são clássicas [R09]. Faltavam contraexemplos explícitos ligados à banda de qualidade e a ações comuns. Hipótese: gêmeos indistinguíveis impedem uma garantia imediata. No PG há prova e limite temporal; no EB há pares aproximados e distância do registro completo. O caso EB não é prova de impossibilidade estrutural. O limite PG é uma aplicação rigorosa, com antecedente interno reconhecido.

**Experimento 9.** Avanços e invariantes já produzem representações úteis a estimação/controle [R10, R11, R22]. A lacuna local era uma redução que preservasse a qualidade sem favorecer o prior inicial. Hipótese: um quociente de cinco estados PG reproduz a qualidade do modelo de seis. A igualdade foi verificada com covariância projetada. Ainda não há evidência de ganho computacional ou de controle que justifique uma nova contribuição algorítmica.

**Experimento 10.** Modelagem por entalpia [R12] e reconciliação termodinâmica [R23] são antecedentes. A lacuna encontrada é o efeito de inconsistências térmicas sobre a suposta informação química. O mínimo executado foi fechar Hess, comparar o núcleo químico/temperatura e perturbar deliberadamente uma referência de entalpia, com refit nominal. Ambos revelaram artefatos que a calibração estática não elimina. Esta é uma candidata forte a nota metodológica, mas a originalidade internacional da proposição precisa de revisão adicional.

**Experimento 11.** Bandas mortas e regiões de controle já integram ferramentas de controle preditivo [R19]. A lacuna local era verificar se esperar ou moderar atuação ajuda diante do núcleo invisível, contabilizando produção perdida. Hipótese: uma política conservadora domina a correção contínua quando a informação é frágil. O mínimo comparou espera, zona morta e gate com as mesmas realizações. Não houve dominância universal; a covariância do filtro não é certificado de confiança.

**Experimento 12.** Viabilidade e aprendizagem ativa segura têm fundamentos anteriores [R16, R24]. A lacuna operacional é separar insuficiência de informação de impossibilidade física, sem chamar falha numérica de prova. O mínimo foi uma família de ações comuns para gêmeos e limites analíticos PG, acrescida de cenários adversos. O atlas é local; não é um núcleo global de viabilidade. A classificação explícita dos níveis de evidência pode sustentar a metodologia experimental.

## O que a revisão permite afirmar

Não foi demonstrado um fenômeno físico novo. Há uma campanha nova nestas reconstruções, com controles de confusão que alteram as conclusões: recursos reais dos ciclos, mesma qualidade, priors iguais, temperaturas históricas e consistência estequiométrica da informação. O antecedente internacional mais próximo da candidata H26 combina [R09] e [R12]; [R23] mostra que conciliar propriedades com leis físicas também é trabalho estabelecido. A demonstração específica de posto espúrio no EB é evidência adicional, não autorização para anunciar um novo princípio geral.

## Referências verificadas

Os identificadores abaixo são usados também no manuscrito. Datas são de publicação, não de atualização do mecanismo de busca.

R01. Pérez-Polo, M. F.; Pérez-Molina, M. Increasing the reactant conversion through induced oscillations in a continuous stirred tank reactor by using PI control. *Journal of Process Control*, 23, 778–792, 2013. DOI [10.1016/j.jprocont.2013.03.007](https://doi.org/10.1016/j.jprocont.2013.03.007). Verificação: resumo do editor.

R02. Nikolić, D.; Seidel-Morgenstern, A.; Petkovska, M. Nonlinear frequency response analysis of forced periodic operation of non-isothermal CSTR using single input modulations. Part I: Modulation of inlet concentration or flow-rate. *Chemical Engineering Science*, 2014. DOI [10.1016/j.ces.2014.06.013](https://doi.org/10.1016/j.ces.2014.06.013). Verificação: editor e registro institucional; paginação omitida por divergência de registros.

R03. Nikolić, D.; Seidel-Morgenstern, A.; Petkovska, M. Periodic Operation with Modulation of Inlet Concentration and Flow Rate. Part I: Nonisothermal CSTR. *Chemical Engineering & Technology*, 39, 2020–2028, 2016. DOI [10.1002/ceat.201600185](https://doi.org/10.1002/ceat.201600185). Verificação: editor.

R04. Živković, L. A.; Vidaković-Koch, T.; Petkovska, M. Computer-Aided Nonlinear Frequency Response Method for Investigating the Dynamics of Chemical Engineering Systems. *Processes*, 8, 1354, 2020. DOI [10.3390/pr8111354](https://doi.org/10.3390/pr8111354). Texto integral consultado pelo repositório PSE/LAPSE.

R05. Felischak, M.; Kaps, L.; Hamel, C.; Nikolić, D.; Petkovska, M.; Seidel-Morgenstern, A. Analysis and experimental demonstration of forced periodic operation of an adiabatic stirred tank reactor: Simultaneous modulation of inlet concentration and total flow-rate. *Chemical Engineering Journal*, 410, 128197, 2021. DOI [10.1016/j.cej.2020.128197](https://doi.org/10.1016/j.cej.2020.128197). Verificação: editor. Há corrigendum: [10.1016/j.cej.2021.132930](https://doi.org/10.1016/j.cej.2021.132930), 2022; nenhum ganho numérico desse estudo é reutilizado aqui.

R06. Leipold, J.; Nikolić, D.; Seidel-Morgenstern, A.; Kienle, A. Optimization of methanol synthesis under forced periodic operation in a non-isothermal fixed-bed reactor. *Computers & Chemical Engineering*, 2025, 109040. DOI [10.1016/j.compchemeng.2025.109040](https://doi.org/10.1016/j.compchemeng.2025.109040). Verificação: editor e Max Planck.

R07. Kaps, L. et al. Forced Periodic Reactor Operation Applied to Methanol Synthesis. *ChemCatChem*, 2026, e202501403. DOI [10.1002/cctc.202501403](https://doi.org/10.1002/cctc.202501403). Primeiro acesso online publicado em 14/12/2025; verificação: editor.

R08. Leipold, J.; Kienle, A. Forced periodic operation of chemical reactors: Origins of performance improvement demonstrated for methanol synthesis. *Chemical Engineering Science*, publicação online em 2026, 124639. DOI [10.1016/j.ces.2026.124639](https://doi.org/10.1016/j.ces.2026.124639). Verificação: resumo do editor e instituição; não confundir ano online com ano do fascículo.

R09. Fjeld, M.; Asbjørnsen, O. A.; Åström, K. J. Reaction invariants and their importance in the analysis of eigenvectors, state observability and controllability of the continuous stirred tank reactor. *Chemical Engineering Science*, 29, 1917–1926, 1974. DOI [10.1016/0009-2509(74)85009-8](https://doi.org/10.1016/0009-2509(74)85009-8). Verificação: editor e Universidade de Lund.

R10. Srinivasan, B.; Amrhein, M.; Bonvin, D. Reaction and flow variants/invariants in chemical reaction systems with inlet and outlet streams. *AIChE Journal*, 44, 1858–1867, 1998. DOI [10.1002/aic.690440815](https://doi.org/10.1002/aic.690440815). Verificação: editor.

R11. Amrhein, M.; Bhatt, N.; Srinivasan, B.; Bonvin, D. Extents of reaction and flow for homogeneous reaction systems with inlet and outlet streams. *AIChE Journal*, 2010. DOI [10.1002/aic.12125](https://doi.org/10.1002/aic.12125). Verificação: editor.

R12. Dochain, D.; Couenne, F.; Jallut, C. Enthalpy based modelling and design of asymptotic observers for chemical reactors. *International Journal of Control*, 82, 1389–1403, 2009. DOI [10.1080/00207170802236085](https://doi.org/10.1080/00207170802236085). Verificação: resumo do editor; acesso integral não obtido.

R13. Skogestad, S. Plantwide control: the search for the self-optimizing control structure. *Journal of Process Control*, 10, 487–507, 2000. DOI [10.1016/S0959-1524(00)00023-8](https://doi.org/10.1016/S0959-1524(00)00023-8). Texto integral do manuscrito do autor consultado na NTNU.

R14. Luyben, W. L. Design and control of the ethylbenzene process. *AIChE Journal*, 2011. DOI [10.1002/aic.12289](https://doi.org/10.1002/aic.12289). Verificação: editor e PDF no acervo TFC. O fluxograma completo não é intercambiável com o R1 isolado.

R15. Benner, P.; Seidel-Morgenstern, A.; Zuyev, A. Analysis of switching strategies for the optimization of periodic chemical reactions with controlled flow-rate. Preprint, 2019. [arXiv:1909.02287](https://arxiv.org/abs/1909.02287). Verificação: repositório dos autores.

R16. Lew, T.; Sharma, A.; Harrison, J.; Bylard, A.; Pavone, M. Safe Active Dynamics Learning and Control: A Sequential Exploration-Exploitation Framework. Preprint, 2020. [arXiv:2008.11700](https://arxiv.org/abs/2008.11700). A identificação consultada é a versão preprint; não se pressupõe equivalência de hipóteses de segurança com nossos reatores.

R17. Coulson, J.; Lygeros, J.; Dörfler, F. Data-Enabled Predictive Control: In the Shallows of the DeePC. Trabalho de 2019; preprint de 2018. [arXiv:1811.05890](https://arxiv.org/abs/1811.05890). Verificação: arXiv/ETH. DeePC não foi implementado nesta campanha.

R18. Yu, H.; Yue, H.; Halling, P. Robust Sampling Time Design for Biochemical Systems. *IFAC-PapersOnLine*, 51(18), 215–220, 2018. DOI [10.1016/j.ifacol.2018.09.302](https://doi.org/10.1016/j.ifacol.2018.09.302). Verificação: editor e [repositório Strathclyde](https://strathprints.strath.ac.uk/63696/).

R19. Hedengren, J. D.; Asgharzadeh Shishavan, R.; Powell, K. M.; Edgar, T. F. Nonlinear modeling, estimation and predictive control in APMonitor. *Computers & Chemical Engineering*, 70, 133–148, 2014. DOI [10.1016/j.compchemeng.2014.04.013](https://doi.org/10.1016/j.compchemeng.2014.04.013). Verificação: página do autor e referências oficiais APMonitor.

R20. Wan, B.; Liu, M.; Grigas, P.; Shen, Z.-J. M. Decision-Focused Sequential Experimental Design: A Directional Uncertainty-Guided Approach. Preprint de 05/02/2026. [arXiv:2602.05340](https://arxiv.org/abs/2602.05340). Não tratado como artigo revisado por pares nem como validação química.

R21. Go, J.; Qian, X.; Yoon, B.-J. Goal-driven Bayesian Optimal Experimental Design for Robust Decision-Making Under Model Uncertainty. Preprint de 25/05/2026. [arXiv:2605.26093](https://arxiv.org/abs/2605.26093). Verificação: arXiv; aplicação não constitui demonstração nos reatores PG/EB.

R22. Marquez Ruiz, A.; Mendez Blanco, C.; Özkan, L. Constrained Control and Estimation of Homogeneous Reaction Systems Using Extent-Based Linear Parameter Varying Models. *Industrial & Engineering Chemistry Research*, 59, 2242–2251, 2020. DOI [10.1021/acs.iecr.9b04412](https://doi.org/10.1021/acs.iecr.9b04412). Verificação: editor e registro dos autores na TU Eindhoven.

R23. Salike, S.; Bhatt, N. Thermodynamically consistent estimation of Gibbs free energy from data: data reconciliation approach. *Bioinformatics*, 36, 1219–1225, 2020; online em 04/10/2019. DOI [10.1093/bioinformatics/btz741](https://doi.org/10.1093/bioinformatics/btz741). Texto integral consultado. A reconciliação de Gibbs é antecedente metodológico; não fornece os Cp faltantes do EB.

R24. Saint-Pierre, P. Approximation of the viability kernel. *Applied Mathematics and Optimization*, 29, 187–209, 1994. DOI [10.1007/BF01204182](https://doi.org/10.1007/BF01204182). Verificação: editor. O atlas finito deste trabalho não implementa uma aproximação certificada desse núcleo.

R25. Brandão, W. Y. de A. *Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares*. Dissertação, UFCG, 2019. Fonte primária recuperada no acervo do usuário; orientação de Heleno Bispo da Silva Júnior, participação de Arioston Araújo de Morais Júnior na banca/agradecimentos.

R26. Brandão, W. Y. de A. *Uso de sensores virtuais como observadores de estado aplicados na dinâmica e controle de processos químicos lineares e não lineares*. Trabalho final de curso, UFPB, 2016. Fonte primária recuperada; orientação de Arioston Araújo de Morais Júnior.
