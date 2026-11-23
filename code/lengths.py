#!/usr/bin/env python3
"""
lengths.py -- Table 2 of the English version: shares of short and long dependencies (length 1, at most 2, at most 4, more than 7) and the parameters
beta and lambda of the fitted distribution, with the shares that the fitted curve predicts. From the length distributions of variants.json
(units of 10-19 and 10-29 words, all relations and microsyntax only). Output: length_shares.json
"""
import os
import sys
import json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from structure import fit  # noqa: E402

TESTS = {"1": lambda k: k == 1, "<=2": lambda k: k <= 2, "<=4": lambda k: k <= 4, ">7": lambda k: k > 7}


def main():
    V = json.load(open(os.path.join(HERE, "variants.json")))
    out = {}
    for tr in ("all", "periph_split"):
        for b in ("10-19", "10-29"):
            for c in ("GSD", "Sequoia", "ParisStories", "Rhapsodie", "CEFC"):
                d = {int(k): v for k, v in V["dists"][f"{c}|{tr}|{b}"]["len"] if int(k) >= 1}
                N = sum(d.values())
                h = np.zeros(max(d))
                for k, v in d.items():
                    h[k - 1] = v
                beta, lam, _ = fit(h)
                xs = np.arange(1, max(d) + 1)
                p = xs ** (-beta) * np.exp(-lam * xs)
                p /= p.sum()
                out[f"{c}|{tr}|{b}"] = {"dependencies": N, "mean": sum(k * v for k, v in d.items()) / N, "beta": beta, "lambda": lam,
                                        "observed": {t: sum(v for k, v in d.items() if f(k)) / N for t, f in TESTS.items()},
                                        "fitted": {t: float(p[np.array([f(x) for x in xs])].sum()) for t, f in TESTS.items()}}
                x = out[f"{c}|{tr}|{b}"]
                print(f"{c:12} {tr:12} {b}  1: {100 * x['observed']['1']:.1f}  <=2: {100 * x['observed']['<=2']:.1f}  >7: {100 * x['observed']['>7']:.2f}  beta {beta:.2f}  lambda {lam:.3f}")
    json.dump(out, open(os.path.join(HERE, "length_shares.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
