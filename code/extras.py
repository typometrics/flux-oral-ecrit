#!/usr/bin/env python3
"""
extras.py -- after Sylvain's comments of 11 October (evening), section 4:
  decomposition   flux per position by nature of the dependency (nominal / macro incl. mod:periph / reparandum / other),
                  10-19 words, all relations  -> fig/fig4_decomposition.png and extras.json
  pairs           disjoint pairs by governor category observed vs expected under independence (NV = 2 sqrt(NN.VV))
  examples        short units with two disjoint noun-governed (written) or verb-governed (spoken) dependencies
  weight4         every unit (all relations, SUD) whose flux weight reaches 4 or 5, for manual checking -> ../v218/site2/download/poids4.txt
  macro figure    the ParisStories utterance of the article (fig 9) redrawn: flux row, and micro row only where the vault is micro
"""
import os
import sys
import json
import glob
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from variants import CORPORA, read_sentences, resegment, words, valid, mark_periph, measure, base, MACRO, MACRO_CEFC, CEFC_NOMINAL, PM  # noqa: E402
from compute2 import contract, is_punct  # noqa: E402
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from figs2 import draw_tree, COL, NAME, RED  # noqa: E402

NOMINAL_UPOS = {"NOUN", "PROPN", "PRON", "NOM", "PRO", "PRQ", "CLS", "CLI", "CLN", "CLO"}
VERB_UPOS = {"VERB", "AUX", "VRB", "VNF", "VPP", "VPR"}
OUT = {"decomposition": {}, "pairs": {}, "examples": {"NN": [], "VV": []}, "weight4": {}}


def nominal_govs(heads, upos):
    """words dominated by (or equal to) a nominal, without crossing a verb on the way up (1-based lists, heads[0] unused)"""
    n = len(heads) - 1
    res = [False] * (n + 1)
    for w in range(1, n + 1):
        x = w
        steps = 0
        while x and steps <= n:
            if upos[x] in NOMINAL_UPOS:
                res[w] = True
                break
            if upos[x] in VERB_UPOS:
                break
            x = heads[x]
            steps += 1
    return res


def unit_items(toks, scheme):
    """(n, heads, upos, rel, forms) of a unit with all relations, mod:periph marked; None if unusable"""
    t = mark_periph(toks, scheme)
    w = words(t)
    if len(w) < 3 or not valid(t):
        return None
    hd = {x["id"]: x["head"] for x in t}
    hv, order = contract(hd, {x["id"] for x in w})
    if hv is None:
        return None
    bt = {x["id"]: x for x in t}
    return len(w), hv, [None] + [bt[o]["upos"] for o in order], [None] + [bt[o]["rel"] for o in order], [None] + [bt[o]["form"] for o in order]


def crossing(hv, i):
    return [(min(d, hv[d]), max(d, hv[d]), d) for d in range(1, len(hv)) if hv[d] and min(d, hv[d]) <= i < max(d, hv[d])]


def main():
    for name, (scheme, paths, reseg) in CORPORA.items():
        macro = (MACRO_CEFC if scheme == "CEFC" else MACRO) | {PM}
        rep = {"disflink"} if scheme == "CEFC" else {"reparandum"}
        dec = Counter()
        pairs = Counter()
        w4 = []
        for p in paths:
            for meta, toks0 in read_sentences(p):
                if scheme == "CEFC":
                    for t in toks0:
                        if t["rel"] == "periph" and t["upos"] in CEFC_NOMINAL:
                            t["rel"] = "dislocated"
                for toks in (resegment(toks0) if reseg else [toks0]):
                    it = unit_items(toks, scheme)
                    if it is None:
                        continue
                    n, hv, upos, rel, forms = it
                    m = measure(toks)
                    if m:
                        mw = max(m[1]["weight"])
                        if mw >= 4:
                            w4.append((meta.get("sent_id", ""), n, mw, " ".join(forms[1:])))
                    if not (10 <= n <= 19):
                        continue
                    nomg = nominal_govs(hv, upos)
                    for i in range(1, n):
                        cr = crossing(hv, i)
                        dec["positions"] += 1
                        for lo, hi, d in cr:
                            b = base(rel[d])
                            if b in macro:
                                dec["macro"] += 1
                            elif b in rep:
                                dec["rep"] += 1
                            elif nomg[hv[d]]:
                                dec["nominal"] += 1
                            else:
                                dec["other"] += 1
                        # disjoint pairs by governor category (all relations)
                        govs = []
                        for lo, hi, d in cr:
                            g = hv[d]
                            cat = "N" if upos[g] in NOMINAL_UPOS else ("V" if upos[g] in VERB_UPOS else "O")
                            govs.append((lo, hi, d, g, cat))
                        seen = set()
                        for a in range(len(govs)):
                            for b2 in range(a + 1, len(govs)):
                                x, y = govs[a], govs[b2]
                                if {x[2], x[3]} & {y[2], y[3]}:
                                    continue
                                key = "".join(sorted(x[4] + y[4]))
                                if key in ("NN", "VV", "NV"):
                                    seen.add(key)
                        for key in seen:
                            pairs[key] += 1
                            if len(OUT["examples"].get(key, [])) < 12 and n <= 14 and ((key == "NN" and reseg) or (key == "VV" and not reseg and scheme == "SUD")):
                                ex = [(x[2], x[3]) for x in govs if x[4] == key[0]]
                                OUT["examples"][key].append({"corpus": name, "sent_id": meta.get("sent_id", ""), "forms": forms[1:], "upos": upos[1:], "heads": hv[1:], "rel": rel[1:],
                                                             "position": i, "pairs": ex})
        P = dec["positions"]
        OUT["decomposition"][name] = {k: dec[k] / P for k in ("nominal", "macro", "rep", "other")}
        OUT["decomposition"][name]["flux"] = sum(OUT["decomposition"][name].values())
        NN, VV, NV = (100 * pairs[k] / P for k in ("NN", "VV", "NV"))
        OUT["pairs"][name] = {"NN": NN, "VV": VV, "NV": NV, "NV_expected": 2 * (NN * VV) ** 0.5, "ratio": NV / (2 * (NN * VV) ** 0.5)}
        OUT["weight4"][name] = w4
        print(name, {k: round(v, 3) for k, v in OUT["decomposition"][name].items()}, {k: round(v, 2) for k, v in OUT["pairs"][name].items()}, "weight>=4:", len(w4), flush=True)
    # ------------------------------------------------------------- figure 8 (decomposition)
    labs, nom, other, rp, mac = [], [], [], [], []
    for u in CORPORA:
        d = OUT["decomposition"][u]
        labs.append(NAME[u]); nom.append(d["nominal"]); other.append(d["other"]); rp.append(d["rep"]); mac.append(d["macro"])
    fig, ax = plt.subplots(figsize=(6.0, 2.6))
    x = np.arange(len(labs))
    ax.bar(x, nom, color="#6aa0d8", label="dans un groupe nominal")
    ax.bar(x, other, bottom=nom, color="#9a9a9a", label="autres (microsyntaxe)")
    ax.bar(x, rp, bottom=np.array(nom) + np.array(other), color="#e59a3a", label="reparandum")
    ax.bar(x, mac, bottom=np.array(nom) + np.array(other) + np.array(rp), color="#b8452a", label="macrosyntaxe (mod:periph compris)")
    ax.set_xticks(x, labs)
    ax.set_ylabel("dépendances par position")
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    ax.set_ylim(0, 2.6)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig", "fig4_decomposition.png"))
    plt.close(fig)
    # ------------------------------------------------------------- weight >= 4 list for manual checking
    with open(os.path.join(HERE, "..", "v218", "site2", "download", "poids4.txt"), "w", encoding="utf-8") as f:
        f.write("Unités dont le poids du flux atteint 4 ou 5 (SUD, toutes les relations, unités d'au moins 3 mots ; GSD et Sequoia segmentés). "
                "Colonnes : corpus, sent_id, longueur, poids maximal, texte.\n")
        for u, rows in OUT["weight4"].items():
            for sid, n, mw, txt in sorted(rows, key=lambda r: (-r[2], r[1])):
                f.write(f"{u}\t{sid}\t{n}\t{mw}\t{txt}\n")
    # ------------------------------------------------------------- figure 9 (macro example, vault-based micro row)
    E = json.load(open(os.path.join(HERE, "..", "v218", "results2", "examples2.json")))
    e = next(x for x in E["french"] if x["corpus"] == "French-ParisStories@latest" and x["profile"] == "macro")
    toks = []
    for line in e["conll"].strip().split("\n"):
        c = line.split("\t")
        toks.append({"id": int(c[0]), "form": c[1], "upos": c[3], "head": int(c[6]), "rel": c[7], "feats": ""})
    it = unit_items(toks, "SUD")
    n, hv, upos, rel, forms = it
    macro = MACRO | {PM}
    flux_row, micro_row = [], []
    for i in range(1, n):
        cr = crossing(hv, i)
        flux_row.append(str(len(cr)))
        vault = min(cr, key=lambda a: a[1] - a[0])
        if base(rel[vault[2]]) in macro:
            micro_row.append("–")
        else:
            micro_row.append(str(sum(1 for lo, hi, d in cr if base(rel[d]) not in macro)))
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    rel_disp = ["mod:periph" if r == PM else r for r in rel[1:]]
    cols = {d: ("#b8452a" if base(rel[d]) in macro else ("#6aa0d8" if base(rel[d]) == "det" else "black")) for d in range(1, n + 1)}
    pos = draw_tree(ax, forms[1:], upos[1:], hv[1:], rel_disp, colors=cols, rows=[("flux", flux_row, "#b5651d"), ("micro", micro_row, "#2a7f62")])
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig", "fig_macro.png"))
    plt.close(fig)
    OUT["macro_example"] = {"sent_id": e["sent_id"], "forms": forms[1:], "rel": rel[1:], "flux": flux_row, "micro": micro_row}
    print("macro example:", " ".join(forms[1:]), flux_row, micro_row)
    json.dump(OUT, open(os.path.join(HERE, "extras.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
