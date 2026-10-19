#!/usr/bin/env python3
"""
mathdata_fr.py -- math.json for the companion site of the French article, computed on the data of the article
(variants.json: units >= 3 words, written corpora re-segmented; "micro" = microsyntax only, macro-syntactic segments cut out;
bootstrap2.json for the standard errors; ContentUD of the re-segmented written corpora for the total variation).
Same output structure as v218/mathdata.py, so site2/math.html can read it. Output: companion/maths/data/math.json
"""
import os
import sys
import json
import collections
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import logsumexp
from scipy.stats import chi2, chi2_contingency

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = "/bigstorage/kim/typometrics/dataanalysis/flux/v218"
sys.path.insert(0, V2)
sys.path.insert(0, HERE)
import mathdata as MD  # noqa: E402  (alt_families, arrays, fit helpers)
from fit import fit_tpl_mle, _nll_tpl  # noqa: E402
from variants import CORPORA, read_sentences, resegment, units_of, measure, valid, words, MIN_WORDS, CEFC_NOMINAL  # noqa: E402

V = json.load(open(os.path.join(HERE, "variants.json")))
B2 = json.load(open(os.path.join(HERE, "bootstrap2.json")))
TR = {"all": "all", "micro": "periph_split"}
METRICS = ("len", "flux", "weight")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "companion", "maths", "data", "math.json")


def dist(name, filt, metric):
    d = V["dists"].get(f"{name}|{TR[filt]}|10-19")
    return {int(k): int(v) for k, v in d[metric] if k >= 1} if d else None


def main():
    M = {"bin": "10-19", "corpora": list(CORPORA), "dists": {}, "fits": {}, "note": "data of the French article: units of 3+ words, written corpora re-segmented; micro = microsyntax only (macro-syntactic segments cut out)"}
    for name in CORPORA:
        for filt in ("all", "micro"):
            for m in METRICS:
                d = dist(name, filt, m)
                if not d:
                    continue
                key = f"{name}|{filt}|{m}"
                M["dists"][key] = sorted(d.items())
                t = fit_tpl_mle(d, two_regime=False)
                M["fits"][key] = {k: t[k] for k in ("n", "xmax", "beta", "lambda", "nll", "se_beta", "se_lambda", "aic_tpl", "aic_pl", "aic_exp", "beta_pl", "lambda_exp")}
                M["fits"][key]["mean"] = float(sum(k * v for k, v in d.items()) / sum(d.values()))
    # landscape, profile, nmax, families, ratios: as in mathdata.py, on GSD / ParisStories flux of the article's data
    d = dist("GSD", "all", "flux")
    xs, cs = MD.arrays(d)
    sup = np.arange(1, int(xs.max()) + 1, dtype=float)
    t = M["fits"]["GSD|all|flux"]
    betas, lams = np.linspace(-8, 3, 56), np.linspace(0, 5, 51)
    M["grid"] = {"unit": "GSD", "metric": "flux", "beta": [round(float(b), 3) for b in betas], "lambda": [round(float(l), 3) for l in lams],
                 "dnll": [[round(min(_nll_tpl((b, l), xs, cs, sup) - t["nll"], 1e6), 2) for b in betas] for l in lams], "beta_hat": t["beta"], "lambda_hat": t["lambda"]}

    def prof(lam):
        return minimize_scalar(lambda b: _nll_tpl((b, lam), xs, cs, sup), bounds=(-20, 10), method="bounded").fun - t["nll"]
    lgrid = np.linspace(t["lambda"] - 0.3, t["lambda"] + 0.3, 121)
    pv = [prof(l) for l in lgrid]
    inside = [l for l, v in zip(lgrid, pv) if v <= 1.9207]
    M["profile"] = {"lambda": [round(float(l), 4) for l in lgrid], "dnll": [round(float(v), 3) for v in pv], "ci95": [round(float(min(inside)), 3), round(float(max(inside)), 3)], "se_hessian": t["se_lambda"]}
    M["nmax"] = {}
    for name, metric in (("GSD", "flux"), ("ParisStories", "flux"), ("GSD", "len")):
        dd = dist(name, "all", metric)
        obs = max(dd)
        rows = []
        for xm in sorted({obs, 12, 15, 20, 40, 80}):
            if xm >= obs:
                f = fit_tpl_mle(dd, two_regime=False, xmax=xm)
                rows.append({"xmax": xm, "beta": f["beta"], "lambda": f["lambda"], "mode": (-f["beta"] / f["lambda"]) if f["lambda"] > 0 else None})
        M["nmax"][f"{name}|{metric}"] = {"observed_max": obs, "rows": rows}
    M["families"], M["ratios"] = {}, {}
    for name in ("GSD", "ParisStories"):
        for m in METRICS:
            dd = dist(name, "all", m)
            fam, xmax = MD.alt_families(dd)
            M["families"][f"{name}|{m}"] = {"xmax": xmax, "n": int(sum(dd.values())),
                                             "models": {k: {kk: (vv if kk != "p" else [round(x, 7) for x in vv]) for kk, vv in v.items()} for k, v in fam.items()}}
            tot = sum(dd.values())
            emp = {n: dd.get(n, 0) / tot for n in range(1, xmax + 1)}
            bt, lm = fam["tpl"]["params"]["beta"], fam["tpl"]["params"]["lambda"]
            M["ratios"][f"{name}|{m}"] = [{"n": n, "p": emp[n], "emp": (emp[n + 1] / emp[n]) if emp[n] else None, "tpl": float(((n + 1) / n) ** (-bt) * np.exp(-lm))} for n in range(1, min(xmax, 8))]
    M["lrtests"] = []
    for a, b in (("GSD", "Sequoia"), ("GSD", "ParisStories"), ("ParisStories", "Rhapsodie"), ("Sequoia", "ParisStories"), ("GSD", "CEFC")):
        for filt, m in (("all", "flux"), ("micro", "flux"), ("all", "weight"), ("micro", "weight")):
            da, db = dist(a, filt, m), dist(b, filt, m)
            fa, fb = fit_tpl_mle(da, two_regime=False), fit_tpl_mle(db, two_regime=False)
            pooled = collections.Counter(da)
            pooled.update(db)
            fp = fit_tpl_mle(dict(pooled), two_regime=False)
            lr = 2 * (fp["nll"] - fa["nll"] - fb["nll"])
            M["lrtests"].append({"a": a, "b": b, "filter": filt, "metric": m, "lambda_a": fa["lambda"], "lambda_b": fb["lambda"], "beta_a": fa["beta"], "beta_b": fb["beta"],
                                 "lambda_pooled": fp["lambda"], "LR": lr, "p": float(chi2.sf(lr, 2)), "n_a": fa["n"], "n_b": fb["n"]})
    # total variation on ContentUD weight, written corpora re-segmented (results2 dists)
    R = os.path.join(V2, "results2", "dists")
    W = {}
    for name, u in (("GSD", "French-GSD@reseg"), ("Sequoia", "French-Sequoia@reseg"), ("ParisStories", "French-ParisStories@latest"), ("Rhapsodie", "French-Rhapsodie@latest")):
        D = json.load(open(f"{R}/treebank__{u}.json"))["dists"]
        W[name] = {int(k): int(v) for k, v in D["ContentUD|all|obs|10-19|weight"] if k >= 1}
    vals = sorted({k for d in W.values() for k in d})
    shares = {n: [d.get(v, 0) / sum(d.values()) for v in vals] for n, d in W.items()}
    sizes = {n: sum(d.values()) for n, d in W.items()}
    tv = lambda p, q: 0.5 * sum(abs(x - y) for x, y in zip(p, q))
    pairs = [(a, b, tv(shares[a], shares[b])) for i, a in enumerate(W) for b in list(W)[i + 1:]]
    pooled = np.array([sum(d.get(v, 0) for d in W.values()) for v in vals], dtype=float)
    pooled /= pooled.sum()
    rng = np.random.default_rng(1)
    sims = {}
    for a, b, _ in pairs:
        tt = [tv(rng.multinomial(sizes[a], pooled) / sizes[a], rng.multinomial(sizes[b], pooled) / sizes[b]) for _ in range(3000)]
        sims[f"{a}|{b}"] = {"mean": float(np.mean(tt)), "q95": float(np.quantile(tt, 0.95)), "q99": float(np.quantile(tt, 0.99))}
    table = [[d.get(1, 0), d.get(2, 0), sum(v for k, v in d.items() if k >= 3)] for d in W.values()]
    c2, p, dof, _ = chi2_contingency(table)
    N = sum(map(sum, table))
    M["tv"] = {"values": vals, "shares": shares, "sizes": sizes, "pairs": pairs, "sims": sims,
               "chi2": {"stat": float(c2), "p": float(p), "dof": int(dof), "cramers_v": float(np.sqrt(c2 / (N * (min(len(table), 3) - 1)))), "table": table}}
    # bootstrap (bootstrap2.json) in the shape math.html expects
    M["bootstrap"] = {}
    for c in CORPORA:
        M["bootstrap"][c] = {}
        for filt in ("all", "micro"):
            o = B2[c][TR[filt]]
            for m in METRICS:
                M["bootstrap"][c][f"{filt}|{m}"] = {"lambda": o[f"lambda_{m}"], "se_lambda": o[f"se_lambda_{m}"],
                                                    "mean": o["mean_flux"] if m != "weight" else o["mean_weight"],
                                                    "se_mean": o["se_mean_flux"] if m != "weight" else o["se_mean_weight"]}
    M["ols"], M["random"] = {}, {}
    # mean flux by exact length, units and components of the article
    M["bylength"] = {}
    for name, (scheme, paths, reseg) in CORPORA.items():
        acc = {tr: collections.defaultdict(lambda: {"units": 0, "pos": 0, "flux": 0.0, "weight": 0.0}) for tr in ("all", "periph_split")}
        for p in paths:
            for meta, toks0 in read_sentences(p):
                if scheme == "CEFC":
                    for t in toks0:
                        if t["rel"] == "periph" and t["upos"] in CEFC_NOMINAL:
                            t["rel"] = "dislocated"
                for toks in (resegment(toks0) if reseg else [toks0]):
                    if len(words(toks)) < MIN_WORDS or not valid(toks):
                        continue
                    for tr in acc:
                        for u, drop in units_of(toks, scheme, tr):
                            mm = measure(u, drop)
                            if mm and 10 <= mm[0] <= 19:
                                a = acc[tr][mm[0]]
                                a["units"] += 1
                                a["pos"] += len(mm[1]["flux"])
                                a["flux"] += sum(mm[1]["flux"])
                                a["weight"] += sum(mm[1]["weight"])
        rows = {}
        for n in range(10, 20):
            a, b = acc["all"][n], acc["periph_split"][n]
            rows[n] = {"units": a["units"], "flux": a["flux"] / a["pos"] if a["pos"] else None, "micro": b["flux"] / b["pos"] if b["pos"] else None,
                       "weight": a["weight"] / a["pos"] if a["pos"] else None, "wmicro": b["weight"] / b["pos"] if b["pos"] else None}
        tu = sum(a["units"] for a in acc["all"].values())
        M["bylength"][name] = {"rows": rows, "mean_len": sum(n * a["units"] for n, a in acc["all"].items()) / tu, "units": tu}
        print(name, "mean length in bin", round(M["bylength"][name]["mean_len"], 2), flush=True)

    def rnd(o):
        if isinstance(o, float):
            return None if (o != o or o in (float("inf"), float("-inf"))) else round(o, 6)
        if isinstance(o, dict):
            return {str(k): rnd(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [rnd(v) for v in o]
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if not np.isfinite(o) else round(float(o), 6)
        return o
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rnd(M), open(OUT, "w"), separators=(",", ":"))
    print("written", OUT)


if __name__ == "__main__":
    main()
