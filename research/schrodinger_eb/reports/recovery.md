# Continuidade e integridade

A execução anterior foi interrompida antes da retenção dos artefatos e da criação da branch final. Na retomada, o diretório local estava vazio e a branch prevista não existia. Foram recuperadas fontes versionadas e Pesquisa_Etilbenzeno_2026.zip.

Todo o código e os experimentos desta entrega foram reconstruídos e reexecutados. Médias de desenvolvimento e resultados principais reproduziram os registros anteriores; esses registros não foram usados como entrada para fabricar dados. Latências foram novamente medidas. Não se afirma identidade bit a bit de todos os diagnósticos e controles reconstruídos; conclusões usam exclusivamente os arquivos entregues.

Na nova auditoria, três linhas finais do JSONL sem observações estavam ausentes, embora CSV, resumo e NPZ estivessem completos. As três execuções foram reexecutadas, exigindo igualdade exata das estimativas com os NPZ. As latências originais foram retidas do CSV. Journal anterior e registro da recuperação estão em results/no_observations/. O escritor foi reforçado com flush, fsync e contagem final.

A auditoria verifica 2.240 registros únicos, 600 datasets, 2.240 trajetórias e 134.400 médias posteriores físicas. Recalcula RMSE dos NPZ e verifica os inventários por solução analítica independente das taxas. SHA-256 dos datasets está em analysis.json. Checkpoints foram salvos durante a retomada.
