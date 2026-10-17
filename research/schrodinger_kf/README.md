# YCS Schrödinger-KF Laboratory 1.0

Laboratório local de filtragem Bayesiana clássica para o CSTR de
propilenoglicol de seis estados do Yanko ProcessLab. Código real, simulações
reproduzíveis e evidências completas. Não é um controlador industrial.

## Abrir no Windows

1. Extraia o ZIP inteiro para uma pasta, por exemplo `C:\YCS\SchrodingerKF`.
2. Para explorar os resultados entregues, abra **VER_RESULTADOS.bat**.
   Funciona offline e dispensa Python.
3. Para simular novas sementes/partículas, instale Python **3.12 ou superior**
   e execute **INICIAR_LAB.bat**. Na primeira vez, as dependências são baixadas.
   O navegador abre em `http://127.0.0.1:8765`. Depois da instalação, o motor
   funciona offline. A janela do terminal deve permanecer aberta.

O botão “Executar no motor Python” roda novamente todos os filtros para
a mesma trajetória. Se abrir o HTML diretamente, o botão fica desabilitado:
os gráficos reproduzem os dados calculados que acompanham o pacote.
O número de partículas e a semente no formulário se aplicam à **nova execução**;
a barra temporal mostra a semente e N da trajetória realmente exibida.

## Explorar

- **Digital Twin:** concentrações simuladas e estimadas, intervalos e temperaturas.
- **Probability Universe:** nuvem ponderada, marginal de CC e projeções 2D/3D.
- **Transport Explorer:** matriz M3, marginais, custo e perda de variância.
- **Filter Arena:** métodos na mesma planta e mesma realização de ruído.
- **Chemical Multiverse:** ambiguidade estrutural do CSTR e bimodalidade sintética separada.
- **Benchmarks:** resultados por cenário, IC pareados e ablação de M5.
- **Control Lab:** comparação de estimadores/controladores no ensaio simulado.

Os controles de tempo animam trajetórias registradas; eles não mudam a
simulação física. “Exportar JSON” exporta os dados do cenário exibido.
Os dados de campanha permanecem fixos quando uma nova simulação é executada.

## Reproduzir e testar

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m schrodinger_lab.server
python scripts/reproduce.py
```

No Windows, use TESTAR.bat e REPRODUZIR.bat. A reprodução cria uma nova
pasta com data/hora e preserva a evidência entregue. Pode levar dezenas de
minutos, dependendo da CPU. Usa um thread BLAS para reduzir variações de tempo.
NumPy/SciPy e CPU são suficientes; não há GPU, pesos neurais nem API paga.

Exemplo de campanha menor:

```sh
python -m schrodinger_lab.experiments --out results/meu_ensaio --trials 10 --steps 48 --particles 128 --epsilon .02 --scenarios gaussian ambiguous
```

N pode ser 64,128,256,512 ou 1024 na interface. Horizonte e N são ajustáveis
na CLI; o custo da ponte cresce aproximadamente como L·N². A campanha
principal usa N=128, 48 amostras/0,72 h e 100 sementes por cenário.

## Arquivos

- `schrodinger_lab/`: física, filtros, Sinkhorn, SDE, métricas, ensaios e servidor.
- `vendor/`: origens preservadas e fixture TypeScript para teste de paridade.
- `configs/`: protocolo congelado e seleção de desenvolvimento.
- `results/`: JSONL por trajetória, CSV, estados/medições/entradas NPZ,
  covariâncias/intervalos NPZ e exemplos completos de nuvens/transportes JSON.
- `reports/`: auditorias física/matemática, relatório experimental e gráficos.
- `web/`: aplicação local e relatório HTML.

NPZ pode ser aberto com `numpy.load`. Colunas dos datasets: `true` tem
passos+1 estados; `u`,`y`,`process` têm passos linhas. O filtro usa a
medição y[k] depois de propagar true[k] para true[k+1]. NaN em y representa
medição ausente. Os JSON da interface convertem NaN em null.

## Limitações verificáveis

A física escolhida é a variante TABLED de main, não o equilíbrio histórico
nem a variante calibrada. M0 da arena é UKF RK4 com sintonia comum; o
UKF original Euler está preservado e testado separadamente. M4 implementa
uma ponte com alvo KDE contínuo e aproximação de Euler–Maruyama, com vieses
medidos; não é reamostragem Sinkhorn. M5 só é ativado se a ablação justificar.
Não se demonstrou originalidade absoluta ou ganho universal. Consulte o
relatório para os resultados, inclusive negativos e execuções interrompidas.

O ambiente de execução desta entrega é Linux/Python 3.12. Scripts Windows
foram preparados, mas não executados em Windows nesta sessão. Não há .exe
nem instalador binário nesta entrega; a aplicação local usa Python e navegador.

## Auditoria e relatórios

`python scripts/audit_results.py` confere as chaves e os traços das 2016
avaliações entregues. O histórico de recuperação de três registros JSONL está
em `results/main/integrity/`; os CSV e traços originais estavam completos.
Para regenerar PDF, HTML e figuras dos resultados entregues, instale também
`requirements-reports.txt` e rode `python scripts/build_report.py`.
`python scripts/build_dashboard.py` recompila os dados usados pela interface.
O arquivo visual usa dez algarismos significativos para reduzir seu tamanho;
os dados científicos originais mantêm a precisão completa em `results/`.
O teste de navegador é opcional: `scripts/test_ui.cjs` requer Playwright (npm)
e Chromium local, com `PLAYWRIGHT_MODULE` e `LAB_CHROMIUM` configurados.
