# PG Estimator Benchmark v0.1
Campanha exploratória pareada: UKF RK4, EKF, EKF com mistura Gaussiana e MHE.
Base preservada: b55a46cd182c70100b50ff5e6c98ba82ed96a5a8, modelo histórico SI completo da dissertação.
O modelo tabulado educacional e o experimento PG Predictor Intervention v0.7 não são intercambiáveis com esta base.

## Pergunta
A robustez das medições melhora a estimação de CC e o controle inferencial sob o mesmo NMPC?
Separar RMSE de estimação, IAE de controle e comportamento térmico.

## Métodos
- UKF_RK4: OnlineUKF e covariâncias históricas preservados.
- EKF: previsão não linear RK4 e Jacobiano exato, correção Gaussiana.
- GM_EKF: quatro componentes de ruído (dois sensores, cada um normal/contaminado), atualização Bayesiana e casamento dos dois primeiros momentos. Não é reprodução do DDR-EKF de Hu et al.
- MHE5: MAP com horizonte de cinco transições, custo de chegada obtido de EKF causal, estados e erros de processo otimizados, cinco avaliações máximas. Não se atribuem a esta implementação as garantias do artigo de Schiller e Mueller.
Nenhum observador recebe concentrações verdadeiras, ruído de entrada real ou dados futuros.

## Execução
Python 3.12, CPU. Dependências do laboratório Darwin existente.
Na raiz do repositório:
```sh
python -m pip install -r research/darwin-observer/requirements.txt
python -m unittest discover -s research/pg-estimator-benchmark -p 'test_*.py' -v
python research/pg-estimator-benchmark/benchmark.py --workers 2
```
Em Linux, o processo inicial compila funções CasADi em C com gcc. Em Windows, usa diretamente os grafos CasADi, sem exigir gcc. Não depende de APIs de IA.
Resultados, dados de cada episódio, configuração e tempos são exportados para results/.
O arquivo PROTOCOL.json é registrado antes da execução. A coluna de temperatura é avaliada na integração fina da planta.
O parâmetro térmico do NMPC é penalização suave; sua ativação não representa uma restrição rígida.

## Interpretação
A campanha usa oito sementes por célula e intervalos exploratórios pareados. Não é validação industrial nem prova geral.
Falhas, fallbacks do MHE e insucessos do NMPC são preservados. Conclusões exigem examinar essas contagens.
Tempos de GitHub Actions não são benchmark do notebook Windows.
O protocolo congela todas as escolhas antes de observar resultados de teste.
