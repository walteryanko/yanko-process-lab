# 2. Mapa de estabilidade

A busca usa redução estacionária exata dos balanços materiais e energético. CA=FA/(v+Vk), CC=VkCA/v, CB=FB/v−CC, CM=FM/v e Tt=Ta+(T−Ta)[1−exp(−UA/(mwCpB))]. O problema escalar de calor é equivalente aos seis balanços no equilíbrio.

Continuação: tangente pelo núcleo do Jacobiano escalado, preditor em pseudo-arco e corretor Newton com hiperplano. Passo nominal 0,025 em coordenadas escaladas; falha de correção reduz o passo pela metade. Uma varredura independente em 121 valores por eixo verifica raízes adicionais. Intervalo térmico matemático: 250–430 K. Foram computados 1044 registros na malha de um parâmetro e 448 equilíbrios em 400 combinações aleatórias. A malha conjunta é exploratória.

| Eixo | Mínimo | Máximo | Pontos no ramo | Correções rejeitadas |
| --- | --- | --- | --- | --- |
| mw | 22.7 | 1366.2 | 170 | 0 |
| T0 | 275 | 325 | 226 | 0 |
| FA | 21.7724 | 50.8023 | 150 | 0 |
| FB | 317.515 | 589.67 | 131 | 0 |
| FM | 22.6796 | 68.0389 | 67 | 0 |
| UA | 15192.8 | 45578.4 | 128 | 0 |
| k0 | 1.1872e+13 | 2.2048e+13 | 134 | 0 |
| E | 73855.2 | 76869.6 | 137 | 0 |

As faixas são domínios de investigação computacional. Não equivalem a faixas operacionais aprovadas. Foram refinadas 14 dobras em famílias de um parâmetro. Essas ocorrências não são necessariamente bifurcações distintas no espaço multidimensional.

| Eixo | Parâmetro na dobra | T K | Resíduo | ∂²f/∂T² |
| --- | --- | --- | --- | --- |
| mw | 767.339 | 319.087 | 1.16634e-11 | -0.156671 |
| mw | 712.64 | 311.205 | 2.38817e-11 | 0.176939 |
| T0 | 295.52 | 309.032 | 1.42518e-11 | 0.257333 |
| T0 | 294.458 | 321.765 | 8.38736e-12 | -0.24549 |
| FA | 33.614 | 312.619 | 1.16348e-10 | 0.102859 |
| FA | 33.5353 | 317.498 | 6.21698e-12 | -0.092683 |

As dobras satisfazem f=0 e ∂f/∂T=0; derivadas em relação ao parâmetro e segunda derivada térmica são não nulas. Candidatos gerados por troca de autovalor dominante foram refinados antes da classificação. Nenhum Hopf foi confirmado nessa triagem; algumas sinalizações grosseiras eram passagem por dobra seguida de um par complexo estável. Não há exclusão global de Hopf fora das regiões varridas.

No nominal, α=−5,3832686 h⁻¹ e há um par −5,3832686 ± 8,9581585i h⁻¹. A baixa vazão de resfriamento, o modo desacoplado de Tt tem λ=−mw/(ρB Vt), próximo de zero mesmo quando a reação permanece fortemente estável. Usar apenas α completo criaria uma interpretação enganosa.

Validação temporal: perturbações nos três equilíbrios encontrados a T0=295 K confirmam restauração local nos ramos extremos e afastamento do ramo intermediário. results/A/local_validation.json contém as trajetórias. Uma seção da bacia foi amostrada em 31 condições iniciais térmicas e integrada por seis horas; não é uma descrição completa da bacia em seis dimensões.

Observabilidade: a matriz de saídas propagadas por 57 passos, escalada pelas unidades de estado, tem posto 3/6 no nominal. A capacidade calorífica torna algumas direções observáveis fora do equilíbrio, mas persistem limitações estruturais. Variância pequena do UKF não elimina incerteza estrutural ou de parâmetros.

![01_bifurcations](figures/01_bifurcations.png)
