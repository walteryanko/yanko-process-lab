# PG Estimator Benchmark v0.1 — análise dos resultados
Data: 20 de outubro de 2026.

## Resultado principal
Na campanha exploratória executada, o EKF por mistura Gaussiana (GM_EKF) melhorou a estimação de propilenoglicol sob medições contaminadas. A melhora de controle foi menor que a melhora de estimação.
O MHE curto não apresentou ganho prático de IAE que justificasse seu maior custo computacional nesta configuração.
Esses resultados são de simulação; não constituem validação industrial ou uma conclusão geral sobre todos os MHEs ou filtros robustos.

## Base e execução
- Modelo histórico SI completo de seis estados, variant=1, preservado da comparação da dissertação.
- Commit de base: b55a46cd182c70100b50ff5e6c98ba82ed96a5a8.
- Código da campanha executada: ef281d3e805fcd1ecded3a12f1d7f34b5e778c7a.
- Resultados originais: e8d6ebba51267007d27ac4790f075cdd6531c84f.
- Estados: CA, CB, CC, CM, T e Tt. Apenas T e Tt são fornecidas aos observadores.
- Ts=0,015 h (54 s); mesmo NMPC histórico, horizontes p=57 e m=6.
- Cenários: OL_FA, SERVO_P10 e REG_FA15. Malha fechada com QR=0 ou QR=1000.
- Duas condições: ruído Gaussiano e contaminação independente de 5% por canal, com desvio-padrão 10 vezes maior nos pontos contaminados.
- Oito sementes por célula; 320 episódios previstos e concluídos; nenhuma falha.
- O protocolo foi registrado antes da execução, sem sintonia posterior com os resultados de teste.
- Execução numérica: Linux, Python 3.12.15, CPU, dois processos; 310,23 s para campanha, análise e exportação, após a preparação.
- A implementação Windows usa grafos CasADi sem exigir gcc, mas não foi executada em Windows nesta validação.

## Comparação representativa: regulatório FA −15%, com penalização térmica, ruído contaminado
Médias de oito realizações pareadas:
| Método | RMSE CC (mol/L) | IAE CC (mol/L·h) | Tempo acima de 344,2611 K (min) | Estimador (ms/amostra) |
|---|---:|---:|---:|---:|
| UKF_RK4 | 0,026955 | 0,325822 | 12,100 | 0,070 |
| EKF | 0,026955 | 0,325866 | 12,431 | 0,263 |
| GM_EKF | 0,017554 | 0,319301 | 4,932 | 0,885 |
| MHE5 | 0,026920 | 0,325835 | 12,084 | 3,032 |

Em relação ao UKF:
- GM_EKF: redução de 34,88% no RMSE de CC e 2,00% no IAE.
- Tempo médio acima do limite: 12,10 → 4,93 min, redução descritiva de 59,24%.
- IC95% bootstrap pareado da diferença GM_EKF−UKF no RMSE: [−0,010306; −0,008528] mol/L.
- IC95% bootstrap pareado da diferença no IAE: [−0,010646; −0,002601] mol/L·h.
- MHE5: diferença média de IAE +0,000013 mol/L·h; IC95% [−0,000297; +0,000300]. Não há evidência de melhora de controle nesse contraste.
- Custo médio do MHE: 3,032 ms/amostra contra 0,070 ms do UKF, aproximadamente 43 vezes maior nesta implementação e neste runner.
- Mesmo o GM_EKF ainda ultrapassou o limite térmico. O maior pico entre os oito episódios foi 344,7663 K, contra 345,7965 K no UKF. As médias da tabela não substituem esses extremos.
Os intervalos são exploratórios: oito sementes e diversos contrastes; não foram corrigidos por multiplicidade.

## Outros cenários e contrapartidas
Sob contaminação, a redução de RMSE pelo GM_EKF foi de 34,41% em OL_FA e 31,86% em SERVO_P10.
Em SERVO_P10 com penalização térmica, o IAE médio caiu de 0,374592 para 0,368103 mol/L·h, redução de 1,73%.
No regime Gaussiano sem contaminação, GM_EKF apresentou pequena piora: em REG_FA15 com penalização, RMSE 0,0170495 → 0,0172340 mol/L e IAE 0,316527 → 0,317920 mol/L·h.
Portanto, esta rodada apoia a utilidade da robustez para o ruído contaminado estudado, com uma pequena contrapartida quando o ruído é Gaussiano.
O EKF convencional ficou muito próximo do UKF nas condições avaliadas. Esta campanha não sustenta trocar o UKF por um MHE apenas por ser um método mais complexo.

## Interpretação e limites
A explicação compatível com os resultados é que a mistura Gaussiana reduz a influência das leituras térmicas anômalas, preservando melhor as concentrações inferidas. O ganho de RMSE não se transfere na mesma proporção ao IAE, porque o resultado de controle também depende do objetivo, do horizonte, da atuação e da dinâmica em malha fechada.
Esta é uma interpretação dos resultados, não uma identificação causal completa de cada contribuição interna do algoritmo.

GM_EKF não é reprodução do DDR-EKF de Hu et al. O MHE com janela de cinco transições e cinco avaliações máximas não herda as garantias teóricas de Schiller e Müller.
O custo de chegada do MHE utiliza um EKF causal na fronteira esquerda; a observação nessa fronteira não é contada novamente no custo da janela.
A planta é nominal; não se testaram aqui erro de cinética/UA, inventários iniciais incertos, sensores ausentes, deriva persistente ou parâmetros de contaminação desconhecidos.
Os parâmetros 5% e fator 10 são conhecidos na configuração do filtro robusto e coincidem com a condição contaminada do gerador. Generalização a outras distribuições permanece em aberto.
QR=1000 é uma penalização suave, não uma restrição rígida. Não se conclui segurança térmica a partir desta campanha.
Os tempos medem estas implementações, incluindo diferenças entre chamadas NumPy/CasADi/Numba; não são medidas puras de complexidade algorítmica.

## Verificação e reprodução
Oito testes científicos passaram: paridade da transição histórica, Jacobiano por diferenças finitas independentes, correção de estados ocultos via covariância cruzada, limite Gaussiano da mistura, atenuação de erros grosseiros, preservação das amostras não contaminadas, paridade com o UKF anterior e prefixo causal do MHE.
A auditoria independente do CSV confirmou 320 linhas e 80 grupos pareados, cada um com quatro métodos e um único hash de ruído. Todas as decisões de NMPC registradas na malha fechada tiveram sucesso; nenhum fallback de controlador ou observador foi usado.
O pacote contém código, protocolo, métricas por episódio, contrastes pareados, dez gráficos e 320 trajetórias comprimidas.
SHA256 do pacote produzido: dc42ffbd6c023779d13a70f7e61bf4c5efc55e6a4c2069df289a404161632cb8.
[Pacote completo](PG_Estimator_Benchmark_v0.1.zip) · [Resultados estruturados](results.json) · [Métricas por episódio](metrics.csv) · [Contrastes pareados](paired.csv).
Execução verificável: https://github.com/walteryanko/yanko-process-lab/actions/runs/39485517361
