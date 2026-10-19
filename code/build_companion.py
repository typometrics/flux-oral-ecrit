#!/usr/bin/env python3
"""
build_companion.py -- assemble the companion site of the French article in article_fr/companion/
(also the content of the GitHub repository typometrics/flux-oral-ecrit, served at https://typometrics.github.io/flux-oral-ecrit/
and mirrored at https://typometrics.elizia.net/flux-oral-ecrit/).
Run export_data.py and mathdata_fr.py first. Nothing of the unpublished flux site (other languages, English paper, reviews) is copied.
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

for d in ("article", "article/fig", "maths", "maths/data", "code", "results", "assets", "vendor"):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)

# ------------------------------------------------------------------ assets (style + helpers with a nav for this site only)
shutil.copy(os.path.join(S2, "assets", "style.css"), os.path.join(OUT, "assets", "style.css"))
shutil.copy(os.path.join(S2, "vendor", "plotly.min.js"), os.path.join(OUT, "vendor", "plotly.min.js"))
js = open(os.path.join(S2, "assets", "common.js"), encoding="utf-8").read()
js = re.sub(r"const NAV = \[.*?\];", '''const NAV = [
  ["index.html", "Accueil"],
  ["article/index.html", "Article"],
  ["maths/index.html", "Statistiques"],
  ["data/index.html", "Données"],
  ["code/index.html", "Code et résultats"],
];''', js, count=1, flags=re.S)
js = re.sub(r"const PART_A = \[.*?\];", "const PART_A = [];", js, count=1, flags=re.S)
js = js.replace('<a class="brand" href="index.html">Flux · UD/SUD 2.18</a>', '<a class="brand" href="${location.pathname.includes("/article/") || location.pathname.includes("/maths/") || location.pathname.includes("/data/") || location.pathname.includes("/code/") ? "../" : ""}index.html">Le flux de dépendance · oral et écrit</a>')
js = js.replace('`<a href="${f}" class="${(f === here || (part === "A" && inA)) ? "active" : ""}">${t}</a>`',
                '`<a href="${(location.pathname.match(/\\/(article|maths|data|code)\\//) ? "../" : "") + f}" class="${location.pathname.endsWith("/" + f) || (f === "index.html" && !location.pathname.match(/\\/(article|maths|data|code)\\//)) ? "active" : ""}">${t}</a>`')
js = re.sub(r"f\.innerHTML = `.*?`;", f'f.innerHTML = `Sylvain Kahane & Kim Gerdes · site compagnon de l\'article « Le flux de dépendance, une mesure de la complexité syntaxique{NB}: l\'oral et l\'écrit en français » · <a href="https://github.com/typometrics/flux-oral-ecrit">github.com/typometrics/flux-oral-ecrit</a>`;', js, count=1, flags=re.S)
open(os.path.join(OUT, "assets", "common.js"), "w", encoding="utf-8").write(js)
open(os.path.join(OUT, "assets", "build.js"), "w").write('window.BUILD_DATE = "2026-10-19";\n')


def page(title, body, lang="fr", depth=0, extra_head=""):
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


# ------------------------------------------------------------------ article
subprocess.run(["pandoc", "article.md", "-t", "html5", "--wrap=none", "-o", "article_body.html"], check=True, cwd=HERE)
body = open(os.path.join(HERE, "article_body.html"), encoding="utf-8").read()
for f in os.listdir(os.path.join(HERE, "fig")):
    shutil.copy(os.path.join(HERE, "fig", f), os.path.join(OUT, "article", "fig", f))
shutil.copy(os.path.join(HERE, "article_flux_oral_ecrit.docx"), os.path.join(OUT, "article", "article_flux_oral_ecrit.docx"))
shutil.copy(os.path.join(HERE, "article.md"), os.path.join(OUT, "article", "article.md"))
title = f"Le flux de dépendance, une mesure de la complexité syntaxique{NB}: l'oral et l'écrit en français"
note = (f'<div class="note" style="font-family:var(--sans)">Version soumise à <i>Studii de lingvistică</i> (numéro sur la complexité), octobre 2026. '
        f'<a href="article_flux_oral_ecrit.docx">.docx</a> · <a href="article.md">source Markdown</a> · <a href="../data/index.html">données</a> · '
        f'<a href="../code/index.html">code et résultats</a>.</div>')
open(os.path.join(OUT, "article", "index.html"), "w", encoding="utf-8").write(page(title, note + f"<h1>{title}</h1>\n" + body, depth=1))

# ------------------------------------------------------------------ maths page (from the flux site, links to unpublished pages removed)
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
open(os.path.join(OUT, "maths", "index.html"), "w", encoding="utf-8").write(m)
assert "reviews" not in m.lower().replace("statistical reviewer", "") and 'href="method.html"' not in m, "unpublished links left in maths page"

# ------------------------------------------------------------------ code and results
code_files = {HERE: ["variants.py", "bootstrap2.py", "extras.py", "pairs_content.py", "figs.py", "figs2.py", "export_data.py", "mathdata_fr.py", "nbsp_pass.py", "make_docx.py", "build_companion.py"],
              V2: ["compute2.py", "compute.py", "fit.py", "mathdata.py", "get_grew_corpus.py"]}
for d, fs in code_files.items():
    for f in fs:
        shutil.copy(os.path.join(d, f), os.path.join(OUT, "code", f))
for f in ["variants.json", "bootstrap2.json", "extras.json", "pairs_content.json"]:
    shutil.copy(os.path.join(HERE, f), os.path.join(OUT, "results", f))
shutil.copy(os.path.join(S2, "download", "poids4.txt"), os.path.join(OUT, "results", "poids4.txt"))
code_index = f"""<h1>Code et résultats</h1>
<p>Les scripts Python qui produisent les chiffres, les figures et le docx de l'article, et les fichiers de résultats qu'ils écrivent. Dépendances{NB}: Python 3, NumPy, SciPy, pandas, Matplotlib, python-docx, pandoc.</p>
<h2>Scripts</h2>
<table class="t">
<tr><th>Fichier</th><th>Rôle</th></tr>
<tr><td><a href="compute2.py">compute2.py</a>, <a href="compute.py">compute.py</a></td><td>lecture des CoNLL-U, contraction des arbres (ponctuation retirée), calcul du flux (taille, poids), segmentation de l'écrit (<code>resegment</code>), conversion SUD → ContentUD</td></tr>
<tr><td><a href="fit.py">fit.py</a></td><td>ajustement de la loi de puissance tronquée par maximum de vraisemblance (Nelder–Mead, SciPy)</td></tr>
<tr><td><a href="variants.py">variants.py</a></td><td>tableaux 1 et 2{NB}: unités d'au moins trois mots, marquage des <code>mod:periph</code>, découpage en composantes illocutoires, distributions et ajustements par corpus et par tranche de longueur → <code>variants.json</code></td></tr>
<tr><td><a href="bootstrap2.py">bootstrap2.py</a></td><td>erreurs types par rééchantillonnage des unités (200 réplicats) → <code>bootstrap2.json</code></td></tr>
<tr><td><a href="extras.py">extras.py</a></td><td>décomposition du flux (figure 8), figure 9, liste des unités de poids 4 et 5 → <code>extras.json</code>, <code>poids4.txt</code></td></tr>
<tr><td><a href="pairs_content.py">pairs_content.py</a></td><td>paires de dépendances disjointes par catégorie des gouverneurs sur ContentUD (section 4.3) → <code>pairs_content.json</code></td></tr>
<tr><td><a href="figs.py">figs.py</a>, <a href="figs2.py">figs2.py</a></td><td>figures 1 à 7</td></tr>
<tr><td><a href="export_data.py">export_data.py</a></td><td>export des corpus tels qu'analysés (unités et composantes illocutoires)</td></tr>
<tr><td><a href="mathdata_fr.py">mathdata_fr.py</a>, <a href="mathdata.py">mathdata.py</a></td><td>données de la page <a href="../maths/index.html">Statistiques</a></td></tr>
<tr><td><a href="make_docx.py">make_docx.py</a>, <a href="nbsp_pass.py">nbsp_pass.py</a>, <a href="build_companion.py">build_companion.py</a></td><td>docx selon la feuille de style de la revue, espaces insécables, construction de ce site</td></tr>
<tr><td><a href="get_grew_corpus.py">get_grew_corpus.py</a></td><td>export d'un corpus depuis un serveur grew-match (versions UD <code>@conv</code>, CEFC-gold)</td></tr>
</table>
<h2>Résultats</h2>
<ul>
<li><a href="../results/variants.json">variants.json</a>{NB}: pour chaque corpus, traitement (toutes les relations, microsyntaxe seule, variantes) et tranche de longueur, le nombre d'unités, les moyennes, les distributions et les paramètres ajustés (β, λ).</li>
<li><a href="../results/bootstrap2.json">bootstrap2.json</a>{NB}: erreurs types du tableau 2.</li>
<li><a href="../results/extras.json">extras.json</a>{NB}: décomposition du flux par nature des dépendances.</li>
<li><a href="../results/pairs_content.json">pairs_content.json</a>{NB}: paires disjointes sur ContentUD, en positions et en paires distinctes.</li>
<li><a href="../results/poids4.txt">poids4.txt</a>{NB}: les unités dont le poids du flux atteint 4 ou 5.</li>
</ul>
<h2>Reproduire</h2>
<pre>python3 variants.py          # tableaux 1-2, distributions
python3 bootstrap2.py        # erreurs types
python3 extras.py            # figures 8-9, poids4.txt
python3 pairs_content.py     # section 4.3
python3 figs.py; python3 figs2.py
python3 make_docx.py         # article.md -> docx</pre>
<p class="small muted">Les scripts attendent les corpus dans les chemins de <code>variants.CORPORA</code> (à adapter) et <code>compute2.py</code>, <code>fit.py</code> dans le même dossier.</p>"""
open(os.path.join(OUT, "code", "index.html"), "w", encoding="utf-8").write(page("Code et résultats", code_index, depth=1))

# ------------------------------------------------------------------ data index
tb = os.path.join(OUT, "data", "treebanks")
rows = []
for d in sorted(os.listdir(tb)):
    files = sorted(os.listdir(os.path.join(tb, d)))
    ver = open(os.path.join(tb, d, "VERSION")).read().strip() if "VERSION" in files else ""
    size = sum(os.path.getsize(os.path.join(tb, d, f)) for f in files) / 1e6
    lic = next((f for f in files if f.upper().startswith("LICENSE")), None)
    rows.append(f"<tr><td><a href=\"treebanks/{d}/\">{d}</a></td><td>{len([f for f in files if f.endswith('.conllu')])} fichiers CoNLL-U, {size:.1f}{NB}Mo</td><td>{ver}</td><td>{('<a href=\"treebanks/' + d + '/' + lic + '\">' + lic + '</a>') if lic else 'voir ci-dessous'}</td></tr>")
derived = sorted(f for f in os.listdir(os.path.join(OUT, "data", "derived")) if f.endswith(".conllu"))
data_index = f"""<h1>Données</h1>
<p>Les corpus exactement tels qu'ils ont été analysés dans l'article, et les unités dérivées sur lesquelles portent les mesures.</p>
<h2>Corpus sources</h2>
<table class="t"><tr><th>Corpus</th><th>Contenu</th><th>Version</th><th>Licence</th></tr>{''.join(rows)}</table>
<p class="small">GSD, ParisStories et Rhapsodie sont distribués sous licence CC BY-SA 4.0 et Sequoia sous LGPL-LR, par le projet <a href="https://surfacesyntacticud.github.io/">SUD</a>{NB}; les versions <code>@conv</code> sont leur conversion automatique en UD par <a href="https://universal.grew.fr/">grew-match</a>. CEFC-gold est l'échantillon de référence du corpus <a href="https://www.ortolang.fr/market/corpora/cefc-orfeo">CEFC-Orféo</a>{NB}; il est reproduit ici tel qu'exporté de grew-match pour permettre la vérification des calculs{NB}; les conditions d'utilisation du corpus Orféo s'appliquent.</p>
<h2>Unités et composantes illocutoires</h2>
<p>Pour chaque corpus, les unités d'au moins trois mots analysées (GSD et Sequoia après segmentation, modifieurs antéposés au sujet réétiquetés <code>mod:periph</code>) et les composantes illocutoires obtenues en coupant les dépendances macrosyntaxiques (section 3.2 de l'article){NB}; détails dans <a href="derived/README.md">derived/README.md</a>.</p>
<ul>{''.join(f'<li><a href="derived/{f}">{f}</a> ({os.path.getsize(os.path.join(OUT, "data", "derived", f)) / 1e6:.1f}{NB}Mo)</li>' for f in derived)}</ul>
<p class="small muted">Dépôt GitHub{NB}: <a href="https://github.com/typometrics/flux-oral-ecrit">typometrics/flux-oral-ecrit</a> (les mêmes fichiers, versionnés).</p>"""
open(os.path.join(OUT, "data", "index.html"), "w", encoding="utf-8").write(page("Données", data_index, depth=1))
# directory listings for the treebank folders (GitHub Pages has no autoindex)
for d in sorted(os.listdir(tb)):
    files = sorted(os.listdir(os.path.join(tb, d)))
    lst = "".join(f'<li><a href="{f}">{f}</a> ({os.path.getsize(os.path.join(tb, d, f)) / 1e6:.2f}{NB}Mo)</li>' for f in files)
    open(os.path.join(tb, d, "index.html"), "w", encoding="utf-8").write(page(d, f"<h1>{d}</h1><ul>{lst}</ul>", depth=3))

# ------------------------------------------------------------------ home
abstract = re.search(r"\*\*Résumé\s*:\*\*\s*(.*?)\n", open(os.path.join(HERE, "article.md"), encoding="utf-8").read()).group(1)
home = f"""<h1>{title}</h1>
<p class="lede" style="font-family:var(--sans)">Sylvain Kahane (Université Paris Nanterre, Modyco, CNRS{NB}; IUF) et Kim Gerdes (Université Paris-Saclay, CNRS, LISN). Article pour le numéro de <i>Studii de lingvistică</i> sur la complexité, octobre 2026.</p>
<p>{abstract}</p>
<div class="grid c2">
<div class="card"><h3><a href="article/index.html">L'article</a></h3><p>Texte intégral avec les figures{NB}; <a href="article/article_flux_oral_ecrit.docx">docx</a>.</p></div>
<div class="card"><h3><a href="data/index.html">Les données</a></h3><p>Les cinq corpus tels qu'ils ont été analysés (versions exactes), les unités et les composantes illocutoires en CoNLL-U.</p></div>
<div class="card"><h3><a href="code/index.html">Le code et les résultats</a></h3><p>Les scripts qui produisent les tableaux, les figures et les erreurs types, et leurs sorties.</p></div>
<div class="card"><h3><a href="maths/index.html">Les statistiques, pas à pas</a></h3><p>Le modèle <i>p</i>(<i>n</i>) ∝ <i>n</i><sup>−β</sup>e<sup>−λ<i>n</i></sup>, l'ajustement, les erreurs types et les tests, expliqués sur les données de l'article (en anglais).</p></div>
</div>
<p class="small muted">Ce site est aussi disponible sur <a href="{MIRROR}">{MIRROR}</a>. Dépôt{NB}: <a href="https://github.com/typometrics/flux-oral-ecrit">github.com/typometrics/flux-oral-ecrit</a>. Le flux de dépendance{NB}: Kahane, Yan & Botalla (2017), Yan (2021).</p>"""
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page(title, home))
open(os.path.join(OUT, ".nojekyll"), "w").write("")
open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write(f"""# Le flux de dépendance, une mesure de la complexité syntaxique : l'oral et l'écrit en français

Sylvain Kahane et Kim Gerdes, 2026. Site compagnon : {URL} (miroir : {MIRROR}).

- `article/` : l'article (HTML, docx, source Markdown, figures)
- `data/treebanks/` : les corpus aux versions analysées (SUD French GSD, Sequoia, ParisStories, Rhapsodie, leurs conversions UD `@conv`, CEFC-gold)
- `data/derived/` : les unités illocutoires analysées et leurs composantes illocutoires (CoNLL-U)
- `code/` : les scripts Python ; `results/` : leurs sorties (JSON) et la liste des unités de poids 4 et 5
- `maths/` : les statistiques de l'article expliquées pas à pas (en anglais)

Licences : code sous licence MIT (`LICENSE`) ; les corpus gardent leur licence (CC BY-SA 4.0 pour GSD, ParisStories et Rhapsodie ; LGPL-LR pour Sequoia ; conditions du projet Orféo pour CEFC-gold).
""")
open(os.path.join(OUT, "LICENSE"), "w").write("""MIT License

Copyright (c) 2026 Sylvain Kahane, Kim Gerdes

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

The data files under data/ are not covered by this licence; see data/index.html.
""")
print("companion built in", OUT)
