Estudo computacional exploratório de propilenoglicol e etilbenzeno

10 de outubro de 2026

# Resumo

Investiga-se se a operação pode facilitar o controle de composição sem medição química contínua, preservando dois modelos históricos de reatores. A campanha combina auditoria física, excitação térmica, ciclos com recursos comparáveis, mapas de sensibilidade e políticas congeladas sob incerteza. No propilenoglicol, excitação senoidal reduziu a incerteza de uma qualidade futura, sem remover dois modos químicos invisíveis. A seleção do regime reduziu o erro médio do mesmo PI térmico em 41,8% com qualidade nominal igual, mas diminuiu a produção em 2,24% e apresentou violações térmicas. No etilbenzeno, a melhora de tracking desapareceu quando a qualidade foi igualada. Nenhum dos ciclos admissíveis superou um estacionário encontrado com recursos iguais ou menores. Uma ablação termodinâmica mostrou que um pequeno defeito de Hess pode aumentar artificialmente o posto de observabilidade local. Os resultados sustentam uma metodologia de falsificação de ganhos inferenciais, sem estabelecer dominância operacional, segurança industrial ou um princípio universal.

Palavras chave: controle inferencial; operação de reatores; observabilidade; invariantes; projeto de experimentos.

# Introdução e revisão crítica

O desempenho de um sistema de controle depende tanto da política quanto do regime físico em que ela atua. Quando a composição não é medida continuamente, mudar a alimentação ou a temperatura pode alterar simultaneamente a produtividade, a informação térmica e a sensibilidade da qualidade. A pergunta relevante é se essa intervenção melhora decisões sob a mesma especificação e restrições.

Operação periódica não é uma ideia nova, inclusive para propilenoglicol [R01]. Resposta não linear em frequência e manipulação com defasagem já foram usadas para avaliar sistemas reacionais [R03, R04]. Resultados recentes em metanol mostram atividade atual nessa linha [R06-R08], mas não autorizam transferir benefícios para outras cinéticas. Controle auto-otimizante relaciona a escolha de variáveis à perda econômica [R13]. Projeto de experimento voltado à decisão explicita que precisão paramétrica e utilidade operacional são objetivos diferentes [R20, R21].

Há antecedentes igualmente importantes para os resultados negativos. Invariantes impõem restrições de observabilidade em CSTRs [R09, R10]; avanços de reação podem simplificar modelos e controladores [R11, R22]. A modelagem por entalpia interfere no projeto de observadores [R12], e propriedades termodinâmicas podem exigir reconciliação [R23]. A contribuição pretendida aqui é testar essas relações nos benchmarks recuperados, expondo comparações confundidas e limites de interpretação. Não se afirma novidade internacional de cada componente.

# Modelos físicos e procedência

O PG parte da dissertação de Brandão de 2019 [R25] e dos códigos históricos e reconstruídos associados. Os seis estados são as concentrações A, B, produto C e inerte M, além das temperaturas do reator e do trocador. A cinética histórica é de primeira ordem em A. Com volume fixo, taxa r e diluição D:

$$
\dot c=D(c_f-c)+\nu r,\qquad
\nu=(-1,-1,1,0)^T,\qquad r=k(T)C_A.
$$

O balanço térmico usa capacidade proporcional à soma das capacidades molares ponderadas pelas concentrações. O calor do trocador depende diretamente da vazão refrigerante e da temperatura do reator; a temperatura dinâmica do trocador não realimenta o balanço do reator. Essa assimetria foi preservada, em vez de substituída por uma camisa convencional. O limite principal é 160 °F, equivalente a 344,261 K; o limite posterior de 180 °F não foi usado para aceitar trajetórias.

O EB é a reconstrução do primeiro reator do TFC de Brandão [R26], associado ao processo discutido por Luyben [R14]. Seus estados são E, B, EB, DEB e temperatura. As reações são E+B para EB, E+EB para DEB e B+DEB para dois EB. As três taxas foram preservadas, assim como o reciclo de entrada nominal. O volume é 200 m³. O produto controlado é a fração molar de EB; a produção líquida desconta o EB que entra no reciclo. O fluxograma com separação e reciclos dinâmicos não foi executado.

A reconstrução EB não é uma planta termodinamicamente reconciliada. Os coeficientes históricos tratados como capacidades caloríficas coincidem aproximadamente com entalpia dividida por temperatura em °C. O dever nominal da reconstrução é 25,370 MW, enquanto o backup Aspen registra 9,088 MW em uma condição próxima, mas distinta. O envelope de 140,85 a 165 °C é exploratório, não industrial certificado. Os novos ensaios assumem acesso a um dever térmico idealizado; essa autoridade adicional é declarada.

# Formulação científica

Considere a incerteza em inventários e parâmetros, representada por uma distribuição b compatível com o histórico de entradas e temperaturas. A escolha de regime z e política causal π deve minimizar custo operacional, incluindo transições, qualidade, produção, recursos e risco. Uma medida relevante de falta de informação é o arrependimento:

$$
\mathcal R(b,z)=\min_\pi {\mathbb E}_b[J(\xi,z,\pi)]
-{\mathbb E}_b[\min_\pi J(\xi,z,\pi)].
$$

A matriz de Fisher fornece um instrumento local, mas não define esse valor. Menor variância de qualidade pode resultar de menor incerteza, menor sensibilidade ou menor influência do inventário inicial. Para uma classe de condições indistinguíveis, uma garantia comum exige interseção não vazia entre suas políticas admissíveis que atendem à especificação. Mudar o regime pode ampliar essa interseção ou eliminá-la por restrições térmicas. A campanha aproxima esse problema por mapas, políticas fixas e decisões finitas; não resolve a otimização global sobre todas as políticas.

No PG, duas perturbações químicas com A e temperaturas iguais e capacidade térmica total igual permanecem termicamente indistinguíveis. Sua diferença segue

$$
\delta c(t)=\delta c(0)\exp\left[-\int_0^t D(s)\,ds\right].
$$

Excitação comum não identifica esses modos. Uma separação inicial de produto de 0,5 kmol/m³ impede garantia simultânea de uma banda de ±2% antes de pelo menos 0,240 h, mesmo usando o maior D permitido. Essa é uma condição necessária; limites de velocidade podem torná-la mais restritiva. O antecedente são os invariantes, e não uma propriedade criada pelo estimador.

# Métodos experimentais

A triagem avaliou 44 projetos de excitação, 144 ciclos e 376 linhas de paisagem estacionária. Os sinais incluem degrau, pulso realizável, PRBS, chirp, senoides e multissenoides. As derivadas incluem inventário inicial e parâmetros térmicos desconhecidos, com escalas físicas mantidas entre regiões. Os ciclos foram avaliados após fechamento periódico, com verificação da partida e médias reais dos atuadores.

O teste não linear de informação compreendeu 192 ajustes MAP, quatro sinais e 24 sementes por reator, das quais oito continham bias fora da família ajustada. A comparação decisória principal usa as 16 sementes da família correta e 17 ações estacionárias futuras comuns, com oráculo de parâmetros claramente identificado. O custo inclui qualidade e penalização térmica; não representa lucro nem controle ótimo dinâmico.

Na malha fechada, os ganhos de um PI térmico com filtro e integral foram selecionados no nominal e congelados. A política não recebe composição verdadeira nem usa a composição estimada em paralelo. A campanha inicial de regiões contém 2304 execuções rotuladas e famílias de mismatch cinético, térmico, combinado, instrumental e fora do domínio. Regiões coincidentes não são réplicas independentes.

Após detectar que a comparação inicial mudava a referência química, executou-se uma rodada exploratória adicional de 216 trajetórias, com três famílias e 12 sementes inéditas. Ajustou-se a alimentação para manter exatamente a mesma qualidade nominal nos pontos comparados. Os recursos resultantes foram reportados, sem presumir igualdade. Intervalos de 95% usam bootstrap pareado de 4000 reamostragens por semente, sem tratar as famílias da mesma semente como independentes. Não houve correção de multiplicidade.

Os baselines adaptados incluem C0, C2 e C3 no PG e reconstrução FKE+PI, cascata e NMPC com envelope no EB, totalizando 180 trajetórias. Ensaios adicionais cobrem esquecimento, amostra atrasada, supervisão, gêmeos e coordenadas reduzidas. Quinze testes científicos e o fluxo E2E foram executados. Dez trajetórias foram reintegradas por DOP853, com diferença térmica máxima de 0,000214 K em relação à integração principal.

# Resultados

## Informação não equivale a decisão

No PG, a melhor senoide reduziu o desvio posterior local da qualidade futura de 0,053965 para 0,008416 kmol/m³. Na validação não linear, o RMSE caiu de 0,016685 para 0,006019. O arrependimento médio passou de 0,105895 a 0,004239; a diferença teve IC95% de -0,183124 a -0,034132. Entretanto, o degrau teve arrependimento médio 0,002931, menor que o da senoide. Logo, a ordenação por precisão preditiva não coincidiu com a ordenação decisória.

No EB, a redução local de desvio posterior foi 7,1%. O arrependimento médio da senoide caiu de 1,496401 para 0,811008, mas o IC da diferença, de -1,695583 a 0,190828, incluiu zero. Não se demonstrou separação confiável das três contribuições cinéticas nem um projeto universalmente superior.

## Periodicidade e seleção de regime

Foram admissíveis 68 ciclos PG e 45 EB. Os maiores ganhos de produção sobre o nominal foram apenas 0,164% e 0,031%. Frente a estacionários encontrados com recursos iguais ou menores, os melhores ciclos ficaram 12,622% e 0,898% abaixo, respectivamente. Esses resultados refutam a dominância da família examinada, não toda forma de operação periódica.

Os mapas identificaram regiões produtivas menos sensíveis em ambos os modelos. No PG, o ponto econômico substituto e o de menor sensibilidade diferiram. No EB, quatro critérios selecionaram o mesmo ponto para os pesos iniciais, mas a seleção mudou sob outros pesos. Menor sensibilidade não foi confundida com maior posto de observabilidade.

Na rodada com qualidade comum, os resultados do PI congelado foram:

| Comparação com nominal | PG a 337 K | PG a 340 K | EB a 162 °C |
|---|---:|---:|---:|
| Variação do IAE normalizado | -30,85% | -41,82% | -0,26% |
| Variação da produção | -1,59% | -2,24% | -0,12% |
| Variação da alimentação | -8,33% | -11,98% | -0,72% |
| Trajetórias com violação | 4/36 | 3/36 | 0/36 |

No PG a 340 K, a diferença de IAE foi -0,014114, IC95% [-0,022466; -0,007626]. A produção caiu 0,638944 kmol/h, IC95% [-0,886668; -0,348401]. O nominal também violou limites em 3/36 trajetórias; a duração média das violações aumentou na alternativa. A condição não é aceita como segura. No EB, o IC da diferença de IAE incluiu zero e o ganho praticamente desapareceu.

![Efeitos com a mesma qualidade e política congelada. Intervalos exploratórios pareados por semente.](figures/same_quality.png){width=95%}

## Informação aparente por inconsistência física

O fechamento isolado do ciclo de Hess trouxe uma falsificação adicional. Seja N a matriz estequiométrica, R a derivada das taxas e D a diluição. O bloco químico linearizado é \(A_c=-DI+NR\). Se \(\Delta H^T=h^TN\), então todo \(v\in\ker(NR)\) satisfaz \(A_cv=-Dv\) e \(\Delta H^TRv=0\). Como os demais termos térmicos da reconstrução não dependem da concentração, esses modos ficam invisíveis à temperatura na linearização.

Nos doze equilíbrios examinados, o núcleo tem dimensão dois. O residual histórico de Hess, 5,5 kcal/kmol, acrescentava uma direção térmica espúria, elevando o posto local de três para quatro. No nominal, o quarto valor singular do registro normalizado passou de 0,001183 para aproximadamente 9e-14 após o fechamento. Seu autovalor de Fisher histórico era apenas 1,4e-6: posto maior não significava informação prática apreciável.

![A direção adicional desaparece ao fechar Hess. A ablação não reconcilia a planta EB.](figures/hess_observability.png){width=90%}

Outro contrafactual trocou incorretamente a referência de temperatura e reajustou Q no nominal. O equilíbrio pôde ser preservado, mas o ganho térmico de alimentação mudou de 1,515 para 4,138 °C por (m³/h). Uma calibração escalar estacionária, portanto, pode esconder uma derivada física incorreta.

# Discussão e limitações

Os resultados favorecem a seleção de regime como variável de pesquisa, mas refutam uma interpretação universalmente favorável. O PG permite reduzir erro sem trocar controlador; ainda assim, os cenários térmicos invalidam a promoção da alternativa. O EB evidencia o risco de atribuir melhoria à informação quando parte do efeito vem de mudança de referência. Transferiu-se uma filosofia experimental, não parâmetros ou uma política ótima.

Três falsificações mudaram a interpretação. Um piloto periódico parecia ganhar aproximadamente 5,4% de produção PG porque a limitação de velocidade deslocava a média da alimentação; a correção eliminou o ganho. A renovação acumulada igual produziu a mesma ambiguidade terminal dos gêmeos PG, apesar de diferenças transitórias. A ablação de Hess mostrou que até o posto formal pode ser favorecido por uma inconsistência.

O atlas adversarial é finito e não certifica um núcleo de viabilidade. Os oráculos de estado e parâmetros são restritos às políticas avaliadas, não ótimos globais. A amostra química é um protocolo separado, com atraso causal; sua seleção por variância não dominou horários fixos em controle. O supervisor e as combinações não demonstraram ganho adicional seguro.

Toda a evidência nova é computacional. MATLAB, Aspen e planta física não foram executados. A termodinâmica EB, a idealização de remoção de calor, o reciclo fixo, os priors sintéticos, o pequeno número de sementes independentes e a busca finita limitam inferências industriais. A revisão é dirigida e encerrada em 10/10/2026. O efeito local de Hess tem antecedentes em invariantes e observadores por entalpia e requer revisão adicional antes de uma reivindicação de originalidade.

# Conclusões

Modificar a operação pode melhorar inferência ou reduzir a informação necessária para algumas decisões, mas os mecanismos e os custos precisam ser separados. Nos modelos estudados, não foi demonstrada uma região segura que melhorasse simultaneamente qualidade, produção e informação nos dois processos. A contribuição mais madura é um protocolo reprodutível que confronta ganhos aparentes com recursos iguais, qualidade comum, limites informacionais e consistência física. Os resultados negativos e a observabilidade espúria merecem investigação adicional, sem serem apresentados como uma nova tecnologia industrial.

# Procedência e disponibilidade

O código, dados brutos, sementes, modelos, testes e figuras acompanham o pacote da campanha. Os modelos históricos são de Walter Yanko de Aragão Brandão [R25, R26]. A participação documentada de Arioston Araújo de Morais Júnior é de orientação no TFC e banca/agradecimentos na dissertação; a orientação do mestrado é de Heleno Bispo da Silva Júnior. O manuscrito não atribui nova coautoria, contribuição individual ou afiliação. Autoria e destino de submissão exigem revisão dos pesquisadores.

# Referências




R01. Pérez-Polo, M. F.; Pérez-Molina, M. Increasing the reactant conversion through induced oscillations in a continuous stirred tank reactor by using PI control. *Journal of Process Control*, 23, 778-792, 2013. DOI [10.1016/j.jprocont.2013.03.007](https://doi.org/10.1016/j.jprocont.2013.03.007). Verificação: resumo do editor.

R03. Nikolić, D.; Seidel-Morgenstern, A.; Petkovska, M. Periodic Operation with Modulation of Inlet Concentration and Flow Rate. Part I: Nonisothermal CSTR. *Chemical Engineering & Technology*, 39, 2020-2028, 2016. DOI [10.1002/ceat.201600185](https://doi.org/10.1002/ceat.201600185). Verificação: editor.

R04. Živković, L. A.; Vidaković-Koch, T.; Petkovska, M. Computer-Aided Nonlinear Frequency Response Method for Investigating the Dynamics of Chemical Engineering Systems. *Processes*, 8, 1354, 2020. DOI [10.3390/pr8111354](https://doi.org/10.3390/pr8111354). Texto integral consultado pelo repositório PSE/LAPSE.

R06. Leipold, J.; Nikolić, D.; Seidel-Morgenstern, A.; Kienle, A. Optimization of methanol synthesis under forced periodic operation in a non-isothermal fixed-bed reactor. *Computers & Chemical Engineering*, 2025, 109040. DOI [10.1016/j.compchemeng.2025.109040](https://doi.org/10.1016/j.compchemeng.2025.109040). Verificação: editor e Max Planck.

R07. Kaps, L. et al. Forced Periodic Reactor Operation Applied to Methanol Synthesis. *ChemCatChem*, 2026, e202501403. DOI [10.1002/cctc.202501403](https://doi.org/10.1002/cctc.202501403). Primeiro acesso online publicado em 14/12/2025; verificação: editor.

R08. Leipold, J.; Kienle, A. Forced periodic operation of chemical reactors: Origins of performance improvement demonstrated for methanol synthesis. *Chemical Engineering Science*, publicação online em 2026, 124639. DOI [10.1016/j.ces.2026.124639](https://doi.org/10.1016/j.ces.2026.124639). Verificação: resumo do editor e instituição; não confundir ano online com ano do fascículo.

R09. Fjeld, M.; Asbjørnsen, O. A.; Åström, K. J. Reaction invariants and their importance in the analysis of eigenvectors, state observability and controllability of the continuous stirred tank reactor. *Chemical Engineering Science*, 29, 1917-1926, 1974. DOI [10.1016/0009-2509(74)85009-8](https://doi.org/10.1016/0009-2509(74)85009-8). Verificação: editor e Universidade de Lund.

R10. Srinivasan, B.; Amrhein, M.; Bonvin, D. Reaction and flow variants/invariants in chemical reaction systems with inlet and outlet streams. *AIChE Journal*, 44, 1858-1867, 1998. DOI [10.1002/aic.690440815](https://doi.org/10.1002/aic.690440815). Verificação: editor.

R11. Amrhein, M.; Bhatt, N.; Srinivasan, B.; Bonvin, D. Extents of reaction and flow for homogeneous reaction systems with inlet and outlet streams. *AIChE Journal*, 2010. DOI [10.1002/aic.12125](https://doi.org/10.1002/aic.12125). Verificação: editor.

R12. Dochain, D.; Couenne, F.; Jallut, C. Enthalpy based modelling and design of asymptotic observers for chemical reactors. *International Journal of Control*, 82, 1389-1403, 2009. DOI [10.1080/00207170802236085](https://doi.org/10.1080/00207170802236085). Verificação: resumo do editor; acesso integral não obtido.

R13. Skogestad, S. Plantwide control: the search for the self-optimizing control structure. *Journal of Process Control*, 10, 487-507, 2000. DOI [10.1016/S0959-1524(00)00023-8](https://doi.org/10.1016/S0959-1524(00)00023-8). Texto integral do manuscrito do autor consultado na NTNU.

R14. Luyben, W. L. Design and control of the ethylbenzene process. *AIChE Journal*, 2011. DOI [10.1002/aic.12289](https://doi.org/10.1002/aic.12289). Verificação: editor e PDF no acervo TFC. O fluxograma completo não é intercambiável com o R1 isolado.

R20. Wan, B.; Liu, M.; Grigas, P.; Shen, Z.-J. M. Decision-Focused Sequential Experimental Design: A Directional Uncertainty-Guided Approach. Preprint de 05/02/2026. [arXiv:2602.05340](https://arxiv.org/abs/2602.05340). Não tratado como artigo revisado por pares nem como validação química.

R21. Go, J.; Qian, X.; Yoon, B.-J. Goal-driven Bayesian Optimal Experimental Design for Robust Decision-Making Under Model Uncertainty. Preprint de 25/05/2026. [arXiv:2605.26093](https://arxiv.org/abs/2605.26093). Verificação: arXiv; aplicação não constitui demonstração nos reatores PG/EB.

R22. Marquez Ruiz, A.; Mendez Blanco, C.; Özkan, L. Constrained Control and Estimation of Homogeneous Reaction Systems Using Extent-Based Linear Parameter Varying Models. *Industrial & Engineering Chemistry Research*, 59, 2242-2251, 2020. DOI [10.1021/acs.iecr.9b04412](https://doi.org/10.1021/acs.iecr.9b04412). Verificação: editor e registro dos autores na TU Eindhoven.

R23. Salike, S.; Bhatt, N. Thermodynamically consistent estimation of Gibbs free energy from data: data reconciliation approach. *Bioinformatics*, 36, 1219-1225, 2020; online em 04/10/2019. DOI [10.1093/bioinformatics/btz741](https://doi.org/10.1093/bioinformatics/btz741). Texto integral consultado. A reconciliação de Gibbs é antecedente metodológico; não fornece os Cp faltantes do EB.

R25. Brandão, W. Y. de A. *Uso de observadores de estado aplicados no controle inferencial preditivo de processos não lineares*. Dissertação, UFCG, 2019. Fonte primária recuperada no acervo do usuário; orientação de Heleno Bispo da Silva Júnior, participação de Arioston Araújo de Morais Júnior na banca/agradecimentos.

R26. Brandão, W. Y. de A. *Uso de sensores virtuais como observadores de estado aplicados na dinâmica e controle de processos químicos lineares e não lineares*. Trabalho final de curso, UFPB, 2016. Fonte primária recuperada; orientação de Arioston Araújo de Morais Júnior.
