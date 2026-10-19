#!/usr/bin/env python3
"""
pairs_content.py -- section 4.3 on ContentUD (Sylvain, 16 October): disjoint pairs of dependencies by governor category,
counted both as positions (share of inter-word positions where such a pair is in the flux) and as distinct pairs (a pair of
dependencies counted once per unit, however many positions it spans); subj/obj/obl triples likewise; example units.
Units of 10-19 SUD words, all relations. Spoken corpora: official UD conversion (@conv) restricted to content words;
written corpora: re-segmented SUD units converted by compute2.sud_to_content. Output: pairs_content.json
"""
import os
import sys
import json
import glob
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = "/bigstorage/kim/typometrics/dataanalysis/flux/v218"
sys.path.insert(0, V2)
sys.path.insert(0, HERE)
from compute2 import read_sentences, is_punct, contract, ud_content_keep, sud_to_content, resegment, base  # noqa: E402
from variants import valid, words  # noqa: E402

FL = "/bigstorage/kim/typometrics/dataanalysis/french_latest"
NOM = {"NOUN", "PROPN", "PRON"}
VRB = {"VERB"}
SUBJ, OBJ, OBL = {"nsubj", "csubj", "subj"}, {"obj", "ccomp", "xcomp", "comp:obj"}, {"obl", "comp:obl"}


def content_units(name):
    """yield (sent_id, n_sud, heads list, upos list, rel list, forms list) of ContentUD units"""
    if name in ("GSD", "Sequoia"):
        for p in sorted(glob.glob(f"{FL}/SUD_French-{name}/*.conllu")):
            for meta, toks0 in read_sentences(p):
                for k, toks in enumerate(resegment(toks0)):
                    w = words(toks)
                    if len(w) < 3 or not valid(toks):
                        continue
                    ch, crel, ck = sud_to_content(toks)
                    if not ck:
                        continue
                    hv, order = contract(ch, ck)
                    if hv is None:
                        continue
                    bt = {t["id"]: t for t in toks}
                    yield f"{meta.get('sent_id','')}#{k}", len(w), hv, [None] + [bt[o]["upos"] for o in order], [None] + [crel.get(o, bt[o]["rel"]) for o in order], [None] + [bt[o]["form"] for o in order]
    else:
        nsud = {}
        for p in sorted(glob.glob(f"{FL}/SUD_French-{name}/*.conllu")):
            for meta, toks in read_sentences(p):
                nsud[meta.get("sent_id", "")] = len(words(toks))
        for meta, toks in read_sentences(f"{FL}/UD_French-{name}@conv/fr_{name}-conv.conllu"):
            sid = meta.get("sent_id", "")
            if sid not in nsud or nsud[sid] < 3 or not valid(toks):
                continue
            heads = {t["id"]: t["head"] for t in toks}
            keep = {t["id"] for t in toks if not is_punct(t)}
            kc = ud_content_keep(toks, keep)
            if not kc:
                continue
            hv, order = contract(heads, kc)
            if hv is None:
                continue
            bt = {t["id"]: t for t in toks}
            yield sid, nsud[sid], hv, [None] + [bt[o]["upos"] for o in order], [None] + [bt[o]["rel"] for o in order], [None] + [bt[o]["form"] for o in order]


def main():
    out = {}
    for name in ("GSD", "Sequoia", "ParisStories", "Rhapsodie"):
        pos = Counter()        # positions with at least one pair of each kind
        pairs = Counter()      # distinct pairs
        tri = {"positions": 0, "triples": 0}
        P = 0
        ex = defaultdict(list)
        for sid, n, hv, upos, rel, forms in content_units(name):
            inbin = 10 <= n <= 19
            m = len(hv) - 1
            arcs = [(min(d, hv[d]), max(d, hv[d]), d, hv[d]) for d in range(1, m + 1) if hv[d]]
            seen_pairs = set()
            seen_tri = set()
            for i in range(1, m):
                cr = [a for a in arcs if a[0] <= i < a[1]]
                kinds = set()
                if not inbin:
                    kinds = None
                for a in range(len(cr) if inbin else 0):
                    for b in range(a + 1, len(cr)):
                        x, y = cr[a], cr[b]
                        if {x[2], x[3]} & {y[2], y[3]}:
                            continue
                        cx = "N" if upos[x[3]] in NOM else ("V" if upos[x[3]] in VRB else "O")
                        cy = "N" if upos[y[3]] in NOM else ("V" if upos[y[3]] in VRB else "O")
                        key = "".join(sorted(cx + cy))
                        if key in ("NN", "VV", "NV"):
                            kinds.add(key)
                            seen_pairs.add((key, x[2], y[2]))
                            if m <= 14 and len(ex[key]) < 15:
                                ex[key].append({"sent_id": sid, "forms": forms[1:], "upos": upos[1:], "heads": hv[1:], "rel": rel[1:], "position": i,
                                                "pair": [(x[2], x[3]), (y[2], y[3])]})
                if inbin:
                    P += 1
                    for k in kinds:
                        pos[k] += 1
                # subj + obj + obl pairwise disjoint
                S = [a for a in cr if base(rel[a[2]]) in SUBJ]
                O = [a for a in cr if base(rel[a[2]]) in OBJ]
                B = [a for a in cr if base(rel[a[2]]) in OBL]
                found = False
                for s in S:
                    for o in O:
                        for b in B:
                            if not ({s[2], s[3]} & {o[2], o[3]}) and not ({s[2], s[3]} & {b[2], b[3]}) and not ({o[2], o[3]} & {b[2], b[3]}):
                                found = True
                                seen_tri.add((s[2], o[2], b[2]))
                if found:
                    tri["positions"] += 1      # triples: all unit lengths
            for k, x, y in seen_pairs:
                pairs[k] += 1
            tri["triples"] += len(seen_tri)
        NN, VV, NV = (100 * pos[k] / P for k in ("NN", "VV", "NV"))
        out[name] = {"positions": P, "pos_pct": {"NN": NN, "VV": VV, "NV": NV}, "pairs": dict(pairs), "NV_expected_pct": 2 * (NN * VV) ** 0.5,
                     "ratio": NV / (2 * (NN * VV) ** 0.5) if NN and VV else None, "triples": tri, "examples": dict(ex)}
        print(name, "positions", P, {k: round(v, 2) for k, v in out[name]["pos_pct"].items()}, "pairs", dict(pairs), "expected NV", round(out[name]["NV_expected_pct"], 2),
              "ratio", round(out[name]["ratio"], 2), "triples", tri, flush=True)
    json.dump(out, open(os.path.join(HERE, "pairs_content.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
