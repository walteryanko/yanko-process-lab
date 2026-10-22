# Formulações e correspondência matemática

## Filtragem causal

A previsão integra p(x_k|x_{k-1},u) contra a posterior anterior; a análise multiplica pela verossimilhança atual. h(x)=T. Nenhum filtro recebe estados verdadeiros ou parâmetros verdadeiros. Testes alteram observações futuras e exigem prefixos idênticos.

M0 usa transformada unscented α=0,35, β=2, κ=0, RK4 e atualização de Joseph para h linear. M1 usa covariância amostral 1/(N-1) e observações perturbadas. M2 acumula log-pesos, ESS=1/Σw² e reamostragem sistemática abaixo de N/2. Normalização, pesos e momentos são testados.

## M3: transporte entrópico

Resolve min ΣPij Cij + εΣPij(log Pij-1), P1=w, Pᵀ1=1/N. Cij=||xi/s-xj/s||², s=[0,1;1,5;0,75;0,25;15] nas unidades dos estados. Parâmetros aumentados usam seus desvios-padrão logarítmicos; viés térmico usa 1,5 °C. Não há distância bruta misturando concentração e temperatura.

K=-C/ε em log; logu=logw-logsumexp(K+logv); logv=log(1/N)-logsumexp(K+logu). Pesos zero são retirados do problema ativo. Exige erro máximo de marginais <1e-8 em até 1.000 iterações. Não convergência causa fallback PF registrado.

x'_j=NΣ_i Pij xi conserva a média ponderada quando convergem as marginais. Por convexidade, a transformação baricêntrica contrai dispersão; não conserva automaticamente covariância, caudas ou modos. Medem-se massa, custo, erro das marginais, erro da média e razão de traços da covariância normalizada. A subcobertura de M3 é um resultado, não escondida por ajuste posterior. M3 não é chamado de Schrödinger Bridge.

## M4: ponte Schrödinger–Föllmer

Referência: Bao e Sun, arXiv:2512.18928v1, equações (3.9), (3.12), (3.13); v4 de Hui Sun (04/08/2026), mesma construção central. A autoria depende da versão. O trabalho é tratado como preprint.

Em z_i=(x_i-c)/s, c e s são calculados apenas da previsão. Q é a lei dV=dW, V0=0, τ∈[0,1]. O alvo é μ=Σ_i wi N(zi,h²I), h>0. A ponte minimiza KL(P||Q) com P0=δ0 e P1=μ. Seu drift é ∇log E[f(v+W_(1-τ))], f=dμ/dN(0,I). Para esse alvo:

```
Dτ = 1 - τ + τ h²
ℓ_i = log wi + (v·zi - τ ||zi||²/2) / Dτ
π_i = softmax(ℓ)_i
a(v,τ) = [Σ_i π_i zi - (1-h²)v] / Dτ
```

h=0 recupera a fórmula empírica publicada. Um alvo estritamente discreto é singular em relação à referência final browniana, portanto não constitui ponte de KL finita sem qualificar o limite. A campanha usa h=0,1 e alvo contínuo. O alisamento modifica explicitamente a posterior aproximada.

Euler–Maruyama integra a SDE em 64 passos, grade τ_j=1-(1-j/L)². A saída é c+sV1. Blocos de 128 trajetórias limitam a memória do drift. A mudança afim induz referência anisotrópica física. Não há aprendizado neural nem observações futuras.

É uma ponte genuína com marginal inicial pontual, usada como gerador posterior. Não é a ponte física entre a prior completa e a posterior, nem solução geral de duas marginais arbitrárias. A implementação acrescenta alvo KDE e normalização pela previsão; não é uma reprodução sem modificações do artigo. Erros: ensemble finito, pesos Monte Carlo, KDE, SDE discretizada, integração física e tratamento de domínio.

Testes verificam drift de um núcleo gaussiano, fórmula empírica publicada, linear-gaussiano, observação parcial, seno e y=x²+v. Ensaios sintéticos têm referência por quadratura, W1, massas dos lados e ablação h/passos. Isso não garante precisão no CSTR.

## Domínio e ruído

Concentrações ≥0 e 0<T<220 °C; 220 é guarda numérica, não limite de fase certificado. Prior e processo usam rejeição condicionada. UKF recusa sigma points e médias inválidos. Análise com partículas inválidas causa fallback de toda a análise para PF, contado. Não há projeção silenciosa.

Condicionar ao domínio altera gaussianas. UKF calcula intervalos analíticos gaussianos; amostras diagnósticas para CRPS/energy são condicionadas. A diferença pode importar perto da fronteira. Rejeições e fallbacks são quantificados em analysis.json.

Partículas usam Student-t ν=3 ou mistura 0,94N(0,R)+0,06N(0,100R) quando informado. UKF/EnKF compartilham aproximação robusta por inflação da covariância; não é Bayes Student-t exato. Viés e AR(1), ρ=0,75, usam estado latente em todos os filtros informados; sua realização verdadeira não é conhecida. Os ingênuos usam R=2,25 sem estado latente. Ausência de medição produz somente previsão.

Incerteza física: cinco log-fatores de k1/k2/k3, calor reacional e concentração efetiva de etileno no balanço material de alimentação. Propriedades térmicas de entrada continuam as publicadas. Não se inventa UA em um modelo com entrada Q ideal; estimação conjunta não equivale a identificar todos os parâmetros de Arrhenius.

## M5 e inferência estatística

Indicador: máximo dos módulos de assimetria e excesso de curtose ponderados. M4 exige indicador acima do limiar e ESS/N>0,05. Limiares 2 e 6 foram testados. O gatilho só é aceito se IC95% superior de ΔCRPS pareado por seed de desenvolvimento for negativo. Os dois cenários da mesma seed são agrupados. Não houve ganho; limiar infinito congela EnKF. M5 não é uma confirmação independente.

IC95% principal: bootstrap pareado, 100 seeds, 2.000 reamostragens; sem correção de multiplicidade. Resultados são exploratórios por cenário, não universais. Trajetórias e ruídos verdadeiros são pareados. Streams Monte Carlo partem compartilhados, mas divergem conforme consumo dos algoritmos. Energy score usa estados escalonados a cada oito passos.

## Referências primárias

- https://arxiv.org/abs/2512.18928v1 e https://arxiv.org/html/2512.18928v4
- Reich (2013), A nonparametric ensemble transform method for Bayesian inference. https://doi.org/10.1137/130907367
- Cuturi (2013), Sinkhorn Distances. https://arxiv.org/abs/1306.0895
- Física e UKF: https://github.com/walteryanko/yanko-process-lab/tree/16aaafb63572d62e0e3341e26d8317b0651bdde0/research/ethylbenzene
- Luyben (2011), Design and control of the ethyl benzene process. https://doi.org/10.1002/aic.12289
