# Instalador Windows verificado — ProcessLab Studio 0.1.0

Em 13 de outubro de 2026, o instalador x64 foi gerado, instalado e aberto
com sucesso na CI, em Windows Server 2022 Datacenter. O aplicativo permanece
um checkpoint científico funcional; Windows 10 e o notebook i5-7200U/8 GB
ainda precisam de validação local.

## Identificação do binário

- Arquivo: `YCS-ProcessLab-Studio-0.1.0-Setup.exe`
- Tamanho: 41.097.520 bytes (aproximadamente 39,2 MiB).
- Commit compilado: `42a85b820740774729f3c28c4e402a3ddeeea52a`.
- SHA-256: `6febf721f91419c6c2a9ac36c25dccb50de430d5505cb8cf9c2096ce2bd0acf1`.
- [CI Windows aprovada](https://github.com/walteryanko/yanko-process-lab/actions/runs/38426966563).
- [Verificação geral do repositório aprovada](https://github.com/walteryanko/yanko-process-lab/actions/runs/38426966967).
- [Código exato do binário](https://github.com/walteryanko/yanko-process-lab/tree/42a85b820740774729f3c28c4e402a3ddeeea52a).

Os commits posteriores de documentação/evidências não alteram este executável.
Os documentos incluídos no instalador refletem o checkpoint anterior à execução
da CI; este relatório registra o resultado posterior da verificação.

## Evidências

| Verificação | Resultado |
|---|---|
| Núcleo histórico TypeScript em Windows | 11 testes passaram |
| Motor Studio e persistência em Windows | 26 testes passaram |
| Interface TypeScript/Vite | Build concluído |
| Executável empacotado | Cinco cenários salvaram, reabriram e avançaram três passos |
| Cenários cobertos | Mistura/aquecimento, tanque PID, PG original, EB reduzido e tanque NMPC/UKF |
| Proveniência no executável | Commit, hash das fontes e versões das dependências presentes |
| Instalação por usuário | Setup silencioso concluiu e o executável instalado foi encontrado |
| Interface instalada | WebView2 renderizou a aplicação e a ponte Python inicializou uma simulação |
| Arquivo baixado | Hash do ZIP conferido com GitHub; hash do Setup conferido com SHA256SUMS |

Os registros originais estão em [`../evidence/windows-ci/`](../evidence/windows-ci/),
incluindo `frozen-smoke.json`, `windows-gui-smoke.json`, `windows-tests.txt`,
`casadi-runtime.json`, versões, informações do host e checksums.
O host tinha aproximadamente 16 GB de RAM: seus resultados não medem o notebook do usuário.

## Usar

Execute o Setup e abra o atalho **YCS ProcessLab Studio**. Python e as bibliotecas
numéricas já estão incluídos; Microsoft Edge WebView2 e .NET precisam estar disponíveis.
O executável não possui assinatura comercial de código. Comece por **Tanque com PID**
e clique em **Executar**. Consulte o [guia rápido](QUICKSTART_PT.md).

As correções de empacotamento trataram os caminhos dos arquivos, a inclusão explícita
do CasADi e a localização das DLLs usadas pelo carregador Windows. A partida agora
registra falhas em `%APPDATA%\YCS ProcessLab Studio\startup-error.json`.
Os modelos científicos históricos foram preservados.

O teste nativo confirma partida e execução funcional; não substitui a verificação
interativa no Windows 10, medição de memória no i5 ou validação física dos modelos.
As limitações científicas e de produto permanecem em [CAPABILITIES.md](CAPABILITIES.md).
