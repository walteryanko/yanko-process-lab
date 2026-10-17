# Changelog

## 1.0.0 - 2026-10-17

- Recuperação do ProcessLab f4444d4, Oracle-KF v0.1, modelo MATLAB e transformação SI histórica completa.
- Núcleo físico com teste de equivalência, UKF/EKF, parâmetros conjuntos, diagnóstico e proposta esparsa restrita.
- Seleção independente, nulidade, casos ambíguos e reversão auditável.
- Campanhas A-E, transferência, diagnóstico cego, ablações e desafios exploratórios.
- NMPC de horizonte 57 e seis movimentos, integrado ao modelo corrigido.
- Laboratório local de seis painéis, exportação de equações e explorer offline.
- Cinco relatórios científicos, PDF consolidado, modelos e datasets reproduzíveis.
- Fechamento: leitura transparente de evidências gzip no GitHub; 27 testes automatizados e 13 verificações reais de navegador.
- Proteção do NMPC verifica todos os movimentos e temperaturas previstos contra o domínio da equação aprovada.

Piloto: previsão inicial por estado nominal aberto mostrou sensibilidade à condição inicial. Antes da campanha final, passou a usar um prefixo causal UKF de 20 amostras. O erro de compilação np.r_ no controlador foi corrigido antes da execução de controle. Resultados-piloto não integram as estatísticas finais.
