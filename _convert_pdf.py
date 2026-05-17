#!/usr/bin/env python3
"""Self-contained MD→PDF using xhtml2pdf (no WeasyPrint/GTK needed on Windows)"""

import argparse, os, re, sys
import markdown2
from xhtml2pdf import pisa
from pathlib import Path


def extract_metadata(md):
    meta = {'title': None, 'author': None, 'date': None}
    m = re.search(r'^# (.+)$', md, re.MULTILINE)
    if m: meta['title'] = m.group(1).strip()
    return meta


def extract_toc(md):
    toc = []
    for line in md.split('\n'):
        m2 = re.match(r'^## (\d+)[\.]\s+(.+)$', line)
        if m2:
            toc.append({'level': 2, 'num': m2.group(1), 'title': re.sub(r'[\U0001F300-\U0001F9FF]', '', m2.group(2)).strip()})
        m3 = re.match(r'^### (\d+\.\d+)\s+(.+)$', line)
        if m3:
            toc.append({'level': 3, 'num': m3.group(1), 'title': re.sub(r'[\U0001F300-\U0001F9FF]', '', m3.group(2)).strip()})
    return toc


def toc_html(toc):
    if not toc: return ''
    rows = ''
    for item in toc:
        indent = '' if item['level'] == 2 else 'margin-left:16px;font-size:9.5pt;color:#555;'
        weight = 'font-weight:600;' if item['level'] == 2 else ''
        rows += f'<div style="{indent}{weight}margin-bottom:4px;">{item["num"]}. {item["title"]}</div>\n'
    return f'''<div style="page-break-after:always;padding:40px 50px;">
<h2 style="font-size:22pt;margin-bottom:24px;border-bottom:2px solid #d2d2d7;padding-bottom:10px;">Table of Contents</h2>
<div>{rows}</div></div>'''


def process_md(md, title):
    md = re.sub(r'^# .+?\n', '', md, count=1, flags=re.MULTILINE)
    md = re.sub(r'[\U0001F300-\U0001F9FF]', '', md)

    def h2_replace(m):
        num, t = m.group(1), m.group(2).strip()
        return f'\n<div style="page-break-before:always;"></div>\n\n## {num}. {t}\n'
    md = re.sub(r'\n## (\d+)\.\s+(.+?)\n', h2_replace, md)

    extras = ['fenced-code-blocks', 'tables', 'break-on-newline', 'code-friendly', 'cuddled-lists', 'strike']
    html = markdown2.markdown(md, extras=extras)
    html = re.sub(r'<table>', '<table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:10pt;">', html)
    html = re.sub(r'<th>', '<th style="padding:10px 14px;text-align:left;font-weight:600;border-bottom:2px solid #d2d2d7;background:#f5f5f7;">', html)
    html = re.sub(r'<td>', '<td style="padding:10px 14px;border-bottom:1px solid #d2d2d7;color:#424245;">', html)
    html = re.sub(r'<pre><code', '<pre style="background:#f5f5f7;border:1px solid #d2d2d7;border-radius:6px;padding:16px;margin:20px 0;font-size:9.5pt;"><code', html)
    html = re.sub(r'<blockquote>', '<blockquote style="border-left:3px solid #06c;padding-left:18px;margin:20px 0;color:#424245;">', html)
    return html


def convert(input_file, output_file=None, title=None, author=None):
    print(f"Reading: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        md = f.read()

    meta = extract_metadata(md)
    if title:  meta['title']  = title
    if author: meta['author'] = author

    toc_items = extract_toc(md)
    print(f"TOC: {len([t for t in toc_items if t['level']==2])} sections")

    body = process_md(md, meta['title'])

    doc_title = meta.get('title') or 'Document'
    doc_author = meta.get('author') or ''

    cover = f'''<div style="height:100vh;display:flex;align-items:center;justify-content:center;
background:linear-gradient(135deg,#f5f5f7 0%,#ffffff 100%);page-break-after:always;">
<div style="text-align:center;padding:60px;">
  <h1 style="font-size:36pt;font-weight:600;color:#1d1d1f;margin-bottom:24px;letter-spacing:-1px;">{doc_title}</h1>
  <p style="font-size:12pt;color:#86868b;margin-top:24px;">{doc_author}</p>
  <p style="font-size:10pt;color:#86868b;margin-top:8px;">Asian Hackathon for Green Future 2026</p>
</div></div>'''

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{doc_title}</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.7; color: #1d1d1f; }}
  h2 {{ font-size: 18pt; font-weight: 600; color: #1d1d1f; margin-top: 28px; margin-bottom: 18px;
       padding-bottom: 8px; border-bottom: 2px solid #d2d2d7; }}
  h3 {{ font-size: 14pt; font-weight: 600; color: #1d1d1f; margin-top: 24px; margin-bottom: 12px; }}
  h4 {{ font-size: 12pt; font-weight: 600; color: #424245; margin-top: 18px; margin-bottom: 8px; }}
  p  {{ margin-bottom: 14px; }}
  ul, ol {{ margin-left: 22px; margin-bottom: 16px; }}
  li {{ margin-bottom: 8px; }}
  code {{ background: #f5f5f7; padding: 2px 5px; border-radius: 3px; font-size: 9.5pt; color: #d70050; }}
  strong {{ font-weight: 600; }}
  a {{ color: #06c; text-decoration: none; }}
  hr {{ border: none; border-top: 1px solid #d2d2d7; margin: 28px 0; }}
  @page {{ size: A4; margin: 2cm 2cm 2cm 2cm; }}
</style>
</head>
<body>
{cover}
{toc_html(toc_items)}
<div>{body}</div>
</body>
</html>"""

    if not output_file:
        output_file = str(Path(input_file).with_suffix('.pdf'))

    print(f"Generating PDF -> {output_file}")
    with open(output_file, 'wb') as out:
        result = pisa.CreatePDF(full_html, dest=out)

    if result.err:
        print(f"ERROR: {result.err}")
        return 1

    size_kb = os.path.getsize(output_file) / 1024
    print(f"Done. {size_kb:.0f} KB → {output_file}")
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('-o', '--output')
    p.add_argument('--title')
    p.add_argument('--author')
    a = p.parse_args()
    sys.exit(convert(a.input, a.output, a.title, a.author))
