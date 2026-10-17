# MASTER WORK PROMPT
# 🧬 YCS DARWIN-OBSERVER LAB v1.0
## Autonomous Scientific Discovery for Nonlinear Chemical Process Estimation and Control

**Projeto:** Yanko Creative Studio | YCS ProcessLab Scientific Research  
**Modelo:** GPT-6  
**Esforço:** Extra High, se disponível  
**Ambiente:** ChatGPT Work  
**Execução:** Engenharia científica real, pesquisa, implementação e experimentação computacional  
**Plataforma:** Windows 10/11 x64, Python 3.11+, CPU-first, 16 GB RAM  
**Data de referência:** Outubro de 2026

**Missão:** RECUPERAR → AUDITAR → FORMULAR → IMPLEMENTAR → EXPERIMENTAR → DESCOBRIR → FALSIFICAR → VALIDAR → ENTREGAR.

---

# 0. MISSÃO CENTRAL

Desenvolva o **YCS Darwin-Observer**, um laboratório científico funcional que investiga se um observador de estados pode descobrir, de maneira parcialmente autônoma, erros estruturais nas equações de um processo químico não linear.

O sistema deverá:

1. Estimar estados não mensurados de um CSTR de propilenoglicol.
2. Detectar discrepâncias entre comportamento observado e modelo matemático.
3. Formular hipóteses físicas alternativas para explicar essas discrepâncias.
4. Descobrir equações candidatas por regressão simbólica e identificação esparsa.
5. Avaliar as hipóteses usando dados não empregados em sua descoberta.
6. Rejeitar hipóteses sem evidência suficiente.
7. Atualizar o modelo de previsão apenas quando existirem evidências quantitativas.
8. Comparar o desempenho contra UKF, observadores adaptativos e outros baselines adequados.
9. Investigar os efeitos da descoberta de modelos sobre um NMPC inferencial.
10. Produzir código funcional, testes, resultados científicos e laboratório visual interativo.

**Pergunta científica principal:**

> Um observador pode identificar autonomamente equações que faltam ou estão incorretas em um modelo de CSTR, usando somente medições operacionais limitadas, e melhorar a estimação de estados químicos sem perder estabilidade, interpretabilidade ou segurança?

Não apresente resultados simulados antes de executar os experimentos.

Não considere uma equação descoberta em uma planta virtual como uma nova lei universal da química.

O objetivo é testar se o método consegue recuperar estrutura física escondida ou desconhecida do seu modelo nominal.

---

# 1. RECUPERAÇÃO DOS PROJETOS EXISTENTES

Antes de implementar novos algoritmos, investigue os ativos existentes.

Repositório principal:

https://github.com/walteryanko/yanko-process-lab

Procure recuperar também, quando acessíveis:

- Implementação original do CSTR de propilenoglicol.
- Equações e parâmetros da dissertação de Walter Yanko de Aragão Brandão, UFCG, 2019.
- Implementações do EKF e UKF.
- Controlador NMPC inferencial.
- Pesquisa RSI-ProcessLab.
- Pesquisa AIRE-NMPC.
- Experimentos NAKE.
- Experimento Oracle-KF.
- Componentes científicos do YCS ProcessLab Studio.

Use o GitHub, os arquivos disponibilizados e conexões acessíveis pelo Work.

Não suponha que todos os projetos estejam disponíveis.

Se algum ativo for inacessível, registre a limitação e continue com as fontes verificadas.

Não substitua implementações existentes por versões simplificadas sem uma justificativa técnica documentada.

Não modifique as branches estáveis dos projetos originais.

Crie um projeto independente, com interfaces de integração ao ProcessLab.

---

# 2. MODELO FÍSICO OBRIGATÓRIO

O processo estudado é um CSTR não isotérmico de hidrólise do óxido de propileno para formação de propilenoglicol.

Reação principal:

A + B → C

Onde:

- A: óxido de propileno.
- B: água.
- C: propilenoglicol.
- M: metanol não reagente.

Vetor de estados:

x = [CA, CB, CC, CM, T, Tt]ᵀ

Vetor de medições operacionais:

y = [T, Tt]ᵀ

Variável manipulada principal:

u = mw, vazão de água refrigerante.

O controle da qualidade é inferencial, uma vez que a concentração de propilenoglicol não é medida diretamente pelo observador.

## 2.1 Preservação da física

Recupere as equações originais:

- Balanços materiais.
- Cinética de pseudo-primeira ordem.
- Equação de Arrhenius.
- Balanço de energia do reator.
- Balanço térmico do refrigerante.
- Transferência de calor.
- Condições de alimentação.
- Limites operacionais.
- Equilíbrios existentes.
- Integração temporal.

Preserve a assimetria térmica presente no modelo histórico.

Audite rigorosamente unidades, conversões, parâmetros e constantes termodinâmicas.

**Atenção:** existem variantes diferentes do modelo PG em nossos projetos, incluindo a implementação histórica e a variante tabelada do ProcessLab. Elas podem apresentar equilíbrios distintos.

Não misture parâmetros dessas variantes.

Escolha uma variante primária depois da auditoria e registre sua identidade, versão, equações, unidades e ponto de equilíbrio.

Use as demais como experiências de transferência e robustez, claramente identificadas.

Se possível, valide derivadas numéricas e equilíbrio contra implementações previamente verificadas.

---

# 3. HIPÓTESE DARWIN

Um observador convencional pressupõe que a estrutura do modelo é conhecida.

O Darwin-Observer trabalhará com a hipótese de que essa estrutura pode estar incompleta.

Formalmente:

dx/dt = f_nominal(x,u,θ) + g(x,u,θ)

Onde:

- f_nominal representa o modelo físico conhecido.
- θ representa parâmetros identificáveis.
- g representa uma correção estrutural desconhecida.

O desafio é descobrir uma expressão interpretável para g, quando os dados sustentarem sua existência.

A correção poderá ser nula.

O sistema não deve ser obrigado a encontrar uma equação.

**A hipótese nula é que o modelo original já é suficientemente adequado.**

Um bom algoritmo deve reconhecer essa situação e permanecer inativo.

---

# 4. ARQUITETURA CIENTÍFICA

Implemente os seguintes módulos.

## 4.1 Physics Core

Núcleo físico independente, testável e versionado.

Responsável por:

- Integração das equações diferenciais.
- Simulação de trajetórias.
- Estados estacionários.
- Aplicação de perturbações.
- Injeção de mudanças estruturais controladas.
- Geração de dados sintéticos reprodutíveis.
- Verificações de domínio físico.

Permita separar completamente a planta virtual verdadeira do modelo utilizado pelo observador.

O modelo nominal não pode conhecer os parâmetros ocultos ou a equação injetada na planta experimental.

## 4.2 Observer Core

Implemente ou reutilize:

- UKF de referência.
- EKF, quando disponível.
- UKF com parâmetros adaptativos.
- Estimador de parâmetros conjunto, quando identificável.
- Observador Darwin com correção estrutural.
- Baseline de correção residual sem regressão simbólica.

Considere MHE como baseline adicional caso seja computacionalmente viável.

Preserve o histórico temporal e as covariâncias.

Não permita acesso do observador aos estados verdadeiros durante a execução operacional.

## 4.3 Residual Intelligence

Crie um módulo de análise de inovações.

Para cada instante:

r_k = y_k − ŷ_k|k−1

Analise:

- Magnitude e persistência dos resíduos.
- Correlação temporal.
- Branqueamento das inovações.
- Mudanças de distribuição.
- Erros sistemáticos de previsão.
- Sensibilidade a entradas.
- Possível deriva de parâmetros.
- Possíveis falhas de sensores.

Utilize testes estatísticos e detectores sequenciais adequados.

Não confunda automaticamente discrepância estatística com falha da física.

## 4.4 Hypothesis Engine

Quando houver evidência de discrepância persistente, o sistema deverá formular hipóteses concorrentes.

Exemplos:

H0: modelo correto, discrepância causada por ruído.

H1: coeficiente global de transferência de calor UA incorreto.

H2: UA depende da vazão de refrigerante.

H3: coeficiente cinético incorreto.

H4: energia de ativação incorreta.

H5: calor de reação incorreto.

H6: erro de composição da alimentação.

H7: viés ou deriva em sensor de temperatura.

H8: dinâmica adicional não representada.

H9: alteração nas propriedades térmicas.

Cada hipótese deverá especificar:

- Parâmetros ou estrutura alterados.
- Variáveis explicativas.
- Complexidade.
- Condições de identificação.
- Evidências favoráveis e contrárias.
- Predições verificáveis.
- Grau de incerteza.

O sistema poderá responder que várias hipóteses são indistinguíveis.

Essa resposta é preferível a uma explicação incorreta apresentada com confiança excessiva.

---

# 5. MOTOR DE DESCOBERTA SIMBÓLICA

Investigue e implemente uma combinação adequada de:

- SINDy.
- Sparse regression.
- Symbolic regression.
- PySR, quando tecnicamente viável.
- SymPy.
- Métodos de seleção esparsa.
- Otimização de parâmetros.
- Inferência probabilística das hipóteses.

Evite dependências pesadas desnecessárias.

Forneça uma implementação CPU-first funcional mesmo quando PySR ou outros componentes opcionais não estiverem disponíveis.

## 5.1 Espaço de expressões

Considere operadores matemáticos como:

+, −, ×, divisão protegida, exponenciais e potências limitadas.

Utilize conhecimento físico para restringir expressões.

Exemplos de hipóteses estruturais:

UA_eff = UA0 × (1 + a × φ(mw))

k_eff(T) = k_nominal(T) × exp(ψ(T))

q_corr = a × ΔT + b × ΔT²

Essas expressões são apenas famílias candidatas.

Não pressuponha que sejam verdadeiras.

## 5.2 Restrições físicas

Implemente mecanismos para:

- Preservar dimensões físicas.
- Respeitar conservação de massa.
- Respeitar estequiometria.
- Evitar concentrações negativas.
- Impor positividade a propriedades que a exigem.
- Restringir expressões singulares.
- Evitar extrapolações não controladas.
- Penalizar complexidade desnecessária.
- Preservar os limites operacionais.

Não permita que a correção estrutural seja uma função arbitrária e instável apenas porque ajusta bem os dados de treinamento.

## 5.3 Ranking das descobertas

Avalie candidatos considerando:

1. Capacidade preditiva fora da amostra.
2. Simplicidade matemática.
3. Consistência física.
4. Identificabilidade.
5. Incerteza paramétrica.
6. Robustez a ruído.
7. Estabilidade em integração prolongada.
8. Generalização a novas perturbações.

Evite escolher modelos apenas pelo menor erro de ajuste.

Salve todas as equações aprovadas e rejeitadas, com os motivos da decisão.

---

# 6. EXPERIMENTOS CIENTÍFICOS OBRIGATÓRIOS

Desenvolva cinco experiências principais.

## EXPERIMENTO A: O Trocador Escondido

**Hipótese:** o observador consegue descobrir uma dependência estrutural desconhecida na transferência de calor.

Na planta virtual, introduza uma dependência de UA com a vazão de refrigerante que não exista no modelo nominal.

O Darwin-Observer deverá:

- Detectar a divergência.
- Diferenciar parâmetros incorretos de estrutura incorreta.
- Formular expressões candidatas.
- Ajustá-las com dados de treinamento.
- Validar a generalização.
- Investigar se uma equação compatível com a estrutura escondida pode ser recuperada.

Execute diferentes intensidades de alteração e diferentes condições de excitação.

Não use a expressão verdadeira da planta para restringir artificialmente a busca.

## EXPERIMENTO B: Cinética Mutante

**Hipótese:** o sistema consegue detectar discrepâncias na cinética da reação sem medições diretas de concentração.

Introduza alterações controladas na relação cinética-temperatura, preservando a consistência física.

Compare:

- UKF nominal.
- UKF com parâmetros adaptativos.
- Darwin-Observer paramétrico.
- Darwin-Observer simbólico.

Investigue se alterações em energia de ativação, fator pré-exponencial e transferência de calor são distinguíveis usando somente T e Tt.

Calcule indicadores de observabilidade, sensibilidade e identificabilidade.

Se a cinética não puder ser identificada de maneira única, documente essa limitação.

## EXPERIMENTO C: O Fantasma do Sensor

**Hipótese:** o Darwin-Observer consegue distinguir um erro de sensor de um erro estrutural do processo.

Introduza:

- Viés em T.
- Deriva lenta em Tt.
- Ruído adicional.
- Intermitência de medições.
- Alteração real em UA.

Faça uma comparação cega.

O sistema não pode conhecer a categoria da falha antes da classificação.

Meça taxas de detecção, falsos alarmes e falsas descobertas de equações.

Um observador científico não deve inventar uma nova lei química para corrigir um termômetro defeituoso.

## EXPERIMENTO D: Transferência entre Universos Físicos

**Hipótese:** uma correção simbólica descoberta em um regime operacional continua útil em outro regime.

Treine em um subconjunto de condições de operação.

Teste em:

- Novas temperaturas de alimentação.
- Novas vazões de refrigerante.
- Diferentes composições de alimentação.
- Ruído não observado no treinamento.
- Outros regimes de operação.
- Variantes documentadas do modelo PG, quando compatíveis.

Evite extrapolações não físicas.

Compare generalização de correções simbólicas com correções neurais e modelos puramente paramétricos.

## EXPERIMENTO E: Darwin + NMPC

**Hipótese:** corrigir a estrutura física usada na previsão melhora o controle inferencial do CSTR.

Integre o Darwin-Observer ao NMPC existente.

Compare:

1. UKF + NMPC nominal.
2. UKF adaptativo + NMPC nominal.
3. Darwin-Observer + NMPC com modelo nominal.
4. Darwin-Observer + NMPC com modelo corrigido.

O objetivo é separar os benefícios de melhorar a estimação daqueles decorrentes da melhoria do modelo utilizado pelo controlador.

Use perturbações, restrições e objetivos equivalentes.

Mantenha mecanismos de proteção e fallback.

A atualização de um modelo em controle só deverá ocorrer após validação e aprovação pelos critérios automáticos estabelecidos.

Se a correção simbólica piorar a previsão ou a viabilidade, o controlador deverá retornar ao modelo nominal.

Nenhum experimento autoriza aplicação direta a equipamentos industriais reais.

---

# 7. EXPERIMENTO EXPLORATÓRIO EXTRA

## DARWIN ADVERSARIAL

Crie um ambiente no qual um gerador de desafios tenta produzir trajetórias que revelem falhas nas hipóteses aprendidas.

O gerador poderá variar:

- Condições iniciais.
- Perturbações.
- Frequências de amostragem.
- Intensidades de ruído.
- Parâmetros desconhecidos.
- Condições operacionais admissíveis.

O sistema deverá procurar exemplos que falsifiquem as equações descobertas.

Mantenha uma divisão clara entre os desafios usados para desenvolvimento e um conjunto final de avaliação independente.

Não permita que o algoritmo refine a mesma hipótese indefinidamente sobre o conjunto de teste.

Esse experimento é exploratório e não deve atrasar os entregáveis científicos fundamentais.

---

# 8. PROTOCOLO DE VALIDAÇÃO

A avaliação científica deve ser reproduzível.

Defina previamente:

- Sementes aleatórias.
- Versões dos modelos.
- Condições iniciais.
- Intervalos paramétricos.
- Perturbações.
- Ruídos.
- Critérios de exclusão.
- Critérios de aceitação.
- Orçamento computacional.

Utilize inicialmente experimentos-piloto para verificar funcionamento.

Depois, realize pelo menos 100 episódios independentes por comparação principal, se viável no orçamento computacional disponível.

Use divisões independentes de treinamento, validação e teste.

Também realize estudos de ablação para determinar a contribuição de:

- Detecção de resíduos.
- Adaptação paramétrica.
- Descoberta simbólica.
- Restrições físicas.
- Ranking e validação de hipóteses.
- Atualização online.
- Mecanismo de fallback.

Relate todas as configurações experimentadas, inclusive as que falharem.

## 8.1 Métricas de estimação

Calcule:

- RMSE de CA, CB, CC e CM.
- RMSE das temperaturas.
- Erro de previsão a múltiplos passos.
- Consistência das inovações.
- Cobertura dos intervalos de confiança.
- Tempo de detecção.
- Frequência de falsos alarmes.

**Métrica prioritária:** RMSE de CC em trajetórias de teste independentes, porque CC representa a concentração de propilenoglicol.

## 8.2 Métricas de descoberta

Calcule:

- Erro de recuperação estrutural.
- Precisão da seleção de termos.
- Erro de parâmetros identificáveis.
- Complexidade simbólica.
- Taxa de falsas descobertas.
- Robustez a ruído.
- Generalização fora do treinamento.

Não equipare similaridade visual de equações com equivalência física.

## 8.3 Métricas de controle

Calcule:

- IAE.
- Erro de rastreamento de CC.
- Desempenho econômico, se o funcional original estiver disponível.
- Produção acumulada.
- Esforço de controle.
- Violações de restrições.
- Viabilidade do NMPC.
- Tempo computacional.

Reporte intervalos de confiança e resultados por semente.

Use comparações pareadas sempre que apropriado.

Não declare superioridade estatística com base apenas em médias.

---

# 9. CONTROLE DE CAUSALIDADE E IDENTIFICABILIDADE

Este é um requisito crítico.

O Darwin-Observer deve operar exclusivamente com informações disponíveis até o instante presente.

As concentrações verdadeiras da planta virtual poderão ser usadas para:

- Avaliação offline.
- Comparação quantitativa.
- Verificação de recuperação da equação escondida.

Elas não poderão ser usadas na descoberta online como se fossem medições industriais.

Da mesma forma, parâmetros ou mecanismos ocultos da planta não poderão ser revelados ao observador.

Avalie se as medições T e Tt são suficientes para distinguir as hipóteses.

Use, quando apropriado:

- Análise de observabilidade local.
- Sensibilidades diferenciais.
- Matriz de informação de Fisher.
- Análise de posto.
- Perfis de verossimilhança.
- Experimentos de excitação persistente.

Se for impossível distinguir duas explicações, preserve ambas como hipóteses plausíveis.

Não force conclusões.

---

# 10. MECANISMO DE EVOLUÇÃO CIENTÍFICA

Implemente uma máquina de estados auditável:

**OBSERVE → DETECT → HYPOTHESIZE → DISCOVER → CHALLENGE → VALIDATE → ACCEPT/REJECT → MONITOR**

Cada descoberta deverá possuir:

- Identificador.
- Equação.
- Versão do modelo original.
- Dados usados.
- Critérios estatísticos.
- Evidência de identificabilidade.
- Métricas comparativas.
- Resultados de falsificação.
- Estado de aceitação.
- Data e versão do experimento.
- Histórico de revisões.

O sistema poderá descobrir que uma hipótese aceita anteriormente deixou de funcionar.

Nesse caso, deverá registrar a contradição e retornar a um modelo previamente validado.

A reversão deverá ser testável.

---

# 11. LABORATÓRIO VISUAL INTERATIVO

Crie o **YCS Darwin-Observer Laboratory**, com identidade visual científica premium, inspirada no YCS ProcessLab.

O laboratório deverá funcionar localmente.

A interface precisa conter funcionalidades reais.

## Painel 1: Digital Twin

Visualização do CSTR com:

- Temperaturas.
- Concentrações reais quando disponíveis na simulação.
- Concentrações estimadas.
- Vazão de refrigerante.
- Perturbações.
- Estado operacional.

## Painel 2: Observer Arena

Compare estimadores lado a lado.

Mostre:

- Trajetórias.
- Incerteza.
- Erros.
- Resíduos.
- Estado do algoritmo.
- Tempo computacional.

## Painel 3: Discovery Engine

Visualize:

- Hipóteses concorrentes.
- Equações propostas.
- Termos selecionados.
- Parâmetros.
- Evidências.
- Ranking.
- Hipóteses rejeitadas.

O usuário deve poder abrir uma descoberta e entender matematicamente por que ela foi aceita ou rejeitada.

## Painel 4: Evolution Timeline

Mostre a sequência real de eventos:

Detecção → hipótese → teste → rejeição ou aceitação → monitoramento.

Não gere eventos ilustrativos apresentados como descobertas reais.

## Painel 5: Scientific Benchmark

Permita selecionar experimentos e visualizar:

- UKF versus Darwin.
- Modelo nominal versus corrigido.
- Gráficos de erro.
- Estatísticas.
- Resultados por semente.
- Intervalos de confiança.
- Equações recuperadas.
- Casos de falha.

## Painel 6: Equation Explorer

Permita visualizar equações matemáticas com renderização adequada.

Quando viável, ofereça:

- Exportação de LaTeX.
- Exportação SymPy.
- Inspeção de unidades.
- Gráficos de contribuição dos termos.
- Comparação entre modelo nominal e corrigido.

## Interface e execução

Priorize uso em notebook Windows de 16 GB RAM.

Use tecnologias adequadas ao ambiente disponível.

Pode ser uma aplicação web local com backend Python, desde que seja funcional.

Não faça apenas um mockup.

Não preencha painéis com resultados fictícios.

Inclua dados de demonstração somente se estiverem explicitamente identificados como sintéticos.

---

# 12. ENGENHARIA DE SOFTWARE

Organize o projeto de maneira modular.

Estrutura sugerida:

darwin-observer/
- physics/
- observers/
- detection/
- hypotheses/
- symbolic/
- identification/
- controllers/
- experiments/
- benchmarks/
- tests/
- dashboard/
- configs/
- reports/
- artifacts/
- README.md
- requirements.txt
- pyproject.toml

Adapte a organização se houver uma alternativa tecnicamente superior.

## Requisitos

- Python 3.11+.
- NumPy e SciPy.
- SymPy.
- Biblioteca de regressão simbólica quando apropriada.
- Simulações determinísticas com sementes.
- Configurações versionadas.
- Logging estruturado.
- Exportação CSV e JSON.
- Testes automatizados.
- Execução local.
- Instalação reproduzível.
- Fallbacks numéricos.
- Documentação científica.

Não exija GPU, serviços pagos ou APIs externas para a operação principal.

Inclua scripts de configuração e execução para Windows.

---

# 13. TESTES OBRIGATÓRIOS

Implemente testes de:

1. Balanços de massa.
2. Integridade dimensional.
3. Equilíbrio.
4. Integração numérica.
5. Equivalência com o modelo recuperado.
6. Convergência e consistência do observador.
7. Preservação da causalidade.
8. Detecção de mudanças.
9. Controle de falsos positivos.
10. Recuperação de estruturas matemáticas simples conhecidas.
11. Rejeição de expressões fisicamente inválidas.
12. Robustez contra overfitting.
13. Separação entre treinamento e teste.
14. Reprodutibilidade.
15. Fallback para o modelo nominal.
16. Restrições do controlador.
17. Funcionamento da interface.
18. Exportação de resultados.

Inclua testes negativos: situações em que o algoritmo deve falhar de maneira segura ou reconhecer falta de evidências.

Uma suíte aprovada não substitui a validação científica.

---

# 14. CRITÉRIOS DE SUCESSO

A investigação será considerada promissora quando conseguir demonstrar, em dados não vistos, pelo menos um dos seguintes avanços relevantes:

**A. Descoberta estrutural:** recuperar uma correção compatível com a estrutura escondida, com evidência de que ela é identificável.

**B. Estimação:** diminuir o erro de concentração de propilenoglicol relativamente aos baselines adequados, sem aumento inaceitável de falsos alarmes.

**C. Controle:** melhorar o desempenho inferencial do NMPC mantendo as restrições aplicáveis.

**D. Diagnóstico:** separar erros de instrumentação de discrepâncias estruturais com desempenho quantitativamente superior ao baseline.

**E. Honestidade científica:** identificar corretamente casos em que a informação disponível é insuficiente para descobrir a estrutura física.

Não estabeleça uma meta de melhoria obrigatória para considerar o código funcional.

Se o algoritmo não superar os baselines, explique por quê.

Resultados negativos são resultados válidos.

---

# 15. RELATÓRIOS CIENTÍFICOS

Produza:

**Relatório 1: Auditoria física**

Equações, parâmetros, unidades, variantes e verificações do CSTR.

**Relatório 2: Fundamentação metodológica**

Regressão simbólica, identificação esparsa, observadores adaptativos, identificabilidade e descoberta de modelos.

**Relatório 3: Experimentos**

Protocolos, configurações, resultados, gráficos, incertezas e falhas.

**Relatório 4: Análise crítica**

Em quais condições a descoberta funciona, quando falha, o que pode ser identificado e o que permanece ambíguo.

**Relatório 5: Potencial acadêmico**

Avalie se os resultados sustentam um artigo científico. Proponha título, hipótese central, contribuições verificadas, limitações e próximos experimentos.

Use fontes acadêmicas verificáveis.

Não invente citações, métricas ou conclusões.

---

# 16. ENTREGÁVEIS FINAIS

Entregue:

1. Código-fonte funcional completo.
2. Implementação dos observadores.
3. Motor de descoberta simbólica.
4. Experimentos reproduzíveis.
5. Testes automatizados.
6. Arquivos de configuração.
7. Datasets sintéticos e metadados das execuções.
8. Equações descobertas e rejeitadas.
9. Resultados CSV/JSON.
10. Gráficos científicos.
11. Relatórios técnicos e científicos.
12. Laboratório visual interativo.
13. Instruções de instalação e execução no Windows.
14. Pacote ZIP organizado.
15. Repositório ou branch GitHub com histórico das alterações, se a conexão permitir.

Não substitua entregáveis reais por uma descrição de como seriam feitos.

Não declare conclusão antes de verificar o funcionamento dos componentes.

Se algum entregável não puder ser produzido, informe precisamente o motivo.

---

# 17. ESTRATÉGIA DE EXECUÇÃO

Trabalhe em incrementos verificáveis.

**Fase 1:** recuperar e auditar a física, os observadores e as implementações existentes.

**Fase 2:** reproduzir o UKF e estabelecer baselines confiáveis.

**Fase 3:** implementar detecção de discrepâncias e teste da hipótese nula.

**Fase 4:** implementar descoberta simbólica restrita pela física.

**Fase 5:** executar os experimentos A, B e C com testes independentes.

**Fase 6:** investigar transferência de modelos e integração com NMPC.

**Fase 7:** executar validação estatística e estudos de ablação.

**Fase 8:** construir ou finalizar o laboratório visual alimentado pelos resultados reais.

**Fase 9:** empacotar, verificar e entregar os artefatos.

Registre checkpoints de execução.

Priorize primeiro um sistema pequeno, correto e capaz de falsificar hipóteses.

Depois amplie a capacidade científica.

Não gaste todo o orçamento computacional procurando equações antes de assegurar que os experimentos estão corretamente instrumentados.

---

# 18. INSTRUÇÃO FINAL

Atue como pesquisador científico, engenheiro de controle, engenheiro químico e desenvolvedor de software.

Utilize o melhor nível de raciocínio e ferramentas disponíveis.

Não procure confirmar que Darwin-Observer funciona.

**Procure descobrir se funciona.**

Se necessário, rejeite a arquitetura inicial e teste alternativas fundamentadas.

Preserve a rastreabilidade integral entre:

equação → hipótese → experimento → dados → resultado → conclusão.

A pergunta fundamental do projeto é:

> Até que ponto uma máquina pode descobrir o que está errado em seu próprio modelo físico, usando apenas as informações que um observador de processo industrial realmente possuiria?

Execute a investigação, implemente os sistemas e entregue os resultados verificáveis.

**INICIAR YCS DARWIN-OBSERVER LAB v1.0.**