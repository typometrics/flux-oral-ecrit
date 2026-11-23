#!/usr/bin/env python3
"""
structure.py -- the English version of the article (November 2026): the structure of the flux on ContentSUD, the tree of
content words obtained from SUD (function words removed, their complement taking their place, chains of conjuncts kept, SUD relations).
Units of 10-19 SUD words; all relations and microsyntax only (macrosyntax, mod:periph included, cut out of the unit as in variants.py).
  weight            distribution, lambda, units reaching 3 and 4
  pairs             pairs of disjoint dependencies crossing a position, by category of the two governors (N, V, other; a word is verbal if it is a VERB or
                    has a subject among its dependents, which covers copular predicates), counted per position and as distinct pairs; the coefficient
                    NV / 2 sqrt(NN VV); pairs of relations (subj, comp:obj, comp:obl, mod, udep); every position where a subject, an object and an oblique are
                    pairwise disjoint
  baseline          the same counts in a random projective order of the same content tree with the same total length (one per unit)
  direction         pending dependencies whose governor comes first (head-initial) or last (head-final), on the full SUD tree
  clausal           clausal weight: disjoint pending core arguments (subj, comp) of a predicate
  bouquets          share of the flux size that bouquets absorb: 1 - weight / size, on ContentSUD
Output: structure.json
"""
import os
import sys
import json
import random
from collections import Counter, defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from variants import CORPORA, read_sentences, resegment, words, valid, units_of, measure, base  # noqa: E402
from compute2 import contract, sud_to_content, measures2  # noqa: E402
from compute import forest_matching  # noqa: E402

LO, HI = 10, 19
NOMINAL = {"NOUN", "PROPN", "PRON"}
RELS = ("subj", "comp:obj", "comp:obl", "mod", "udep")


# ---------------------------------------------------------------------------- random orders of equal total length, weight, fit
def total_len(heads):
    return sum(abs(d - h) for d, h in enumerate(heads) if d and h)


def project(heads, local):
    """local: node -> ordered list of units (the node itself and its children). Returns position of each node (1-based)."""
    n = len(heads) - 1
    root = [d for d in range(1, n + 1) if heads[d] == 0]
    order = []
    stack = [("x", r) for r in reversed(root)]
    while stack:
        k, x = stack.pop()
        if k == "e":
            order.append(x)
            continue
        units = local[x]
        stack.extend(reversed([("e", u) if u == x else ("x", u) for u in units]))
    return {old: i + 1 for i, old in enumerate(order)}


def relabel(heads, pos):
    n = len(heads) - 1
    new = [0] * (n + 1)
    for d in range(1, n + 1):
        new[pos[d]] = pos[heads[d]] if heads[d] else 0
    return new


def lm_projective(heads, target, rng, max_iter=3000):
    """Random projective order with total length == target (local search from a random projective order)."""
    n = len(heads) - 1
    kids = defaultdict(list)
    for d in range(1, n + 1):
        if heads[d]:
            kids[heads[d]].append(d)
    local = {}
    for x in range(1, n + 1):
        u = [x] + kids[x]
        rng.shuffle(u)
        local[x] = u
    movable = [x for x in range(1, n + 1) if len(local[x]) > 1]
    pos = project(heads, local)
    cur = abs(sum(abs(pos[d] - pos[heads[d]]) for d in range(1, n + 1) if heads[d]) - target)
    it = 0
    while cur and it < max_iter and movable:
        it += 1
        x = rng.choice(movable)
        u = local[x]
        i, j = rng.sample(range(len(u)), 2)
        u[i], u[j] = u[j], u[i]
        p2 = project(heads, local)
        c2 = abs(sum(abs(p2[d] - p2[heads[d]]) for d in range(1, n + 1) if heads[d]) - target)
        if c2 <= cur:
            pos, cur = p2, c2
        else:
            u[i], u[j] = u[j], u[i]
    return pos, cur == 0


def sub_weight(heads, keep_arc):
    """Weight restricted to the arcs d->heads[d] for which keep_arc(d) is true."""
    n = len(heads) - 1
    arcs = [(min(d, heads[d]), max(d, heads[d])) for d in range(1, n + 1) if heads[d] and keep_arc(d)]
    out = []
    for i in range(1, n):
        cr = [a for a in arcs if a[0] <= i < a[1]]
        out.append(len(cr) if len(cr) <= 1 else forest_matching(cr))
    return out


def fit(hist, degree=2):
    """hist: counts of the values 1..K. degree 2: returns (beta, lambda, log-likelihood); degree 3: a term -gamma n^2 is added, (beta, lambda, gamma, ll)."""
    hist = np.asarray(hist, dtype=float)
    K = len(hist)
    N = hist.sum()
    bad = (float("nan"),) * (degree + 1)
    if N < 50 or (hist > 0).sum() <= degree:
        return bad
    x = np.arange(1.0, K + 1.0)
    T = np.stack([np.log(x), x / K, (x / K) ** 2][:degree])
    s = T @ hist / N

    def ll(e):
        a = e @ T
        top = a.max()
        return e @ s - top - np.log(np.exp(a - top).sum())
    eta = np.zeros(degree)
    cur = ll(eta)
    for _ in range(300):
        a = eta @ T
        p = np.exp(a - a.max())
        p /= p.sum()
        m = T @ p
        g = s - m
        C = (T * p) @ T.T - np.outer(m, m)
        try:
            step = np.linalg.solve(C + 1e-12 * np.eye(degree), g)
        except np.linalg.LinAlgError:
            return bad
        t = 1.0
        while t > 1e-6:
            e2 = eta + t * step
            v = ll(e2)
            if v >= cur:
                break
            t /= 2
        if t <= 1e-6:
            break
        eta, delta = e2, v - cur
        cur = v
        if delta < 1e-11:
            break
    if not np.all(np.isfinite(eta)) or abs(eta[1]) / K > 80:
        return bad
    return (-eta[0], -eta[1] / K) + ((-eta[2] / K ** 2,) if degree == 3 else ()) + (float(cur * N),)


def to_hist(c, shift=0):
    c = {int(k) + shift: v for k, v in c.items() if int(k) + shift >= 1}
    if not c:
        return np.zeros(1)
    h = np.zeros(max(c))
    for k, v in c.items():
        h[k - 1] = v
    return h


def relkey(r):
    return r if r.startswith("comp:obj") or r.startswith("comp:obl") else base(r)


def content_tree(u):
    """ContentSUD of a unit: (heads list, rel list, cat list, forms list) or None."""
    ch, crel, ck = sud_to_content(u, chains=True)
    if len(ck) < 3:
        return None
    hv, order = contract(ch, ck)
    if hv is None:
        return None
    bt = {t["id"]: t for t in u}
    rel = [None] + [crel[o] for o in order]
    m = len(order)
    subj_gov = {hv[d] for d in range(1, m + 1) if base(rel[d]) == "subj"}
    cat = [None]
    for k, o in enumerate(order, 1):
        t = bt[o]
        ext = next((f[7:] for f in t.get("feats", "_").split("|") if f.startswith("ExtPos=")), None)
        up = ext or t["upos"]
        cat.append("V" if up == "VERB" or k in subj_gov else ("N" if up in NOMINAL else "O"))
    return hv, rel, cat, [bt[o]["form"] for o in order]


def pairs_of(H, rel, cat, C, P, R, distinct, triples=None, forms=None):
    m = len(H) - 1
    arcs = [(min(d, H[d]), max(d, H[d]), d, H[d]) for d in range(1, m + 1) if H[d]]
    seen = set()
    for i in range(1, m):
        cr = [a for a in arcs if a[0] <= i < a[1]]
        C["positions"] += 1
        kinds = set()
        for x in range(len(cr)):
            for y in range(x + 1, len(cr)):
                a, b = cr[x], cr[y]
                if {a[2], a[3]} & {b[2], b[3]}:
                    continue
                k = "".join(sorted(cat[a[3]] + cat[b[3]]))
                P[k] += 1
                kinds.add(k)
                if (a[2], b[2]) not in seen:
                    seen.add((a[2], b[2]))
                    distinct[k] += 1
                ra, rb = relkey(rel[a[2]]), relkey(rel[b[2]])
                if ra in RELS and rb in RELS:
                    R["+".join(sorted((ra, rb)))] += 1
        for k in kinds:
            C["pos_" + k] += 1
        if triples is not None:
            core = [a for a in cr if relkey(rel[a[2]]) in ("subj", "comp:obj", "comp:obl")]
            for x in range(len(core)):
                for y in range(x + 1, len(core)):
                    for z in range(y + 1, len(core)):
                        t3 = [core[x], core[y], core[z]]
                        ws = [w for a in t3 for w in (a[2], a[3])]
                        if len(set(ws)) == 6:
                            triples.append({"words": forms, "pos": i, "arcs": [(forms[a[2] - 1], forms[a[3] - 1], rel[a[2]]) for a in t3]})


def main():
    rng = random.Random(7)
    out = {}
    examples = defaultdict(list)
    for name, (scheme, paths, reseg) in CORPORA.items():
        for tr in ("all", "periph_split"):
            W, MW, CW, MCW = Counter(), Counter(), Counter(), Counter()
            Wl, MWl = Counter(), Counter()
            C, P, R, D = Counter(), Counter(), Counter(), Counter()
            Cl, Pl, Rl, Dl = Counter(), Counter(), Counter(), Counter()
            dirc = Counter()
            size_sum = weight_sum = 0
            triples = []
            units = 0
            for p in paths:
                for meta, toks0 in read_sentences(p):
                    for toks in (resegment(toks0) if reseg else [toks0]):
                        if len(words(toks)) < 3 or not valid(toks):
                            continue
                        for u, drop in units_of(toks, scheme, tr):
                            n = len(words(u))
                            if not LO <= n <= HI or not valid(u):
                                continue
                            m = measure(u)
                            if m is None:
                                continue
                            units += 1
                            res = measures2([0] + m[1]["heads"], [None] + m[1]["rel"], "SUD", extended=True)
                            dirc["head_final"] += sum(res["depwait"])
                            dirc["head_initial"] += sum(res["govwait"])
                            dirc["positions"] += len(res["flux"])
                            if scheme != "SUD":
                                continue
                            ct = content_tree(u)
                            if ct is None:
                                continue
                            H, rel, cat, forms = ct
                            mz = measures2(H, rel, "SUD", extended=False)
                            W.update(mz["weight"])
                            MW[max(mz["weight"])] += 1
                            size_sum += sum(mz["flux"])
                            weight_sum += sum(mz["weight"])
                            cw = sub_weight(H, lambda d: base(rel[d]) in ("subj", "comp") and cat[H[d]] == "V")
                            CW.update(cw)
                            MCW[max(cw)] += 1
                            pairs_of(H, rel, cat, C, P, R, D, triples, forms)
                            if tr == "all" and len(forms) <= 14:
                                for k in ("NN", "VV"):
                                    if len(examples[f"{name}|{k}"]) < 25 and any(True for _ in [0]):
                                        cc, pp = Counter(), Counter()
                                        pairs_of(H, rel, cat, cc, pp, Counter(), Counter())
                                        if pp[k]:
                                            examples[f"{name}|{k}"].append({"sent_id": meta.get("sent_id"), "forms": forms, "heads": H[1:], "rel": rel[1:], "cat": cat[1:]})
                            pos, ok = lm_projective(H, total_len(H), rng)
                            if ok:
                                H2 = relabel(H, pos)
                                rel2, cat2 = [None] * len(H), [None] * len(H)
                                for old, new in pos.items():
                                    rel2[new], cat2[new] = rel[old], cat[old]
                                w2 = measures2(H2, rel2, "SUD", extended=False)["weight"]
                                Wl.update(w2)
                                MWl[max(w2)] += 1
                                pairs_of(H2, rel2, cat2, Cl, Pl, Rl, Dl)
            x = {"units": units, "direction": {k: v / max(1, dirc["positions"]) for k, v in dirc.items() if k != "positions"}}
            if W:
                tot = sum(P[k] for k in ("NN", "VV", "NV"))
                totl = sum(Pl[k] for k in ("NN", "VV", "NV"))
                x.update({"weight_dist": dict(W), "weight_mean": sum(k * v for k, v in W.items()) / sum(W.values()), "weight_lambda": fit(to_hist(W))[1],
                          "weight_lambda_lm": fit(to_hist(Wl))[1], "reach3": sum(v for k, v in MW.items() if k >= 3) / sum(MW.values()),
                          "reach4": sum(v for k, v in MW.items() if k >= 4) / sum(MW.values()), "reach3_lm": sum(v for k, v in MWl.items() if k >= 3) / sum(MWl.values()),
                          "clausal_dist": dict(CW), "clausal_reach2": sum(v for k, v in MCW.items() if k >= 2) / sum(MCW.values()),
                          "clausal_reach3": sum(v for k, v in MCW.items() if k >= 3) / sum(MCW.values()), "bouquet_share": 1 - weight_sum / size_sum, "size_mean": size_sum / sum(W.values()),
                          "pos_share": {k: C["pos_" + k] / C["positions"] for k in ("NN", "VV", "NV")}, "pos_share_lm": {k: Cl["pos_" + k] / max(1, Cl["positions"]) for k in ("NN", "VV", "NV")},
                          "pair_share": {k: P[k] / tot for k in ("NN", "VV", "NV")}, "pair_share_lm": {k: Pl[k] / totl for k in ("NN", "VV", "NV")},
                          "kappa": P["NV"] / (2 * (P["NN"] * P["VV"]) ** .5), "kappa_lm": Pl["NV"] / (2 * (Pl["NN"] * Pl["VV"]) ** .5),
                          "distinct": dict(D), "rel_pairs": dict(R), "rel_pairs_lm": dict(Rl), "triples": triples})
            out[f"{name}|{tr}"] = x
            print(name, tr, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items() if not isinstance(v, (dict, list))}, x.get("pos_share"), x.get("direction"), flush=True)
    out["examples"] = examples
    json.dump(out, open(os.path.join(HERE, "structure.json"), "w"), ensure_ascii=False, default=float, indent=0)


if __name__ == "__main__":
    main()
