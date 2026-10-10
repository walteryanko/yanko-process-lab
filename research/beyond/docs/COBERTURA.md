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
