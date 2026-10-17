# Auditoria matemática — Schrödinger-KF v1.0

## Construções diferentes

**M0.** UKF recuperado em `vendor/processlab/observer.ts`. A referência histórica
usa Euler, α=0,001, β=2, Q publicado e R=(1% da temperatura nominal)².
O teste de paridade preserva esse observador. A arena usa **M0 RK4**, α=0,35,
prior comum e ruído experimental de 0,35 K: é uma referência nova, identificada
como tal. A observação T/Tt é linear; a correção usa P previsto **incluindo Q**,
ganho de Kalman e forma de Joseph. Isso evita excluir indevidamente ruído de
processo da covariância de inovação.

**M1.** EnKF estocástico com observações perturbadas e covariância amostral
1/(N−1). Não representa uma posterior arbitrária por uma atualização Bayesiana
exata. M0/M1 recebem a mesma família de ruído dos métodos de partículas; no
caso robusto usam uma aproximação gaussiana por ajuste da covariância da inovação.

**M2.** Bootstrap PF: propagação da lei de transição, pesos em log e
reamostragem sistemática quando ESS<N/2. Os pesos são conservados nos passos
sem reamostragem. Não se adiciona rejuvenescimento oculto.

**M3.** Transporte entrópico com custo ||(xi−xj)/s||², marginais (w,1/N)
e atualização baricêntrica xj'=NΣi Pij xi. Sinkhorn alterna potenciais em log.
O teste exige erro máximo absoluto das marginais <10⁻⁸. Pesos exatamente nulos
são removidos do problema ativo e restaurados como linhas/colunas nulas.
Conserva a média até a tolerância das marginais, mas reduz a covariância.
Não há correção de segunda ordem: esse viés é medido, não escondido.

**M4.** Integração de uma difusão de Schrödinger–Föllmer. NÃO chama Sinkhorn.
A implementação de base segue o gerador de Bao e Sun, versão 1,
equações 3.9/3.12/3.13. A versão 4, de Hui Sun, mantém esse núcleo e discute
estabilidade dos pesos. O processo auxiliar começa no centro da previsão,
em coordenadas afins normalizadas. Sua escala é calculada da previsão, sem
acesso ao estado verdadeiro. Na versão entregue, a marginal alvo é uma
aproximação contínua por kernels gaussianos da posterior ponderada. Não é uma
reprodução bit a bit dos experimentos publicados.

Referências primárias:

- Bao & Sun (2025), [arXiv:2512.18928v1](https://arxiv.org/html/2512.18928v1).
- Sun (2026), [arXiv:2512.18928v4](https://arxiv.org/html/2512.18928v4).
- Reich, [A non-parametric ensemble transform method for Bayesian inference](https://arxiv.org/abs/1210.0375).
- Acevedo, de Wiljes & Reich, [Second-order accurate ensemble transform particle filters](https://arxiv.org/abs/1608.08179).
- Léonard, [A survey of the Schrödinger problem](https://arxiv.org/abs/1308.0215).
- Stromme, [Sampling From a Schrödinger Bridge](https://proceedings.mlr.press/v206/stromme23a/stromme23a.pdf).

## Formulação contínua implementada e derivação

Em coordenadas z=(x−a)/s, fixadas durante a assimilação, seja Q a lei do
movimento Browniano padrão iniciado em zero, no tempo auxiliar τ∈[0,1].
A marginal alvo é μh=Σj wj N(zj,h²I), com h=0,05 na campanha. Para h>0,
μh tem densidade e KL(μh||N(0,I)) finita. O minimizador em espaço de caminhos
com P0=δ0 e P1=μh tem mudança de medida g(V1)=μh(V1)/φ(V1).
O drift é ατ=∇log E_Q[g(V1)|Vτ=x]. Esta é uma ponte de Schrödinger genuína
com marginal inicial pontual; não é uma ponte entre a prior física e a
posterior física. A prior física fornece a aproximação de μh.

Integrando analiticamente cada kernel gaussiano, definimos D=1−τ+τh²:

    logits_j = log(wj) + (x·zj − τ||zj||²/2)/D
    pj = softmax(logits)_j
    ατ(x) = [Σj pj zj − (1−h²)x]/D

Esta redução é derivada para este código. Ela evita diferenças de grandes
exponenciais e não requer redes neurais ou treinamento. No limite h=0,
recupera a aproximação empírica da equação 3.9 publicada.

Integramos dV=ατ(V)dτ+dWτ por Euler–Maruyama. A malha quadrática
τl=1−(1−l/L)² reduz o passo perto do extremo final. Há três erros distintos:
aproximação da posterior por partículas, suavização KDE e discretização da
SDE. Um alvo empírico atômico exato é singular em relação à marginal
Browniana contínua; por isso **não se atribui KL finita a h=0**. Esse caso é
somente uma ablação da aproximação numérica publicada.

Em coordenadas físicas a referência Browniana é anisotrópica, determinada
pela escala diagonal da previsão. A normalização altera a referência Q e
o caminho, não o significado das coordenadas finais. O alvo regularizado
também muda com essa escala; sua influência é uma limitação explícita.

## Causalidade e informação

`advance(u,y)` recebe só o comando do intervalo e a observação disponível
no fim desse intervalo. Não recebe a planta verdadeira, seus parâmetros ou
observações futuras. O tempo τ da ponte não representa o futuro do reator.
O teste de prefixo modifica medições futuras e exige estimativas anteriores
idênticas. Avaliadores e gráficos têm acesso à verdade para calcular erros,
mas essa informação não retorna ao estimador.

## Ruído e parâmetros

Nas caudas pesadas usa-se t multivariada com ν=3 e matriz de escala R; sua
covariância é 3R. Os outliers seguem 0,94 N(0,R)+0,06 N(0,100R).
Ruído correlacionado significa correlação contemporânea 0,75 entre sensores,
sem correlação temporal. Medidas ausentes são marginalizadas por máscara.
O viés de sensor é constante desconhecido por trajetória e não estimado:
esse ensaio é deliberadamente de modelo de observação mal especificado.

A física incerta usa θ=[log(UA/UA0),log(k0/k00),log(FA/FA0),log(q/q0)].
Sua prior é informada a todos; os valores sorteados da planta não são.
Na versão aumentada, M0/M1 fazem estimação conjunta e M2–M4 carregam e
atualizam amostras dos parâmetros. Não se afirma identificar separadamente
E e k0. Não há passeio aleatório artificial dos parâmetros estáticos.

## Limites da contribuição

O método não cria informação que a função de observação não contém. Também
não pode recuperar um modo ausente da previsão sem depender do kernel ou
do erro de discretização. Gerar pontos novos não equivale a descobrir modos
novos. A nomenclatura Schrödinger-KF descreve este laboratório clássico;
não há computação quântica, vantagem quântica ou originalidade absoluta alegada.

M5 foi implementado como chave entre EnKF e M4 baseada em momentos ponderados
de assimetria/curtose e ESS. O gatilho só é ativado se a ablação de
desenvolvimento justificar o uso. A decisão concreta e todas as candidatas
estão em `results/development/selection.json`.
