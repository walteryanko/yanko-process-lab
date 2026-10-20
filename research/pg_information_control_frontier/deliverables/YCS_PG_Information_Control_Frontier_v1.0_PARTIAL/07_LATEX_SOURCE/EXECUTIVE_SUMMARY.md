---
title: "Síntese executiva para discussão científica — PG Frontier"
author: "Walter Yanko de Aragão Brandão"
date: "20 de outubro de 2026"
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

| Candidate | Baseline | Gain (%) | IAE diff. | CI lower | CI upper | Holm p |
| --- | --- | --- | --- | --- | --- | --- |
| P2 regret | B1 ukf | 0.63459 | 0.0008501 | -0.0010082 | 0.0028354 | 0.41857 |
| P3 adaptive regret | B2 both | 0.65721 | 0.00057897 | -0.00020713 | 0.0014596 | 0.41857 |
| B2 both | B2 estimator | 39.912 | 0.058515 | 0.056526 | 0.060461 | 3.1106e-22 |


Os ganhos adicionais de P2 e P3 foram 0,63% e 0,66%, com IC incluindo zero, sem confirmação de benefício. O ganho de 39,91% vem de compartilhar a correção paramétrica com o preditor. O PI teve IAE favorável, mas excedeu amplamente a temperatura limite; informação química ajudou no inventário incerto, sem ganho uniforme sob mismatch.

O confronto contínuo utiliza a mesma parametrização curta de dois blocos. Ainda falta a comparação com o NMPC histórico de horizonte 57 e seis movimentos, além da sintonia competitiva do PI/MHE. A meta exploratória de 10% não deve ser lida como promessa ou como critério suficiente de publicação.

\newpage

# Contraexemplos e perguntas para discussão

| scenario | Candidate | Gain (%) | CI lower | CI upper |
| --- | --- | --- | --- | --- |
| correlated noise | B0 PI | -592.59 | -0.012046 | -0.0090047 |
| saturation | P5 noisy | -453.52 | -0.011561 | -0.0035668 |
| saturation | B2 both | -414.81 | -0.0099462 | -0.00387 |
| correlated noise | B2 both | -398.96 | -0.010116 | -0.0040413 |
| dropout | P5 noisy | -381.22 | -0.0093647 | -0.0033412 |
| nominal | P5 noisy | -381.22 | -0.0093315 | -0.0032564 |


Perguntas centrais para colaboradores: quais correlações experimentais Cp(T) devem substituir as hipóteses? Qual é a informação inicial realmente disponível sobre os inventários? O ganho de cada contraste persiste quando horizonte, solver e orçamento são equiparados ao baseline histórico? Qual sensor adicional pode ser instalado e qual seu atraso real?

\newpage

# Decisão científica e próximo gate

A limitação do modelo histórico está demonstrada sob hipóteses explícitas. Uma limitação universal do reator físico não está demonstrada. O valor de informação depende do objetivo e da autoridade de atuação. O artigo não deve reivindicar nova teoria geral, melhor controlador universal ou validação industrial.

O pacote fornece código, dados, figuras, fontes LaTeX, PDF compilado, DOCX, revisão dirigida e registro das lacunas. Para promover a versão a FINAL: recuperar e reexecutar ICAC/C08; obter propriedades físicas e dinâmica de analisadores; concluir baselines contínuos fortes; revisar causalidade/identificabilidade com especialista; confirmar regimes novos; e só então decidir o periódico e a submissão.
