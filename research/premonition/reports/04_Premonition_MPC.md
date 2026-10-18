# 4. Premonition-MPC e controle

Arquitetura operacional: pacote causal → detector → supervisor com confirmação por dois passos → NMPC → guard físico independente → fallback. O avaliador mantém estados verdadeiros, parâmetros ocultos e perturbações futuros fora desse contrato. A referência oracle_offline é a única exceção deliberada e identificada.

J0=Σ(k=1..57)0,8[(CC_sp−CC_hat_k)/CC_sp]² + Σ(k=1..6)0,2[(mw_k−mw_(k−1))/mw0]². Todos os controladores usam 22,7≤mw≤1366,2 kmol/h, o mesmo integrador e a mesma busca coordenada determinística. A soma de violações previstas acima de 344 K tem prioridade lexicográfica sobre o custo.

R_T=0,02 Σ[max(0,T_hat_k−(344−m))]². C1 usa m=2 K; C3/C4 usam m=1+2I_supervisor K; o conservador fixo usa m=4 K. R_α=0,02 Σ[max(0,α_reativo+1)]² somente onde ||f/S||²<1. C2 adiciona R_α; C4 adiciona R_T+R_α+10⁻⁴Σ(mw/umax)⁴[1+min(σT,3)]. As constantes são escolhas do protocolo, não leis universais nem margens formais de robustez.

C3 usa D4; C4 usa D5. A ablação C4_noEWS usa a mesma arquitetura probabilística sem atributos EWS. O supervisor também reage a previsão física próxima do limite. D5 foi calibrado sob a distribuição de detecção, não sob todas as políticas em malha fechada. Essa mudança de distribuição é uma limitação central.

O guard verifica a sequência inteira. Se a política modificada falha e a nominal é viável, a nominal é usada. Se não há sequência aceita, aplica-se resfriamento máximo e a inviabilidade permanece registrada. Não há garantia formal de recuperação; a vazão real pode ser limitada por saturação da planta virtual. Falha do detector não desabilita essas verificações.

Experimentos E/F: 100 sementes independentes; 800 execuções, cada uma com 120 decisões (1,8 h). Todas as políticas compartilham estado inicial, ruído, parâmetros e distúrbios por semente. Há mudanças de setpoint, perda de UA, perturbações de alimentação, saturação, deriva, ruído colorido e oscilação.

| Controle | Pares | Eventos térmicos | IAE médio | Violação K·h | Produção kmol | Proxy econômico |
| --- | --- | --- | --- | --- | --- | --- |
| C0 | 100 | 40 | 0.185898 | 0.847992 | 53.7685 | 53.3274 |
| C1 | 100 | 40 | 0.186512 | 0.844339 | 53.76 | 53.3183 |
| C2 | 100 | 40 | 0.1859 | 0.847992 | 53.7684 | 53.3273 |
| C3 | 100 | 40 | 0.1866 | 0.837771 | 53.7572 | 53.3151 |
| C4 | 100 | 40 | 0.186749 | 0.83761 | 53.7553 | 53.3132 |
| conservative | 100 | 40 | 0.187223 | 0.823666 | 53.7454 | 53.3021 |
| oracle_offline | 100 | 48 | 0.425149 | 0.82161 | 49.1942 | 48.5645 |
| C4_noEWS | 100 | 40 | 0.186839 | 0.83761 | 53.7542 | 53.312 |

IAE=Σ|CC−CC_sp|Δt; RMSE químico usa estado verdadeiro e estimativa causal no mesmo instante. Produção=Σv CC Δt; esforço=Σ(Δmw/mw0)². O proxy econômico é produção−0,0005×refrigerante, em kmol-equivalentes arbitrários. Não é lucro nem resultado monetário.

O gráfico de efeitos pareados apresenta somente políticas operacionais para preservar a resolução da escala; a referência offline permanece nas tabelas e na arena. A referência offline recebe estado verdadeiro, parâmetros, perturbações e capacidade futura do atuador. Ainda usa um horizonte finito e um otimizador local com orçamento fixo. Portanto, não é limite superior de desempenho nem solução ótima de controle com futuro perfeito. Uma decisão excessivamente conservadora pode conduzir a outro ramo de equilíbrio e prejudicar a produção.

Tempo do núcleo de controle (supervisor, NMPC e guard) medido por perf_counter; a métrica mean_ms exclui a atualização do UKF e dos atributos do detector. A duração total de E/F foi 581.332 s. Medidas no ambiente Linux de execução; não é benchmark do notebook do usuário. A primeira compilação JIT pode contaminar a primeira medida. Falhas numéricas e passos inviáveis são contados separadamente; ausência de falha numérica não implica estacionariedade ou otimalidade da solução.

![06_controller_arena](figures/06_controller_arena.png)

![07_paired_effects](figures/07_paired_effects.png)
