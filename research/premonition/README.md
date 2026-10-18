# YCS Premonition-MPC Laboratory v1.0

Laboratório científico de simulação do CSTR de propilenoglicol, com modelo histórico auditado, continuação numérica, UKF, detectores D0–D5 e oito políticas de controle. Projeto Yanko Creative Studio / YCS ProcessLab. Referência: outubro de 2026.

## Abrir e executar

1. Extraia o ZIP em uma pasta gravável. Abra `PREMONITION_LAB.html` ou `ABRIR_RESULTADOS.bat` para explorar os resultados sem instalar nada e sem internet.
2. Para calcular novas simulações, instale Python 3.11+ x64 com o Python Launcher e execute `CONFIGURAR_WINDOWS.bat` uma vez. Essa instalação baixa as bibliotecas gratuitas.
3. Abra `INICIAR_LAB.bat`. O motor Python funciona em `http://127.0.0.1:8765`; o botão **Calcular com Python** executa uma nova simulação real do NMPC. Depois da instalação, nenhum serviço externo é necessário.
4. Execute `TESTAR.bat` para a verificação automatizada. `REPRODUZIR.bat` recalcula as campanhas em `results_reproduced`, preservando os dados entregues.

O HTML contém os resultados científicos incorporados. Inclui os sete painéis pedidos, exportação JSON/CSV, 200 trajetórias de detecção e 96 trajetórias de controle representativas, selecionadas pelas primeiras 12 sementes antes da inspeção visual. As 800 trajetórias completas de controle estão em `results/EF/episodes`; todas as métricas são usadas no benchmark.

## O que foi encontrado

| Questão | Resultado desta execução |
|---|---|
| Existem bifurcações no PG histórico? | Sim: dobras refinadas e múltiplos equilíbrios. Nenhum Hopf confirmado na triagem. |
| O nominal é instável? | Não: T=332,333618 K e abscissa espectral −5,383269 h⁻¹. |
| A perda do equilíbrio é igual ao evento térmico? | Não: 50 perdas do equilíbrio frio e 50 mudanças de ramo em B, sem ultrapassar 344 K. |
| O detector espectral antecipa essas perdas? | 50/50, antecedência mediana 37,35 min, sob modelo e entrada corrente conhecidos. |
| EWS isolado antecipa as mesmas perdas? | 0/50 nesse protocolo. |
| D5 antecipa eventos térmicos inéditos? | 50/51; mediana 7,2 min; 1 falso início em 114,69 h de exposição válida. |
| EWS acrescentou informação convincente? | Não demonstrado: a ablação sem EWS antecipou 51/51; os IC pareados de Brier incluem zero. |
| Robustez ao ruído adversarial | D5: 18 falsos inícios; sem EWS: 5, nas mesmas 100 trajetórias. |
| C4 evita mais eventos que C0? | Não nessa campanha: ambos 40/100; nenhum par mudou o desfecho binário. |
| Há algum efeito de controle? | C4 reduz a violação média em 0,01038 K·h e aumenta IAE e consumo de refrigerante. |

As estatísticas e intervalos completos estão nos seis relatórios em `reports/` e no PDF agregado. Um intervalo bootstrap nulo com zero pares discordantes não prova equivalência. O resultado mais forte é a separação verificável entre bifurcação, ultrapassagem térmica e capacidade de recuperação.

## Modelo e causalidade

O primário é `original_MATLAB_SI`, transformação fiel de `modeloCT.m`, e não a variante tabelada nem a calibrada. Preserva o calor 83.736 kJ/kmol, R=8,3191716 kJ/(kmol K), o deslocamento Arrhenius de 0,183333333 K e a assimetria em que Tt não realimenta o calor transferido. Fontes, unidades, equações e hashes: `results/physical_audit.json`, `vendor/` e Relatório 1.

O contrato operacional `Observation` aceita somente T/Tt, entradas correntes, estado/covariância do observador e resíduos. Os estados verdadeiros e parâmetros ocultos ficam na planta/evaluador. `oracle_offline` recebe o futuro deliberadamente e nunca é apresentado como política operacional ou ótimo global. Os alvos probabilísticos térmico e de bifurcação são treinados separadamente.

C0 é o porte da busca coordenada pública do ProcessLab, com P=57, M=6, Qe=0,8, RΔu=0,2, usando o primário histórico e um guard comum. Não é uma reprodução binária de MATLAB/fmincon. UKF histórico é o baseline, com Euler e Q/R convertidos; RK4, EKF e UKF adaptativo são ablações.

## Campanhas e arquivos

| Módulo | Entradas e saídas principais |
|---|---|
| A — mapa | Oito eixos de continuação, 400 combinações exploratórias, equilíbrios, autovalores, pontos críticos, seção da bacia e validação temporal. |
| B — desaceleração | 80 treino / 40 calibração / 100 teste; 84 sensibilidades; retorno perturbado e alvo de perda do equilíbrio. |
| C/D — sensores e falsos alertas | 160 treino / 80 calibração / 100 teste / 100 adversariais; modelos JSON, calibração, PR, ablações de estimador e arquivos NPZ. |
| E/F — controle pareado | 100 sementes × 8 políticas × 120 decisões; episódios JSON, métricas CSV, IC pareados e falha deliberada do detector. |
| Interface | `web/template.html`, `premonition/dashboard.py`, `premonition/server.py`. |
| Ciência | `premonition/physics.py`, `continuation.py`, `stability.py`, `observer.py`, `ews.py`, `detectors.py`, `control.py`. |
| Protocolos | `configs/protocol.json`, `results/CAUSALITY_CONTRACT.json`, `results/CD/holdout_freeze.json`. |
| Verificação | `tests/test_science.py`, `scripts/browser_smoke.cjs`, `results/tests.xml`, `results/browser_verification.json`. |

As sementes finais de C/D são 300000–300099 e 400000–400099, distintas do piloto e da avaliação exploratória. Os modelos e limiares foram congelados antes desse teste. Os resumos exploratórios permanecem em `results/development_CD` apenas para rastreabilidade. Nenhum resultado exploratório é usado nas tabelas finais.

## Linha de comando

```text
python -m pip install -r requirements.txt
python -m pytest -q
python -m premonition audit --out results_new
python -m premonition A --out results_new
python -m premonition B --out results_new --n 100
python -m premonition CD --out results_new
python -m premonition EF --out results_new --n 100
python -m premonition reports --out results_new --report-out reports_new
python -m premonition dashboard --out results_new
python -m premonition serve
```

`python -m premonition all --out results_reproduced --n 100` executa a sequência. B requer o mapa A; EF requer modelos CD; os relatórios requerem todas as campanhas. O comando dashboard recompõe o HTML a partir da pasta escolhida. O servidor de novas simulações usa os modelos entregues em `results/CD`; alterações de pesquisa devem usar modelos e limiares da mesma campanha.

## Limites da entrega

As campanhas são sintéticas e delimitadas. O modelo líquido extrapolado acima do domínio de fase não valida previsões físicas industriais. Nem 344 K nem 355,4 K certificam segurança. A abscissa é uma propriedade local; a probabilidade depende da distribuição simulada. O guard não consegue vencer perda de capacidade do atuador. A observabilidade local nominal tem posto 3/6 e o UKF apresenta subcobertura sob erro de modelo.

O pacote foi executado e verificado em Linux, incluindo Chromium e a API local. Os scripts e caminhos foram preparados para Windows, mas Windows nativo não foi executado. Sem GPU, hardware industrial, API paga ou dependência obrigatória de nuvem. Consulte `MANUAL_WINDOWS.md`, `PROVENANCE.md` e `THIRD_PARTY_NOTICES.md`.
