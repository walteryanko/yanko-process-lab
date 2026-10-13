# Autotuning e laboratório — ProcessLab Studio 0.2.0

A sintonia é uma busca computacional offline no modelo selecionado. O programa não
opera equipamentos físicos, não identifica automaticamente uma planta desconhecida
e não promete um ótimo global.

## Espaço de busca

| Estratégia | Parâmetros pesquisados |
|---|---|
| PID | Kp: 0,1–4 vezes a escala nominal; Ki: 0,03–8 vezes; Kd: intervalo linear a partir de zero |
| NMPC | Penalidade de movimento: 0,001–10; horizonte inteiro: 2–12 passos, dependendo do horizonte atual |
| EKF / UKF / MHE | Multiplicador Q: 0,001–100; multiplicador R: 0,05–20 |

As escalas de PID incluem um piso derivado da faixa de atuação e da amostragem para
permitir busca mesmo com ganhos iniciais nulos. Os limites exatos estão no relatório.
A configuração original participa como candidato zero, mesmo fora dos limites da busca.
Na busca conjunta, os dois grupos são pesquisados simultaneamente.

## Critério divulgado no relatório

Controle: IAE normalizado por duração e escala do objetivo, mais 0,02 vezes a média
do quadrado dos movimentos normalizados da entrada, mais 0,2 vezes a fração de falhas
do NMPC. A escala de temperatura é 5 K/°C; para qualidade, o máximo de 0,05 e 5% da meta.

Sensor: média dos RMSE dos estados divididos por suas escalas, mais RMSE da qualidade
normalizado, mais uma penalidade de 0,05 vezes o déficit de cobertura abaixo de 90%.
Cobertura é descritiva; a penalidade não torna a covariância estatisticamente calibrada.
O MHE continua mostrando a covariância do EKF auxiliar. Busca conjunta soma os critérios.
Estados simulados só participam dessa avaliação posterior; não são realimentados como
medições do observador ou do controlador.

## Treino, validação e uso em aula

A busca usa a semente do projeto. O vencedor é congelado antes de dois ensaios de
validação (semente +104729 e +209759, módulo 2^32). Original e candidato usam sementes
pareadas. Só há recomendação com ambos completos, melhoria média >=1% e piora <=5%
por semente. Alterar o projeto impede aplicar uma recomendação antiga por engano.

Em aula, peça uma hipótese antes de executar: aumentar Kp sempre reduz o IAE? Atraso
prejudica o sensor? Q/R resolve falta de observabilidade? Depois compare condições
que não participaram da busca. Professores podem distribuir projetos JSON; estudantes
entregam estudos JSON/CSV com sementes, parâmetros, versão do código e conclusões.

O gráfico de qualidade pode parecer preciso mesmo com estados individuais errados.
O exemplo de propilenoglicol preserva ambiguidades térmicas conhecidas. Investigue
medições químicas adicionais e consulte o diagnóstico de observabilidade.

## Reprodutibilidade e tempo

JSON contém o projeto original, configurações de cada trajetória, métricas, versões,
hashes do mecanismo e os dados efetivamente calculados. Comparações não alteram a
simulação principal. O cancelamento salva ensaios completos; resultados parciais não
são recomendados. O limite de tempo é cooperativo: o passo numérico em curso termina
antes da interrupção. Comece com EKF, poucos passos e um orçamento de 90 s.
