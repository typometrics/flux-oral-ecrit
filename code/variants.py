#!/usr/bin/env python3
"""
variants.py -- numbers for the French article after Sylvain's remarks of 11 October:
  units of at least 3 words (for 2 words the flux is always 1);
  written corpora in their re-segmented version (GSD, Sequoia);
  macro-syntax removed in two ways:
     inplace  the macro-syntactic dependencies are removed, the words stay (what the site does);
     split    the macro-syntactic subtrees are cut out of the unit; a piece of >= 3 words becomes a unit of its own
              (recursively), a smaller piece is dropped; the host unit is renumbered;
  periph   Sylvain's extended macro-syntax: in SUD every mod/udep placed before the subject of its (verbal) governor is
           treated as mod:periph and removed like macro-syntax; in CEFC-gold every periph (nominal or not);
  norep    split + reparandum subtrees dropped (whatever their size).
Also searches example sentences for the figures. Output: variants.json
"""
import os
import sys
import json
import glob
from collections import Counter, defaultdict

V2 = "/bigstorage/kim/typometrics/dataanalysis/flux/v218"
sys.path.insert(0, V2)
from compute2 import read_sentences, is_punct, contract, measures2, filtered, resegment, base, MACRO, MACRO_CEFC, CEFC_NOMINAL  # noqa: E402
from fit import fit_tpl_mle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FL = "/bigstorage/kim/typometrics/dataanalysis/french_latest"
CORPORA = {"GSD": ("SUD", sorted(glob.glob(f"{FL}/SUD_French-GSD/*.conllu")), True),
           "Sequoia": ("SUD", sorted(glob.glob(f"{FL}/SUD_French-Sequoia/*.conllu")), True),
           "ParisStories": ("SUD", sorted(glob.glob(f"{FL}/SUD_French-ParisStories/*.conllu")), False),
           "Rhapsodie": ("SUD", sorted(glob.glob(f"{FL}/SUD_French-Rhapsodie/*.conllu")), False),
           "CEFC": ("CEFC", [f"{FL}/cefc-gold.conllu"], False)}
MIN_WORDS = 3
MIN_PIECE = 3
PERIPH_RELS = {"mod", "udep"}
PM = "periph_macro"           # label given to Sylvain's mod:periph
BINS = {"3-9": (3, 9), "10-19": (10, 19), "20-29": (20, 29), "10-29": (10, 29), "10+": (10, 10 ** 6), "all": (3, 10 ** 6)}
TREATMENTS = ("all", "micro_inplace", "micro_split", "periph_inplace", "periph_split", "norep_inplace", "norep_split")


def valid(toks):
    heads = {t["id"]: t["head"] for t in toks}
    for t in toks:
        h, steps = t["head"], 0
        while h:
            if h not in heads or steps > len(toks):
                return False
            h = heads[h]
            steps += 1
    return True


def renumber(sel, root):
    order = [t["id"] for t in sel]
    newid = {o: k + 1 for k, o in enumerate(order)}
    out = []
    for t in sel:
        t2 = dict(t)
        t2["id"] = newid[t["id"]]
        t2["head"] = 0 if t["id"] == root else newid.get(t["head"], 0)
        if t["id"] == root:
            t2["rel"] = "root"
        out.append(t2)
    return out


def words(toks):
    return [t for t in toks if not is_punct(t)]


def mark_periph(toks, scheme):
    """Sylvain's mod:periph: mod/udep before the subject of a verbal governor (SUD); every periph in CEFC."""
    out = [dict(t) for t in toks]
    if scheme == "CEFC":
        for t in out:
            if t["rel"] == "periph":
                t["rel"] = PM
        return out
    kids = defaultdict(list)
    bt = {t["id"]: t for t in out}
    for t in out:
        kids[t["head"]].append(t["id"])
    for t in out:
        if base(t["rel"]) not in PERIPH_RELS or not t["head"]:
            continue
        g = bt[t["head"]]
        if g["upos"] not in ("VERB", "AUX"):
            continue
        subj = [k for k in kids[g["id"]] if base(bt[k]["rel"]) == "subj"]
        if subj and t["id"] < min(subj) and t["id"] < g["id"]:
            t["rel"] = PM
    return out


def split_macro(toks, macro, drop_rels=(), min_piece=MIN_PIECE):
    """Cut the macro-syntactic subtrees out. Returns [host, piece, piece, ...] (token lists, renumbered),
    pieces of fewer than min_piece words dropped, subtrees of drop_rels always dropped. Recursive."""
    kids = defaultdict(list)
    bt = {t["id"]: t for t in toks}
    for t in toks:
        kids[t["head"]].append(t["id"])

    def subtree(i):
        out, st = [], [i]
        while st:
            x = st.pop()
            out.append(x)
            st.extend(kids[x])
        return set(out)

    def is_cut(t):
        return base(t["rel"]) in macro or base(t["rel"]) in drop_rels

    cut = []
    for t in toks:
        if not is_cut(t) or not t["head"]:
            continue
        # maximal: no cut ancestor (step limit: a few CEFC-gold structures are cyclic)
        h, anc, steps = t["head"], False, 0
        while h and h in bt and steps <= len(toks):
            if is_cut(bt[h]):
                anc = True
                break
            h = bt[h]["head"]
            steps += 1
        if not anc:
            cut.append(t["id"])
    if not cut:
        return [toks]
    removed = set()
    pieces = []
    for c in cut:
        sub = subtree(c)
        removed |= sub
        if base(bt[c]["rel"]) in drop_rels:
            continue
        sel = [t for t in toks if t["id"] in sub]
        if len(words(sel)) >= min_piece:
            pieces.append(renumber(sel, c))
    host_sel = [t for t in toks if t["id"] not in removed]
    roots = [t["id"] for t in host_sel if t["head"] == 0 or t["head"] in removed]
    host = renumber(host_sel, roots[0]) if len(roots) == 1 else [dict(t, head=(0 if t["head"] in removed else t["head"])) for t in host_sel]
    if len(roots) != 1:
        host = renumber(host, -1)
    out = [host]
    for p in pieces:
        out.extend(split_macro(p, macro, drop_rels, min_piece))
    return out


def measure(toks, drop=()):
    """measures of one unit (punctuation removed); drop = relations removed in place. Returns (n, res) or None."""
    w = words(toks)
    n = len(w)
    if n < MIN_WORDS or not valid(toks):
        return None
    heads = {t["id"]: t["head"] for t in toks}
    keep = {t["id"] for t in w}
    hv, order = contract(heads, keep)
    if hv is None:
        return None
    bt = {t["id"]: t for t in toks}
    rl = [None] + [bt[o]["rel"] for o in order]
    if drop:
        hv = filtered(hv, rl, set(drop))
    res = measures2(hv, rl, "SUD", extended=False)
    res["forms"] = [bt[o]["form"] for o in order]
    res["upos"] = [bt[o]["upos"] for o in order]
    res["rel"] = rl[1:]
    res["heads"] = hv[1:]
    return n, res


def units_of(toks, scheme, treatment):
    """the units produced by one original sentence under a treatment: list of (toks, drop set)"""
    macro = MACRO_CEFC if scheme == "CEFC" else MACRO
    rep = {"disflink"} if scheme == "CEFC" else {"reparandum"}
    t = toks
    if treatment.startswith("periph"):
        t = mark_periph(t, scheme)
        macro = macro | {PM}
    if treatment == "all":
        return [(t, set())]
    if treatment.endswith("inplace"):
        return [(t, macro | (rep if treatment.startswith("norep") else set()))]
    return [(u, set()) for u in split_macro(t, macro, drop_rels=(rep if treatment.startswith("norep") else ()))]


def main():
    out = {"corpora": {}, "cells": {}, "dists": {}, "examples": {"weight3": [], "flux3w2": [], "rep": []}}
    for name, (scheme, paths, reseg) in CORPORA.items():
        dists = defaultdict(lambda: defaultdict(Counter))      # (treatment, bin) -> metric -> Counter
        stats = defaultdict(lambda: Counter())                   # (treatment, bin) -> counters
        c1 = Counter()
        deps = Counter()
        for p in paths:
            for meta, toks0 in read_sentences(p):
                if scheme == "CEFC":
                    for t in toks0:
                        if t["rel"] == "periph" and t["upos"] in CEFC_NOMINAL:
                            t["rel"] = "dislocated"
                pieces = resegment(toks0) if reseg else [toks0]
                for toks in pieces:
                    w = words(toks)
                    if len(w) < MIN_WORDS or not valid(toks):
                        continue
                    # table 1
                    c1["units"] += 1
                    c1["words"] += len(w)
                    macro = MACRO_CEFC if scheme == "CEFC" else MACRO
                    for t in w:
                        b = base(t["rel"])
                        deps["all"] += 1
                        if b in macro:
                            deps["macro"] += 1
                        if b in ("reparandum", "disflink"):
                            deps["rep"] += 1
                    for t in words(mark_periph(toks, scheme)):
                        if base(t["rel"]) == PM:
                            deps["periph"] += 1
                    if w[0]["upos"] in ("CCONJ", "COO"):
                        c1["cconj_first"] += 1
                    for tr in TREATMENTS:
                        us = units_of(toks, scheme, tr)
                        if tr.endswith("split"):
                            stats[(tr, "all")]["pieces"] += len(us) - 1
                        for k, (u, drop) in enumerate(us):
                            m = measure(u, drop)
                            if m is None:
                                continue
                            n, res = m
                            for b, (lo, hi) in BINS.items():
                                if lo <= n <= hi:
                                    st = stats[(tr, b)]
                                    st["units"] += 1
                                    st["positions"] += n - 1
                                    st["flux_sum"] += sum(res["flux"])
                                    st["weight_sum"] += sum(res["weight"])
                                    st["len_sum"] += sum(res["len"])
                                    st["deps"] += len(res["len"])
                                    st["maxweight_ge3"] += max(res["weight"] + [0]) >= 3
                                    st["maxweight_ge4"] += max(res["weight"] + [0]) >= 4
                                    for metric in ("len", "flux", "weight"):
                                        dists[(tr, b)][metric].update(res[metric])
                            # examples (spoken corpora, all relations)
                            if tr == "all" and scheme == "SUD" and not reseg and 9 <= n <= 12:
                                sid = meta.get("sent_id", "")
                                ex = {"corpus": name, "sent_id": sid, "n": n, "forms": res["forms"], "upos": res["upos"], "heads": res["heads"],
                                      "rel": res["rel"], "flux": res["flux"], "weight": res["weight"]}
                                if max(res["weight"]) >= 3 and len(out["examples"]["weight3"]) < 60:
                                    out["examples"]["weight3"].append(ex)
                                if any(f == 3 and wgt == 2 for f, wgt in zip(res["flux"], res["weight"])) and len(out["examples"]["flux3w2"]) < 60:
                                    out["examples"]["flux3w2"].append(ex)
                                rels = {base(r) for r in res["rel"]}
                                if "reparandum" in rels and n <= 12 and len(out["examples"]["rep"]) < 80:
                                    ex2 = dict(ex, has_reform=any(r == "conj:reform" for r in res["rel"]))
                                    out["examples"]["rep"].append(ex2)
        out["corpora"][name] = {"units": c1["units"], "words": c1["words"], "mean_len": c1["words"] / c1["units"],
                                "macro_pct": 100 * deps["macro"] / deps["all"], "rep_pct": 100 * deps["rep"] / deps["all"],
                                "periph_pct": 100 * deps["periph"] / deps["all"], "cconj_initial_pct": 100 * c1["cconj_first"] / c1["units"],
                                "reseg": reseg, "pieces_split": stats[("micro_split", "all")]["pieces"],
                                "pieces_periph_split": stats[("periph_split", "all")]["pieces"]}
        for (tr, b), st in stats.items():
            if "units" not in st:
                continue
            cell = {"units": st["units"], "positions": st["positions"], "deps": st["deps"],
                    "flux_mean": st["flux_sum"] / st["positions"], "weight_mean": st["weight_sum"] / st["positions"],
                    "len_mean": st["len_sum"] / st["deps"] if st["deps"] else None,
                    "maxweight_ge3_pct": 100 * st["maxweight_ge3"] / st["units"], "maxweight_ge4_pct": 100 * st["maxweight_ge4"] / st["units"]}
            for metric in ("len", "flux", "weight"):
                d = {k: v for k, v in dists[(tr, b)][metric].items() if k >= 1}
                f = fit_tpl_mle(d, two_regime=False) if sum(d.values()) >= 50 else None
                cell[metric] = {"lambda": f["lambda"], "beta": f["beta"], "se_lambda": f["se_lambda"], "xmax": f["xmax"]} if f else None
            out["cells"][f"{name}|{tr}|{b}"] = cell
            if b in ("10-19", "10-29") and tr in ("all", "micro_inplace", "micro_split", "periph_split"):
                out["dists"][f"{name}|{tr}|{b}"] = {m: sorted(dists[(tr, b)][m].items()) for m in ("len", "flux", "weight")}
        print(name, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in out["corpora"][name].items()}, flush=True)
        for tr in TREATMENTS:
            c = out["cells"].get(f"{name}|{tr}|10-19")
            if c:
                print(f"   10-19 {tr:15} units {c['units']:6} flux {c['flux_mean']:.3f} λ {c['flux']['lambda'] if c['flux'] else None:.2f} "
                      f"weight {c['weight_mean']:.3f} λw {c['weight']['lambda'] if c['weight'] else None:.2f} λlen {c['len']['lambda'] if c['len'] else None:.2f}")
    json.dump(out, open(os.path.join(HERE, "variants.json"), "w"), ensure_ascii=False, default=float)
    print("examples:", {k: len(v) for k, v in out["examples"].items()})


if __name__ == "__main__":
    main()
