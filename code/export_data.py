#!/usr/bin/env python3
"""
export_data.py OUTDIR -- the data of the French article, as used, for the companion site:
  treebanks/   the four SUD treebanks at the commits used (CoNLL-U, LICENSE, README, VERSION), their official UD conversion (@conv),
               and CEFC-gold as exported from grew-match (with the periph relabelling applied by the article in a separate file)
  derived/     per corpus, CoNLL-U of (a) the illocutionary units analysed (>= 3 words; GSD and Sequoia re-segmented; mod:periph
               relabelled; CEFC nominal periph -> dislocated) and (b) the illocutionary components (macro-syntactic segments cut out,
               pieces of >= 3 words kept as units, smaller pieces dropped), all columns of the source kept, ids renumbered.
"""
import os
import sys
import glob
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from variants import CORPORA, FL, mark_periph, split_macro, words, valid, MIN_WORDS, MACRO, MACRO_CEFC, CEFC_NOMINAL, PM  # noqa: E402
from compute2 import resegment, is_punct  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "companion")


def read_full(path):
    """like compute2.read_sentences, but every token keeps its full column list in "cols" and the comment lines in meta["_lines"]"""
    toks, meta, lines = [], {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                if toks:
                    meta["_lines"] = lines
                    yield meta, toks
                toks, meta, lines = [], {}, []
                continue
            if line.startswith("#"):
                lines.append(line)
                if "=" in line:
                    k, v = line[1:].split("=", 1)
                    meta[k.strip()] = v.strip()
                continue
            c = line.split("\t")
            if len(c) < 8 or not c[0].isdigit():
                continue
            try:
                h = int(c[6])
            except ValueError:
                h = -1
            toks.append({"id": int(c[0]), "form": c[1], "upos": c[3], "feats": c[5], "head": h, "rel": c[7].split("@")[0], "cols": c})
    if toks:
        meta["_lines"] = lines
        yield meta, toks


def conllu(toks, sid, text_comment=True):
    out = [f"# sent_id = {sid}"]
    if text_comment:
        out.append("# text = " + " ".join(t["form"] for t in toks))
    for t in toks:
        c = list(t["cols"]) + ["_"] * max(0, 10 - len(t["cols"]))
        c[0], c[6], c[7] = str(t["id"]), str(t["head"]), ("mod:periph" if t["rel"] == PM else t["rel"])
        out.append("\t".join(c))
    return "\n".join(out) + "\n\n"


def main():
    tb = os.path.join(OUT, "data", "treebanks")
    dv = os.path.join(OUT, "data", "derived")
    os.makedirs(tb, exist_ok=True)
    os.makedirs(dv, exist_ok=True)
    for name in ("GSD", "Sequoia", "ParisStories", "Rhapsodie"):
        src = os.path.join(FL, f"SUD_French-{name}")
        dst = os.path.join(tb, f"SUD_French-{name}")
        os.makedirs(dst, exist_ok=True)
        for f in glob.glob(os.path.join(src, "*.conllu")) + glob.glob(os.path.join(src, "LICENSE*")) + glob.glob(os.path.join(src, "README*")):
            shutil.copy(f, dst)
        h = subprocess.run(["git", "-C", src, "log", "-1", "--format=%H %ci"], capture_output=True, text=True).stdout.strip()
        open(os.path.join(dst, "VERSION"), "w").write(f"https://github.com/surfacesyntacticud/SUD_French-{name} commit {h}\n")
        cdst = os.path.join(tb, f"UD_French-{name}@conv")
        os.makedirs(cdst, exist_ok=True)
        for f in glob.glob(os.path.join(FL, f"UD_French-{name}@conv", "*.conllu")):
            shutil.copy(f, cdst)
        open(os.path.join(cdst, "VERSION"), "w").write(f"automatic UD conversion of SUD_French-{name} (commit above) by grew-match, corpus UD_French-{name}@conv, downloaded 2026-10-16\n")
    cdst = os.path.join(tb, "CEFC-gold")
    os.makedirs(cdst, exist_ok=True)
    shutil.copy(os.path.join(FL, "cefc-gold.conllu"), cdst)
    open(os.path.join(cdst, "VERSION"), "w").write("cefc-gold as exported from https://gmd-orfeo.grew.fr (corpus cefc-gold), 2026-10-10. Orféo project (Benzitoun, Debaisieux & Deulofeu 2016).\n")
    # derived units and components
    stats = {}
    for name, (scheme, paths, reseg) in CORPORA.items():
        macro = (MACRO_CEFC if scheme == "CEFC" else MACRO) | {PM}
        fu = open(os.path.join(dv, f"{name}_unites_illocutoires.conllu"), "w", encoding="utf-8")
        fc = open(os.path.join(dv, f"{name}_composantes_illocutoires.conllu"), "w", encoding="utf-8")
        nu = nc = 0
        for p in paths:
            for meta, toks0 in read_full(p):
                sid = meta.get("sent_id", "")
                if scheme == "CEFC":
                    for t in toks0:
                        if t["rel"] == "periph" and t["upos"] in CEFC_NOMINAL:
                            t["rel"] = "dislocated"
                            t["cols"][7] = "dislocated"
                pieces = resegment(toks0) if reseg else [toks0]
                for k, toks in enumerate(pieces):
                    if len(words(toks)) < MIN_WORDS or not valid(toks):
                        continue
                    usid = sid if len(pieces) == 1 else f"{sid}.{k + 1}"
                    marked = mark_periph(toks, scheme)
                    fu.write(conllu(marked, usid))
                    nu += 1
                    for j, comp in enumerate(split_macro(marked, macro)):
                        if len(words(comp)) < MIN_WORDS or not valid(comp):
                            continue
                        fc.write(conllu(comp, f"{usid}.c{j + 1}"))
                        nc += 1
        fu.close()
        fc.close()
        stats[name] = (nu, nc)
        print(name, "units", nu, "components", nc, flush=True)
    open(os.path.join(dv, "README.md"), "w", encoding="utf-8").write(
        "# Unités et composantes illocutoires\n\n"
        "Pour chaque corpus, deux fichiers CoNLL-U, ponctuation conservée, colonnes de la source conservées, identifiants renumérotés :\n\n"
        "- `*_unites_illocutoires.conllu` : les unités d'au moins trois mots analysées dans l'article (GSD et Sequoia après segmentation des coordinations "
        "et parataxes de propositions principales, `sent_id` suffixé `.1`, `.2`… ; les modifieurs antéposés au sujet réétiquetés `mod:periph` ; dans CEFC-gold, "
        "les `periph` nominaux réétiquetés `dislocated`).\n"
        "- `*_composantes_illocutoires.conllu` : les composantes obtenues en coupant les dépendances macrosyntaxiques (`discourse`, `dislocated`, `vocative`, "
        "`parataxis`, `mod:periph` ; CEFC-gold : `dm`, `parenth`, `periph`) ; un segment détaché d'au moins trois mots devient une composante (`sent_id` suffixé "
        "`.c2`, `.c3`…), un segment plus court est retiré ; la composante hôte porte le suffixe `.c1`.\n\n"
        + "".join(f"- {n} : {u} unités, {c} composantes\n" for n, (u, c) in stats.items()))


if __name__ == "__main__":
    main()
