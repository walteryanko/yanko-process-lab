---
title: "Síntese executiva para discussão científica — PG Frontier"
author: "Walter Yanko de Aragão Brandão"
date: "20 October 2026"
lang: "pt-BR"
fontsize: 11pt
geometry: margin=24mm
colorlinks: true
---

# Resultado e escopo

Foram executadas 5320 trajetórias principais, 400 confirmações e 18 verificações de grade. Esta entrega documenta o núcleo computacional e permanece PARCIAL frente à missão integral. A auditoria recalculou IAE e RMSE em 5720 arquivos de trajetória. O histórico completo ICAC e o modelo físico calibrado M1 não foram recuperados.

A contribuição matemática mais útil é separar as dependências físicas necessárias para a ambiguidade. Com cinética de primeira ordem em A e capacidades caloríficas constantes, duas direções químicas podem permanecer invisíveis às temperaturas. Tornar a camisa recíproca não remove esse núcleo. Propriedades independentes dependentes de temperatura podem reduzir esse núcleo, sem necessariamente fornecer sinal mensurável no tempo útil ao controle.

\newpage

# Resultados de controle

Melhoria positiva favorece o candidato. As diferenças são pareadas por semente e condicionadas à suíte finita, com modelos e limites compartilhados. Não equivalem a uma conclusão industrial.

| candidate | baseline | percent_improvement | mean_improvement | ci95_low | ci95_high | p_holm_primary |
| --- | --- | --- | --- | --- | --- | --- |
| P2_regret | B1_ukf | 0.634593 | 0.000850102 | -0.00100823 | 0.00283537 | 0.418569 |
| P3_adaptive_regret | B2_both | 0.657212 | 0.000578973 | -0.000207131 | 0.00145957 | 0.418569 |
| B2_both | B2_estimator | 39.912 | 0.0585153 | 0.0565261 | 0.0604609 | 3.11056e-22 |


Os ganhos adicionais de P2 e P3 foram 0,63% e 0,66%, com IC incluindo zero, sem confirmação de benefício. O ganho de 39,91% vem de compartilhar a correção paramétrica com o preditor. O PI teve IAE favorável, mas excedeu amplamente a temperatura limite; informação química ajudou no inventário incerto, sem ganho uniforme sob mismatch.

O confronto contínuo utiliza a mesma parametrização curta de dois blocos. Ainda falta a comparação com o NMPC histórico de horizonte 57 e seis movimentos, além da sintonia competitiva do PI/MHE. A meta exploratória de 10% não deve ser lida como promessa ou como critério suficiente de publicação.

\newpage

# Contraexemplos e perguntas para discussão

| scenario | candidate | percent_improvement | ci95_low | ci95_high |
| --- | --- | --- | --- | --- |
| correlated_noise | B0_PI | -592.588 | -0.0120465 | -0.00900468 |
| saturation | P5_noisy | -453.515 | -0.0115612 | -0.00356675 |
| saturation | B2_both | -414.805 | -0.00994615 | -0.00387001 |
| correlated_noise | B2_both | -398.963 | -0.0101161 | -0.00404126 |
| dropout | P5_noisy | -381.224 | -0.00936466 | -0.0033412 |
| nominal | P5_noisy | -381.224 | -0.00933152 | -0.00325644 |


Perguntas centrais para colaboradores: quais correlações experimentais Cp(T) devem substituir as hipóteses? Qual é a informação inicial realmente disponível sobre os inventários? O ganho de cada contraste persiste quando horizonte, solver e orçamento são equiparados ao baseline histórico? Qual sensor adicional pode ser instalado e qual seu atraso real?

\newpage

# Decisão científica e próximo gate

A limitação do modelo histórico está demonstrada sob hipóteses explícitas. Uma limitação universal do reator físico não está demonstrada. O valor de informação depende do objetivo e da autoridade de atuação. O artigo não deve reivindicar nova teoria geral, melhor controlador universal ou validação industrial.

O pacote fornece código, dados, figuras, fontes LaTeX, PDF compilado, DOCX, revisão dirigida e registro das lacunas. Para promover a versão a FINAL: recuperar e reexecutar ICAC/C08; obter propriedades físicas e dinâmica de analisadores; concluir baselines contínuos fortes; revisar causalidade/identificabilidade com especialista; confirmar regimes novos; e só então decidir o periódico e a submissão.
