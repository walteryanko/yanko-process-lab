# Verificação da entrega v1.0

Data: 17 de outubro de 2026.

O pacote inclui o código completo, fontes recuperadas, configurações, modelos treinados, hipóteses aceitas e rejeitadas, datasets sintéticos, resultados por semente, gráficos, cinco relatórios, PDF de 14 páginas e laboratório local.

## Execução realizada

- 18 cenários principais, com 100 episódios independentes em cada cenário e sete estimadores: 12.600 avaliações.
- Diagnóstico cego em 600 episódios; 400 malhas de controle, usando 100 sementes pareadas para quatro combinações.
- 3.300 avaliações de ablação e 40 desafios exploratórios; sementes de desenvolvimento e teste separadas.
- 27 testes automatizados aprovados, incluindo causalidade, equivalência das duas variantes físicas, rejeição de hipóteses, controle e API.
- 13 verificações em Chromium real, incluindo navegação, exportação, nova simulação Python, tela pequena e HTML offline; nenhum erro JavaScript.
- PDF renderizado e conferido visualmente nas 14 páginas.

Os logs e resultados de verificação estão em `artifacts/`. Os resultados científicos completos estão em `artifacts/main/`. O manifesto SHA-256 cobre os arquivos do ZIP e pode ser verificado com `python scripts/verify_manifest.py`.

## Escopo e limites

A validação executada usou Linux e Python 3.12.14. Os scripts para Windows foram preparados, mas não executados em um Windows real. A instalação inicial requer internet; a operação principal passa a funcionar localmente, sem serviços pagos.

O arquivo `Laboratorio_Darwin_Observer.html` permite explorar os resultados sem instalação. Novas simulações e diagnóstico cego requerem o backend Python, iniciado por `INICIAR_LAB.bat`.

Todos os dados são sintéticos. A descoberta usa uma gramática física restrita; explicações concorrentes podem permanecer indistinguíveis. O ganho de estimação com boa excitação não se estende a todos os cenários: excitação fraca não demonstrou ganho e a transferência direta para a variante histórica piorou o RMSE. A cinética fora da gramática foi confundida com erro de alimentação.

No fechamento, foi acrescentada uma checagem explícita do domínio em todo o horizonte previsto do NMPC. A comparação das 100 trajetórias corrigidas com a campanha original está em `artifacts/release_control_verification.json`. Os tempos computacionais originais não incluem essa checagem adicional.

A branch GitHub contém código, modelos, relatórios Markdown e evidências tabulares/recortes de trajetórias. Os datasets completos e os arquivos visuais estão neste ZIP. O PDF e os gráficos também podem ser reconstruídos a partir da branch.
