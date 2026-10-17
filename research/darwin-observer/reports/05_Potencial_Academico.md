# Relatório 5 - Potencial acadêmico

## Veredito

Os resultados sustentam um estudo computacional metodológico e um protótipo científico reproduzível. Ainda não sustentam uma afirmação de descobridor universal de física nem validação industrial. Um artigo é plausível se sua contribuição for delimitada e comparada a trabalhos de identificação com observação parcial e modelos de discrepância. A busca bibliográfica realizada confirma referências de base, mas não é uma revisão sistemática de novidade.

## Título proposto

Descoberta restrita de discrepâncias em um CSTR parcialmente observado: recuperação térmica, ambiguidade química e impacto no NMPC inferencial.

## Hipótese central

A separação entre balanço térmico diretamente informado e estados químicos ocultos permite descobrir certas correções funcionais de transferência de calor, enquanto outras causas permanecem não identificáveis ou confundíveis. Validar previsão, diagnóstico e qualidade de controle são tarefas distintas.

## Contribuições verificadas que podem ser defendidas

1. Integração reproduzível de observadores, hipóteses físicas concorrentes, proposta esparsa de balanço integral, validação fora da amostra e monitoramento de reversão.
2. Comparação com UKF, EKF, UKF conjunto de parâmetros, modelos paramétricos selecionados, RBF e MLP usando somente medições operacionais no aprendizado.
3. Demonstração quantitativa da diferença entre corrigir o observador e corrigir a previsão do NMPC em 100 sementes pareadas.
4. Casos negativos explícitos: baixa excitação, erro de variante, confusão cinética-alimentação e subcobertura de incerteza.
5. Registro público auditável de código, configuração, hipóteses aceitas/rejeitadas, dados sintéticos e interface de exploração.

O certificado de não observabilidade, os algoritmos UKF/SINDy e a proposta de um modelo de discrepância são antecedentes, não novidades individuais. O nome Darwin-Observer é uma denominação de projeto, não uma categoria estabelecida ou um algoritmo com superioridade universal demonstrada.

## Experimentos necessários antes de uma submissão forte

Introduzir falhas simultâneas, atrasos, mudanças em instantes desconhecidos e ruído de processo. Comparar com MHE robusto e métodos esparsos para estados latentes. Propagar incerteza dos parâmetros e da seleção até o NMPC. Usar classes geradoras externas à gramática, parâmetros sorteados entre episódios e outra implementação independente da planta. Repetir o diagnóstico com magnitudes pequenas e erros de calibração de alimentação. Testar correção exclusivamente de UA sobre a variante histórica completa, em vez de transferir cegamente todo o modelo nominal.

Adicionar medições químicas esparsas para quantificar o valor da informação frente ao núcleo invisível. Executar em Windows, registrar consumo de memória e latência na máquina-alvo e realizar validação com dados reais de um experimento seguro, sob supervisão adequada. Não aplicar o controlador diretamente em equipamento industrial com base nestes resultados.

## Fontes verificadas

[1] Brunton, S. L.; Proctor, J. L.; Kutz, J. N. (2016). Discovering governing equations from data by sparse identification of nonlinear dynamical systems. PNAS 113(15), 3932-3937. DOI: 10.1073/pnas.1517384113. https://doi.org/10.1073/pnas.1517384113

[2] de Silva, B. M.; Higdon, D. M.; Brunton, S. L.; Kutz, J. N. (2020). Discovery of Physics From Data: Universal Laws and Discrepancies. Frontiers in Artificial Intelligence 3:25. DOI: 10.3389/frai.2020.00025. https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2020.00025/full

[3] Raue, A. et al. (2009). Structural and practical identifiability analysis of partially observed dynamical models by exploiting the profile likelihood. Bioinformatics 25(15), 1923-1929. DOI: 10.1093/bioinformatics/btp358. https://doi.org/10.1093/bioinformatics/btp358

[4] Julier, S. J.; Uhlmann, J. K. (2004). Unscented Filtering and Nonlinear Estimation. Proceedings of the IEEE 92(3), 401-422. DOI: 10.1109/JPROC.2003.823141. https://www.cs.ubc.ca/~murphyk/Papers/Julier_Uhlmann_mar04.pdf

[5] Brandão, Walter Yanko de Aragão (2019). Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares. Dissertação, UFCG. Fonte fornecida pelo autor e recuperada no acervo; equações 33-55 e Tabela 1. Orientador: Heleno Bispo da Silva Júnior; Arioston Araújo de Morais Júnior consta como examinador.

[6] walteryanko/yanko-process-lab. Commit f4444d4c238291b8633743930249ee387ad94541. lib/simulation/model.ts, observer.ts e controller.ts. https://github.com/walteryanko/yanko-process-lab/tree/f4444d4c238291b8633743930249ee387ad94541

Acervo interno consultado: YCS_OracleKF_Checkpoint_v0.1.zip; Codigo_CSTR_Reproduzivel.zip; RSI_ProcessLab_Relatorio.pdf; AIRE_NMPC_Relatorio_Tecnico.pdf; CSTR_NAKE_UKF_Relatorio.pdf. O manifesto de proveniência identifica hashes das fontes efetivamente copiadas. Resultados desses documentos não foram tratados como novas execuções.
