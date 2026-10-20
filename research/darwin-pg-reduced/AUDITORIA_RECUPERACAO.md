# Darwin Observer — PG reduzido: auditoria e ponto de retomada

Data: 20/10/2026. Estado: **RECUPERAÇÃO E AUDITORIA PARCIAIS; CAMPANHA NÃO EXECUTADA**.

Este documento não é um relatório de resultados da nova campanha. Nenhum RMSE, IAE, intervalo de confiança, gráfico ou teste novo de simulação foi produzido. A hipótese de superioridade do modelo reduzido permanece aberta.

## 1. Bloqueio de execução e contabilidade

O executor local recusou duas chamadas, incluindo uma verificação explícita de Python, com:
`No usable execution environment is available. Wait for an environment to become available before using this tool.`

- Novas trajetórias iniciadas: 0.
- Novas trajetórias concluídas: 0.
- Novas trajetórias interrompidas: 0.
- Protocolo final congelado: não.
- Quantidade final de trajetórias planejadas: ainda não definida; depende do piloto e da matriz final de condições.
- O workflow já existente em `.github/workflows/verify.yml` executa testes e demo TypeScript/Node; sua existência não prova execução desta campanha Python.
- Nenhum workflow novo ou simulação remota foi disparado nesta etapa.
- Nenhum teste de integração, UKF, NMPC ou reprodução de métricas foi executado nesta etapa.

Esta branch parte do commit histórico `b55a46cd182c70100b50ff5e6c98ba82ed96a5a8`; os resultados herdados são anteriores, e não resultados desta campanha.

## 2. Fontes efetivamente lidas

Os caminhos abaixo são relativos a `research/darwin-observer/`, no commit-base:

| Fonte | Conteúdo conferido |
|---|---|
| `vendor/thesis_original/modeloCT.m` | Seis balanços históricos, cinética e convenção térmica |
| `vendor/thesis_original/modeloFun_KF.m` | Mesma dinâmica e Euler com h=0,015 h |
| `vendor/thesis_original/medFun_KF.m` | Medições exclusivamente T e Tt |
| `vendor/thesis_original/NMPC_Fmincon.m` | SQP contínuo, limites de atuação e penalização térmica |
| `vendor/thesis_original/cost.m` | Rotina histórica de sintonia do filtro; não confundir com o custo do NMPC |
| `darwin/physics.py` | Variantes distintas: ProcessLab tabulado e histórico convertido integralmente |
| `darwin/observers.py` | UKF, covariâncias, fatoração e regularização |
| `darwin/thesis_control.py` | Reconstrução contínua SLSQP/CasADi do controlador da dissertação |
| `darwin/thesis_cases.py` | Cenários, eventos, ruídos e conversões |
| `darwin/discovery.py` | H0, hipóteses, validação independente e reversão |
| `darwin/identification.py` | Ajuste paramétrico por temperaturas e previsão fora da amostra |
| `artifacts/thesis/protocol.json` | Configuração da campanha anterior |
| `artifacts/thesis/source_provenance.json` | Proveniência histórica e divergências documentadas |
| `artifacts/thesis/execution.json` | Registro anterior de execução; não reexecutado agora |

Também foram lidos o modelo `lib/simulation/model.ts` da branch principal e trechos relevantes da dissertação `Dissertacao_WalterYanko(1).pdf`, incluindo as equações 53–57 e a definição do trocador, nas páginas PDF 40–41 (páginas impressas 30–31).

Foi lida a versão atual 7 de `RESULTADOS.md`, modificada em 20/10/2026 às 17:18:34 UTC. O relatório anterior `Comparacao_Darwin_Dissertacao(1).pdf` foi lido parcialmente, incluindo metodologia e cenários.

### Arquivos localizados, mas não abertos/descompactados

| Arquivo | Identidade persistente | Tamanho em bytes |
|---|---|---:|
| PG_Temporal_Causality_v0.5.zip | libfile_c6e54cc590948191b311d6969d1c6d9e | 1279119 |
| PG_Actuator_Authority_v0.6.zip | libfile_91d1ced31e9881919eff6924a0c8c6ff | 3588859 |
| PG_Predictor_Intervention_v0.7.zip | libfile_993644f713348191bf983fd757d2bcda | 549675 |
| Comparacao_Darwin_Reproduzivel.zip | libfile_9de4a5430d0881919f4cf49ba40cd1d4 | 297925706 |
| YCS_Darwin_Dissertacao_Entrega_Recuperada.zip | libfile_1e4284abb7c481918c0108be8c094d50 | 33152474 |

Não se inspecionou o conteúdo interno desses ZIPs. Os UKFs reduzidos e o controlador enumerativo das versões v0.5–v0.7 ainda precisam ser recuperados e auditados. Não declarar paridade com essas versões com base apenas no resumo.

## 3. Duas variantes físicas que não devem ser misturadas

A branch principal traz os parâmetros SI tabulados, enquanto a reconstrução da dissertação usa a conversão integral do código imperial histórico. Existem diferenças em calor de reação, Arrhenius, propriedades e condições nominais.

Em particular, `physics.py` usa `variant=1` para o histórico integral e `variant=0` para a variante tabulada. A nova campanha precisa declarar explicitamente a variante; não combinar silenciosamente a planta histórica com constantes do modelo tabulado.

A convenção histórica `T + 460` em Fahrenheit exige, para sua reprodução literal em kelvin, o deslocamento de 0,183333... K já registrado em `legacy_rhs_factors`. Essa reprodução literal deve ser identificada, não apresentada como nova correção cinética descoberta.

### Temperatura do trocador

O código histórico e as equações 54–55 da dissertação usam:

```text
Qcool = mw cpB (Ta1 - T) [1 - exp(-UA / (mw cpB))]
dTt/dt = [mw cpB (Ta1 - Tt) - Qcool] / (rhoB Vt cpB)
```

Tt é a temperatura dinâmica do líquido no interior do trocador. Qcool depende de T e da temperatura de entrada Ta1, e não do estado Tt. Tt recebe a influência de T, mas não realimenta o balanço do reator nessa formulação. Substituir Qcool por UA(Tt-T) muda o processo.

### Amostragem e controlador histórico

- Amostragem confirmada no código e na dissertação: 0,015 h = 54 s.
- Medições: T e Tt.
- NMPC reconstruído: contínuo, SLSQP com derivadas CasADi; não enumerativo.
- Horizontes recuperados: previsão 57 e controle 6.
- Pesos recuperados: Qe=0,8 e Rdu=0,2.
- Limites históricos do código: 50–3000 lbmol/h, aproximadamente 22,680–1360,777 kmol/h.
- A tabela SI da dissertação apresenta aproximações diferentes; informar qual convenção está sendo usada.
- Limite térmico histórico: 160 °F = 344,261111... K.
- O termo de peso 1000 no custo é uma penalização suave. Não garante T abaixo do limite.
- Cenários e percentuais de temperatura históricos devem ser aplicados em Fahrenheit antes da conversão para kelvin.

## 4. Redução de inventários: dedução algébrica

Para o código recuperado, com cinética r=k(T)CA, vazão volumétrica v0 e D=v0/V:

```text
dCA = FA/V - D CA - r
dCB = FB/V - D CB - r
dCC =       - D CC + r
dCM = FM/V - D CM
```

Portanto:

```text
SA = CA + CC       dSA = FA/V - D SA
SB = CB + CC       dSB = FB/V - D SB
M  = CM            dM  = FM/V - D M
```

O cancelamento da reação é exato para essas equações. SA, SB e M precisam ser propagados com as alimentações e a diluição de cada intervalo; não são constantes durante distúrbios.

Se inventários iniciais e alimentações forem conhecidos, os estados estocásticos ativos podem ser z=(CC,T,Tt), com:

```text
CA=SA-CC; CB=SB-CC; CM=M.
```

Isso é uma formulação condicional com informação inicial física adicional em relação a seis estados inicialmente livres. Ainda não prova melhoria de RMSE ou de controle.

Com inventários incertos, uma representação (z,SA,SB,M) carrega seis variáveis incertas. Precisa manter covariâncias cruzadas e incerteza das entradas. Deve ser descrita como 3+3, dimensão efetiva 6, e não como um UKF estocástico puramente 3D.

## 5. Dois modos químicos invisíveis: dedução estrutural

Este resultado é algébrico, válido para a família de equações lida. Não é um posto calculado por SVD, nem um resultado de simulação.

Defina H=cpA CA + cpB CB + cpC CC + cpM CM, capacidade térmica por volume. Com cp constantes e conhecidos:

```text
dCA = FA/V - D CA - k(T)CA
dH  = (cpA FA + cpB FB + cpM FM)/V
      - D H + (cpC-cpA-cpB) k(T)CA
```

Os balanços de T e Tt dependem de (CA,H,T,Tt) e das entradas. Assim, o subsistema que produz as temperaturas fecha em quatro variáveis.

Considere duas condições iniciais com mesmas entradas e parâmetros, mesmo T/Tt, e perturbação química satisfazendo:

```text
delta_CA = 0
cpB delta_CB + cpC delta_CC + cpM delta_CM = 0.
```

Há duas direções independentes desse tipo no interior do domínio físico. Suas diferenças evoluem como exp(-integral D dt) e mantêm as mesmas temperaturas. Elas podem envolver valores distintos de CC.

Consequências condicionais:

1. O modelo completo não é localmente observável em seus seis estados livres por essas duas temperaturas; a dimensão distinguível não excede quatro.
2. Os modos invisíveis são estáveis para D>0. Detectabilidade e esquecimento do erro inicial não são recuperação da informação química perdida.
3. Inventários conhecidos removem ambiguidades por conhecimento físico. Isso deve ser separado de ganho puramente numérico por redução de dimensão.
4. Uma parametrização reduzida não torna a causa de um desvio identificável por si só.
5. Verificar numericamente posto, escalonamento e Gramian nas variantes efetivamente usadas continua obrigatório.

Não extrapolar essa dedução para cinéticas dependentes de CB, cp não lineares por espécie ou outra dinâmica térmica sem refazer a análise.

## 6. Comparação probabilística que falta implementar

Para inventários exatos, a reconstrução afim tem matriz G:

```text
         CC   T  Tt
CA       -1   0   0
CB       -1   0   0
CC        1   0   0
CM        0   0   0
T         0   1   0
Tt        0   0   1
```

O controle compatível exige médias reconstruídas, P6=G P3 G^T e Q6=G Q3 G^T, sob a mesma hipótese de ruído condicional. P6 é singular, com posto no máximo três.

O UKF completo compatível deve usar os mesmos pontos sigma transportados por G e os mesmos pesos efetivos do reduzido. Regenerar pontos sigma com uma regularização diagonal independente ou alterar a dimensão usada nos pesos pode romper a equivalência.

A rotina histórica `sym_psd` soma 1e-12 I; não pode ser reaproveitada sem avaliar e registrar o efeito sobre restrições exatas. Uma fatoração no suporte, que preserve as direções nulas, é necessária nesta ablação.

Para inventários incertos, usar a transformação afim invertível completa e transformar a covariância conjunta, inclusive os blocos cruzados. Não descartar a incerteza dos inventários na reconstrução das espécies.

## 7. Continuidade do Darwin

A implementação lida já possui H0, detecção, ajuste, validação em episódios separados, critérios de aceitação, monitoramento e reversão. Seu aproveitamento ainda exige:

- Admitir o observador reduzido nas rotinas de identificação e validação, em vez de manter silenciosamente o UKF completo.
- Restringir inicialmente a gramática a H0, multiplicador positivo de k, multiplicador positivo de UA e viés de sensor.
- Admitir correção combinada apenas após teste de identificabilidade condicional.
- Manter a mesma família, dados e inicialização na calibração paramétrica simples.
- Congelar modelos comissionados antes dos testes; falhas posteriores não podem ser antecipadas.
- Registrar monitoramento/reversões sem confundi-los com identificação online ou uso de concentrações verdadeiras.

## 8. Resultados anteriores e limites do conhecimento atual

O relatório anterior da dissertação e `execution.json` registram 1800 simulações, com 20 realizações por configuração, e empate Darwin/H0 versus UKF RK4. São resultados herdados; não foram reexecutados nem auditados a partir de trajetórias nesta etapa.

A versão 7 de `RESULTADOS.md` descreve uma intervenção oracular no preditor para v0.7. Ela relata que melhor RMSE de estimação não implicou melhor IAE de controle em um regime selecionado. Isso motiva observadores em sombra e decisões avaliadas no mesmo estado físico; não valida um Darwin reduzido identificado com dados operacionais.

Não transferir ao Darwin o benefício de revelar parâmetros verdadeiros.

## 9. Próximas condições de liberação científica

1. Obter um executor Python funcional.
2. Recuperar e abrir os ZIPs v0.5–v0.7; conferir implementações reduzidas, objetivos e limites.
3. Implementar redução, covariâncias singulares compatíveis e controles paramétricos, preservando a planta completa.
4. Passar testes de dinâmica, conservação, integração independente, cronologia, causalidade e equivalência probabilística.
5. Executar piloto de custo; definir matriz com 24 sementes pareadas por condição principal, mínimo 20.
6. Congelar protocolo, sementes, cenários, ruídos, critérios Darwin e controlador.
7. Executar identificação, validação e teste com separação explícita.
8. Auditar métricas por trajetórias salvas; gerar PDF, CSV, PNG/SVG, galeria offline e pacote completo.

A campanha só pode ser declarada concluída após essas etapas. Este checkpoint registra avanço de recuperação e dedução estrutural; não confirma nem refuta a hipótese experimental.
