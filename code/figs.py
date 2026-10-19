#!/usr/bin/env python3
"""figs.py -- figures of the French article (PNG, 300 dpi) in article_fr/fig/."""
import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = "/bigstorage/kim/typometrics/dataanalysis/flux/v218"
OUT = os.path.join(HERE, "fig")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 300, "legend.frameon": False})
CORP = ["French-GSD@reseg", "French-Sequoia@reseg", "French-ParisStories@latest", "French-Rhapsodie@latest", "French-CEFC@gold"]
NAME = {"French-GSD@reseg": "GSD", "French-Sequoia@reseg": "Sequoia", "French-ParisStories@latest": "ParisStories",
        "French-Rhapsodie@latest": "Rhapsodie", "French-CEFC@gold": "CEFC"}
COL = {"GSD": "#1f4e8c", "Sequoia": "#6aa0d8", "ParisStories": "#b8452a", "Rhapsodie": "#e59a3a", "CEFC": "#7a3f8f"}
MRK = {"GSD": "o", "Sequoia": "s", "ParisStories": "^", "Rhapsodie": "v", "CEFC": "D"}


def load(u):
    return json.load(open(os.path.join(V2, "results2", "dists", f"treebank__{u}.json")))


def fitrow(u, view, filt, b, m):
    import pandas as pd
    global FITS
    if "FITS" not in globals():
        f = pd.read_csv(os.path.join(V2, "results2", "fits.csv"), low_memory=False)
        FITS = f[(f.level == "treebank") & f.unit.str.startswith("French")]
    s = FITS[(FITS.unit == u) & (FITS.view == view) & (FITS["filter"] == filt) & (FITS.kind == "obs") & (FITS.bin == b) & (FITS.metric == m)]
    return s.iloc[0] if len(s) else None


def tpl(beta, lam, xmax, xs):
    sup = np.arange(1, xmax + 1)
    z = (sup ** -beta * np.exp(-lam * sup)).sum()
    return xs ** -beta * np.exp(-lam * xs) / z


def fig_dots():
    forms = ["Celle-ci", "offre", "également", "aux", "randonneurs", "dix", "stations", "d'", "environnement", "informatives"]
    heads = [2, 0, 2, 2, 4, 7, 2, 7, 8, 7]
    n = len(forms)
    arcs = sorted([(min(d, heads[d - 1]), max(d, heads[d - 1]), d) for d in range(1, n + 1) if heads[d - 1]], key=lambda a: a[1] - a[0])
    lev = {}
    for a in arcs:
        lev[a] = 1 + max([lev[b] for b in arcs if b in lev and b[0] >= a[0] and b[1] <= a[1] and b != a] + [0])
    fig, ax = plt.subplots(figsize=(7.0, 2.4))
    pos, x = {}, 0.0
    for i, w in enumerate(forms, 1):
        wdt = max(0.85, 0.15 * len(w) + 0.5)
        x += wdt / 2
        pos[i] = x
        x += wdt / 2
    X = lambda i: pos[i]
    base = 0
    def ell(a, x):
        xa, xb = X(a[0]), X(a[1]); xm, r = (xa + xb) / 2, (xb - xa) / 2
        H = 0.42 * lev[a] + 0.12
        return base + 0.08 + H * np.sqrt(max(0.0, 1 - ((x - xm) / r) ** 2))
    for a in arcs:
        xs = np.linspace(X(a[0]), X(a[1]), 120)
        ax.plot(xs, [ell(a, x) for x in xs], color="black", lw=0.8)
        dx = X(a[0]) if a[2] == a[0] else X(a[1])
        ax.plot([dx - 0.07, dx, dx + 0.07], [base + 0.22, base + 0.08, base + 0.22], color="black", lw=0.8)
        for i in range(a[0], a[1]):
            xm = (X(i) + X(i + 1)) / 2
            ax.plot(xm, ell(a, xm), "o", color="#c0392b", ms=4.2, zorder=3)
    top = base + max(lev.values()) * 0.42 + 0.75
    for i in range(1, n):
        xm = (X(i) + X(i + 1)) / 2
        ax.plot([xm, xm], [base - 0.05, top - 0.25], color="#999", lw=0.5, ls=(0, (2, 2)))
        f = sum(1 for a in arcs if a[0] <= i < a[1])
        ax.text(xm, top - 0.1, str(f), ha="center", va="bottom", color="#b5651d", fontsize=9, fontweight="bold")
    for i, w in enumerate(forms, 1):
        ax.text(X(i), base - 0.18, w, ha="center", va="top", fontsize=8)
        L = next((a[1] - a[0] for a in arcs if a[2] == i), None)
        ax.text(X(i), base - 0.62, "–" if L is None else str(L), ha="center", va="top", color="#1f4e8c", fontsize=9, fontweight="bold")
    ax.text(-0.15, top - 0.1, "flux", ha="right", va="bottom", color="#b5651d", fontsize=7.5)
    ax.text(-0.15, base - 0.62, "longueur", ha="right", va="top", color="#1f4e8c", fontsize=7.5)
    ax.set_xlim(-1.0, x + 0.1)
    ax.set_ylim(base - 1.0, top + 0.3)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_points.png"))
    plt.close(fig)


def fig_dist(metric, views, fname, ylab):
    fig, axes = plt.subplots(1, len(views), figsize=(6.3, 2.6), sharey=True)
    for ax, (view, filt, title) in zip(axes, views):
        for u in CORP:
            D = load(u)["dists"].get(f"{view}|{filt}|obs|10-19|{metric}")
            if not D:
                continue
            d = np.array(D, dtype=float)
            d = d[d[:, 0] >= 1]
            y = d[:, 1] / d[:, 1].sum()
            keep = d[:, 1] >= 5
            nm = NAME[u]
            ax.plot(d[keep, 0], y[keep], MRK[nm], color=COL[nm], ms=3.5, label=nm)
            r = fitrow(u, view, filt, "10-19", metric)
            if r is not None and not np.isnan(r.mle_lambda):
                xs = np.linspace(1, d[:, 0].max(), 200)
                yy = tpl(r.mle_beta, r.mle_lambda, int(d[:, 0].max()), xs)
                ok = yy > 1e-5
                ax.plot(xs[ok], yy[ok], "-", color=COL[nm], lw=0.8, alpha=0.8)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(0.9, 12)
        ax.set_ylim(1e-5, 1)
        ax.set_xticks([1, 2, 3, 5, 8, 12])
        ax.set_xticklabels(["1", "2", "3", "5", "8", "12"])
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel("n")
    axes[0].set_ylabel(ylab)
    axes[-1].legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname))
    plt.close(fig)


def fig_decomp():
    N = json.load(open(os.path.join(HERE, "numbers.json")))
    labs, macro, rep, nom, other = [], [], [], [], []
    for u in CORP:
        r = N["rel"][f"{u}|all|10-19"]
        labs.append(NAME[u])
        macro.append(r["macro_per_pos"])
        rep.append(r["rep_per_pos"])
        nom.append(r["nominal_per_pos"])
        other.append(r["flux_per_pos"] - r["macro_per_pos"] - r["rep_per_pos"] - r["nominal_per_pos"])
    fig, ax = plt.subplots(figsize=(6.0, 2.6))
    x = np.arange(len(labs))
    b1 = ax.bar(x, nom, color="#6aa0d8", label="dans un groupe nominal")
    b2 = ax.bar(x, other, bottom=nom, color="#9a9a9a", label="autres (microsyntaxe)")
    b3 = ax.bar(x, rep, bottom=np.array(nom) + np.array(other), color="#e59a3a", label="reparandum")
    b4 = ax.bar(x, macro, bottom=np.array(nom) + np.array(other) + np.array(rep), color="#b8452a", label="macrosyntaxe")
    ax.set_xticks(x, labs)
    ax.set_ylabel("dépendances par position")
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    ax.set_ylim(0, 2.6)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig4_decomposition.png"))
    plt.close(fig)


if __name__ == "__main__":
    fig_dots()
    # written corpora in their re-segmented version (11 October); fig2 (flux) is now made by figs2.py from variants.json
    fig_dist("weight", [("SUD", "all", "SUD"), ("ContentUD", "all", "ContentUD")], "fig3_poids.png", "fréquence relative")
    fig_decomp()
    print(os.listdir(OUT))
