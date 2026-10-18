# Registro de validação v1.0

44 testes científicos passaram no ambiente de referência. O aviso Numba sobre contiguidade de arrays é de desempenho, não de resultado ou falha. A verificação Chromium confirmou os sete módulos, dados nos gráficos, exportação de 800 registros, três equilíbrios, nova simulação pelo Python, funcionamento offline e ausência de transbordamento horizontal na largura móvel.

| Requisito | Evidência principal |
|---|---|
| 1. Equações físicas | Comparação aleatória com referência independente; invariantes materiais; assimetria térmica. |
| 2. Equilíbrio | Resíduo dos seis balanços e raízes calculadas. |
| 3. Integração | RK4 comparado a DOP853 em três vazões. |
| 4. Jacobiano | Forma analítica comparada a diferenças centrais. |
| 5. Autovalores | Espectro completo versus forma reduzida, incluindo modo passivo. |
| 6. Múltiplos equilíbrios | Três raízes a T0=295 K; estável / instável / estável. |
| 7. Continuação | Travessia da dobra x²−μ=0, resíduos e rejeição de condição inicial inválida. |
| 8. Bifurcações conhecidas | Dobra e par de Hopf em formas normais; refinamento não degenerado da dobra PG. |
| 9. EWS | Remoção de tendência, AR(1), insuficiência de dados e prefixo causal. |
| 10. Falsos alarmes | Histórico quieto, início antecipado fora do horizonte, censura e campanhas negativas. |
| 11. Causalidade | Invariância a futuro alterado e nenhum crédito pós-evento. |
| 12. Estados ocultos | Contrato `Observation` inspecionado; Oracle exige futuro explícito. |
| 13. Ruído | Ruído colorido aumenta autocorrelação sem mudar a estabilidade; campanha adversarial. |
| 14. Restrições | Guard rejeita ação inválida; limites de vazão em decisões nominais. |
| 15. Fallback | Previsão irrecuperável, saturação e detector deliberadamente inválido. |
| 16. Reprodutibilidade | Sementes determinísticas; checkpoint rejeita identidade alterada. |
| 17. Separação de dados | Faixas disjuntas; hashes de congelamento antes do teste final. |
| 18. Dashboard | `scripts/browser_smoke.cjs`, resultados em `browser_verification.json`. |
| 19. Exportação | JSON estrito sem NaN; CSV do navegador com 800 registros. |
| 20. Falha do detector | Abstenção com escore inválido e guard independente; `EF/dead_detector.json`. |

A concordância máxima entre as três temperaturas de equilíbrio de JavaScript e Python foi 1,44×10⁻¹⁰ K no caso de verificação. Esse teste cobre consistência de implementação, não validação experimental do modelo físico.

Os testes de formas normais verificam a rotina básica de continuação e sinalização espectral. A classificação de Hopf do PG exigiria confirmação local adicional; nenhum foi confirmado nesta versão. A observabilidade local, as bacias amostradas e os guardas são limitados ao modelo e aos domínios declarados.

Os modelos e controladores finais não foram ajustados após observar as sementes finais. Alterações de apresentação, nomenclatura estatística, retomada por identidade e relatórios foram realizadas depois, sem alteração das trajetórias científicas. O teste de navegador usa semente 700001 fora das campanhas principais.

Windows nativo, comunicação industrial, solver global e garantias formais de segurança não foram verificados. O laboratório permanece exclusivamente computacional.
