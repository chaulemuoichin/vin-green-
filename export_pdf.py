import markdown
import pathlib
from weasyprint import HTML

md_path = pathlib.Path(r"A:\Spring_2026\GreenFuture\GreenShield_SchoolShield_PreliminaryRound.md")
pdf_path = md_path.with_suffix(".pdf")

md_text = md_path.read_text(encoding="utf-8")
html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

css = """
@page { margin: 2cm 2.2cm; }
body { font-family: Georgia, serif; font-size: 11pt; line-height: 1.65; color: #111; }
h1 { font-size: 14pt; text-align: center; margin-bottom: 6px; }
h2 { font-size: 12pt; border-bottom: 1px solid #aaa; padding-bottom: 3px; margin-top: 20px; }
h3 { font-size: 11pt; font-style: italic; margin-bottom: 4px; }
table { border-collapse: collapse; width: 100%; font-size: 10pt; margin: 10px 0; }
th, td { border: 1px solid #bbb; padding: 5px 8px; }
th { background: #eee; font-weight: bold; }
code, pre { font-family: Consolas, monospace; font-size: 9pt; background: #f5f5f5; padding: 2px 5px; border-radius: 3px; }
pre { padding: 8px; white-space: pre-wrap; word-break: break-word; }
ul, ol { margin: 6px 0; padding-left: 22px; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #ccc; margin: 14px 0; }
"""

html = "<!DOCTYPE html><html><head><meta charset='utf-8'><style>" + css + "</style></head><body>" + html_body + "</body></html>"

HTML(string=html).write_pdf(str(pdf_path))
print(f"Exported: {pdf_path}")
