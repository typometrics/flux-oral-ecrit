#!/usr/bin/env python3
"""bootstrap2.py -- sentence-bootstrap standard errors for the cells of the French article (variants of variants.py):
treatments all / micro_split / periph_split, sentences of 10-19 words, SUD. The per-unit measures are computed once per
original sentence; each of the 200 replicates resamples the original sentences (so that the pieces cut out of a sentence
travel with it) and refits. Output: bootstrap2.json"""
import os
import sys
import json
import random
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from variants import CORPORA, read_sentences, resegment, units_of, measure, valid, words, MIN_WORDS, CEFC_NOMINAL, fit_tpl_mle  # noqa: E402

TREATMENTS = ("all", "micro_split", "periph_split", "micro_inplace")
NBOOT = 200


def corpus(name):
    scheme, paths, reseg = CORPORA[name]
    sents = []        # per original sentence: {treatment: [(n, flux list, weight list, len list), ...]}
    for p in paths:
        for meta, toks0 in read_sentences(p):
            if scheme == "CEFC":
                for t in toks0:
                    if t["rel"] == "periph" and t["upos"] in CEFC_NOMINAL:
                        t["rel"] = "dislocated"
            rec = {tr: [] for tr in TREATMENTS}
            for toks in (resegment(toks0) if reseg else [toks0]):
                if len(words(toks)) < MIN_WORDS or not valid(toks):
                    continue
                for tr in TREATMENTS:
                    for u, drop in units_of(toks, scheme, tr):
                        m = measure(u, drop)
                        if m and 10 <= m[0] <= 19:
                            rec[tr].append((m[1]["flux"], m[1]["weight"], m[1]["len"]))
            if any(rec.values()):
                sents.append(rec)
    rng = random.Random(7)
    full = list(range(len(sents)))
    out = {}
    for tr in TREATMENTS:
        vals = {"flux": [], "weight": [], "len": [], "mean_flux": [], "mean_weight": []}
        for b in range(NBOOT + 1):
            idx = full if b == 0 else rng.choices(full, k=len(full))
            cf, cw, cl = Counter(), Counter(), Counter()
            for i in idx:
                for fl, wt, ln in sents[i][tr]:
                    cf.update(fl)
                    cw.update(wt)
                    cl.update(ln)
            pos = sum(cf.values())
            vals["mean_flux"].append(sum(k * v for k, v in cf.items()) / pos)
            vals["mean_weight"].append(sum(k * v for k, v in cw.items()) / pos)
            for m, c in (("flux", cf), ("weight", cw), ("len", cl)):
                f = fit_tpl_mle({k: v for k, v in c.items() if k >= 1}, two_regime=False)
                vals[m].append(f["lambda"] if f else float("nan"))
        def sd(x):
            x = [v for v in x[1:] if v == v]
            mu = sum(x) / len(x)
            return (sum((v - mu) ** 2 for v in x) / (len(x) - 1)) ** 0.5
        out[tr] = {"units": sum(len(s[tr]) for s in sents), "mean_flux": vals["mean_flux"][0], "se_mean_flux": sd(vals["mean_flux"]),
                   "mean_weight": vals["mean_weight"][0], "se_mean_weight": sd(vals["mean_weight"]),
                   **{f"lambda_{m}": vals[m][0] for m in ("flux", "weight", "len")}, **{f"se_lambda_{m}": sd(vals[m]) for m in ("flux", "weight", "len")}}
    print(name, {tr: {k: round(v, 3) for k, v in o.items()} for tr, o in out.items()}, flush=True)
    return name, out


if __name__ == "__main__":
    # bootstrap2.py [corpus ...]: without arguments all corpora; results are merged into bootstrap2.json
    names = sys.argv[1:] or list(CORPORA)
    path = os.path.join(HERE, "bootstrap2.json")
    res = json.load(open(path)) if os.path.exists(path) else {}
    with ProcessPoolExecutor(min(5, len(names))) as ex:
        res.update(dict(ex.map(corpus, names)))
    json.dump(res, open(path, "w"), indent=1)
    print("written bootstrap2.json", sorted(res))
