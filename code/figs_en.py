#!/usr/bin/env python3
"""figs_en.py -- the two new figures of the English version (fig_en/):
  fig_len.png      distribution of dependency length, units of 10-19 words, all relations and microsyntax only (variants.json)
  fig_weight.png   distribution of flux weight on ContentSUD, units of 10-19 words, all relations and microsyntax only (structure.json)
Run with the system python3 (matplotlib)."""
import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fig_en")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 300, "legend.frameon": False})
COL = {"GSD": "#1f4e8c", "Sequoia": "#6aa0d8", "ParisStories": "#b8452a", "Rhapsodie": "#e59a3a", "CEFC": "#7a3f8f"}
MRK = {"GSD": "o-", "Sequoia": "s-", "ParisStories": "o--", "Rhapsodie": "s--", "CEFC": "^--"}
NAME = {"CEFC": "CEFC-gold"}
PANELS = [("all", "all relations"), ("periph_split", "microsyntax only")]


def fig_len():
    V = json.load(open(os.path.join(HERE, "variants.json")))
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7), sharey=True)
    for ax, (tr, title) in zip(axes, PANELS):
        for u in COL:
            d = np.array(V["dists"][f"{u}|{tr}|10-19"]["len"], dtype=float)
            d = d[(d[:, 0] >= 1) & (d[:, 0] <= 14)]
            tot = np.array(V["dists"][f"{u}|{tr}|10-19"]["len"], dtype=float)[:, 1].sum()
            ax.plot(d[:, 0], d[:, 1] / tot, MRK[u], color=COL[u], ms=2.8, lw=0.7, label=NAME.get(u, u))
        ax.set_yscale("log")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel("dependency length")
    axes[0].set_ylabel("relative frequency")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_len.png"))
    plt.close(fig)


def fig_weight():
    S = json.load(open(os.path.join(HERE, "structure.json")))
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.6), sharey=True)
    for ax, (tr, title) in zip(axes, PANELS):
        for u in ("GSD", "Sequoia", "ParisStories", "Rhapsodie"):
            w = {int(k): v for k, v in S[f"{u}|{tr}"]["weight_dist"].items() if int(k) >= 1}
            tot = sum(w.values())
            xs = sorted(w)
            ax.plot(xs, [w[x] / tot for x in xs], MRK[u], color=COL[u], ms=3, lw=0.7, label=u)
        ax.set_yscale("log")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel("flux weight (ContentSUD)")
    axes[0].set_ylabel("relative frequency")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_weight.png"))
    plt.close(fig)


if __name__ == "__main__":
    fig_len()
    fig_weight()
