# Conteúdo desta branch de pesquisa

Esta branch contém o código científico completo, testes, fontes históricas, modelos calibrados, protocolos, relatórios Markdown e resultados tabulares compactos.

O pacote **YCS_Premonition_MPC_Lab_v1.0.zip**, entregue na conversa do ChatGPT Work, contém também todas as 800 trajetórias de controle, arquivos NPZ, gráficos PNG/PDF, relatório agregado e o laboratório HTML offline. Os arquivos volumosos gerados não foram duplicados nesta branch.

Para reconstruir todos os resultados e o HTML a partir deste checkout: execute `CONFIGURAR_WINDOWS.bat` e `REPRODUZIR.bat`, ou `python -m premonition all --out results_reproduced --n 100`. Isso preserva os resultados compactos entregues. As sementes e modelos estão identificados; veja README.md e MANUAL_WINDOWS.md.

Commit local completo usado no ZIP: `1702899e302b41e95d74078bd2041c8bf6104d7f`. A branch remota usa uma árvore reduzida de artefatos gerados, mantendo os mesmos fontes e modelos. Main foi preservada.
