# YCS ProcessLab Studio — entrega de implementação

13 de outubro de 2026 · versão 0.1.0 · checkpoint científico funcional

## Resultado

Foi implementado um aplicativo com interface React/React Flow e mecanismo Python
real, integrado ao repositório existente, preservando o núcleo TypeScript e as
pesquisas históricas. O código foi executado e verificado em Linux e na CI Windows.
Após autorização explícita do usuário, a branch foi publicada. O instalador x64 foi
gerado, instalado e aberto com sucesso no Windows Server 2022 da CI.

Os cinco cenários passaram dentro do executável empacotado. O commit exato do
binário é `42a85b820740774729f3c28c4e402a3ddeeea52a`; consulte `WINDOWS_VALIDATION.md`.
O Windows 10 e o notebook do usuário ainda não foram testados. A versão continua
sendo um checkpoint de pesquisa, sem alegação de conclusão de todo o MASTER.

## Recuperação

- Repositório completo e quatro branches científicas auditados, com histórico Git.
- PG original MATLAB e sua tradução SI recuperados; temperatura nominal ≈332,3336 K.
- Variante TypeScript tabelada ≈340,3035 K e variante calibrada 332,3 K preservadas.
- Etilbenzeno R1 reduzido recuperado, com discrepância termodinâmica explicitada.
- Pacote AIRE-NMPC recuperado para auditoria isolada, com testes selecionados rerodados.
- Relatórios RSI recuperados. A branch RSI apontava ao commit anterior, sem o código
  referido no relatório; não foi inventada uma implementação substituta.

## Implementado

- Fluxogramas com 12 tipos de unidade, incluindo fontes de material e energia,
  mistura, divisão, tanque, CSTR simples, bomba, válvula e trocadores limitados.
- Validação de portas, conservação, regime permanente e simulação dinâmica.
- RK4, RK45, DOP853, BDF e Radau, com erros numéricos explícitos.
- PID com anti-windup; NMPC experimental com entradas e taxas limitadas.
- EKF, UKF e MHE de janela curta; ruído, viés, deriva, atraso, perdas e laboratório esparso.
- Cinco cenários executáveis, incluindo adaptadores diretos dos modelos PG e EB.
- Editor com inspeção, drag-and-drop, undo/redo, salvar, reabrir e exportar.
- Persistência atômica, backup anterior, CSV/JSON, semente e manifesto de execução.
- Replay das mudanças de referência, observabilidade local e benchmark por CLI.
- Shell desktop pywebview, dependências fixadas, NSIS e workflow Windows com testes
  do executável congelado, instalação e renderização nativa aprovados na CI.

## Verificado

| Conjunto | Resultado local |
|---|---|
| Núcleo TypeScript original | 11/11 testes passaram |
| Campanha científica PG/EB preservada | 15/15 testes passaram |
| ProcessLab Studio | 26/26 testes passaram |
| AIRE recuperado: estimação e observabilidade | 18/18 testes passaram |
| Interface no Chromium/Linux | 12 verificações passaram; zero erros JavaScript |
| Benchmark funcional | 23 trajetórias concluídas, sem falhas numéricas |
| Build TypeScript/Vite | Concluído |
| Smoke do programa por CLI | Concluído em Linux, sem congelamento |
| Testes no Windows Server 2022 | 26/26 Studio e 11/11 TypeScript passaram |
| Executável Windows empacotado | Cinco cenários salvaram, reabriram e simularam |
| Compilação/instalação Windows | Instalador gerado e instalação por usuário aprovada |
| Interface nativa instalada | Renderização e inicialização da ponte Python aprovadas |

Os testes novos incluem uma solução analítica do tanque, fechamento de balanços,
conversão dimensional, paridade PG com equações imperiais independentes, manutenção
da ambiguidade térmica, replay de observações atrasadas, controle limitado, gravação
atômica, proteção da API local e repetição de mudanças de referência.

No benchmark do tanque, o IAE médio foi aproximadamente 7131,06 K·s em malha aberta
e 763,02 K·s com PID, em cinco sementes pareadas. Isso mostra que o controle implementado
atua nesse cenário; não é uma demonstração de superioridade científica geral.
Os ensaios EKF/UKF do PG e EB usaram três sementes por modelo/método. O ensaio NMPC
foi funcional, com uma semente, e não autoriza ranking estatístico.
Tempos medidos pertencem ao host Linux compartilhado, não ao i5-7200U do usuário.

## Pendências reais

1. Verificar no Windows 10 e no notebook do usuário a instalação, WebView2, partida,
   consumo de memória e experiência de edição.
2. AIRE permanece em auditoria e RSI sem código recuperado na branch indicada.
3. Sem colunas de destilação, equilíbrio de fases, reciclos, DAE geral, importação FMU,
   controle robusto/econômico/cascata ou integração com hardware.
4. A termodinâmica EB e a planta Aspen completa continuam não reconciliadas.
5. Sem autosave em segundo plano, editor geral de matrizes Q/R, ou garantias estatísticas
   para a covariância. O MHE é determinístico e usa covariância auxiliar EKF.

## Como continuar

Branch publicada: `work/ycs-processlab-studio-20261013`.
Base: `88c40e65204fa6aa5bed02cc64fb15be79a53bb1`.
O checkpoint anterior preserva o trabalho anterior à autorização de publicação.
A entrega atual inclui o instalador verificado; os registros Windows estão em
`studio/evidence/windows-ci/` e identificam o commit efetivamente compilado.

Leia `QUICKSTART_PT.md`, `ARCHITECTURE.md`, `RECOVERY.md` e `CAPABILITIES.md`.
As alterações posteriores à compilação atualizam somente documentação e evidências.
