# ProcessLab Studio 0.2.0 — laboratório e aprendizagem

## Entregas

- Autotuning offline de PID, horizonte/penalidade NMPC e Q/R de EKF, UKF e MHE.
- Busca conjunta, candidatos reproduzíveis, duas sementes de validação e aplicação guardada.
- Laboratório por projeto, até seis cenários, comparações, histórico e exportação JSON/CSV.
- Equipamentos com desenhos técnicos SVG, valores da simulação e animação durante execução.
- Ajuda offline por F1, busca de conceitos e três tutoriais práticos em português.

## Evidência local

35 testes Python, 11 testes TypeScript e 18 verificações do navegador aprovados.
O smoke executa os cinco cenários e os dois modos do laboratório.
`studio/evidence/laboratory-benchmark.json` registra quatro demonstrações reproduzíveis:
PID do tanque: melhoria de 14,95% no score de validação; EKF do tanque com ruído:
recomendação rejeitada; UKF do PG: recomendação rejeitada; EKF do EB reduzido:
melhoria de 3,66% no ensaio curto. Esses percentuais valem apenas para os casos
registrados e não demonstram precisão física ou superioridade universal.

## Compatibilidade

Projetos v1 anteriores continuam sendo abertos. A penalidade de movimento NMPC tem
padrão 0,05, preservando o comportamento anterior. Modelos científicos arquivados e
suas equações não foram alterados. Sem dependências adicionais de execução.

O Windows CI executa os testes, empacota o programa, roda o laboratório no executável
congelado, instala o Setup e abre a interface nativa, o laboratório e a ajuda.
A execução no runner Windows Server 2022 não substitui um teste de desempenho no
Windows 10 / i5-7200U / 8 GB. O programa segue sem assinatura comercial de código.

Instalador aprovado no Windows: consulte `WINDOWS_VALIDATION_0.2.0.md` e os registros
em `studio/evidence/windows-ci-0.2.0`. O binário corresponde ao commit `3acc74b`.
