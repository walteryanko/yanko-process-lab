# YCS Darwin-Observer Laboratory v1.0

Laboratório científico local de descoberta restrita de erros de modelo em um CSTR de propilenoglicol. Dados e resultados são sintéticos, calculados por execução real. Python 3.11+, CPU, sem GPU ou APIs pagas.

## Abrir agora

Abra `Laboratorio_Darwin_Observer.html` com duplo clique para explorar os resultados, alternar cenários e observadores, percorrer a linha do tempo e exportar equações. Essa versão não executa novos experimentos Python; o botão informa isso.

## Aplicativo completo no Windows 10/11

1. Instale Python 3.11 ou superior, incluindo o Python Launcher (`py`).
2. Extraia TODO o ZIP em uma pasta, por exemplo `C:\YCS\DarwinObserver`. Não execute dentro do ZIP.
3. Abra `INICIAR_LAB.bat`. Na primeira vez, a configuração baixa dependências para `.venv`.
4. O navegador abre `http://127.0.0.1:8765`. Mantenha a janela do terminal aberta enquanto usa o laboratório.
5. Escolha um cenário e execute um episódio com outra seed. A opção de diagnóstico cego só permite aplicar uma correção após a validação temporal.

A primeira compilação de kernels pode levar dezenas de segundos. Depois da instalação, a operação principal funciona offline. Se a configuração automática falhar, abra PowerShell na pasta e execute `powershell -NoProfile -ExecutionPolicy Bypass -File .\CONFIGURAR_WINDOWS.ps1`. Essa configuração vale apenas para o processo do script, não altera a política permanente do computador.

Os scripts Windows foram preparados e inspecionados; a validação executada nesta entrega foi Linux/Python 3.12, não um teste em Windows real. Não é um instalador `.exe`.

## Instalação manual / Linux

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m darwin.dashboard --open
```

## O que foi observado

- A_rich: redução de aproximadamente 28,7% do RMSE de CC versus UKF nominal, em 100 episódios independentes; forma de UA próxima à potência escondida.
- NMPC: redução de aproximadamente 73,3% do IAE quando a correção também entra na previsão; melhorar somente a estimação não trouxe o mesmo benefício.
- Excitação fraca: ganho químico não demonstrado. Transferência direta para a variante histórica piorou o erro.
- Cinética fora da biblioteca: uma correção preditiva foi confundida com erro de alimentação. O sistema não identificou corretamente essa causa.
- Diagnóstico cego: 555 acertos, 45 abstenções e nenhuma falsa equação física nos 500 episódios sem alteração física. Isso é evidência deste gerador, não garantia universal.

Consulte o PDF e os cinco relatórios Markdown para intervalos de confiança, comparadores fortes, cobertura e limitações.

## Reproduzir

```bash
python -m pytest -q
python -m darwin.experiments --stage all --n 100 --workers 4
python -m darwin.ablations
python -m darwin.reporting
```

Também existe `REPRODUZIR.bat`. Por padrão, as novas execuções substituem `artifacts/main`; para preservar a campanha entregue, use `--out artifacts/minha_campanha` no runner. `--stage fit`, `test`, `blind` e `control` permitem etapas separadas. O comando de relatório usa a pasta `artifacts/main`.

O perfil completo grava centenas de megabytes de trajetórias e covariâncias. Há 18 × 100 episódios principais, 600 diagnósticos cegos, quatro malhas de controle × 100 sementes, 3.300 avaliações de ablação e 40 desafios. O tempo depende da CPU, da compilação inicial e do disco. Reduzir `--n` serve para desenvolvimento; não reproduz os intervalos publicados de n=100. Os modelos de `fit` usam 12 episódios de treino e oito de validação, separados do teste.

## Organização

- `darwin/physics.py`: seis estados, balanços, constantes e variantes completas.
- `darwin/data.py`: interface operacional sem estados verdadeiros.
- `darwin/truth.py`: plantas virtuais; módulo exclusivo do gerador/evaluador.
- `darwin/observers.py`: UKF, EKF e UKF conjunto de parâmetros.
- `darwin/detection.py`: inovações, persistência, autocorrelação e NIS.
- `darwin/identification.py`, `symbolic.py`, `discovery.py`: hipóteses, ajuste, ranking, registro e reversão.
- `darwin/residual.py`: RBF e rede neural pequena, treinadas com o balanço térmico observável.
- `darwin/blind.py`: classificação cega com divisão temporal e atuação posterior.
- `darwin/control.py`: NMPC inferencial e proteção.
- `dashboard/` e `darwin/dashboard.py`: seis painéis reais, backend local e exportações.
- `artifacts/main/models/`: parâmetros e pesos treinados em JSON, sem desserialização pickle.
- `artifacts/main/discoveries/`: todos os candidatos aprovados/rejeitados, evidências e eventos.
- `artifacts/main/datasets/`: NPZ com entradas, medições, verdade de avaliação, estimativas e covariâncias.
- `artifacts/main/*.csv`: resultados por seed; JSON com estatísticas e decisões.
- `reports/`: cinco relatórios científicos e gráficos exportáveis.
- `vendor/`: fontes recuperadas para equivalência e proveniência.
- `tests/`: testes científicos, negativos, de causalidade, controle e API.

## Interface com ProcessLab

```python
from darwin.physics import Model
from darwin.observers import OnlineUKF
observer = OnlineUKF(Model())
# u = [FA, FB, FM, mw, Tfeed, Tcool]; y = [T, Tt]
xhat, diagnostics = observer.update(u, y, dt=0.015)
```

Use `Model.from_dict(...)` para uma correção salva. Para comissionamento e reversão auditados, use `GuardedDarwin` com um registro retornado por `discover(train_records, validation_records)`. Não passe objetos `Episode` ou dados de verdade ao estimador. O histórico químico sintético é usado só para avaliação.

## Limites deliberados

Esta versão usa gramática restrita, STLSQ e SymPy; não executa PySR/Julia nem MHE. Não garante identificabilidade de todos os estados nem unicidade de mecanismos. A cobertura de incerteza é inadequada em alguns regimes. O NMPC é uma portabilidade do controlador público com busca por coordenadas, não reprodução exata de MATLAB/SQP. Não há validação industrial ou autorização de uso em equipamento real.

Todos os resultados são rastreáveis ao protocolo, às seeds e aos arquivos brutos. `scripts/verify_manifest.py` verifica os hashes do pacote. Reproduções podem diferir ligeiramente com BLAS, compilador, versão de Python e sistema operacional; as bibliotecas numéricas principais estão fixadas em `requirements.txt`.
