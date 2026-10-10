"""Build scientific report PDF and review manuscript in LaTeX/PDF/Word.

Run from any directory; requires Pandoc, XeLaTeX and python-docx.
Rendered page QA is a separate human/agent step, not asserted by this builder.
"""
from pathlib import Path
import re,subprocess,json,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables';OUT.mkdir(exist_ok=True)
LOG=ROOT/'results';DOCS=ROOT/'docs'

def call(cmd):
    r=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    with (LOG/'document_build.log').open('a') as f:f.write(' '.join(map(str,cmd))+'\n'+r.stdout+'\n')
    if r.returncode:raise RuntimeError(r.stdout[-6000:])

def clean(s):
    return s.replace('−','-').replace('–','-').replace('—','-').replace('\u00a0',' ').replace('(../figures/','(figures/')

def latex(md,title,stem,report=False):
    path=OUT/(stem+'.md');path.write_text(clean(md))
    header=OUT/('report_header.tex' if report else 'article_header.tex')
    header.write_text(r"""
\usepackage{microtype}
\usepackage{needspace}
\usepackage{seqsplit}
\usepackage{caption}
\usepackage{float}
\makeatletter\def\fps@figure{H}\makeatother
\renewcommand{\figurename}{Figura}
\renewcommand{\contentsname}{Conteúdo}
\captionsetup{font=small,labelfont=bf}
\setlength{\emergencystretch}{3em}
\setlength{\parskip}{0.45em}
\setlength{\parindent}{0pt}
\setcounter{tocdepth}{1}
\widowpenalty=10000
\clubpenalty=10000
"""+(r"\usepackage{titlesec}\newcommand{\sectionbreak}{\clearpage}" if report else ""))
    tex=OUT/(stem+'.tex')
    cmd=['pandoc',str(path),'-f','markdown+tex_math_single_backslash','-s','-o',str(tex),
         '--metadata','title='+title,'--metadata','date=10 de outubro de 2026',
         '-V','documentclass=article','-V','papersize=letter','-V','geometry:margin=0.8in',
         '-V','fontsize=11pt','-V','mainfont=DejaVu Serif','-V','sansfont=DejaVu Sans',
         '-V','monofont=DejaVu Sans Mono','-V','colorlinks=true','-V','urlcolor=black',
         '-V','linkcolor=black','-H',str(header)]
    call(cmd)
    content=tex.read_text()
    content=re.sub(r'\b[0-9a-f]{40}\b',lambda m:r'\texttt{\seqsplit{'+m.group(0)+'}}',content)
    content=content.replace(r'\_',r'\_\allowbreak{}')
    tex.write_text(content)
    # Explicit driver invocation detects truncated PDF writes hidden by XeTeX.
    for _ in range(2):call(['xelatex','-no-pdf','-interaction=nonstopmode','-halt-on-error','-output-directory='+str(OUT),str(tex)])
    call(['xdvipdfmx','-o',str(OUT/(stem+'.pdf')),str(OUT/(stem+'.xdv'))])
    from pypdf import PdfReader
    PdfReader(OUT/(stem+'.pdf'))
    return path

def word(md,title,stem):
    from docx import Document
    from docx.shared import Inches,Pt,RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    path=OUT/(stem+'.docx')
    call(['pandoc',str(md),'-f','markdown+tex_math_single_backslash','-s','-o',str(path),'--metadata','title='+title])
    doc=Document(path)
    for section in doc.sections:
        section.page_width=Inches(8.5);section.page_height=Inches(11)
        section.top_margin=Inches(.8);section.bottom_margin=Inches(.8)
        section.left_margin=Inches(.85);section.right_margin=Inches(.85)
        section.footer_distance=Inches(.35)
        p=section.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        r=p.add_run();r.font.size=Pt(9);r.font.name='DejaVu Serif'
        fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
    for name in ['Normal','Body Text','First Paragraph','Compact']:
        if name in doc.styles:
            st=doc.styles[name];st.font.name='DejaVu Serif';st.font.size=Pt(11);st.font.color.rgb=RGBColor(0,0,0)
            st.paragraph_format.line_spacing=1.08;st.paragraph_format.space_after=Pt(6)
            st.paragraph_format.widow_control=True
    for name,size in [('Title',20),('Subtitle',12),('Heading 1',15),('Heading 2',12),('Heading 3',11)]:
        st=next(s for s in doc.styles if s.name==name);st.font.name='DejaVu Serif';st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
        st.font.underline=False;st.font.bold=name.startswith('Heading')
        st.paragraph_format.space_before=Pt(13 if name.startswith('Heading') else 0)
        st.paragraph_format.space_after=Pt(7);st.paragraph_format.keep_with_next=True
        for e in list(st.element.iter(qn('w:pBdr'))):e.getparent().remove(e)
        for e in st.element.iter(qn('w:color')):
            for attr in ['themeColor','themeTint','themeShade']:e.attrib.pop(qn('w:'+attr),None)
    for p in doc.paragraphs:
        if p._p.xpath('.//w:drawing'):p.paragraph_format.keep_with_next=True
        if p.style.name.startswith(('Title','Subtitle','Heading')):
            for r in p.runs:r.font.color.rgb=RGBColor(0,0,0);r.font.underline=False
            for e in list(p._p.iter(qn('w:pBdr'))):e.getparent().remove(e)
        if p.style.name=='Image Caption':
            p.paragraph_format.space_after=Pt(9)
            for r in p.runs:r.font.size=Pt(9)
    for shape in doc.inline_shapes:
        if shape.width>Inches(6.7):
            h=int(shape.height*Inches(6.7)/shape.width);shape.width=Inches(6.7);shape.height=h
    for table in doc.tables:
        table.autofit=False
        widths=[3.05,1.20,1.20,1.20] if len(table.columns)==4 else [6.7/len(table.columns)]*len(table.columns)
        for rowidx,row in enumerate(table.rows):
            if rowidx==0:
                trPr=row._tr.get_or_add_trPr();rep=OxmlElement('w:tblHeader');trPr.append(rep)
            for j,cell in enumerate(row.cells):
                cell.width=Inches(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                pr=cell._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
                for edge in ['top','left','bottom','right','insideH','insideV']:
                    e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');b.append(e)
                pr.append(b);mar=OxmlElement('w:tcMar')
                for edge,value in [('top','90'),('bottom','90'),('left','100'),('right','100')]:
                    e=OxmlElement('w:'+edge);e.set(qn('w:w'),value);e.set(qn('w:type'),'dxa');mar.append(e)
                pr.append(mar)
                if rowidx==0:
                    sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'DCE6F1');pr.append(sh)
                for p in cell.paragraphs:
                    p.paragraph_format.space_after=Pt(1);p.paragraph_format.space_before=Pt(1)
                    p.paragraph_format.line_spacing=1.05
                    p.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 else WD_ALIGN_PARAGRAPH.CENTER
                    for r in p.runs:r.font.size=Pt(10);r.font.name='DejaVu Serif';r.bold=(rowidx==0);r.font.color.rgb=RGBColor(0,0,0)
    doc.core_properties.author='';doc.core_properties.last_modified_by='';doc.core_properties.title=title
    doc.core_properties.subject='Estudo computacional exploratório PG e EB'
    doc.save(path)
    from zipfile import ZipFile
    with ZipFile(path) as z:
        xml=z.read('word/document.xml').decode()
        (LOG/'word_equation_check.json').write_text(json.dumps(dict(native_math_elements=xml.count('<m:oMath'),contains_raw_latex='\\delta' in xml),indent=2))

def main():
    (LOG/'document_build.log').write_text('')
    review=(DOCS/'LITERATURA.md').read_text()
    reviewbody,refs=review.split('## Referências verificadas',1)
    summary="""# Síntese da investigação

Esta investigação testou se modificar a operação facilita o controle de composição sem medição química contínua nos modelos PG e EB recuperados. A resposta é condicional: houve ganho informacional e menor erro em parte do domínio PG, mas nenhum regime seguro e dominante nos dois processos.

Os quatro experimentos principais foram executados e aprofundados segundo os resultados. A periodicidade perdeu para um estacionário encontrado com recursos comparáveis. Com a mesma referência química e o mesmo PI, o erro PG caiu 41,8%, acompanhado de 2,24% menos produção e violações térmicas. No EB, a melhora praticamente desapareceu. Uma pequena inconsistência de Hess acrescentava uma direção de observabilidade local espúria.

O pacote reúne auditoria, revisão crítica, formulação, hipóteses, código, dados brutos, figuras, baselines, resultados negativos e reprodução. A contribuição mais madura é metodológica. As novas evidências são de simulação Python; MATLAB, Aspen e planta real não foram executados. A autoria científica e qualquer submissão precisam de revisão dos pesquisadores.

| Evidência executada | Quantidade |
|---|---:|
| Projetos de excitação e ajustes MAP | 44 e 192 |
| Candidatos periódicos e linhas de mapa | 144 e 376 |
| Malhas principais rotuladas e rodada de qualidade comum | 2304 e 216 |
| Baselines recuperados reexecutados | 180 |
| Malhas com amostra atrasada e supervisão | 192 e 120 |
| Testes científicos e verificações DOP853 | 15 e 10 |

As contagens não são tamanhos de amostras independentes. As diferenças e intervalos pareados estão no capítulo de resultados. Os limites históricos e exploratórios permanecem separados.

\\clearpage
\\tableofcontents

"""
    parts=[summary,(DOCS/'AUDITORIA.md').read_text(),reviewbody,(DOCS/'FORMULACAO.md').read_text(),
        (DOCS/'COBERTURA.md').read_text(),(DOCS/'RESULTADOS.md').read_text(),(DOCS/'HIPOTESES.md').read_text(),
        '# Referências verificadas\n'+refs]
    report='\n\n'.join(parts)
    report=report.replace('## Verificação com a mesma referência de composição','## Verificação com a mesma referência de composição')
    report=report.replace('## Baselines e combinações','![Efeitos com qualidade nominal comum e intervalos pareados.](figures/same_quality.png){width=95%}\n\n## Baselines e combinações')
    report=report.replace('## Classificação da contribuição e maturidade','![A ablação de Hess remove uma direção local com informação prática desprezível.](figures/hess_observability.png){width=90%}\n\n## Classificação da contribuição e maturidade')
    report=report.replace('## Respostas às dez perguntas','\\clearpage\n\n## Respostas às dez perguntas')
    report=report.replace('## Quatro níveis de modelo','\\clearpage\n\n## Quatro níveis de modelo')
    report+='\n\n# Figuras complementares\n\n'
    for fn,caption in [('frequency_response','Ganhos e fases empíricos dos registros amostrados'),('pareto','Fronteira de Pareto para três critérios locais'),('control_tradeoffs','Campanha inicial com referências próprias por região'),('chemical_twins','Dissipação e indistinguibilidade química')]:
        report+=f'![{caption}.](figures/{fn}.png){{width=95%}}\n\n'
    latex(report,'Operação e informação nos reatores de propilenoglicol e etilbenzeno','Relatorio_Descobertas_PG_EB',True)
    if '--report-only' in sys.argv:return
    raw=(DOCS/'MANUSCRITO.md').read_text();title=raw.splitlines()[0][2:]
    body=raw.split('\n\n',1)[1]
    body=body.replace('As referências completas são inseridas a partir do registro verificado da revisão bibliográfica, mantendo os identificadores R.','')
    used=set(re.findall(r'R\d\d',body))
    # Explicit ranges cited in prose.
    used.update(['R06','R07','R08'])
    refslist=[p for p in refs.split('\n\n') if re.match(r'R\d\d\.',p)]
    body+='\n\n'+'\n\n'.join(p for p in refslist if p[:3] in used)
    # Convert content headings to level one after removing the title.
    body=re.sub(r'^(#{2,3}) ',lambda m:m.group(1)[1:]+' ',body,flags=re.M)
    md=latex(body,title,'Manuscrito_Operacao_Informacao')
    word(md,title,'Manuscrito_Operacao_Informacao')
    print('Built report PDF and manuscript LaTeX/PDF/DOCX.',flush=True)

if __name__=='__main__':main()
