# 6. Potencial de publicação e referências

Conclusão científica: é possível perceber perda de estabilidade antes de um alarme térmico neste modelo e neste protocolo, principalmente quando a física, a entrada corrente e o ramo operacional são conhecidos. Isso não valida uma previsão universal de catástrofes por EWS nem demonstra superioridade geral do controlador proposto.

Contribuição possível: benchmark auditável de bifurcação versus excursão térmica, com a assimetria histórica do trocador preservada, análise de observabilidade, separação causal, calibração independente e ablações. O resultado negativo sobre informação incremental de EWS é publicável como questão científica, se confrontado com literatura e baselines adicionais.

O pacote é um laboratório de pesquisa v1.0, não um manuscrito pronto para aceitação. Antes de submissão: revisão independente das conversões históricas; análise de sensibilidade aos pesos e horizontes em protocolo pré-definido; controladores robustos e SQP de maior orçamento; validação cruzada por família de perturbação; caracterização mais ampla de bacias e fronteiras de viabilidade; validação experimental se houver infraestrutura apropriada.

Não se confirma Hopf do PG nesta entrega. Um par imaginário em benchmark matemático valida a rotina básica, mas não substitui uma classificação local completa no reator. A continuação, a varredura e os testes de retorno tratam regiões delimitadas, sem certificação global.

O controle econômico usa um proxy declarado. Uma análise econômica real exigiria preços, capacidade de equipamento, especificação de produto e custos de transição. Nenhum valor monetário foi inferido.

Fontes verificáveis consultadas em outubro de 2026. Revisão focalizada, não sistemática. Distinguem-se artigos publicados, preprints, resumos acessíveis e resultados próprios.

[1] Brandão, W. Y. A. (2019). Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares. Dissertação, UFCG. Fonte primária recuperada e conferida; equações implementadas rastreáveis no repositório https://github.com/walteryanko/yanko-process-lab .

[2] Scheffer et al. (2009). Early-warning signals for critical transitions. Nature 461, 53–59. https://doi.org/10.1038/nature08227 . Fundamenta a associação entre certos mecanismos de perda de estabilidade e indicadores antecipativos; não garante eficácia universal.

[3] Boettiger & Hastings (2012). Quantifying limits to detection of early warning for critical transitions. J. R. Soc. Interface. https://doi.org/10.1098/rsif.2012.0125 . Motiva quantificar falsos positivos e negativos, em vez de selecionar apenas séries que sofreram transição.

[4] Boettiger & Hastings. Early Warning Signals and the Prosecutor’s Fallacy. https://arxiv.org/abs/1210.1204 . A seleção retrospectiva de transições pode inflar evidência de EWS; foram incluídos controles negativos e sementes independentes.

[5] Radhakrishnan et al. (2025). Early warnings are too late when parameters change rapidly. Scientific Reports 15, 20256. https://doi.org/10.1038/s41598-025-06525-5 ; preprint dos autores: https://arxiv.org/abs/2408.07296 . O estudo termoacústico mostra limitações sob variação rápida. Sua transferência ao PG é uma hipótese, não um resultado já comprovado pela fonte.

[6] Use of bifurcation analysis for identification of a safe CSTR operability. https://www.sciencedirect.com/science/article/abs/pii/S0950423004000713 . O resumo trata de hidrólise de óxido de propileno com reações consecutivas; esse modelo não é idêntico ao PG de seis estados utilizado aqui.

[7] Heinlein, Subramanian & Lucia (2025). Robust Model Predictive Control Exploiting Monotonicity Properties. IEEE TAC, DOI https://doi.org/10.1109/TAC.2025.3558137 ; https://arxiv.org/abs/2408.17348 . Estuda conjuntos alcançáveis e conservadorismo em sistemas não lineares, incluindo cascata de reatores. O presente laboratório não implementa nem reivindica essas garantias robustas.

[8] Köhler et al. A computationally efficient robust model predictive control framework for uncertain nonlinear systems. Fonte dos autores: https://www.ist.uni-stuttgart.de/de/institut/team/PDFs_MA-Seiten/JK/Robust_Nonlin.pdf . Construção de tubos robustos exige hipóteses e verificações adicionais à penalização de risco adotada neste laboratório.

[9] Ma (2026). Early warning of noise-induced critical transitions in two-dimensional ecosystems. Chaos 36, 023121. https://pubs.aip.org/aip/cha/article/36/2/023121/3379059/Early-warning-of-noise-induced-critical . Referência recente consultada pelo resumo; não estabelece capacidade preditiva para este CSTR.

[10] Sanders & Bastiaansen (2025), preprint. Early warning of critical transitions: distinguishing tipping points from Turing destabilizations. https://arxiv.org/abs/2510.01959 . Reforça distinguir o mecanismo de transição; sistemas espacialmente distribuídos não são equivalentes ao CSTR concentrado.
