# Operação e informação nos reatores PG e EB

Campanha exploratória de 10/10/2026 sobre os modelos recuperados de Walter Yanko de Aragão Brandão. Os arquivos históricos não foram alterados. Esta pasta pertence à branch research/beyond-conventional-operation-20261010, baseada em 16aaafb63572d62e0e3341e26d8317b0651bdde0.

**Resultado principal:** a operação muda informação e sensibilidade, mas não foi encontrada uma política segura e dominante nos dois reatores. A periodicidade testada perdeu para estacionários com recursos comparáveis. O ganho de tracking PG com PI congelado envolve compromissos e violações; a reconstrução EB continua termodinamicamente não reconciliada.

## Reprodução

Use Python 3.12. As versões efetivamente executadas estão em requirements.txt e results/environment.json.

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    python reproduce.py --output /tmp/pg-eb-smoke
    python reproduce.py --full --output /tmp/pg-eb-full

O destino deve estar vazio. O comando padrão executa os testes científicos e o fluxo curto completo de complementos, exportando novos resultados. O modo --full executa a campanha sequencial, os baselines e os relatórios numéricos; pode levar horas conforme a máquina. Os CSV/NPZ entregues nunca são apagados. Pequenas diferenças de otimizadores/BLAS e tempo de execução são possíveis; as sementes e identidades físicas estão fixadas.

Para recriar somente as figuras dos resultados entregues:

    python reproduce.py --figures

Para um módulo isolado, por exemplo:

    BEYOND_RESULTS=/tmp/pg-eb-custom python -m beyond.spectra

Alguns módulos dependem de resultados anteriores. A ordem do modo completo em reproduce.py explicita essas dependências. O módulo baselines recebe PG ou EB. A pasta vendor contém as cópias essenciais dos códigos recuperados para reprodução sem baixar os grandes arquivos históricos.

## Organização

- beyond/: equações, experimentos, políticas, diagnósticos e agregação.
- tests/: identidades físicas, fidelidade a fontes, invisibilidade, limites de atuação e fluxo E2E.
- results/: tabelas, trajetórias NPZ, parâmetros, sementes, testes e contrastes.
- results/pilot_v0/: resultados inválidos ou superados, preservados e excluídos das conclusões.
- figures/: mapas, respostas, Pareto, comparação periódica, decisões e gêmeos em PNG/PDF.
- docs/: auditoria, revisão, formulação, hipóteses, cobertura e resultados.
- deliverables/: relatório e manuscrito em formatos de leitura e edição.
- provenance/: hashes das fontes, modelo MATLAB essencial e disponibilidade de software.

Os NPZ de malha fechada contêm entradas realmente aplicadas, estados da planta simulada e estimativas, separados. Os estados verdadeiros servem à avaliação e aos oráculos rotulados; o PI direto não os lê. O teste científico verifica essa separação. Os arquivos de escopo JSON registram hipóteses das campanhas adicionais.

O ZIP entregue contém todas as trajetórias NPZ, tabelas detalhadas, pilotos invalidados e documentos finais. A branch pública contém código, fontes editoriais, figuras PNG e tabelas de síntese; os arquivos volumosos e os formatos binários finais permanecem no pacote reproduzível. A simulação completa pode reconstruí-los a partir do código da branch.

O arquivo MANIFEST.sha256 permite verificar cada arquivo entregue. Para empacotar novamente após simular e gerar os documentos, execute `python scripts/package_release.py /tmp/Pesquisa_Operacao_PG_EB_Reproduzivel.zip`. O script verifica a leitura dos PDF/PNG/NPZ/DOCX e compara todos os bytes do ZIP com o manifesto.

## Unidades e limites

PG: h, kmol, m³, K, kJ. Limite histórico de 160 °F = 344,261111 K; 180 °F é um limite posterior distinto, não usado para aceitar trajetórias.

EB: h, kmol, m³, °C, kcal; Arrhenius usa K. Envelope exploratório 140,85–165 °C, sem certificação industrial. Apenas R1, reciclo fixo e dever térmico idealizado. A variante hess fecha uma relação estequiométrica de entalpias; não é uma reconciliação completa.

## Evidência e limites

A campanha principal tem 2304 execuções rotuladas, não independentes; a verificação de qualidade comum tem 216. Os baselines têm 180; a identificação, 192 ajustes; a amostragem atrasada, 192; o supervisor, 120. O pareamento estatístico agrupa cenários que compartilham a semente. Os intervalos são exploratórios, sem correção de multiplicidade.

Os 15 testes e o fluxo E2E foram executados. A comparação DOP853 verifica dez trajetórias escolhidas, com diferença térmica máxima de 0,000214 K. Consulte os logs; não há execução MATLAB/Simulink/Aspen nem experimento físico.

O custo econômico é substituto, a energia é calor removido e o desgaste é variação total de atuação. Não há dados suficientes para lucro industrial, utilidades reais ou certificado de segurança.

## Documentos e fontes

Para gerar novamente os documentos, instale python-docx e disponibilize Pandoc/XeLaTeX; execute python scripts/build_documents.py. Essa etapa editorial não é necessária para simular. Para compilar apenas o LaTeX entregue, a partir desta pasta:

    xelatex -interaction=nonstopmode -output-directory=deliverables deliverables/Manuscrito_Operacao_Informacao.tex

As figuras referidas pelo LaTeX ficam em figures/. As referências têm DOI/URL e nível de acesso em docs/LITERATURA.md. Não se redistribuem PDFs integrais de terceiros. O código novo segue a licença MIT do repositório. Isso não concede direitos sobre documentos acadêmicos de terceiros.

Nenhuma nova coautoria foi atribuída. A dissertação PG registra Heleno Bispo da Silva Júnior como orientador e Arioston Araújo de Morais Júnior na banca/agradecimentos; o TFC EB registra Arioston como orientador.
