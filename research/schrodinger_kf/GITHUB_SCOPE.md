# Escopo desta branch

Esta branch contém o código completo, testes, auditorias, relatório, resultados
por trajetória CSV/JSONL, benchmarks e o laboratório visual com oito cenários.
Para evitar duplicar arquivos grandes no repositório, os NPZ de plantas e
traços, matrizes completas e JSON de demonstração ficam no ZIP completo
YCS_SchrodingerKF_Lab_v1.0.zip entregue com o relatório. Nenhum resultado foi
substituído por dados fictícios. web/data.js é um export visual dos dados reais.

Os testes Python e o motor de novas simulações funcionam diretamente nesta
branch. A reprodução cria evidências novas em reproductions/. Para conferir
o pacote original com audit_results.py e regenerar o relatório original,
use os dados completos do ZIP. PACKAGE_MANIFEST.json, no ZIP, contém hashes.

A comparação primária usa 100 sementes por cenário. M4 apresentou RMSE de CC
22,3% maior no cenário gaussiano e 18,2% maior no ambíguo que o UKF. M5 não
ativa a ponte, pois a ablação não justificou o gatilho. Consulte os relatórios
para intervalos, condições e limitações.
