# Manual Windows 10/11 x64

## Explorar os resultados sem instalação

Extraia o ZIP completamente, por exemplo em `C:\YCS\Premonition`. Clique em `ABRIR_RESULTADOS.bat` ou abra `PREMONITION_LAB.html` no Edge, Chrome ou Firefox. O arquivo incorpora dados e gráficos, funciona sem internet e não precisa de Python. A animação reproduz dados calculados; não substitui o motor de simulação.

Use a seleção de semente e controlador no Reactor Digital Twin. O Bifurcation Explorer permite percorrer os ramos e calcular novos equilíbrios estacionários, em JavaScript, com os mesmos parâmetros. A API Python foi usada para verificar esse cálculo. O painel Failure Explorer inclui eventos perdidos e falsos alertas. O Scientific Benchmark exporta CSV e JSON.

## Instalar o motor científico

Instale uma distribuição oficial Python 3.11 ou superior, 64 bits, incluindo Python Launcher. Execute `CONFIGURAR_WINDOWS.bat`; ele cria `.venv` local e instala `requirements.txt`. A primeira instalação requer internet. Para um computador isolado, prepare previamente um diretório de wheels compatíveis com a versão do Python e Windows x64 e instale com `python -m pip install --no-index --find-links wheels -r requirements.txt` dentro da venv.

Abra `INICIAR_LAB.bat` e mantenha o terminal aberto. O endereço é `http://127.0.0.1:8765`. Uma nova simulação executa 120 intervalos de 54 s, usando a semente e o controlador selecionados. O primeiro cálculo pode demorar pela compilação Numba. As simulações interativas ficam na sessão da página; use as campanhas em linha de comando para registros persistentes.

Para encerrar, pressione Ctrl+C no terminal. Se a porta estiver ocupada: `.venv\Scripts\python.exe -m premonition serve --port 8767`. Não é necessário expor portas à rede. O servidor aceita somente conexões locais e roda uma simulação por vez.

## Reproduzir e retomar

`TESTAR.bat` executa os testes científicos. `REPRODUZIR.bat` recalcula todas as campanhas, estatísticas, gráficos, relatórios e dashboard. Dados novos ficam em `results_reproduced`, e relatórios em `reports_results_reproduced`. O HTML principal é recomposto com esses dados; o pacote original deve ser mantido como referência.

As oito políticas são comparadas com 100 sementes comuns. A campanha de controle salva um checkpoint JSON ao concluir cada episódio. Reexecutar EF na mesma pasta retoma episódios compatíveis, conferindo a identidade do modelo, políticas, cenários e classificadores. Para modificar esses componentes, use uma nova pasta de resultados. A/B/CD são recalculadas quando invocadas; não há retomada parcial dessas campanhas nesta versão.

O protocolo e os parâmetros de implementação estão versionados. Alterar `configs/protocol.json` isoladamente não altera os algoritmos: é um registro do experimento. As constantes efetivas estão em `physics.py`, `control.py`, `scenarios.py` e nos módulos de campanha; qualquer alteração deve ter novo protocolo e nova pasta.

## Recursos e tempos

CPU-first, sem CUDA. Use Python x64; a máquina-alvo é 16 GB RAM. Os resultados não exigem serviço pago. A geração dos dados incorporados no HTML pode usar mais memória que uma simulação individual; feche abas desnecessárias. A versão foi exercitada em Linux e preparada para caminhos Windows, sem teste nativo de Windows nem medição de pico de RAM na máquina-alvo.

Na execução de referência, E/F levou cerca de 581 s para 800 episódios. As médias por decisão ficaram na ordem de milissegundos depois da compilação, no processador deste ambiente; esses tempos não são garantia para outro computador. Uma reprodução completa inclui treinamento, B e relatórios, portanto leva mais tempo. Logs JSON mostram o avanço das campanhas.

O arquivo `requirements_reference.txt` registra versões do ambiente de referência. `requirements.txt` aceita versões compatíveis para instalação. Pequenas diferenças numéricas e de desempenho entre BLAS, versões e sistemas são possíveis; modelos treinados e resultados originais estão incluídos.

## Problemas frequentes

| Sintoma | Procedimento |
|---|---|
| `py` não encontrado | Instale o Python Launcher ou crie a venv manualmente usando o caminho do Python. |
| Pasta protegida ou acesso negado | Extraia em uma pasta do usuário; evite executar dentro do ZIP. |
| Botão de simular pede motor | Abra `INICIAR_LAB.bat` e use o endereço HTTP local, não o HTML por `file://`. |
| Primeira simulação lenta | Aguarde a compilação Numba; o terminal mostra erros se ocorrerem. |
| Mudança de código invalida checkpoint | Use outra pasta `--out`; não misture resultados de algoritmos diferentes. |
| Modelo ou campanha ausente | Execute as dependências na ordem audit → A → B → CD → EF → reports → dashboard. |
| Resfriamento máximo não evita evento | É um resultado possível da planta simulada; verifique `feasible`, saturação e `fallback`. |

## Validação adicional do navegador

O teste opcional `scripts/browser_smoke.cjs` usa Node e Playwright, sem ser dependência da aplicação. Instale Playwright em um ambiente de desenvolvimento e disponibilize Chromium. Execute `node scripts/browser_smoke.cjs`. `BROWSER_EXECUTABLE` pode indicar um Chromium instalado e `PYTHON` o Python da venv. A execução verifica os sete painéis, três equilíbrios, consistência Python/JavaScript, uma simulação, exportação, acesso offline e largura móvel.
