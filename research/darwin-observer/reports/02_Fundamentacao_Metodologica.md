# Relatório 2 - Fundamentação metodológica

## Hipótese científica e nulidade

O objetivo é investigar discrepâncias de um modelo conhecido sob observação parcial, não inferir uma lei universal. A hipótese H0 é operacional: o modelo nominal é suficiente frente ao ruído e às excitações oferecidas. O algoritmo pode rejeitar todas as correções.

O ponto de partida metodológico é a identificação esparsa em bibliotecas de funções [1], combinada com a abordagem de modelos de discrepância [2]. Não se aplica SINDy diretamente às concentrações ocultas. A implementação calcula propostas usando o balanço integral da camisa, que depende de T, Tt e das entradas disponíveis. Os termos são posteriormente reajustados por erro de saída no modelo completo de seis estados.

## Espaço de expressões e descoberta CPU-first

Defina v = mw/453,6. A biblioteca adimensional é [1, v-1, log(v), (v-1)^2, 1/v-1, sqrt(v)-1]. A expressão UA_eff = UA0 exp(sum(a_j phi_j(v))) mantém positividade. A família cinética é k_eff = k_nominal exp(b0 + 10 b1 (340/T-1)). Há hipóteses alternativas de calor de reação, composição, capacidade térmica, temperatura de entrada, vieses dos sensores e deriva de Tt. O operador recíproco só é permitido no domínio positivo e limitado de v; não há divisão por variáveis que possam zerar.

O ajuste esparso STLSQ é uma proposta local linearizada do balanço integral, não um estimador final imparcial. A etapa de erro de saída usa least_squares, perda soft_l1 e caixas paramétricas explícitas. A biblioteca inclui várias famílias concorrentes e foi congelada antes dos testes. A planta UA usa uma potência, representável por uma das famílias; o desafio de saturação e a cinética curva não coincidem exatamente com as expressões simples. Isso é descoberta dentro de uma gramática física, não regressão simbólica irrestrita. PySR/Julia não é obrigatório nem foi executado; SymPy fornece as expressões e exportações.

## Treinamento, validação e causalidade

Doze episódios completos por condição são usados no ajuste e oito na validação. As concentrações iniciais têm prior e não são reveladas. Um prefixo de 20 passos inicializa causalmente o UKF de cada candidato; a previsão de saída subsequente fica em malha aberta e não recebe as medições de validação posteriores. O primeiro ponto do prefixo, quando presente no resíduo, é praticamente assimilado; seu peso é pequeno frente aos 100 pontos posteriores. O código explicita esse detalhe para que a escolha seja auditável.

No teste principal, os modelos já foram selecionados em episódios anteriores; parâmetros ficam congelados. Não se usa qualquer estado verdadeiro na descoberta. A classe Record não contém truth, categoria de falha ou parâmetros escondidos. Um teste de prefixo confirma que as estimativas passadas não mudam quando se retira o futuro. Resultados após alteração do vetor truth permanecem idênticos.

O diagnóstico cego adicional é específico por episódio: treino até o passo 60; validação nos passos 61-90; avaliação e eventual atuação nos passos 91-120. A classificação recebe apenas Record. Selecionar uma hipótese no passo 90 não a aplica retroativamente. Esse braço mede adaptação causal após uma janela de evidência; não significa descoberta instantânea.

## Ranking e aceitação

O escore é MSE de saída normalizado por 0,2 K, acrescido de 0,025 d + log(N)d/N. A aceitação exige: melhoria de pelo menos 10% em validação, limite inferior positivo do bootstrap pareado entre episódios, detecção persistente, convergência do otimizador, posto local completo e condicionamento inferior a 1e5. Integrações de seis horas e uma grade de coeficientes no domínio de operação rejeitam extrapolações inválidas.

Coeficientes físicos são considerados plausíveis somente no envelope mw de 150 a 1.250 kmol/h e T de 295 a 350 K. O rank numérico é calculado com sensitividades locais. Erros-padrão condicionais e correlações ficam nos registros; são aproximações locais sob perda robusta e prior de inicialização, não intervalos universais de parâmetros. A escolha não produz probabilidades bayesianas. Candidatos com escore próximo são preservados como explicações plausíveis.

## Observadores e baselines

UKF e EKF estimam seis estados com y=[T,Tt]. O UKF usa alpha=0,5 e beta=2, ruído R=diag(0,2^2,0,2^2) K² e Q documentada no código; a sintonia é fixa e não foi otimizada no teste. O UKF adaptativo estima conjuntamente log UA e log k com passeios aleatórios e caixas de parâmetros. Esse baseline tem incerteza dos parâmetros aproximada pela covariância ampliada.

DarwinParametric usa a melhor hipótese não estrutural aprovada pelo mesmo holdout. ResidualRBF e Neural aprendem log UA a partir do balanço integral da camisa: o primeiro com bases RBF densas e ridge; o segundo com uma MLP tanh 1-12-8-1. Os alvos são inferidos das temperaturas, nunca dos parâmetros verdadeiros. Não há supervisão por concentração. Seus pesos estão exportados em JSON. A incerteza dessas funções aprendidas não é integrada à covariância do filtro. MHE não foi implementado como baseline nesta versão; o ajuste de erro de saída não é denominado MHE.

## Diagnóstico, identificabilidade e monitoramento

A detecção usa o máximo temporal de uma estatística de média de inovações padronizadas, calibrada em 50 episódios nominais independentes. NIS, autocorrelação de cinco defasagens, Ljung-Box, CUSUM e disponibilidade são registrados. CUSUM e Ljung-Box são diagnósticos adicionais, não prova de mudança física. Dependência temporal e Q mal especificada afetam a interpretação dos p-valores.

A identificabilidade é examinada por singularidades de sensibilidades, perfis condicionais e um certificado exato de estados invisíveis, inspirado na distinção entre identificabilidade estrutural e prática [3]. Melhor ajuste térmico não implica que a causa química correta tenha sido recuperada. O monitor compara previsões anteriores à assimilação contra um UKF nominal paralelo; se a perda piora por uma janela de 20 passos, volta ao nominal. O controlador também reverte quando uma correção perde viabilidade ou sai do envelope. Reversões por domínio e por piora de previsão têm testes negativos.

## Estatística

A unidade de reamostragem é o episódio, não o instante. O bootstrap usa 2.000 reamostragens e seed 61017; as diferenças são pareadas porque os comparadores recebem a mesma planta, ruído e entradas em malha aberta. O teste de Wilcoxon acompanha as diferenças e Holm corrige a família Darwin versus UKF entre cenários. Comparações contra outros baselines e ablações são exploratórias. Em malha fechada, o ruído e o estado inicial são pareados, mas ações diferentes geram plantas percorridas diferentes. Não se soma o número de métodos para inflar o número de episódios independentes.
