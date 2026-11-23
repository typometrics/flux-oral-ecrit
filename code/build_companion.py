#!/usr/bin/env python3
"""
build_companion.py -- assemble the companion site of the article on spoken and written French in article_fr/companion/
(also the content of the GitHub repository typometrics/flux-oral-ecrit, served at https://typometrics.github.io/flux-oral-ecrit/
and mirrored at https://typometrics.elizia.net/flux-oral-ecrit/).
Run export_data.py, mathdata_fr.py, structure.py and lengths.py first. Since 23 November 2026 the article is the English version (article_en.md, figures in fig_en/),
with a PDF printed by headless Chromium; the French version of October stays available. Nothing of the unpublished flux site (other languages, other papers, reviews)
is copied: the maths page is kept as it was built in October (REBUILD_MATHS=1 rebuilds it from the flux site, whose maths page now also covers unpublished work).
"""
import os
import re
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(HERE, "..", "v218")
S2 = os.path.join(V2, "site2")
OUT = os.path.join(HERE, "companion")
NB = " "
URL = "https://typometrics.github.io/flux-oral-ecrit/"
MIRROR = "https://typometrics.elizia.net/flux-oral-ecrit/"

for d in ("article", "article/fig", "article/fig_en", "maths", "maths/data", "code", "results", "assets", "vendor"):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)

# ------------------------------------------------------------------ assets (style + helpers with a nav for this site only)
shutil.copy(os.path.join(S2, "assets", "style.css"), os.path.join(OUT, "assets", "style.css"))
shutil.copy(os.path.join(S2, "vendor", "plotly.min.js"), os.path.join(OUT, "vendor", "plotly.min.js"))
js = open(os.path.join(S2, "assets", "common.js"), encoding="utf-8").read()
js = re.sub(r"const NAV = \[.*?\];", '''const NAV = [
  ["index.html", "Home"],
  ["article/index.html", "Article"],
  ["maths/index.html", "Statistics"],
  ["data/index.html", "Data"],
  ["code/index.html", "Code and results"],
];''', js, count=1, flags=re.S)
js = re.sub(r"const PART_A = \[.*?\];", "const PART_A = [];", js, count=1, flags=re.S)
js = js.replace('<a class="brand" href="index.html">Flux · UD/SUD 2.18</a>', '<a class="brand" href="${location.pathname.includes("/article/") || location.pathname.includes("/maths/") || location.pathname.includes("/data/") || location.pathname.includes("/code/") ? "../" : ""}index.html">The dependency flux · spoken and written French</a>')
js = js.replace('`<a href="${f}" class="${(f === here || (part === "A" && inA)) ? "active" : ""}">${t}</a>`',
                '`<a href="${(location.pathname.match(/\\/(article|maths|data|code)\\//) ? "../" : "") + f}" class="${location.pathname.endsWith("/" + f) || (f === "index.html" && !location.pathname.match(/\\/(article|maths|data|code)\\//)) ? "active" : ""}">${t}</a>`')
js = re.sub(r"f\.innerHTML = `.*?`;", f'f.innerHTML = `Sylvain Kahane & Kim Gerdes · companion site of the article “The dependency flux as a measure of syntactic complexity: spoken and written French” · <a href="https://github.com/typometrics/flux-oral-ecrit">github.com/typometrics/flux-oral-ecrit</a>`;', js, count=1, flags=re.S)
open(os.path.join(OUT, "assets", "common.js"), "w", encoding="utf-8").write(js)
open(os.path.join(OUT, "assets", "build.js"), "w").write('window.BUILD_DATE = "2026-11-23";\n')


def page(title, body, lang="en", depth=0, extra_head=""):
    rel = "../" * depth
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{rel}assets/style.css">
<script src="{rel}assets/build.js"></script>
<script src="{rel}assets/common.js"></script>
{extra_head}
<style>
  .paper p {{ text-align: justify; hyphens: auto; }}
  .paper img {{ max-width: 100%; display: block; margin: 0 auto; background: #fff; border-radius: 6px; }}
  .paper .authors p {{ text-align: right; font-family: var(--sans); }}
  .paper .abstract {{ font-size: 15px; margin: 8px 0; }}
  .paper .ex {{ margin: 12px 0 12px 1.5em; font-size: 15.5px; }}
  .paper .refs p {{ padding-left: 1.5em; text-indent: -1.5em; font-size: 14.5px; margin: 4px 0; }}
  .paper table {{ border-collapse: collapse; font-family: var(--sans); font-size: 13px; margin: 10px auto; }}
  .paper table td, .paper table th {{ border: 1px solid var(--border); padding: 4px 8px; }}
  .paper table caption {{ caption-side: top; font-family: var(--sans); font-size: 13px; color: var(--muted); padding: 6px; }}
  .paper figcaption {{ text-align: center; }}
  .paper section.footnotes {{ font-size: 14px; border-top: 1px solid var(--border); margin-top: 24px; }}
  table.t {{ border-collapse: collapse; font-family: var(--sans); font-size: 14px; }}
  table.t td, table.t th {{ border: 1px solid var(--border); padding: 4px 10px; text-align: left; vertical-align: top; }}
</style>
</head>
<body>
<main class="narrow paper">
{body}
</main>
</body>
</html>"""


# ------------------------------------------------------------------ article: the English version, and the French version of October
# the public copy has no e-mail addresses (the submitted docx keeps them)
pub = re.sub(r";\s*[\w.+-]+@[\w.-]+\.\w+(?=\.\])", "", open(os.path.join(HERE, "article_en.md"), encoding="utf-8").read())
assert "@" not in pub.split("# 1. Introduction")[0], "e-mail address left in the public article"
open(os.path.join(HERE, "article_en_public.md"), "w", encoding="utf-8").write(pub)
subprocess.run(["python3", "make_docx.py", "article_en_public.md", "article_en_public.docx"], check=True, cwd=HERE)
subprocess.run(["pandoc", "article_en_public.md", "-t", "html5", "--wrap=none", "-o", "article_en_body.html"], check=True, cwd=HERE)
body = open(os.path.join(HERE, "article_en_body.html"), encoding="utf-8").read()
for f in os.listdir(os.path.join(HERE, "fig_en")):
    shutil.copy(os.path.join(HERE, "fig_en", f), os.path.join(OUT, "article", "fig_en", f))
shutil.copy(os.path.join(HERE, "article_en_public.docx"), os.path.join(OUT, "article", "article_flux_spoken_written.docx"))
shutil.copy(os.path.join(HERE, "article_en_public.md"), os.path.join(OUT, "article", "article_en.md"))
# PDF: the article as a plain standalone page (no navigation), printed by headless Chromium
css = ("@page{size:A4;margin:2cm 2cm 2.2cm}body{font-family:'DejaVu Serif',Georgia,serif;font-size:11pt;line-height:1.45;max-width:17cm;margin:auto}h1{font-size:16pt;text-align:center}"
       "h1,h2{font-family:'DejaVu Sans',sans-serif}h2{font-size:12.5pt}p{text-align:justify}img{max-width:100%;display:block;margin:auto}figure{margin:12px 0;page-break-inside:avoid}"
       "figcaption{font-size:9.5pt;text-align:center}.authors p{text-align:right}.abstract{font-size:10pt}.ex{margin-left:1.5em}"
       "table{display:table!important;width:100%!important;overflow:visible!important;border-collapse:collapse;font-family:'DejaVu Sans',sans-serif;font-size:7.5pt;margin:8px auto;page-break-inside:avoid}td,th{border:1px solid #999;padding:2px 5px}"
       "caption{font-size:8.5pt;padding:4px}body{max-width:none!important;padding:0!important}.refs p{padding-left:1.5em;text-indent:-1.5em;font-size:9.5pt;margin:2px 0}section.footnotes{font-size:9pt}")
tmp = os.path.join(HERE, "article_en_print.html")
subprocess.run(["pandoc", "article_en_public.md", "-s", "--metadata", "pagetitle=article", "-t", "html5", "--wrap=none", "-o", tmp], check=True, cwd=HERE)
h = open(tmp, encoding="utf-8").read().replace("</head>", f"<style>{css}</style></head>")
open(tmp, "w", encoding="utf-8").write(h)
chrome = os.path.expanduser("~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome")
pdf = os.path.join(OUT, "article", "article_flux_spoken_written.pdf")
subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", "file://" + tmp], check=True, capture_output=True)
os.remove(tmp)
title = "The dependency flux as a measure of syntactic complexity: spoken and written French"
note = ('<div class="note" style="font-family:var(--sans)">Version of 23 November 2026 for <i>Studii de lingvistică</i> (issue on complexity). Download: '
        '<a href="article_flux_spoken_written.pdf">PDF</a> · <a href="article_flux_spoken_written.docx">.docx</a> · <a href="article_en.md">Markdown source</a> · '
        '<a href="fr.html">French version of October 2026</a> · <a href="../data/index.html">data</a> · <a href="../code/index.html">code and results</a>.</div>')
open(os.path.join(OUT, "article", "index.html"), "w", encoding="utf-8").write(page(title, note + f"<h1>{title}</h1>\n" + body.replace('src="fig_en/', 'src="fig_en/'), depth=1))
subprocess.run(["pandoc", "article.md", "-t", "html5", "--wrap=none", "-o", "article_body.html"], check=True, cwd=HERE)
body_fr = open(os.path.join(HERE, "article_body.html"), encoding="utf-8").read()
for f in os.listdir(os.path.join(HERE, "fig")):
    shutil.copy(os.path.join(HERE, "fig", f), os.path.join(OUT, "article", "fig", f))
shutil.copy(os.path.join(HERE, "article_flux_oral_ecrit.docx"), os.path.join(OUT, "article", "article_flux_oral_ecrit.docx"))
shutil.copy(os.path.join(HERE, "article.md"), os.path.join(OUT, "article", "article.md"))
title_fr = f"Le flux de dépendance, une mesure de la complexité syntaxique{NB}: l'oral et l'écrit en français"
note_fr = (f'<div class="note" style="font-family:var(--sans)">Version française d\'octobre 2026, remplacée par la <a href="index.html">version anglaise</a>. '
           f'<a href="article_flux_oral_ecrit.docx">.docx</a> · <a href="article.md">source Markdown</a>.</div>')
open(os.path.join(OUT, "article", "fr.html"), "w", encoding="utf-8").write(page(title_fr, note_fr + f"<h1>{title_fr}</h1>\n" + body_fr, lang="fr", depth=1))
# ------------------------------------------------------------------ maths page (from the flux site, links to unpublished pages removed)
REBUILD_MATHS = os.environ.get("REBUILD_MATHS") == "1"
m = open(os.path.join(S2, "math.html"), encoding="utf-8").read()
m = m.replace('<script src="vendor/plotly.min.js"></script>', '<script src="../vendor/plotly.min.js"></script>')
m = m.replace('<link rel="stylesheet" href="assets/style.css">', '<link rel="stylesheet" href="../assets/style.css">')
m = m.replace('<script src="assets/build.js"></script>', '<script src="../assets/build.js"></script>').replace('<script src="assets/common.js"></script>', '<script src="../assets/common.js"></script>')
m = m.replace('<meta name="robots" content="noindex">\n', "")
m = m.replace("and the statistics that the <a href=\"reviews_fr.html#r1\">statistician's review</a> asks for.", "and the statistics a statistical reviewer would ask for.")
m = m.replace("All the numbers\nbelow are computed on the five French corpora, SUD trees, sentences of 10–19 words: the setting of the French article.",
              "All the numbers\nbelow are computed on the data of the article: the five French corpora, SUD trees, units of 10–19 words (written corpora re-segmented); “micro” means\nmicrosyntax only, i.e. macro-syntactic segments cut out as in the article.")
m = m.replace('<a href="#s9">9 The review decoded</a>', "")
m = re.sub(r'<h2 id="s9">.*?</ol>\n', "", m, count=1, flags=re.S)
m = m.replace('<a href="#s10">10 Glossary</a>', '<a href="#s10">9 Glossary</a>').replace('<h2 id="s10">10. Glossary</h2>', '<h2 id="s10">9. Glossary</h2>')
m = re.sub(r'<a href="(method|lambda|random|french|reviews_fr|matrices|extended|table|potential)\.html[^"]*">(.*?)</a>', r"\2", m)
m = m.replace("(see\n<a href=\"method.html\">Measures</a>)", "").replace("(the method of the June pages)", "")
m = m.replace('The site\'s answer is the random baseline:', "The answer used on the full flux site is a random baseline:")
m = m.replace('<p class="small muted">Computed from <code>v218/mathdata.py</code> (data/math.json); sentence bootstrap from <code>article_fr/bootstrap.py</code>.</p>',
              '<p class="small muted">Computed from <code>mathdata_fr.py</code> (data/math.json) on the article\'s data; standard errors from <code>bootstrap2.py</code>. The OLS and random-baseline tables are empty here: they belong to the larger study.</p>')
m = m.replace('const FLAB = { all: "all relations", micro: "without macro-syntax" };', 'const FLAB = { all: "all relations", micro: "microsyntax only" };')
m = m.replace('<option value="all|flux|lambda">λ flux</option>', '<option value="all|flux|lambda">λ flux</option>')
# guard the tables that have no data in this version
m = m.replace("function olsTable() {\n  const rows = [];", "function olsTable() {\n  if (!Object.keys(M.ols).length) { document.getElementById('olsTable').innerHTML = '<p class=\"small muted\">Not computed on the article data.</p>'; return; }\n  const rows = [];")
m = m.replace("function randomTable() {\n  const rows = [];", "function randomTable() {\n  if (!Object.keys(M.random).length) { document.getElementById('randomTable').innerHTML = '<p class=\"small muted\">Not computed on the article data; see the article\\'s discussion of the random baseline.</p>'; return; }\n  const rows = [];")
if REBUILD_MATHS:
    open(os.path.join(OUT, "maths", "index.html"), "w", encoding="utf-8").write(m)
assert not REBUILD_MATHS or "reviews" not in m.lower().replace("statistical reviewer", "") and 'href="method.html"' not in m, "unpublished links left in maths page"

# ------------------------------------------------------------------ code and results
code_files = {HERE: ["variants.py", "bootstrap2.py", "extras.py", "pairs_content.py", "structure.py", "lengths.py", "figs.py", "figs2.py", "figs_en.py", "export_data.py", "mathdata_fr.py",
                     "nbsp_pass.py", "make_docx.py", "build_companion.py"],
              V2: ["compute2.py", "compute.py", "fit.py", "mathdata.py", "get_grew_corpus.py"]}
for d, fs in code_files.items():
    for f in fs:
        shutil.copy(os.path.join(d, f), os.path.join(OUT, "code", f))
for f in ["variants.json", "bootstrap2.json", "extras.json", "pairs_content.json", "structure.json", "length_shares.json"]:
    shutil.copy(os.path.join(HERE, f), os.path.join(OUT, "results", f))
shutil.copy(os.path.join(S2, "download", "poids4.txt"), os.path.join(OUT, "results", "poids4.txt"))
code_index = """<h1>Code and results</h1>
<p>The Python scripts that produce the numbers, figures and docx of the article, and the result files they write. Requirements: Python 3, NumPy, SciPy, pandas, Matplotlib, python-docx, pandoc.</p>
<h2>Scripts</h2>
<table class="t">
<tr><th>File</th><th>Role</th></tr>
<tr><td><a href="compute2.py">compute2.py</a>, <a href="compute.py">compute.py</a></td><td>reading CoNLL-U, contracting the trees (punctuation removed), computing the flux (size, weight), segmenting the written corpora (<code>resegment</code>), ContentSUD (<code>sud_to_content(..., chains=True)</code>)</td></tr>
<tr><td><a href="fit.py">fit.py</a></td><td>maximum-likelihood fit of the power law with exponential cut-off (Nelder–Mead, SciPy)</td></tr>
<tr><td><a href="variants.py">variants.py</a></td><td>Tables 1 and 3: sentences of at least three words, <code>mod:periph</code>, illocutionary components, distributions and fits by corpus and length class → <code>variants.json</code></td></tr>
<tr><td><a href="lengths.py">lengths.py</a></td><td>Table 2: shares of short and long dependencies, observed and predicted by the fitted curve → <code>length_shares.json</code></td></tr>
<tr><td><a href="structure.py">structure.py</a></td><td>sections 4.3 and 4.4: weight on ContentSUD, pairs of disjoint dependencies by category of the governors and by relation, random orders of the same trees with the same total length, direction of the pending dependencies, bouquets (Table 4) → <code>structure.json</code></td></tr>
<tr><td><a href="bootstrap2.py">bootstrap2.py</a></td><td>standard errors by resampling the sentences (200 replicates) → <code>bootstrap2.json</code></td></tr>
<tr><td><a href="extras.py">extras.py</a></td><td>Figure 9, list of the sentences of weight 4 and 5 → <code>extras.json</code>, <code>poids4.txt</code></td></tr>
<tr><td><a href="figs.py">figs.py</a>, <a href="figs2.py">figs2.py</a>, <a href="figs_en.py">figs_en.py</a></td><td>figures (<code>FIGLANG=en</code> for the English labels)</td></tr>
<tr><td><a href="export_data.py">export_data.py</a></td><td>export of the corpora as analyzed (sentences and illocutionary components)</td></tr>
<tr><td><a href="mathdata_fr.py">mathdata_fr.py</a>, <a href="mathdata.py">mathdata.py</a></td><td>data of the <a href="../maths/index.html">Statistics</a> page</td></tr>
<tr><td><a href="make_docx.py">make_docx.py</a>, <a href="nbsp_pass.py">nbsp_pass.py</a>, <a href="build_companion.py">build_companion.py</a></td><td>docx in the journal's style, French non-breaking spaces, this site</td></tr>
<tr><td><a href="pairs_content.py">pairs_content.py</a></td><td>pairs of disjoint dependencies on ContentUD (French version of October)</td></tr>
<tr><td><a href="get_grew_corpus.py">get_grew_corpus.py</a></td><td>export of a corpus from a grew-match server (UD <code>@conv</code> versions, CEFC-gold)</td></tr>
</table>
<h2>Results</h2>
<ul>
<li><a href="../results/variants.json">variants.json</a>: for each corpus, treatment (all relations, microsyntax only, variants) and length class, the number of sentences, the means, the distributions and the fitted parameters.</li>
<li><a href="../results/length_shares.json">length_shares.json</a>: Table 2.</li>
<li><a href="../results/structure.json">structure.json</a>: Table 4 and section 4.4 (pairs, relations, occurrences, examples).</li>
<li><a href="../results/bootstrap2.json">bootstrap2.json</a>: standard errors.</li>
<li><a href="../results/extras.json">extras.json</a>, <a href="../results/pairs_content.json">pairs_content.json</a>: results of the French version of October.</li>
<li><a href="../results/poids4.txt">poids4.txt</a>: the sentences whose flux weight reaches 4 or 5.</li>
</ul>
<h2>Reproduce</h2>
<pre>python3 variants.py          # Tables 1 and 3, distributions
python3 lengths.py           # Table 2
python3 structure.py         # Table 4, section 4.4
python3 bootstrap2.py        # standard errors
python3 extras.py            # Figure 9, poids4.txt
FIGLANG=en python3 figs2.py; python3 figs_en.py
python3 make_docx.py article_en.md article_flux_spoken_written.docx</pre>
<p class="small muted">The scripts expect the corpora at the paths of <code>variants.CORPORA</code> (to be adapted), and <code>compute2.py</code>, <code>compute.py</code>, <code>fit.py</code> in the same folder.</p>"""
open(os.path.join(OUT, "code", "index.html"), "w", encoding="utf-8").write(page("Code and results", code_index, depth=1))

# ------------------------------------------------------------------ data index
tb = os.path.join(OUT, "data", "treebanks")
rows = []
for d in sorted(os.listdir(tb)):
    files = sorted(os.listdir(os.path.join(tb, d)))
    ver = open(os.path.join(tb, d, "VERSION")).read().strip() if "VERSION" in files else ""
    size = sum(os.path.getsize(os.path.join(tb, d, f)) for f in files) / 1e6
    lic = next((f for f in files if f.upper().startswith("LICENSE")), None)
    rows.append(f"<tr><td><a href=\"treebanks/{d}/\">{d}</a></td><td>{len([f for f in files if f.endswith('.conllu')])} CoNLL-U files, {size:.1f} MB</td><td>{ver}</td><td>{('<a href=\"treebanks/' + d + '/' + lic + '\">' + lic + '</a>') if lic else 'see below'}</td></tr>")
derived = sorted(f for f in os.listdir(os.path.join(OUT, "data", "derived")) if f.endswith(".conllu"))
data_index = f"""<h1>Data</h1>
<p>The corpora exactly as they were analyzed in the article, and the derived units on which the measures are computed.</p>
<h2>Source corpora</h2>
<table class="t"><tr><th>Corpus</th><th>Content</th><th>Version</th><th>Licence</th></tr>{''.join(rows)}</table>
<p class="small">GSD, ParisStories and Rhapsodie are distributed under the CC BY-SA 4.0 licence and Sequoia under LGPL-LR, by the <a href="https://surfacesyntacticud.github.io/">SUD</a> project; the <code>@conv</code> versions are their automatic conversion to UD by <a href="https://universal.grew.fr/">grew-match</a>. CEFC-gold is the reference sample of the <a href="https://www.ortolang.fr/market/corpora/cefc-orfeo">CEFC-Orféo</a> corpus; it is reproduced here as exported from grew-match so that the computations can be checked; the terms of use of the Orféo corpus apply.</p>
<h2>Sentences and illocutionary components</h2>
<p>For each corpus, the sentences of at least three words that were analyzed (GSD and Sequoia after segmentation, modifiers placed before the subject relabeled <code>mod:periph</code>) and the illocutionary components obtained by cutting the macrosyntactic dependencies (section 3.3 of the article); details in <a href="derived/README.md">derived/README.md</a>.</p>
<ul>{''.join(f'<li><a href="derived/{f}">{f}</a> ({os.path.getsize(os.path.join(OUT, "data", "derived", f)) / 1e6:.1f} MB)</li>' for f in derived)}</ul>
<p class="small muted">GitHub repository: <a href="https://github.com/typometrics/flux-oral-ecrit">typometrics/flux-oral-ecrit</a> (the same files, versioned).</p>"""
open(os.path.join(OUT, "data", "index.html"), "w", encoding="utf-8").write(page("Data", data_index, depth=1))
# directory listings for the treebank folders (GitHub Pages has no autoindex)
for d in sorted(os.listdir(tb)):
    files = sorted(os.listdir(os.path.join(tb, d)))
    lst = "".join(f'<li><a href="{f}">{f}</a> ({os.path.getsize(os.path.join(tb, d, f)) / 1e6:.2f} MB)</li>' for f in files)
    open(os.path.join(tb, d, "index.html"), "w", encoding="utf-8").write(page(d, f"<h1>{d}</h1><ul>{lst}</ul>", depth=3))

# ------------------------------------------------------------------ home
abstract = re.search(r"\*\*Abstract:\*\*\s*(.*?)\n", open(os.path.join(HERE, "article_en.md"), encoding="utf-8").read()).group(1)
home = f"""<h1>{title}</h1>
<p class="lede" style="font-family:var(--sans)">Sylvain Kahane (Modyco (CNRS), Université Paris Nanterre; IUF) and Kim Gerdes (LISN (CNRS), Université Paris-Saclay). Article for the issue of <i>Studii de lingvistică</i> on complexity, version of 23 November 2026.</p>
<p>{abstract}</p>
<div class="grid c2">
<div class="card"><h3><a href="article/index.html">The article</a></h3><p>Full text with the figures. Download: <a href="article/article_flux_spoken_written.pdf">PDF</a> · <a href="article/article_flux_spoken_written.docx">docx</a>. <a href="article/fr.html">French version of October 2026</a>.</p></div>
<div class="card"><h3><a href="data/index.html">The data</a></h3><p>The five corpora as they were analyzed (exact versions), the sentences and the illocutionary components in CoNLL-U.</p></div>
<div class="card"><h3><a href="code/index.html">The code and the results</a></h3><p>The scripts that produce the tables, the figures and the standard errors, and their outputs.</p></div>
<div class="card"><h3><a href="maths/index.html">The statistics, step by step</a></h3><p>The model <i>p</i>(<i>n</i>) ∝ <i>n</i><sup>−β</sup>e<sup>−λ<i>n</i></sup>, the fit, the standard errors and the tests, explained on the data of the article.</p></div>
</div>
<p class="small muted">This site is also available at <a href="{MIRROR}">{MIRROR}</a>. Repository: <a href="https://github.com/typometrics/flux-oral-ecrit">github.com/typometrics/flux-oral-ecrit</a>. The dependency flux: Kahane, Yan & Botalla (2017), Yan (2021).</p>"""
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page(title, home))
open(os.path.join(OUT, ".nojekyll"), "w").write("")
open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(f"""# The dependency flux as a measure of syntactic complexity: spoken and written French

Sylvain Kahane and Kim Gerdes, 2026. Companion site: {URL} (mirror: {MIRROR}).

- `article/`: the article (HTML, PDF, docx, Markdown source, figures); `article/fr.html`: the French version of October 2026
- `data/treebanks/`: the corpora in the versions analyzed (SUD French GSD, Sequoia, ParisStories, Rhapsodie, their UD conversions `@conv`, CEFC-gold)
- `data/derived/`: the sentences analyzed and their illocutionary components (CoNLL-U)
- `code/`: the Python scripts; `results/`: their outputs (JSON) and the list of the sentences of weight 4 and 5
- `maths/`: the statistics of the article explained step by step

Licences: code under the MIT licence (`LICENSE`); the corpora keep their licence (CC BY-SA 4.0 for GSD, ParisStories and Rhapsodie; LGPL-LR for Sequoia; terms of the Orféo project for CEFC-gold).
""")
open(os.path.join(OUT, "LICENSE"), "w").write("""MIT License

Copyright (c) 2026 Sylvain Kahane, Kim Gerdes

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

The data files under data/ are not covered by this licence; see data/index.html.
""")
print("companion built in", OUT)
