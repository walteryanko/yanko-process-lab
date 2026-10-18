# Proveniência e decisão de modelo

Fonte principal: https://github.com/walteryanko/yanko-process-lab . O laboratório foi desenvolvido em diretório independente `research/premonition` e branch `research/premonition-mpc-v1-20261018`, sem alterar branches estáveis.

| Fonte recuperada | Versão / identidade | Uso |
|---|---|---|
| ProcessLab main | f4444d4c238291b8633743930249ee387ad94541 | Controlador, variante tabelada, identidade visual científica. |
| Darwin / dissertação | b55a46cd182c70100b50ff5e6c98ba82ed96a5a8 | Modelo MATLAB original, NMPC e parâmetros do filtro. |
| Beyond / referência | 88c40e65204fa6aa5bed02cc64fb15be79a53bb1 | Implementação independente `pg_reference.py` e conferência SI. |
| Schrödinger | 7ff42ff2b894085002c5b9c214f19e7e681aebc3 | Auditoria de estimador; não usado como baseline primário. |
| NAKE | f9ad5c7743094681eb66a78b47936eae0cf5cb48 | Variante calibrada; mantida separada. |
| Dissertação UFCG 2019 | Walter Yanko de Aragão Brandão, PDF recuperado | Equações 33–55; limitações operacionais; referências de implementação. PDF não redistribuído. |
| Oracle-KF v0.1 | Checkpoint fonte recuperado | Auditada família tabelada; pesos não transferidos. |
| Quantum-MPC v0.2 e Multiverse-MPC v0.1 | Checkpoints fonte recuperados | Auditoria de identidade de modelo; não misturados ao primário. |

Os hashes dos arquivos-fonte arquivados estão em `results/physical_audit.json`. `vendor/` conserva o conteúdo de referência e os avisos existentes. Os arquivos `.m` e `.ts` são evidência e não são executados em produção pelo laboratório Python.

O UKF usa parâmetros históricos convertidos; inicialização de estado/covariância, integração da planta e salvaguardas numéricas são declaradas nos relatórios. O NMPC é um porte CPU da busca coordenada pública com modelo histórico e guard comum, sem alegação de equivalência ao solver original fmincon.

O piloto e a avaliação exploratória precederam o congelamento final. Para evitar reutilizar trajetórias inspecionadas, o teste final C/D foi refeito com sementes inéditas. `holdout_freeze.json` registra os hashes dos modelos e limiares anteriores a esse teste. As alterações posteriores foram diagnósticos, documentação, apresentação, validação de checkpoints e nomenclatura estatística; não houve novo ajuste do controlador ou dos detectores ao teste final.

A referência de projeto é outubro de 2026. Timestamps de arquivo são de execução do ambiente, não de um experimento industrial. Toda visualização de intervenção, evento ou contrafactual provém da planta virtual.
