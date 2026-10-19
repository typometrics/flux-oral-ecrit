#!/usr/bin/env python3
"""figs2.py -- figures added after Sylvain's remarks of 11 October (PNG, 300 dpi, in article_fr/fig/):
  fig_exemple.png     spoken sentence with POS and relations, two cuts (simple / heavy flux)        [introduction]
  fig_poids.png       the same sentence cut where flux = 3 and weight = 2, with Botalla's matrix    [2.3]
  fig_rhap_dist.png   Rhapsodie, 10-19 words: distributions of length, flux, weight with fits and λ  [2.4]
  fig_rep.png         a sentence with a reparandum and a conj:reform                                 [3.2]
  fig_flux_dist.png   flux-size distributions, all relations / without macro-syntax (split) / without mod:periph  [4.1]
Data: variants.json (variants.py)."""
import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Ellipse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fig")
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 300, "legend.frameon": False})
V = json.load(open(os.path.join(HERE, "variants.json")))
NAME = {"GSD": "GSD", "Sequoia": "Sequoia", "ParisStories": "ParisStories", "Rhapsodie": "Rhapsodie", "CEFC": "CEFC"}
COL = {"GSD": "#1f4e8c", "Sequoia": "#6aa0d8", "ParisStories": "#b8452a", "Rhapsodie": "#e59a3a", "CEFC": "#7a3f8f"}
MRK = {"GSD": "o", "Sequoia": "s", "ParisStories": "^", "Rhapsodie": "v", "CEFC": "D"}
MCOL = {"len": "#1f4e8c", "flux": "#b5651d", "weight": "#2a7f62"}
RED = "#c0392b"


def example(sent_id):
    for k in ("weight3", "flux3w2", "rep"):
        for e in V["examples"][k]:
            if e["sent_id"] == sent_id:
                return e
    raise KeyError(sent_id)


def draw_tree(ax, forms, upos, heads, rels, cuts=(), show_pos=True, highlight=(), lw=0.8, fs=8, rows=(), colors=None):
    """arcs above the words, relation labels on the arcs, POS under the words; cuts = [(position i, label, colour)]
    (position i = between word i and i+1, 1-based). Returns the x of each word."""
    n = len(forms)
    arcs = sorted([(min(d, heads[d - 1]), max(d, heads[d - 1]), d) for d in range(1, n + 1) if heads[d - 1]], key=lambda a: a[1] - a[0])
    lev = {}
    for a in arcs:
        lev[a] = 1 + max([lev[b] for b in arcs if b in lev and b[0] >= a[0] and b[1] <= a[1] and b != a] + [0])
    pos, x = {}, 0.0
    for i, w in enumerate(forms, 1):
        wdt = max(0.9, 0.16 * len(w) + 0.45)
        x += wdt / 2
        pos[i] = x
        x += wdt / 2
    X = lambda i: pos[i]
    base = 0.0
    H = lambda a: 0.5 * lev[a] + 0.15

    def ell(a, xx):
        xa, xb = X(a[0]), X(a[1])
        xm, r = (xa + xb) / 2, (xb - xa) / 2
        return base + 0.1 + H(a) * np.sqrt(max(0.0, 1 - ((xx - xm) / r) ** 2))
    for a in arcs:
        xs = np.linspace(X(a[0]), X(a[1]), 160)
        col = (colors or {}).get(a[2], RED if a[2] in highlight else "black")
        ax.plot(xs, [ell(a, v) for v in xs], color=col, lw=lw)
        dx = X(a[0]) if a[2] == a[0] else X(a[1])
        ax.plot([dx - 0.08, dx, dx + 0.08], [base + 0.24, base + 0.1, base + 0.24], color=col, lw=lw)
        xm = (X(a[0]) + X(a[1])) / 2
        ax.text(xm, base + 0.1 + H(a) + 0.04, rels[a[2] - 1], ha="center", va="bottom", fontsize=fs - 1.5, color=col,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))
    top = base + max(lev.values()) * 0.5 + 0.9
    for i, w in enumerate(forms, 1):
        ax.text(X(i), base - 0.2, w, ha="center", va="top", fontsize=fs)
        if show_pos:
            ax.text(X(i), base - 0.55, upos[i - 1], ha="center", va="top", fontsize=fs - 2, color="#555")
    for i, label, col in cuts:
        xm = (X(i) + X(i + 1)) / 2
        ax.plot([xm, xm], [base - 0.9, top + 0.1], color=col, lw=1.0, ls=(0, (4, 3)))
        ax.text(xm, top + 0.15, label, ha="center", va="bottom", fontsize=fs - 1, color=col)
    yrow = base - (0.95 if show_pos else 0.6)
    for label, vals, col in rows:
        ax.text(X(1) - 0.55, yrow, label, ha="right", va="top", fontsize=fs - 1, color=col)
        for i, v in enumerate(vals, 1):
            ax.text((X(i) + X(i + 1)) / 2, yrow, v, ha="center", va="top", fontsize=fs - 1, color=col, fontweight="bold")
        yrow -= 0.38
    ax.set_xlim(-0.9 if rows else -0.2, x + 0.2)
    ax.set_ylim(min(base - 1.0, yrow + 0.1), top + 0.75)
    ax.axis("off")
    return pos


def fig_exemple():
    e = example("Rhap_D0001-44")
    f, w = e["flux"], e["weight"]
    cuts = [(8, f"flux {f[7]}, poids {w[7]}", "#1f4e8c"), (6, f"flux {f[5]}, poids {w[5]}", RED)]
    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    draw_tree(ax, e["forms"], e["upos"], e["heads"], e["rel"], cuts=cuts)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_exemple.png"))
    plt.close(fig)
    return e


def fig_poids():
    e = example("Rhap_D0001-44")
    forms, heads = e["forms"], e["heads"]
    i = 5                                   # cut between "un" and "très": flux 3, weight 2
    f, w = e["flux"][i - 1], e["weight"][i - 1]
    crossing = [(min(d, heads[d - 1]), max(d, heads[d - 1])) for d in range(1, len(forms) + 1) if heads[d - 1] and min(d, heads[d - 1]) <= i < max(d, heads[d - 1])]
    left = sorted({a for a, b in crossing}, reverse=True)       # closest to the cut first
    right = sorted({b for a, b in crossing})
    rel_of = {}
    for d in range(1, len(forms) + 1):
        if heads[d - 1]:
            a, b = min(d, heads[d - 1]), max(d, heads[d - 1])
            rel_of[(a, b)] = (e["rel"][d - 1] + ">") if d == b else ("<" + e["rel"][d - 1])
    lab = lambda k: f"{forms[k - 1]}_{e['upos'][k - 1]}"
    fig = plt.figure(figsize=(7.0, 4.1))
    ax = fig.add_axes([0.01, 0.42, 0.98, 0.56])
    draw_tree(ax, forms, e["upos"], heads, e["rel"], cuts=[(i, f"flux {f}, poids {w}", RED)])
    ax2 = fig.add_axes([0.22, 0.02, 0.62, 0.36])
    ax2.axis("off")
    nr, nc = len(left), len(right)
    cw = 2.0
    ax2.set_xlim(-2.4, cw * nc + 0.2)
    ax2.set_ylim(-0.2, nr + 1.2)
    for j, r in enumerate(right):
        ax2.text(cw * (j + 0.5), nr + 0.35, lab(r), ha="center", va="bottom", fontsize=8)
    matching = {(5, 8), (4, 10)}            # un-trajet, est-quatre-vingt-six: two disjoint dependencies
    for k, l in enumerate(left):
        y = nr - 1 - k
        ax2.text(-0.15, y + 0.5, lab(l), ha="right", va="center", fontsize=8)
        for j, r in enumerate(right):
            ax2.add_patch(Rectangle((cw * j, y), cw, 1, fc="white", ec="#888", lw=0.6))
            if (l, r) in crossing:
                ax2.text(cw * (j + 0.5), y + 0.5, rel_of[(l, r)], ha="center", va="center", fontsize=7, color="black")
                if (l, r) in matching:
                    ax2.add_patch(Ellipse((cw * (j + 0.5), y + 0.5), 1.6, 0.8, fc="none", ec=RED, lw=1.2))
    ax2.text(cw * nc / 2, -0.15, "matrice du flux entre un et très\n(lignes : mots de gauche, du plus proche au plus éloigné ; colonnes : mots de droite ; > < : direction de la dépendance)",
             ha="center", va="top", fontsize=7, color="#444")
    fig.savefig(os.path.join(OUT, "fig_poids.png"))
    plt.close(fig)


def tpl(beta, lam, xmax, xs):
    sup = np.arange(1, xmax + 1)
    z = (sup ** -beta * np.exp(-lam * sup)).sum()
    return xs ** -beta * np.exp(-lam * xs) / z


def fig_rhap_dist():
    D = V["dists"]["Rhapsodie|all|10-19"]
    C = V["cells"]["Rhapsodie|all|10-19"]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    titles = {"len": "longueur des dépendances", "flux": "taille du flux", "weight": "poids du flux"}
    for m in ("len", "flux", "weight"):
        d = np.array(D[m], dtype=float)
        d = d[d[:, 0] >= 1]
        y = d[:, 1] / d[:, 1].sum()
        keep = d[:, 1] >= 5
        fit = C[m]
        ax.plot(d[keep, 0], y[keep], "o", color=MCOL[m], ms=3.5, label=f"{titles[m]} (β = {fit['beta']:.2f}, λ = {fit['lambda']:.2f})")
        xs = np.linspace(1, d[:, 0].max(), 200)
        yy = tpl(fit["beta"], fit["lambda"], int(fit["xmax"]), xs)
        ok = yy > 1e-5
        ax.plot(xs[ok], yy[ok], "-", color=MCOL[m], lw=0.9)
    ax.set_yscale("log")
    ax.set_xscale("log")
    ax.set_ylim(1e-5, 1)
    ax.set_xticks([1, 2, 3, 5, 10, 18])
    ax.set_xticklabels(["1", "2", "3", "5", "10", "18"])
    ax.set_xlabel("n")
    ax.legend(fontsize=7, loc="lower left")
    ax.set_ylabel("fréquence relative")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_rhap_dist.png"))
    plt.close(fig)
    return C


def fig_rep():
    e = dict(example("ParisStories_2019_peripleCrous_1"))
    heads = list(e["heads"])
    heads[1] = 7       # "et" depends on the second "était" (Sylvain, 16 October)
    heads[0] = 2       # the first "euh" is attached to "et"
    cols = {d + 1: ("#e59a3a" if r.split(":")[0] == "reparandum" else "#2a7f62") for d, r in enumerate(e["rel"]) if r.split(":")[0] == "reparandum" or r == "conj:reform"}
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    draw_tree(ax, e["forms"], e["upos"], heads, e["rel"], show_pos=True, fs=7.5, colors=cols)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_rep.png"))
    plt.close(fig)
    return e


def fig_flux_dist():
    panels = [("all", "toutes les relations"), ("periph_split", "microsyntaxe seulement")]
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.6), sharey=True)
    for ax, (tr, title) in zip(axes, panels):
        for u in NAME:
            D = V["dists"].get(f"{u}|{tr}|10-19")
            if not D:
                continue
            d = np.array(D["flux"], dtype=float)
            d = d[d[:, 0] >= 1]
            y = d[:, 1] / d[:, 1].sum()
            keep = d[:, 1] >= 5
            ax.plot(d[keep, 0], y[keep], MRK[u], color=COL[u], ms=3.5, label=NAME[u])
            fit = V["cells"][f"{u}|{tr}|10-19"]["flux"]
            xs = np.linspace(1, d[:, 0].max(), 200)
            yy = tpl(fit["beta"], fit["lambda"], int(fit["xmax"]), xs)
            ok = yy > 1e-5
            ax.plot(xs[ok], yy[ok], "-", color=COL[u], lw=0.8, alpha=0.8)
        ax.set_yscale("log")
        ax.set_ylim(1e-5, 1)
        ax.set_xlim(0.5, 10.5)
        ax.set_xticks(range(1, 11))
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel("taille du flux")
    axes[0].set_ylabel("fréquence relative")
    axes[-1].legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_flux_dist.png"))
    plt.close(fig)


if __name__ == "__main__":
    e = fig_exemple()
    print("exemple:", " ".join(e["forms"]), e["flux"], e["weight"])
    fig_poids()
    print("rhap fits:", {m: (round(v["beta"], 2), round(v["lambda"], 2)) for m, v in fig_rhap_dist().items() if isinstance(v, dict)})
    r = fig_rep()
    print("rep:", " ".join(r["forms"]), r["rel"])
    fig_flux_dist()
    print(sorted(os.listdir(OUT)))
