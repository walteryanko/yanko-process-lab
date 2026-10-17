# Relatório 4 - Análise crítica

## O que foi sustentado

O laboratório demonstra que um balanço térmico auxiliar pode tornar uma discrepância de transferência de calor identificável como função das entradas, mesmo sem sensores diretos de concentração. A correção recuperou aproximadamente o expoente injetado e melhorou CC fora da amostra sob excitação ampla. O controle melhorou principalmente quando a correção entrou também na previsão do NMPC. A hipótese nula foi preservada na campanha nominal e nos cenários de ruído/perda de medições usados para comissionamento.

Isso sustenta recuperação de uma estrutura dentro de uma gramática e de uma planta virtual específica. Não sustenta descoberta geral de leis químicas. Os exemplos e magnitudes foram escolhidos para investigar mecanismos definidos; não representam uma distribuição validada de falhas industriais.

## O limite exato de informação química

Para delta x = [0, -cpC/cpB delta, delta, 0, 0, 0], CA e a capacidade térmica total não mudam. A diferença química é diluída por exp(-integral D dt), enquanto T e Tt permanecem iguais. No teste numérico, a separação inicial de CC é 0,12 kmol/m³ e a maior separação térmica é 0 K. Esse certificado já era conhecido no acervo RSI e não é apresentado como novidade do Darwin.

Há duas direções químicas estruturalmente invisíveis quando se permite variar CB, CC e CM mantendo CA e a capacidade térmica agregada. No equilíbrio, a matriz de sensibilidades calculada tem posto 3/6; em uma condição fora do equilíbrio tem posto 4/6. Bom RMSE após lavagem pode resultar do prior e da diluição dos erros iniciais, não da reconstrução de todo estado não observável. Um canal químico adicional ou um prior fundamentado pode ser necessário para distinguir mundos equivalentes.

[[FIG:05_identifiability.png]]

## Onde a inferência falhou

Com excitação fraca, diversas funções de UA têm desempenho parecido. A seleção de uma forma matemática não merece confiança de mecanismo único. A cinética curva foi confundida com alimentação. A transferência direta entre variantes completas piorou o erro. São resultados negativos centrais, e não episódios removidos por serem inconvenientes.

A cobertura de 95% de CC em B_activation foi 77.1% para Darwin, apesar do grande ganho médio em RMSE. Portanto, o observador corrigido ainda é excessivamente confiante nesse regime. As covariâncias não integram incerteza de seleção de modelo e de seus parâmetros. A melhora de média não basta para afirmar consistência probabilística.

## Limites metodológicos

Todos os dados são sintéticos e usam a mesma forma básica de balanços. Ruído aditivo de temperatura e falhas são simples; não há mistura arbitrária de falhas simultâneas, ruído de processo correlacionado, atrasos variáveis ou mecanismos industriais desconhecidos. O benchmark não contém comparação com MHE nem PySR irrestrito. A rede é uma pequena aproximação de UA, não uma rede neural geral de estado. Os testes de sensor representam classes e magnitudes específicas, com possibilidade real de abstenção.

O erro de saída usa um prefixo UKF dependente do modelo. As sensitividades e os erros-padrão são condicionais a essa inicialização. O ranking usa validação para escolher entre vários candidatos, o que torna essa validação uma etapa de seleção; a estimativa final de desempenho permanece no conjunto de teste independente. As comparações por cenário têm Holm apenas na família pré-declarada; outras leituras são exploratórias. O conjunto de 100 episódios mede variabilidade entre realizações, não cobre todos os possíveis mecanismos.

O baseline adaptativo é forte em mudanças de taxa simples e mais fraco em alguns problemas de sensor, pois pode absorver o erro do termômetro em parâmetros químicos. Darwin não domina todas as condições: isso é visível no CSV e nas bandas pareadas. As configurações são fixas, não ótimos universais de cada baseline.

## Engenharia e rastreabilidade

As decisões têm identificador, fingerprints dos registros, versão do modelo, parâmetros, candidatos rejeitados, motivos, condições, métricas e eventos. Modelos salvos podem ser restaurados, e GuardedDarwin pode reverter sem apagar o histórico. Em cada atualização aceita, o estado/covariância corrente é mantido; em reversão usa-se o nominal paralelo. Arquivos de dados incluem os estados verdadeiros somente como artefatos de avaliação, separados da interface Record.

A operação principal não usa GPU, API paga ou serviço externo. A instalação inicial baixa bibliotecas Python; depois o laboratório funciona localmente. Código e backend foram executados em Linux/Python 3.12. O ambiente Windows 10/11 é atendido por scripts e dependências com suporte Python 3.11+, mas não houve teste em um Windows real nesta sessão. Nenhum executável Windows nativo é alegado.
