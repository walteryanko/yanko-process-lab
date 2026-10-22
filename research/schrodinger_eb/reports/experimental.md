YCS PROCESSLAB · PESQUISA CIENTÍFICA · 22 OUT 2026

Schrödinger-KF Lab<br/>Reator de etilbenzeno

Uma distribuição mais rica produz conhecimento químico mais útil quando só a temperatura é observada?

**Resultado desta campanha: a configuração testada não demonstrou vantagem sobre o UKF.** A ponte generativa funcionou nos testes matemáticos, mas teve maior erro e menor cobertura no reator. A representação de partículas preserva possibilidades; não cria informação ausente nas medições.

| Cenário · 100 sementes | UKF: RMSE CEB | M4: RMSE CEB | Diferença |

| --- | --- | --- | --- |

| gaussian | 0.06992 | 0.08150 | 16.6% |

| weak_thermal | 0.15582 | 0.17698 | 13.6% |

RMSE em kmol/m³. A diferença positiva significa erro maior para M4. Os dois intervalos de confiança pareados de ΔRMSE excluem zero; não há alegação de dominância universal dos baselines.

| Evidência entregue | Quantidade |

| --- | --- |

| Execuções de estimação | 2.240 |

| Avaliações de desenvolvimento | 176 |

| Ensaios de controle + fallback | 40 + 3 |

| Testes automatizados aprovados | 35 |

| Datasets / trajetórias de estimação | 600 / 2.240 |

**Escopo:** primeiro reator de alquilação de benzeno com etileno; cinco estados, medição apenas de temperatura. Simulação de uma reconstrução das equações do ProcessLab. Não é operação industrial, reprodução termodinâmica de Aspen ou vantagem quântica.

O pacote inclui código, dados brutos, resultados por semente, auditorias, interface offline e servidor local para novas simulações. A entrega foi reexecutada após perda do ambiente temporário; veja reports/recovery.md.

01 · Física recuperada e auditada



Fonte congelada: commit 16aaafb63572d62e0e3341e26d8317b0651bdde0. Arquivos originais model.py, observer.py e control.py em vendor/. As auditorias históricas de 2016 e a investigação térmica recuperadas acompanham o pacote.

| Grandeza | Convenção nesta release |

| --- | --- |

| Estados | CE, CB, CEB, CDEB [kmol/m³], T [°C] |

| Medição | T; não existe T de camisa neste modelo |

| Volume / período | 200 m³ / 0,025 h = 90 s |

| Vazões nominais | 82.59918, 57.95784, 88.92402 m³/h |

| Equilíbrio | 0.035894, 4.630172, 1.969910, 0.371690, 160.876134 |

| Q efetivo nominal | 21718243.890 kcal/h = 25.241426 MW |

| Cinética | A em m³/(kmol s), multiplicador 3.600 para horas |

| Arrhenius | E=[17000,20000,15000] cal/mol; R=1,987 cal/(mol K) |

| Calores de reação | [-27150,-26950,-205,5] kcal/kmol |

Reações: E+B→EB; EB+E→DEB; DEB+B→2EB. A matriz estequiométrica tem posto 2. Inventários independentes: zA=CB+CEB+CDEB e zE=CE+CEB+2CDEB. Ambos seguem balanços lineares de alimentação/saída, independentemente das taxas.

A planta usa DOP853; os filtros usam RK4 com oito subpassos. O máximo resíduo do balanço analítico de inventário, descontado o ruído de processo registrado, foi 0.000000000000004 kmol/m³. O equilíbrio e a integração foram verificados contra o código fonte e integrador independente.

**Limitação térmica decisiva:** os coeficientes publicados coincidem com h/T°C do backup Aspen, não com Cp derivativo. Q=25,24 MW é o fechamento efetivo dessa equação; o backup registra 9,0879 MW e Luyben cerca de 10,3 MW. Esses valores não são intercambiáveis. A identidade de Hess também difere em 5,5 kcal/kmol. Nenhum desses ajustes foi silenciosamente aplicado ao baseline.

02 · Algoritmos e ponte genuína



| Método | Implementação efetiva |

| --- | --- |

| M0 | UKF α=0,35, β=2, κ=0; RK4; Joseph; paridade com original em domínio sem projeções. |

| M1 | EnKF com observações perturbadas; covariância amostral consistente. |

| M2 | Bootstrap PF com log-pesos, ESS e reamostragem sistemática. |

| M3 | Sinkhorn no domínio logarítmico; transformação baricêntrica; escala física; fallback explícito. |

| M4 | Gerador Schrödinger–Föllmer com referência browniana pontual e alvo posterior KDE. |

| M5 | Gatilho por não gaussianidade e ESS; nesta release o desenvolvimento mantém EnKF. |

M3 resolve o transporte entrópico com marginais w e 1/N. Seu custo usa escalas [0,1;1,5;0,75;0,25;15]. A análise x′j=NΣPijxi preserva a média, mas contrai dispersão. Não é uma ponte de difusão e não preserva automaticamente covariância ou modos.

M4 minimiza KL(P||Q), P0=δ0, P1=Σwi N(zi,h²I), em coordenadas da previsão. Para D=1-τ+τh² e π=softmax[logw+(v·z-τ||z||²/2)/D], o drift é:

a(v,τ) = [Σ πi zi − (1−h²)v] / D<br/>dVτ = a(Vτ,τ)dτ + dWτ; V0=0

A fórmula com h=0 coincide com o drift empírico de Bao/Sun v1; h&gt;0 fornece alvo contínuo e evita chamar um alvo discreto singular de ponte de KL finita. Usam-se h=0,1 e 64 passos Euler–Maruyama em grade quadrática. A normalização pela previsão e o KDE são extensões explícitas à formulação publicada.

**Distinção:** esta é uma ponte com marginal inicial pontual que gera a posterior. Não é a ponte física geral entre toda a prior e a posterior. Erros de Monte Carlo, suavização, discretização e domínio permanecem. A derivação completa e correspondência com as equações (3.9), (3.12), (3.13) estão em mathematics.md.

Preprint consultado: arXiv:2512.18928, v1 Bao e Sun; v4 Hui Sun, agosto de 2026. ETPF: Reich 2013; transporte entrópico: Cuturi 2013. A contribuição desta entrega é implementação auditável e evidência no processo, não originalidade absoluta.

03 · Desenho experimental e seleção



| Campanha | Seeds / métodos | Execuções |

| --- | --- | --- |

| Principal | 2000–2099; 2 condições; M0–M5 | 1200 |

| Ruído informado | 3000–3011; 6 condições; M0–M4 | 360 |

| Ruído ingênuo | mesmas seeds; 4 condições; M0–M4 | 240 |

| Física fixa / conjunta | 3500–3519; M0–M4 | 100 + 100 |

| UKF Q × 64 | 2000–2019; 2 condições | 40 |

| Sem observações | 2000–2099; 2 condições; M0 | 200 |

| Desenvolvimento | 101–108; 2 condições; 11 candidatos | 176 |

| Controle | 4000–4009; 4 braços | 40 |

Cada trajetória tem 60 amostras (1,5 h), 128 partículas nos métodos de ensemble. Prior contínua gaussiana condicionada ao domínio: desvios [0,012;0,35;0,18;0,06;1,5]; no cenário de ambiguidade [0,012;0,8;0,4;0,15;1,5]. Nenhum modo foi plantado na prior do CSTR. Ruído térmico nominal σ=1,5 °C.

As plantas, entradas e ruídos são pareados; o filtro só acessa u e y. Seeds de desenvolvimento e teste são disjuntas. Para modelos robustos, todos recebem a mesma classe de ruído, nunca sua realização verdadeira. IC95% principal: bootstrap pareado com 2.000 reamostragens, sem ajuste de multiplicidade.

| Seleção no desenvolvimento | Resultado |

| --- | --- |

| M3: ε ∈ {0,005;0,02;0,1} | ε=0,1: 5% fallback; menores ε: 75,6% e 38,8% |

| M4: 32/64/128 passos; h=0,02/0,05/0,1 | 64 passos, h=0,1: menor CRPS entre candidatos |

| M5: limiares 2 e 6 | Ganho não demonstrado; limiar infinito |

Regra M3: exigir pelo menos 90% de atualizações convergentes e então minimizar CRPS. M4: menor CRPS. Gatilho: limite superior de IC95% de ΔCRPS agrupado por seed abaixo de zero. Foram congelados antes da campanha teste.

Testes matemáticos: linear-gaussiano, função seno, observação parcial e y=x²+v bimodal. Ablações guardam sensibilidade ao número de passos, largura KDE, viés de momentos, W1 e massas dos modos.

04 · Comparação principal: resultado negativo



![primary](figures/primary.png)

| Cenário | ΔRMSE M4−UKF | IC95% pareado | Vitórias M4 |

| --- | --- | --- | --- |

| gaussian | 0.01158 | [0.00707, 0.0161] | 29/100 |

| weak_thermal | 0.02116 | [0.01107, 0.03141] | 31/100 |

M3 ficou próximo do UKF em RMSE no caso gaussiano, mas a cobertura de 90% caiu para 1,7%; sob ambiguidade, 11,2%. Isso mostra por que erro pontual não valida a representação probabilística. M4 cobriu 60,9% e 66,4%, também abaixo do nominal.

UKF e EnKF ficaram próximos; M5 reproduz EnKF porque o gatilho não foi justificado. As 1.200 execuções principais concluíram, sem excluir sementes desfavoráveis. Resultados de MAE de todos os estados, CRPS, energy, ESS e previsão em 1/3/6 passos estão nos JSONL.

05 · Ambiguidade térmica e modos posteriores



![ambiguity](figures/ambiguity.png)

Duas hipóteses admissíveis separadas inicialmente por 0.728 kmol/m³ em CEB produzem diferença térmica RMS de 0.0061 °C, muito menor que σ=1,5 °C. A KL entre suas observações térmicas nominais é 0.000675. Isso demonstra ambiguidade local, não dois modos posteriores.

![posteriors](figures/posteriors.png)

A sensibilidade térmica escalonada em 81 instantes tem posto local 4/5; o problema com cinco parâmetros adicionais tem posto 5/10 pelo limiar relativo 1e-7. Singularidades: 47.3, 2.85, 0.0663, 0.000252, 2.18e-09. São diagnósticos locais, não provas globais.

PF 4.096/8.192, mesma seed, prior contínua: picos extras do passo 24 aparecem apenas na menor suavização KDE e desaparecem nas demais. Não foi estabelecida bimodalidade persistente. Já o problema auxiliar conhecido tem dois modos e o M4 os reproduz. W1 em relação ao PF 8.192 está em analysis.json.

06 · Ruído hostil e física incerta



| Condição | UKF informado | M4 informado | M4 ingênuo |

| --- | --- | --- | --- |

| bias | 0.1033 | 0.1082 | 0.1088 |

| correlated | 0.1016 | 0.1212 | 0.1167 |

| feed_step | 0.1020 | 0.1138 | não aplicável |

| missing | 0.1026 | 0.1088 | não aplicável |

| outliers | 0.1031 | 0.1122 | 0.1330 |

| student | 0.1030 | 0.1136 | 0.1088 |

RMSE CEB, 12 sementes por condição. Em outliers, conhecer a mistura melhora M4 frente ao próprio M4 ingênuo; isso é benefício do modelo de ruído, não prova de superioridade do transporte. Student-t e estados latentes não melhoraram universalmente. Coberturas, falhas e contrastes pareados completos permanecem disponíveis.

![physics](figures/physics.png)

Incertezas são cinco log-fatores: k1, k2, k3, calor reacional e concentração efetiva de etileno na alimentação. Desvios [0,08;0,08;0,08;0,03;0,03]. Filtros fixos desconhecem a realização verdadeira; conjuntos estimam fatores estáticos. Não se inventa UA no modelo com entrada Q ideal.

A estimação conjunta melhorou RMSE de vários métodos, mas não resolve a identificabilidade. O posto local aumentado é deficiente. Estimar A e E separadamente numa faixa térmica estreita não seria sustentado por estes ensaios. A comparação fixa/conjunta também altera a representação da incerteza, não apenas o estimador.

07 · Integração experimental com NMPC



![control](figures/control.png)

| Braço | IAE médio xEB·h | Δ vs UKF | IC95% |

| --- | --- | --- | --- |

| M0_nominal | 0.007543 | 0.000000 | [0.0, 0.0] |

| M1_nominal | 0.007606 | 0.000063 | [-0.00034, 0.000497] |

| M4_nominal | 0.008088 | 0.000545 | [-0.000394, 0.001467] |

| M4_risk | 0.007919 | 0.000375 | [-0.000326, 0.001219] |

Dez seeds por braço; mesmos ruídos exógenos, plantas dependentes da política. Horizonte 20 passos, quatro movimentos, SLSQP com derivadas CasADi. Limites fE/fE0=[0,04;2], Q/Q0=[0,6;1,4], variação máxima [0,12;0,08] por amostra e T≤165 °C como limite de estudo.

M4 com cenários usa a média e partículas representativas dos quantis 10/90% de xEB e T. É uma aproximação de incerteza, não controle de risco garantido. Não houve violação térmica nem fallback nos 40 ensaios. O fallback nominal limitado foi exercitado em três ensaios forçados. Nenhum braço demonstrou melhoria clara; todos os IC95% de ΔIAE versus UKF incluem zero.

08 · Custo, domínio e verificações



![scaling](figures/scaling.png)

| N | M4 média (ms) | P99 descritivo (ms) | Pico rastreado (MiB) |

| --- | --- | --- | --- |

| 64 | 13.32 | 13.56 | 0.15 |

| 128 | 17.86 | 18.43 | 0.48 |

| 256 | 54.79 | 56.07 | 1.14 |

| 512 | 116.05 | 125.74 | 2.22 |

| 1024 | 406.05 | 437.49 | 4.35 |

Cinco atualizações após aquecimento por ponto. P95/P99 não são garantias de cauda com essa amostra. tracemalloc mede alocações rastreadas, não RSS total. O maior P99 medido foi 437.5 ms, ante 90.000 ms de amostragem EB. Os números são de Linux/Python 3.12.14; não foram validados em notebook Windows.

| Método | Rejeições inicial + dinâmica | Fallbacks | Amostras diagnósticas rejeitadas |

| --- | --- | --- | --- |

| M0 | 0 | 0 | 219 |

| M1 | 107 | 2 | 0 |

| M2 | 105 | 0 | 0 |

| M3 | 105 | 89 | 0 |

| M4 | 108 | 3 | 0 |

| M5 | 107 | 2 | 0 |

Rejeição condiciona a distribuição; fallback troca a análise inteira por PF. Nenhuma concentração negativa foi aceita silenciosamente. Intervalos UKF são analíticos; seus scores de ensemble usam amostras gaussianas condicionadas. Essa diferença é documentada.

09 · Reprodução, limites e publicação



**Verificação:** 35 testes passaram, incluindo física, equilíbrio, integração, conservação, domínio, UKF recuperado, linear-gaussiano, posterior bimodal, causalidade, Sinkhorn, momentos, reamostragem, fallback, exportação e API. Testes estocásticos usam sementes e tolerâncias explícitas; não constituem prova de convergência para qualquer distribuição.

A interface foi verificada em navegador: sete painéis, projeção 3D, CSV, tela estreita, arquivo offline e nova execução N=64/8 passos. Os gráficos usam dados reais. O botão de simulação precisa do servidor local; o HTML isolado permite apenas exploração dos dados entregues.

**Uso:** extraia o ZIP; execute INICIAR_LAB.bat no Windows com Python 3.11+ x64. VER_RESULTADOS.bat abre o HTML offline. TESTAR.bat verifica o código; REPRODUZIR.bat cria uma cópia isolada para repetir as campanhas. Fontes em eblab/, dados em results/, equações e parâmetros em configs/. O README contém comandos portáveis.

**Limites da contribuição:** modelo térmico herdado com ressalvas; 1,5 h por trajetória; N=128 na inferência principal; um único processo e ponto operacional; referência posterior numérica em uma seed; incertezas paramétricas estáticas e idealização do atuador Q. Não se validaram dados industriais, termodinâmica completa, robustez global do controlador ou ganhos em outros regimes.

Perguntas sustentáveis para pesquisa

1. Quanto da inferência de CEB vem das medições, versus dissipação de inventário e prior? A ablação sem medições tem RMSE muito semelhante: 0,06949 versus 0,06992 e 0,15462 versus 0,15582. Isso não significa que T seja inútil para estimar T.

2. Correção de covariância/segunda ordem e atualizações condicionadas por ESS evitam o colapso de M3 sem destruir modos? Isso deve ser avaliado em nova partição teste, não ajustado retrospectivamente.

3. Com termodinâmica de referência consistente, excitação térmica e medições químicas esparsas, pontes melhoram calibração e decisões? A auditoria de h/T é pré-requisito para uma alegação física mais ampla.

Fontes e rastreabilidade

ProcessLab: github.com/walteryanko/yanko-process-lab, commit 16aaafb...<br/>Luyben (2011): doi.org/10.1002/aic.12289<br/>EnSBF: arxiv.org/abs/2512.18928v1; arxiv.org/html/2512.18928v4<br/>Reich (2013): doi.org/10.1137/130907367<br/>Cuturi (2013): arxiv.org/abs/1306.0895

A recuperação preservou CSV e NPZ completos; três linhas ausentes do journal sem medições foram reconstruídas por execução determinística e comparação exata. Auditou-se a correspondência de todos os RMSE com os NPZ. Todos os resultados, inclusive negativos, rejeições e fallbacks, permanecem no pacote.