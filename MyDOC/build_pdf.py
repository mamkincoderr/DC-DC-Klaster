# -*- coding: utf-8 -*-
"""
Сборка PDF из глав ЭП: Markdown -> HTML -> печать в PDF безголовым Chrome.

    python build_pdf.py ЭП_8_Моделирование.md [ещё файлы...]

Формулы вида $$ ... $$ отдаются KaTeX (загружается из сети при сборке).
Ключ --html оставляет промежуточный HTML для проверки вёрстки.
"""
import os
import re
import subprocess
import sys
import tempfile

from markdown_it import MarkdownIt

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
KATEX = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist'

CSS = """
@page { size: A4; margin: 20mm 18mm 20mm 22mm; }
body  { font-family: "Times New Roman", Times, serif; font-size: 11.5pt;
        line-height: 1.42; color: #000; margin: 0; text-align: justify;
        hyphens: auto; -webkit-hyphens: auto; }
h1 { font-size: 17pt; margin: 0 0 14pt; text-align: left; }
h2 { font-size: 14pt; margin: 18pt 0 8pt; text-align: left;
     page-break-after: avoid; }
h3 { font-size: 12.5pt; margin: 14pt 0 6pt; text-align: left;
     page-break-after: avoid; }
p  { margin: 0 0 7pt; }
ul, ol { margin: 0 0 8pt 0; padding-left: 20pt; }
li { margin-bottom: 3pt; }
code { font-family: Consolas, "Courier New", monospace; font-size: 90%;
       background: #f2f2f2; padding: 0 2px; }
pre  { font-family: Consolas, "Courier New", monospace; font-size: 9pt;
       background: #f6f6f6; border: 1px solid #ddd; padding: 6pt 8pt;
       white-space: pre-wrap; page-break-inside: avoid; }

/* таблицы: во всю ширину полосы, не рвутся между страницами */
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt;
        font-size: 9.5pt; page-break-inside: avoid; }
th, td { border: 0.5pt solid #444; padding: 2.5pt 4pt; text-align: left;
         vertical-align: top; }
th { background: #ececec; font-weight: bold; }
tbody tr:nth-child(even) td { background: #fafafa; }

/* иллюстрации: вписываются в полосу, не режутся страницей */
img { display: block; max-width: 100%; height: auto; margin: 8pt auto 2pt; }
p > img + em, .caption { display: block; text-align: center; font-size: 10pt; }
p:has(img) { page-break-inside: avoid; page-break-after: avoid; text-align: center; }

/* подпись под рисунком — это абзац, начинающийся со слова "Рисунок" */
p.figcaption { text-align: center; font-size: 10pt; margin: 0 0 12pt; }

/* формулы */
.eq { text-align: center; margin: 9pt 0; page-break-inside: avoid; }
.katex { font-size: 1.02em; }

strong { font-weight: bold; }
h1 + p, h2 + p, h3 + p { margin-top: 0; }
"""

HTML = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>{title}</title>
<link rel="stylesheet" href="{katex}/katex.min.css">
<style>{css}</style></head>
<body>
{body}
<script src="{katex}/katex.min.js"></script>
<script src="{katex}/contrib/auto-render.min.js"></script>
<script>
  renderMathInElement(document.body, {{
    delimiters: [{{left: "$$", right: "$$", display: true}}],
    throwOnError: false
  }});
</script>
</body></html>
"""


def convert(md_path, keep_html=False):
    src = open(md_path, encoding='utf-8').read()

    # формулы прячем от разметки: подчёркивания и фигурные скобки ей не по зубам
    eqs = []

    def stash(m):
        eqs.append(m.group(0))
        return f'\n\nEQPLACEHOLDER{len(eqs) - 1}\n\n'

    src = re.sub(r'\$\$.*?\$\$', stash, src, flags=re.S)

    md = MarkdownIt('commonmark').enable(['table', 'strikethrough'])
    body = md.render(src)

    for i, e in enumerate(eqs):
        body = body.replace(f'<p>EQPLACEHOLDER{i}</p>', f'<div class="eq">{e}</div>')

    # подписи к рисункам оформляем отдельным классом
    body = re.sub(r'<p>(Рисунок [^<]*)</p>', r'<p class="figcaption">\1</p>', body)

    html = HTML.format(title=os.path.splitext(os.path.basename(md_path))[0],
                       katex=KATEX, css=CSS, body=body)
    html_path = os.path.splitext(md_path)[0] + '.html'
    open(html_path, 'w', encoding='utf-8').write(html)

    pdf_path = os.path.splitext(md_path)[0] + '.pdf'
    profile = tempfile.mkdtemp()
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--no-sandbox',
                    f'--user-data-dir={profile}',
                    '--virtual-time-budget=30000',
                    '--no-pdf-header-footer',
                    f'--print-to-pdf={os.path.abspath(pdf_path)}',
                    'file:///' + os.path.abspath(html_path).replace('\\', '/')],
                   capture_output=True, timeout=300)
    if not keep_html:
        os.remove(html_path)
    return pdf_path, os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    keep = '--html' in sys.argv
    for f in args:
        p, n = convert(f, keep)
        print(f'{p}: {n} байт')
