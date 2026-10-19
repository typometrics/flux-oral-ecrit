#!/usr/bin/env python3
"""
mathdata.py -- numbers for site2/math.html (the maths of the site explained step by step).
French corpora, SUD, sentences of 10-19 words:
  dists        counts per value for length / flux / weight, with and without macro-syntax, and their fits
  grid         likelihood landscape NLL(beta, lambda) - NLL_min for one distribution (the beta/lambda valley)
  profile      profile-likelihood 95 % interval for lambda, against the Hessian and bootstrap standard errors
  nmax         the same fit with the support truncated at different n_max
  families     alternative two- or one-parameter families fitted to the same counts, with their AIC
  ratios       empirical p(n+1)/p(n) against the fitted ones
  lrtests      pooled vs separate fits for pairs of corpora (likelihood-ratio test)
  tv           total-variation distance between ContentUD weight distributions, with its sampling noise
  bootstrap    sentence-bootstrap standard errors (article_fr/bootstrap.json)
  ols          regression-on-log-counts estimates against the maximum-likelihood ones (fits.csv)
  random       cut-offs of random projective orders of the same trees (fits.csv)
  bylength     mean flux and weight at each exact sentence length 10..19 (recomputed from the treebanks)
Output: site2/data/math.json
"""
import os
import sys
import json
import glob
import collections
import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.special import logsumexp, gammaln, expit
from scipy.stats import chi2, chi2_contingency

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fit import fit_tpl_mle, _nll_tpl  # noqa: E402
from compute import is_tree  # noqa: E402
from compute2 import read_sentences, is_punct, contract, measures2, filtered, MACRO, MACRO_CEFC, CEFC_NOMINAL  # noqa: E402

DA = os.path.abspath(os.path.join(HERE, "..", ".."))
FL = os.path.join(DA, "french_latest")
R2 = os.path.join(HERE, "results2")
OUT = os.path.join(HERE, "site2", "data", "math.json")
UNITS = {"GSD": "French-GSD@latest", "Sequoia": "French-Sequoia@latest", "ParisStories": "French-ParisStories@latest",
         "Rhapsodie": "French-Rhapsodie@latest", "CEFC": "French-CEFC@gold"}
BIN = "10-19"
METRICS = ("len", "flux", "weight")
_D = {}


def dist(name, view, filt, kind, metric):
    u = UNITS[name]
    if u not in _D:
        _D[u] = json.load(open(os.path.join(R2, "dists", f"treebank__{u}.json")))["dists"]
    d = _D[u].get(f"{view}|{filt}|{kind}|{BIN}|{metric}")
    return {int(k): int(v) for k, v in d if k >= 1} if d else None


def arrays(d):
    xs = np.array(sorted(d), dtype=float)
    cs = np.array([d[int(x)] for x in xs], dtype=float)
    return xs, cs


def nll_of(logp_support, xs, cs, support):
    """negative log-likelihood of counts cs at xs for log-probabilities (unnormalised) on the support"""
    lz = logsumexp(logp_support)
    idx = (xs - support[0]).astype(int)
    return -float((cs * (logp_support[idx] - lz)).sum())


def alt_families(d):
    """shifted Poisson, shifted negative binomial, discrete Weibull, plus TPL / geometric / power law from fit.py"""
    xs, cs = arrays(d)
    xmax = int(xs.max())
    sup = np.arange(1, xmax + 1, dtype=float)
    out = {}

    def best_of(f, starts, k):
        b = None
        for s in starts:
            r = minimize(f, s, method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-7, "maxiter": 5000})
            if b is None or r.fun < b.fun:
                b = r
        return b

    # shifted Poisson: n - 1 ~ Poisson(mu)
    f = lambda p: nll_of((sup - 1) * p[0] - gammaln(sup), xs, cs, sup)   # mu = exp(p0)
    r = best_of(f, [(0.0,), (-1.0,), (1.0,)], 1)
    mu = float(np.exp(r.x[0]))
    out["poisson"] = {"k": 1, "params": {"mu": mu}, "nll": float(r.fun), "aic": 2 + 2 * r.fun,
                      "p": list(np.exp((sup - 1) * r.x[0] - gammaln(sup) - logsumexp((sup - 1) * r.x[0] - gammaln(sup))))}
    # shifted negative binomial: n - 1 ~ NB(r, p)
    def lnb(p):
        rr, pp = np.exp(min(p[0], 7.0)), np.clip(expit(p[1]), 1e-9, 1 - 1e-9)   # r <= 1097: beyond that the NB is a Poisson
        return gammaln(sup - 1 + rr) - gammaln(rr) - gammaln(sup) + rr * np.log(pp) + (sup - 1) * np.log1p(-pp)
    f = lambda p: nll_of(lnb(p), xs, cs, sup)
    r = best_of(f, [(0.0, 0.0), (2.0, 1.0), (-1.0, -1.0), (3.0, 2.0)], 2)
    lp = lnb(r.x)
    out["negbin"] = {"k": 2, "params": {"r": float(np.exp(min(r.x[0], 7.0))), "p": float(expit(r.x[1]))}, "nll": float(r.fun), "aic": 4 + 2 * r.fun,
                     "p": list(np.exp(lp - logsumexp(lp)))}
    # discrete Weibull: P(N >= n) = q^((n-1)^b)
    def lw(p):
        q, b = expit(p[0]), np.exp(p[1])
        s = q ** ((sup - 1) ** b) - q ** (sup ** b)
        return np.log(np.maximum(s, 1e-300))
    f = lambda p: nll_of(lw(p), xs, cs, sup)
    r = best_of(f, [(0.0, 0.0), (1.0, 0.5), (-1.0, 0.3), (2.0, 1.0)], 2)
    lp = lw(r.x)
    out["dweibull"] = {"k": 2, "params": {"q": float(expit(r.x[0])), "b": float(np.exp(r.x[1]))}, "nll": float(r.fun), "aic": 4 + 2 * r.fun,
                       "p": list(np.exp(lp - logsumexp(lp)))}
    t = fit_tpl_mle(d, two_regime=False)
    for key, beta, lam, k in (("tpl", t["beta"], t["lambda"], 2), ("powerlaw", t["beta_pl"], 0.0, 1), ("geometric", 0.0, t["lambda_exp"], 1)):
        lp = -beta * np.log(sup) - lam * sup
        nll = _nll_tpl((beta, lam), xs, cs, sup)
        out[key] = {"k": k, "params": {"beta": beta, "lambda": lam}, "nll": nll, "aic": 2 * k + 2 * nll, "p": list(np.exp(lp - logsumexp(lp)))}
    return out, xmax


def main():
    M = {"bin": BIN, "corpora": list(UNITS), "dists": {}, "fits": {}}
    # ------------------------------------------------------------- distributions and fits
    for name in UNITS:
        for filt in ("all", "micro"):
            for m in METRICS:
                d = dist(name, "SUD", filt, "obs", m)
                if not d:
                    continue
                key = f"{name}|{filt}|{m}"
                M["dists"][key] = sorted(d.items())
                t = fit_tpl_mle(d, two_regime=False)
                M["fits"][key] = {k: t[k] for k in ("n", "xmax", "beta", "lambda", "nll", "se_beta", "se_lambda", "aic_tpl", "aic_pl", "aic_exp", "beta_pl", "lambda_exp")}
                M["fits"][key]["mean"] = float(sum(k * v for k, v in d.items()) / sum(d.values()))
    # ------------------------------------------------------------- likelihood landscape (GSD flux, all relations)
    d = dist("GSD", "SUD", "all", "obs", "flux")
    xs, cs = arrays(d)
    sup = np.arange(1, int(xs.max()) + 1, dtype=float)
    t = M["fits"]["GSD|all|flux"]
    betas = np.linspace(-8, 3, 56)
    lams = np.linspace(0, 5, 51)
    grid = [[_nll_tpl((b, l), xs, cs, sup) - t["nll"] for b in betas] for l in lams]
    M["grid"] = {"unit": "GSD", "metric": "flux", "beta": [round(float(b), 3) for b in betas], "lambda": [round(float(l), 3) for l in lams],
                 "dnll": [[round(min(v, 1e6), 2) for v in row] for row in grid], "beta_hat": t["beta"], "lambda_hat": t["lambda"]}
    # profile likelihood for lambda
    def prof(lam):
        r = minimize_scalar(lambda b: _nll_tpl((b, lam), xs, cs, sup), bounds=(-20, 10), method="bounded")
        return r.fun - t["nll"]
    lgrid = np.linspace(t["lambda"] - 0.3, t["lambda"] + 0.3, 121)
    pv = [prof(l) for l in lgrid]
    inside = [l for l, v in zip(lgrid, pv) if v <= 1.9207]
    M["profile"] = {"lambda": [round(float(l), 4) for l in lgrid], "dnll": [round(float(v), 3) for v in pv],
                    "ci95": [round(float(min(inside)), 3), round(float(max(inside)), 3)], "se_hessian": t["se_lambda"]}
    # n_max sensitivity
    M["nmax"] = {}
    for name, metric in (("GSD", "flux"), ("ParisStories", "flux"), ("GSD", "len")):
        dd = dist(name, "SUD", "all", "obs", metric)
        obs = max(dd)
        rows = []
        for xm in sorted({obs, 12, 15, 20, 40, 80}):
            if xm < obs:
                continue
            f = fit_tpl_mle(dd, two_regime=False, xmax=xm)
            rows.append({"xmax": xm, "beta": f["beta"], "lambda": f["lambda"], "mode": (-f["beta"] / f["lambda"]) if f["lambda"] > 0 else None})
        M["nmax"][f"{name}|{metric}"] = {"observed_max": obs, "rows": rows}
    # ------------------------------------------------------------- alternative families and local ratios
    M["families"] = {}
    M["ratios"] = {}
    for name in ("GSD", "ParisStories"):
        for m in ("flux", "weight", "len"):
            dd = dist(name, "SUD", "all", "obs", m)
            fam, xmax = alt_families(dd)
            M["families"][f"{name}|{m}"] = {"xmax": xmax, "n": int(sum(dd.values())),
                                             "models": {k: {kk: (vv if kk != "p" else [round(x, 7) for x in vv]) for kk, vv in v.items()} for k, v in fam.items()}}
            tot = sum(dd.values())
            emp = {n: dd.get(n, 0) / tot for n in range(1, xmax + 1)}
            bt, lm = fam["tpl"]["params"]["beta"], fam["tpl"]["params"]["lambda"]
            M["ratios"][f"{name}|{m}"] = [{"n": n, "p": emp[n], "emp": (emp[n + 1] / emp[n]) if emp[n] else None,
                                           "tpl": float(((n + 1) / n) ** (-bt) * np.exp(-lm))} for n in range(1, min(xmax, 8))]
    # ------------------------------------------------------------- likelihood-ratio tests pooled vs separate
    M["lrtests"] = []
    for a, b in (("GSD", "Sequoia"), ("GSD", "ParisStories"), ("ParisStories", "Rhapsodie"), ("Sequoia", "ParisStories"), ("GSD", "CEFC")):
        for filt, m in (("all", "flux"), ("micro", "flux"), ("all", "weight"), ("micro", "weight")):
            da, db = dist(a, "SUD", filt, "obs", m), dist(b, "SUD", filt, "obs", m)
            fa, fb = fit_tpl_mle(da, two_regime=False), fit_tpl_mle(db, two_regime=False)
            pooled = collections.Counter(da)
            pooled.update(db)
            fp = fit_tpl_mle(dict(pooled), two_regime=False)
            lr = 2 * (fp["nll"] - fa["nll"] - fb["nll"])
            M["lrtests"].append({"a": a, "b": b, "filter": filt, "metric": m, "lambda_a": fa["lambda"], "lambda_b": fb["lambda"], "beta_a": fa["beta"], "beta_b": fb["beta"],
                                 "lambda_pooled": fp["lambda"], "LR": lr, "p": float(chi2.sf(lr, 2)), "n_a": fa["n"], "n_b": fb["n"]})
    # ------------------------------------------------------------- total variation, ContentUD weight
    W = {name: dist(name, "ContentUD", "all", "obs", "weight") for name in ("GSD", "Sequoia", "ParisStories", "Rhapsodie")}
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
        t = []
        for _ in range(3000):
            x = rng.multinomial(sizes[a], pooled) / sizes[a]
            y = rng.multinomial(sizes[b], pooled) / sizes[b]
            t.append(tv(x, y))
        sims[f"{a}|{b}"] = {"mean": float(np.mean(t)), "q95": float(np.quantile(t, 0.95)), "q99": float(np.quantile(t, 0.99))}
    # chi-square on the 4 x K table, values >= 3 merged
    table = [[d.get(1, 0), d.get(2, 0), sum(v for k, v in d.items() if k >= 3)] for d in W.values()]
    c2, p, dof, _ = chi2_contingency(table)
    N = sum(map(sum, table))
    M["tv"] = {"values": vals, "shares": shares, "sizes": sizes, "pairs": pairs, "sims": sims,
               "chi2": {"stat": float(c2), "p": float(p), "dof": int(dof), "cramers_v": float(np.sqrt(c2 / (N * (min(len(table), 3) - 1)))), "table": table}}
    # ------------------------------------------------------------- bootstrap, OLS, random
    M["bootstrap"] = json.load(open(os.path.join(HERE, "..", "article_fr", "bootstrap.json")))
    F = pd.read_csv(os.path.join(R2, "fits.csv"), low_memory=False)
    F = F[(F.level == "treebank") & (F.bin.isin([BIN, "all"])) & (F.view == "SUD") & F.unit.isin(UNITS.values())]
    inv = {v: k for k, v in UNITS.items()}
    M["ols"] = {}
    M["random"] = {}
    for _, r in F.iterrows():
        key = f"{inv[r.unit]}|{r['filter']}|{r.metric}" + ("" if r.bin == BIN else "|allbin")
        if r.bin != BIN and not (r.kind == "obs" and r["filter"] == "all"):
            continue
        if r.kind == "obs" and r.metric in METRICS:
            M["ols"][key] = {"ols_lambda": r.ols_lambda, "ols_beta": r.ols_beta, "ols_npoints": r.ols_npoints, "mle_lambda": r.mle_lambda, "mle_beta": r.mle_beta}
        if r.kind == "rnd" and r["filter"] == "all" and r.metric in METRICS and r.bin == BIN:
            M["random"][key] = {"lambda": r.mle_lambda, "beta": r.mle_beta, "mean": r.desc_mean}
    # ------------------------------------------------------------- mean flux by exact length (recomputed)
    def bylength(paths, scheme):
        acc = collections.defaultdict(lambda: {"units": 0, "flux": 0.0, "micro": 0.0, "weight": 0.0, "wmicro": 0.0, "pos": 0})
        for p in paths:
            for meta, toks in read_sentences(p):
                heads = {t["id"]: t["head"] for t in toks}
                if any(h < 0 for h in heads.values()):
                    continue
                keep = {t["id"] for t in toks if not is_punct(t)}
                n = len(keep)
                if not (10 <= n <= 19):
                    continue
                hv, order = contract(heads, keep)
                if hv is None or not is_tree(hv):
                    continue
                bt = {t["id"]: t for t in toks}
                rel = []
                for o in order:
                    r = bt[o]["rel"]
                    if scheme == "CEFC" and r == "periph" and bt[o]["upos"] in CEFC_NOMINAL:
                        r = "dislocated"
                    rel.append(r)
                rl = [None] + rel
                macro = MACRO_CEFC if scheme == "CEFC" else MACRO
                v = measures2(hv, rl, "SUD")
                vm = measures2(filtered(hv, rl, macro), rl, "SUD")
                a = acc[n]
                a["units"] += 1
                a["pos"] += len(v["flux"])
                a["flux"] += sum(v["flux"])
                a["micro"] += sum(vm["flux"])
                a["weight"] += sum(v["weight"])
                a["wmicro"] += sum(vm["weight"])
        rows = {}
        for n, a in sorted(acc.items()):
            rows[n] = {"units": a["units"], "flux": a["flux"] / a["pos"], "micro": a["micro"] / a["pos"], "weight": a["weight"] / a["pos"], "wmicro": a["wmicro"] / a["pos"]}
        tu = sum(a["units"] for a in acc.values())
        return {"rows": rows, "mean_len": sum(n * a["units"] for n, a in acc.items()) / tu, "units": tu}
    M["bylength"] = {}
    for name in UNITS:
        if name == "CEFC":
            M["bylength"][name] = bylength([os.path.join(FL, "cefc-gold.conllu")], "CEFC")
        else:
            M["bylength"][name] = bylength(sorted(glob.glob(os.path.join(FL, f"SUD_French-{name}", "*.conllu"))), "SUD")
        print(name, "mean length in bin", round(M["bylength"][name]["mean_len"], 2), flush=True)

    def rnd(o):
        if isinstance(o, float):
            return None if (o != o or o in (float("inf"), float("-inf"))) else round(o, 6)
        if isinstance(o, dict):
            return {str(k): rnd(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [rnd(v) for v in o]
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else round(float(o), 6)
        return o
    with open(OUT, "w") as f:
        json.dump(rnd(M), f, separators=(",", ":"))
    print("written", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
