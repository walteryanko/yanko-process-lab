# Hipóteses adicionais e decisões de investigação

As hipóteses abaixo foram formuladas durante a campanha, a partir dos resultados da triagem. São exploratórias, não hipóteses confirmatórias previamente registradas. Uma conexão matemática conhecida não recebe automaticamente status de descoberta original.

| ID | Hipótese falsificável | Menor teste e resultado | Decisão |
|--------|----------------------------|------------------------------|------------------------|
| H13 | Reordenar a alimentação, mantendo a renovação acumulada, reduz a incerteza terminal do PG | Três sinais de 0,6 h; separação terminal igual a 0,00948686 kmol/m³ | Refutada para os modos invariantes; a ambiguidade integrada muda menos de 1% |
| H14 | Ajustar Q no nominal torna uma equação térmica independente da referência de temperatura | Mudança deliberadamente incorreta de referência, seguida de refit; ganho térmico de alimentação muda 173% | Refutada; diagnóstico de derivadas é necessário |
| H15 | É possível remover um estado químico sem perder a qualidade controlada | Quociente de cinco coordenadas, mesmo prior projetado; erro de qualidade abaixo de 5e-14 | Sustentada numericamente; antecedente geral são coordenadas invariantes |
| H16 | O melhor projeto de Fisher também minimiza o arrependimento de controle | MAP e 17 decisões futuras, sementes novas; senoide prevê melhor, degrau tem menor arrependimento médio PG | Refutada como regra de ordenação universal |
| H17 | A pequena inconsistência de Hess explica a maior parte da baixa informação do EB | 24 ensaios espectrais com e sem fechamento do ciclo | Não sustentada; efeito pequeno na incerteza do alvo futuro sob o prior usado |
| H18 | Um ponto robusto local continua seguro ao se deslocar até ele | Transições de quatro tempos de residência, estados iniciais comuns e mismatch | Refutada para algumas escolhas PG; pontos bons não certificam caminhos |
| H19 | Excitação periódica e região robusta produzem ganhos adicionais quando combinadas | PI térmico fixo, nominal/alternativa com/sem modulação | Não promovida; qualidade média piora e as médias de recursos diferem |
| H20 | Uma amostra escolhida para reduzir variância também melhora mais o controle que um horário fixo | Atualização química com atraso e replay causal em 12 sementes novas | Não sustentada universalmente; no PG a seleção piora com atraso de dois tempos de residência |
| H21 | Aumentar a precisão térmica remove todos os modos desconhecidos do PG | Produto da Fisher pela direção invisível e prova de equivalência | Refutada estruturalmente; ruído menor não cria a informação ausente |
| H22 | Uma política compacta de memória pode ser útil sem reconstruir composição | PI de temperatura filtrada e integral, sem usar o estado químico calculado em paralelo | Sustentada como candidato local; não resolve aliasing nem domina baselines |
| H23 | O ponto econômico e o robusto são necessariamente diferentes | Mapas O1 a O4 e variação de pesos econômicos | Refutada; no EB coincidem para os pesos iniciais, e mudam quando os pesos mudam |
| H24 | Uma inovação térmica alta identifica unicamente erro cinético | Equação do residual: calor, entalpia, remoção e bias podem gerar o mesmo escalar | Refutada como diagnóstico único; falta identificação causal multissinal |
| H25 | O benefício de escolher outra região persiste com a mesma qualidade nominal | Nova campanha com 216 trajetórias e sementes 70000 a 70011 | PG melhora tracking com menor produção e risco residual; EB não mostra diferença clara |
| H26 | Uma violação de Hess pode aumentar artificialmente o posto de observabilidade térmica | Doze equilíbrios EB em duas variantes, com escalas idênticas; posto local quatro passa a três ao fechar Hess | Sustentada nesta linearização; a direção adicional tem informação prática desprezível |

H13 e H14 são as duas experiências autônomas curtas principais. H15 a H25 ampliam a interpretação sem acrescentar uma nova arquitetura por estética. Foram descartadas, sem execução, propostas de usar caos intencional próximo de bifurcações, deslocamentos rápidos entre ramos e controle extremo com cortes de alimentação além da autoridade declarada: a triagem já mostrou perda de margem térmica e não havia um conjunto seguro certificado que justificasse aprofundá-las. Não se conclui que tais técnicas sejam impossíveis em outros equipamentos.

O antecedente interno mais próximo de H13, H15, H21 e H24 já estava nos relatórios CSTR/ICAC/MOSAIC. A novidade possível aqui é o protocolo comparativo e sua evidência adicional, não a descoberta retrospectiva dessas propriedades.

Na verificação final de H13, a primeira versão de degraus limitados e recentrados excedia a velocidade permitida no primeiro movimento. Ela foi excluída e preservada em pilot_v0. A versão final usa uma senoide de amplitude relativa 0,06, média exatamente zero e máximo de 0,837 do limite de velocidade, incluindo a partida. O resultado terminal permanece o mesmo.
