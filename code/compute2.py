#!/usr/bin/env python3
"""
compute2.py -- second version of the flux computation (October 2026, after Sylvain's
comments of 10 October).

Differences with compute.py
---------------------------
* Punctuation is always removed. Three views of a sentence:
      SUD        SUD tree (from SUD files)
      UD         UD tree (from UD files)
      ContentUD  UD tree restricted to content words (function words det, case, aux, cop,
                 mark, cc, clf and their fixed/flat/goeswith parts removed). For the latest
                 SUD versions of the French treebanks, which have no UD version, ContentUD
                 is derived from the SUD tree by sud_to_content() (see there).
  Sentence length n is always the number of words without punctuation (the same for the
  three views), so that length bins select the same sentences in every view.
* Relation filters (the words are kept, only the arcs are removed):
      all     every dependency
      micro   macro-syntactic dependencies removed: discourse, parataxis, dislocated
              (all subtypes) and vocative; for CEFC-gold: dm, parenth, and periph whose dependent is a
              noun or pronoun
      norep   micro, and reparandum removed too (CEFC: disflink)
  With micro / norep the structure is a forest; flux, weight etc. are computed on the
  remaining arcs (Christiansen & Chater 2016: macro-syntax handled at another level).
* Measures (per inter-word position unless stated):
      len flux weight lvert rvert depwait govwait   as in compute.py
      pot      potential flux, projective stack (Kahane & Yan 2019), left to right
      pot2     same, but a word attached by a "closed" relation (UD function words, which
               take no dependents by the guidelines: det case cc mark aux cop clf fixed flat
               goeswith; SUD: det cc fixed flat goeswith) leaves the potential flux as soon as
               its governor has been read, unless it still has a dependent to come
      potR, pot2R   the same, computed right to left (on the mirrored sentence)
      maxlen maxflux maxweight maxpot   per-sentence peaks
  Random baseline (filter all): one random projective re-linearisation per sentence.

Output: out2/<unit>.pkl with counts[(view, filter, kind, metric)] = Counter{(n, value): k}
"""
import os
import sys
import glob
import pickle
import random
import zlib
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compute import is_tree, forest_matching  # noqa: E402

DA = os.path.abspath(os.path.join(HERE, "..", ".."))
MAX_LEN = 300
UD_FUNC = {"det", "case", "aux", "cop", "mark", "cc", "clf"}
FOLLOW_REMOVED = {"fixed", "goeswith", "flat"}
MACRO = {"discourse", "parataxis", "dislocated", "vocative"}
# CEFC-gold: periph is split by the category of its dependent (Sylvain, 10 Oct.): nouns and
# pronouns are counted as dislocated (macro), the other periph as modifiers outside the nucleus
# (micro). The split is done when the CEFC sentences are read (relation renamed "dislocated").
MACRO_CEFC = {"dm", "parenth", "dislocated"}
CEFC_NOMINAL = {"NOM", "PRO", "PRQ", "CLS", "CLI", "CLN", "CLO"}
REP = {"reparandum"}
REP_CEFC = {"disflink"}
CLOSED = {"UD": {"det", "case", "cc", "mark", "aux", "cop", "clf", "fixed", "flat", "goeswith"},
          "SUD": {"det", "cc", "fixed", "flat", "goeswith"}}


# ---------------------------------------------------------------------------- reading
def read_sentences(path):
    """Yield (meta, tokens) with tokens = list of dicts for syntactic words."""
    toks, meta = [], {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                if toks:
                    yield meta, toks
                toks, meta = [], {}
                continue
            if line.startswith("#"):
                if "=" in line:
                    k, v = line[1:].split("=", 1)
                    meta[k.strip()] = v.strip()
                continue
            c = line.split("\t")
            if len(c) < 8 or not c[0].isdigit():
                continue
            try:
                h = int(c[6])
            except ValueError:
                h = -1
            feats = c[5] if len(c) > 5 else "_"
            toks.append({"id": int(c[0]), "form": c[1], "upos": c[3], "feats": feats, "head": h,
                         "rel": c[7].split("@")[0]})
    if toks:
        yield meta, toks


def base(rel):
    return rel.split(":")[0]


def is_punct(t):
    return t["upos"] in ("PUNCT", "PONCT") or base(t["rel"]) == "punct"


# ---------------------------------------------------------------------------- trees
def contract(heads, keep):
    """heads: dict id->head. keep: set of ids. Returns (new_heads list, old ids in order)."""
    order = sorted(keep)
    newid = {old: k + 1 for k, old in enumerate(order)}
    res = [0] * (len(order) + 1)
    for old in order:
        h = heads[old]
        steps = 0
        while h != 0 and h not in keep:
            h = heads.get(h, 0)
            steps += 1
            if steps > 1000:
                return None, None
        res[newid[old]] = newid[h] if h != 0 else 0
    return res, order


def ud_content_keep(toks, keep_np):
    rel = {t["id"]: base(t["rel"]) for t in toks}
    heads = {t["id"]: t["head"] for t in toks}
    removed = {i for i in rel if i not in keep_np or rel[i] in UD_FUNC}
    changed = True
    while changed:
        changed = False
        for i in rel:
            if i not in removed and rel[i] in FOLLOW_REMOVED and heads[i] in removed:
                removed.add(i)
                changed = True
    return set(rel) - removed


SUD_FUNC_UPOS = {"ADP", "AUX", "SCONJ"}
SUD_COMP = ("comp:obj", "comp:aux", "comp:pred", "comp", "comp:obl", "comp:cleft")


def sud_to_content(toks):
    """SUD tree -> content-word skeleton comparable to ContentUD.
    1. Function heads (ADP, AUX, SCONJ) with a comp* dependent: the complement (resolved
       recursively, e.g. AUX -> AUX -> VERB) takes the place of the function word; the other
       dependents of the function word are re-attached to it (subject of an auxiliary ->
       main verb, as in UD).
    2. Coordination: SUD chains (A -conj-> B -conj-> C) become UD bouquets (A->B, A->C).
    3. Function words (ADP, AUX, SCONJ, DET, CCONJ, PART attached by det/cc) and
       punctuation are removed; their remaining dependents go to the nearest kept ancestor.
    Returns (heads dict over kept ids, rel dict, kept set)."""
    heads = {t["id"]: t["head"] for t in toks}
    rel = {t["id"]: t["rel"] for t in toks}
    upos = {t["id"]: t["upos"] for t in toks}
    kids = defaultdict(list)
    for i, h in heads.items():
        kids[h].append(i)

    def comp_of(f):
        cands = [k for k in kids[f] if rel[k] in SUD_COMP or rel[k].startswith("comp:")]
        if not cands:
            return None
        # prefer comp:aux / comp:pred / comp:obj, then the first one to the right
        for pref in ("comp:aux", "comp:pred", "comp:obj"):
            for k in sorted(cands):
                if rel[k] == pref:
                    return k
        right = [k for k in sorted(cands) if k > f]
        return right[0] if right else sorted(cands)[0]

    func = [i for i in sorted(heads) if upos[i] in SUD_FUNC_UPOS]
    promoted = set()

    def depth(i):
        d, h = 0, heads[i]
        while h and d < 1000:
            d, h = d + 1, heads[h]
        return d
    # process function words top-down so that chains AUX->AUX->V resolve
    for f in sorted(func, key=depth):
        c = comp_of(f)
        if c is None:
            continue
        heads[c] = heads[f]
        rel[c] = rel[f]
        for k in list(kids[f]):
            if k != c:
                heads[k] = c
        heads[f] = c
        rel[f] = {"ADP": "case", "AUX": "aux", "SCONJ": "mark"}[upos[f]]
        promoted.add(f)
        kids = defaultdict(list)
        for i, h in heads.items():
            kids[h].append(i)
    # coordination / flat chains -> bouquets (UD attaches every conjunct to the first one)
    for i in sorted(heads):
        if rel[i] in ("conj", "conj:coord") or base(rel[i]) == "flat":
            h = heads[i]
            while h and rel.get(h) == rel[i] and heads[h]:
                h = heads[h]
            heads[i] = h

    def is_func(i):
        b = base(rel[i])
        return (i in promoted
                or (b == "det" and upos[i] == "DET")
                or b in ("cc", "case", "mark", "aux", "cop")
                or upos[i] == "PUNCT" or b == "punct")
    removed = {i for i in heads if is_func(i)}
    changed = True
    while changed:              # parts of fixed expressions follow their head
        changed = False
        for i in heads:
            if i not in removed and base(rel[i]) in ("fixed", "flat", "goeswith", "unk") and heads[i] in removed:
                removed.add(i)
                changed = True
    keep = set(heads) - removed
    return heads, rel, keep


# ---------------------------------------------------------------------------- measures
def stack_potential(n, arcs, heads, closed=None, rel=None):
    """Projective stack after each word j < n. arcs: list of (lo, hi). heads: list.
    closed: set of relation names whose words leave once their governor is read."""
    left_arcs = defaultdict(list)
    right_deps = defaultdict(int)   # word -> its rightmost dependent position
    for lo, hi in arcs:
        left_arcs[hi].append(lo)
    for d in range(1, n + 1):
        h = heads[d]
        if h and d > h:
            right_deps[h] = max(right_deps[h], d)
    stack, onstack = [], set()
    out = []
    for j in range(1, n + 1):
        lefts = left_arcs.get(j)
        if lefts:
            m = min(lefts)
            while stack and stack[-1] > m:
                onstack.discard(stack.pop())
            if heads[m] == j and stack and stack[-1] == m:
                onstack.discard(stack.pop())
        stack.append(j)
        onstack.add(j)
        if j < n:
            if closed is None:
                out.append(len(stack))
            else:
                c = 0
                for w in stack:
                    h = heads[w]
                    if base(rel[w]) in closed and h and h <= j and right_deps.get(w, 0) <= j:
                        continue
                    c += 1
                out.append(c)
    return out


def measures2(heads, rel, scheme, extended=True):
    """heads: list 1..n (0 = root; several roots allowed). rel: list of relations."""
    n = len(heads) - 1
    arcs = [(min(d, heads[d]), max(d, heads[d]), d) for d in range(1, n + 1) if heads[d] > 0]
    res = {"len": [hi - lo for lo, hi, _ in arcs]}
    diff = [0] * (n + 2)
    for lo, hi, _ in arcs:
        diff[lo] += 1
        diff[hi] -= 1
    flux, acc = [], 0
    for i in range(1, n):
        acc += diff[i]
        flux.append(acc)
    res["flux"] = flux
    starts = defaultdict(list)
    for lo, hi, _ in arcs:
        starts[lo].append((lo, hi))
    active, weight = [], []
    for i in range(1, n):
        active = [a for a in active if a[1] > i]
        active.extend(starts.get(i, []))
        weight.append(len(active) if len(active) <= 1 else forest_matching(active))
    res["weight"] = weight
    if not extended:
        return res
    # left / right vertices, waiting directions
    rr = [0] * (n + 1)
    ll = [n + 1] * (n + 1)
    for lo, hi, _ in arcs:
        rr[lo] = max(rr[lo], hi)
        ll[hi] = min(ll[hi], lo)
    d1, d2, d3 = [0] * (n + 2), [0] * (n + 2), [0] * (n + 2)
    for w in range(1, n + 1):
        if rr[w] > w:
            d1[w] += 1
            d1[rr[w]] -= 1
        if ll[w] < w:
            d2[ll[w]] += 1
            d2[w] -= 1
    for lo, hi, d in arcs:
        if d == lo:
            d3[lo] += 1
            d3[hi] -= 1
    lv, rv, dw = [], [], []
    a1 = a2 = a3 = 0
    for i in range(1, n):
        a1 += d1[i]
        a2 += d2[i]
        a3 += d3[i]
        lv.append(a1)
        rv.append(a2)
        dw.append(a3)
    res["lvert"], res["rvert"], res["depwait"] = lv, rv, dw
    res["govwait"] = [f - d for f, d in zip(flux, dw)]
    plain = [(lo, hi) for lo, hi, _ in arcs]
    res["pot"] = stack_potential(n, plain, heads)
    res["pot2"] = stack_potential(n, plain, heads, CLOSED[scheme], rel)
    # right-to-left reading: bouquets / chains are first re-headed on their last member
    # (Sylvain, 10 Oct.), then the sentence is mirrored
    th, trel = rtl_tree(heads, rel, scheme)
    mh = [0] * (n + 1)
    mrel = [None] * (n + 1)
    for d in range(1, n + 1):
        mh[n + 1 - d] = (n + 1 - th[d]) if th[d] else 0
        mrel[n + 1 - d] = trel[d]
    marcs = [(min(d, mh[d]), max(d, mh[d])) for d in range(1, n + 1) if mh[d] > 0]
    res["potR"] = stack_potential(n, marcs, mh)
    res["pot2R"] = stack_potential(n, marcs, mh, CLOSED[scheme], mrel)
    for m in ("len", "flux", "weight", "pot"):
        res["max" + m] = [max(res[m])] if res[m] else []
    return res


RTL_UD = ("fixed", "flat", "list", "conj", "parataxis")      # bouquets, word level first
RTL_SUD_CHAINS = ("fixed", "flat", "conj")                   # SUD chains
RTL_SUD_BOUQUETS = ("list", "parataxis")


def rtl_tree(heads, rel, scheme):
    """Tree to use when the sentence is read from right to left.
    UD: in a bouquet (A with dependents D of the same relation conj/fixed/flat/list/parataxis),
    the last member becomes the head: it takes the incoming arc of A and every other member
    depends on it. SUD: chains A -> B -> C of conj/fixed/flat are reversed (C -> B -> A, C
    taking the incoming arc of A); list/parataxis bouquets as in UD. Other dependents keep their
    governor. Returns (heads, rel) lists; the original ones if the result is not a tree."""
    n = len(heads) - 1
    h, r = list(heads), list(rel)
    if n < 2:
        return h, r

    def depth(x):
        d = 0
        while h[x] and d < 1000:
            x, d = h[x], d + 1
        return d
    rep_ = list(range(n + 1))

    def R(x):
        while rep_[x] != x:
            x = rep_[x]
        return x

    def bouquet(types):
        for t in types:
            groups = []
            for a in range(1, n + 1):
                D = [d for d in range(1, n + 1) if heads[d] == a and r[d] and base(rel[d]) == t]
                if D:
                    groups.append((a, D))
            for a, D in sorted(groups, key=lambda g: -depth(g[0])):
                A = R(a)
                G = sorted({A} | {R(d) for d in D})
                H = G[-1]
                if H == A:
                    continue
                h[H], r[H] = h[A], r[A]
                for x in G:
                    if x != H:
                        h[x], r[x] = H, t
                        rep_[x] = H

    if scheme == "UD":
        bouquet(RTL_UD)
    else:
        for t in RTL_SUD_CHAINS:
            starts = [a for a in range(1, n + 1)
                      if any(heads[d] == a and base(rel[d]) == t for d in range(1, n + 1))
                      and not (heads[a] and base(rel[a]) == t)]
            for a in starts:
                chain = [a]
                while True:
                    nxt = [d for d in range(1, n + 1) if heads[d] == chain[-1] and base(rel[d]) == t]
                    if len(nxt) != 1:
                        break
                    chain.append(nxt[0])
                if len(chain) < 2:
                    continue
                top_h, top_r = h[chain[0]], r[chain[0]]
                L = chain[-1]
                h[L], r[L] = top_h, top_r
                for i in range(len(chain) - 1):
                    h[chain[i]], r[chain[i]] = chain[i + 1], t
        bouquet(RTL_SUD_BOUQUETS)
    if not is_tree(h) and is_tree(heads):
        return list(heads), list(rel)
    return h, r


def filtered(heads, rel, drop):
    """Remove arcs whose relation base is in drop (the dependent becomes a root)."""
    h = list(heads)
    for d in range(1, len(h)):
        if h[d] and base(rel[d]) in drop:
            h[d] = 0
    return h


# ---------------------------------------------------------------------------- resegmentation
def resegment(toks):
    """Cut a written SUD sentence at conj / parataxis dependents of the root (recursively),
    except when the subject is shared (subject of the first clause Shared=Yes, second clause
    without subject). Only cuts leaving contiguous units (punctuation ignored).
    Returns a list of token lists with heads renumbered within each unit."""
    words = [t for t in toks if not is_punct(t)]
    if not words:
        return [toks]
    ids = [t["id"] for t in words]
    heads = {t["id"]: t["head"] for t in toks}
    rel = {t["id"]: t["rel"] for t in toks}
    feats = {t["id"]: t["feats"] for t in toks}
    kids = defaultdict(list)
    for i, h in heads.items():
        kids[h].append(i)

    def subtree(i):
        out, st = [], [i]
        while st:
            x = st.pop()
            out.append(x)
            st.extend(kids[x])
        return set(out)

    units = []          # list of (root, set of ids)
    pending = [(r, subtree(r)) for r in kids[0]]
    while pending:
        r, span = pending.pop()
        cut = None
        for d in sorted(kids[r]):
            if d not in span or base(rel[d]) not in ("conj", "parataxis"):
                continue
            subj_r = [k for k in kids[r] if base(rel[k]) == "subj"]
            subj_d = [k for k in kids[d] if base(rel[k]) == "subj"]
            if subj_r and not subj_d and any("Shared=Yes" in feats[k] for k in subj_r):
                continue
            sub = subtree(d) & span
            sub_w = sorted(i for i in sub if i in ids)
            rest_w = sorted(i for i in span - sub if i in ids)
            if not sub_w or not rest_w:
                continue
            if sub_w != list(range(sub_w[0], sub_w[-1] + 1)) and \
                    sub_w != [i for i in ids if sub_w[0] <= i <= sub_w[-1]]:
                continue
            if rest_w[-1] > sub_w[0]:      # material of the first clause after the cut
                continue
            cut = (d, sub)
            break
        if cut is None:
            units.append((r, span))
        else:
            d, sub = cut
            pending.append((r, span - sub))
            pending.append((d, sub))
    if len(units) == 1:
        return [toks]
    out = []
    for r, span in sorted(units, key=lambda u: min(u[1])):
        sel = [t for t in toks if t["id"] in span]
        order = [t["id"] for t in sel]
        newid = {o: k + 1 for k, o in enumerate(order)}
        nt = []
        for t in sel:
            t2 = dict(t)
            t2["id"] = newid[t["id"]]
            t2["head"] = 0 if t["id"] == r else newid.get(t["head"], 0)
            if t["id"] == r:
                t2["rel"] = "root"
            nt.append(t2)
        out.append(nt)
    return out


# ---------------------------------------------------------------------------- main loop
def add(counts, key, n, vals):
    c = counts[key]
    for v in vals:
        c[(n, v)] += 1


def process(args):
    unit, sources, out_path, seed, reseg = args
    rng = random.Random(seed)
    counts = defaultdict(Counter)
    meta, wo = Counter(), Counter()
    for src in sources:          # scheme: UD, SUD, SUDlatest, CEFC
        scheme, files = src[0], src[1]
        conv = {}
        if len(src) > 2 and not reseg:          # UD versions converted by grew-match (@conv)
            for cf in src[2]:
                for cm, ct in read_sentences(cf):
                    conv[cm.get("sent_id")] = ct
        macro = MACRO_CEFC if scheme == "CEFC" else MACRO
        rep = REP_CEFC if scheme == "CEFC" else REP
        for path in files:
            for smeta, toks0 in read_sentences(path):
                meta[f"sentences_raw_{scheme}"] += 1
                pieces = resegment(toks0) if reseg else [toks0]
                if reseg and len(pieces) > 1:
                    meta["reseg_cuts"] += len(pieces) - 1
                if scheme == "CEFC":
                    for t in toks0:
                        if t["rel"] == "periph" and t["upos"] in CEFC_NOMINAL:
                            t["rel"] = "dislocated"
                for toks in pieces:
                    ids = [t["id"] for t in toks]
                    if ids != list(range(1, len(ids) + 1)):
                        meta["skipped_ids"] += 1
                        continue
                    heads = {t["id"]: t["head"] for t in toks}
                    full = [0] + [t["head"] for t in toks]
                    if any(h < 0 for h in full[1:]) or not is_tree(full):
                        # CEFC has a few multi-rooted sentences: keep them as forests
                        if scheme != "CEFC" or any(h < 0 or h > len(toks) for h in full[1:]):
                            meta["skipped_not_tree"] += 1
                            continue
                    keep_np = {t["id"] for t in toks if not is_punct(t)}
                    if len(keep_np) > MAX_LEN:
                        meta["skipped_too_long"] += 1
                        continue
                    n = len(keep_np)
                    if n < 2:
                        continue
                    views = []
                    if scheme == "UD":
                        hv, order = contract(heads, keep_np)
                        if hv is not None:
                            views.append(("UD", "UD", hv, order))
                        kc = ud_content_keep(toks, keep_np)
                        hv2, order2 = contract(heads, kc) if kc else (None, None)
                        if hv2 is not None:
                            views.append(("ContentUD", "UD", hv2, order2))
                    else:
                        hv, order = contract(heads, keep_np)
                        if hv is not None:
                            views.append(("SUD", "SUD", hv, order))
                        ctoks = conv.get(smeta.get("sent_id")) if conv else None
                        if scheme == "SUDlatest" and ctoks is not None:
                            # UD and ContentUD from the official conversion; n stays the SUD length
                            cheads = {t["id"]: t["head"] for t in ctoks}
                            ckeep = {t["id"] for t in ctoks if not is_punct(t)}
                            cfull = [0] + [t["head"] for t in ctoks]
                            if [t["id"] for t in ctoks] == list(range(1, len(ctoks) + 1)) and is_tree(cfull):
                                hu, ou = contract(cheads, ckeep)
                                if hu is not None:
                                    views.append(("UD", "UD", hu, ["c", ou]))
                                kc = ud_content_keep(ctoks, ckeep)
                                hc, oc = contract(cheads, kc) if kc else (None, None)
                                if hc is not None:
                                    views.append(("ContentUD", "UD", hc, ["c", oc]))
                            else:
                                meta["conv_not_tree"] += 1
                        elif scheme == "SUDlatest":
                            if conv:
                                meta["conv_missing"] += 1
                            ch, crel, ck = sud_to_content(toks)
                            hv2, order2 = contract(ch, ck) if ck else (None, None)
                            if hv2 is not None:
                                views.append(("ContentUD", "UD", hv2, ["d", order2]))
                    relmap = {t["id"]: t["rel"] for t in toks}
                    crel_map = None
                    if scheme == "SUDlatest":
                        _, crel_map, _ = sud_to_content(toks)
                        if conv and smeta.get("sent_id") in conv:
                            cmap = {t["id"]: t["rel"] for t in conv[smeta.get("sent_id")]}
                    for view, rscheme, hv, order in views:
                        src_map = relmap
                        if isinstance(order, list) and order and order[0] in ("c", "d"):
                            src_map = cmap if order[0] == "c" else crel_map
                            order = order[1]
                        m = len(hv) - 1
                        if m < 2:
                            continue
                        if scheme != "CEFC" and not is_tree(hv):
                            meta[f"contract_fail_{view}"] += 1
                            continue
                        rl = [None] + [src_map[o] for o in order]
                        meta[f"sentences_{view}"] += 1
                        meta[f"words_{view}"] += m
                        meta[f"deps_{view}"] += sum(1 for d in range(1, m + 1) if hv[d])
                        meta[f"hi_{view}"] += sum(1 for d in range(1, m + 1) if 0 < hv[d] < d)
                        for filt, drop in (("all", set()), ("micro", macro), ("norep", macro | rep)):
                            hf = filtered(hv, rl, drop) if drop else hv
                            if drop:
                                meta[f"dropped_{view}_{filt}"] += sum(1 for d in range(1, m + 1) if hv[d] and not hf[d])
                            res = measures2(hf, rl, rscheme, extended=(filt == "all"))
                            for metric, vals in res.items():
                                add(counts, (view, filt, "obs", metric), n, vals)
                            if filt != "all":
                                for mm in ("len", "flux", "weight"):
                                    if res[mm]:
                                        add(counts, (view, filt, "obs", "max" + mm), n, [max(res[mm])])
                        # random baseline (whole tree), relations follow their words
                        if is_tree(hv):
                            rh, perm = random_projective_perm(hv, rng)
                            rrel = [None] * (m + 1)
                            for old, new in perm.items():
                                rrel[new] = rl[old]
                            rres = measures2(rh, rrel, rscheme, extended=True)
                            for metric in ("len", "flux", "weight", "pot", "pot2", "lvert",
                                           "maxlen", "maxflux", "maxweight", "maxpot"):
                                add(counts, (view, "all", "rnd", metric), n, rres[metric])
                    # word order (on the original tree, per scheme)
                    for t in toks:
                        h = t["head"]
                        if h <= 0 or is_punct(t):
                            continue
                        b = base(t["rel"])
                        wo[f"{scheme}_deps"] += 1
                        wo[f"{scheme}_hi"] += h < t["id"]
                        hu = next((x["upos"] for x in toks if x["id"] == h), None)
                        if (scheme == "UD" and b == "obj") or (scheme != "UD" and t["rel"].startswith("comp:obj") and hu == "VERB"):
                            wo[f"{scheme}_obj"] += 1
                            wo[f"{scheme}_vo"] += h < t["id"]
    result = {"unit": unit, "sources": [(src[0], [os.path.basename(f) for f in src[1]]) for src in sources],
              "meta": dict(meta), "wo": dict(wo), "counts": {k: dict(v) for k, v in counts.items()}}
    with open(out_path, "wb") as f:
        pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)
    return unit, meta.get("sentences_SUD", 0) + meta.get("sentences_UD", 0)


def random_projective_perm(heads, rng):
    """Random projective linearisation; returns (new heads, mapping old id -> new id)."""
    n = len(heads) - 1
    kids = defaultdict(list)
    roots = []
    for d in range(1, n + 1):
        if heads[d] == 0:
            roots.append(d)
        else:
            kids[heads[d]].append(d)
    order = []
    stack = [("expand", r) for r in reversed(roots)]
    while stack:
        kind, x = stack.pop()
        if kind == "emit":
            order.append(x)
            continue
        units = [("emit", x)] + [("expand", c) for c in kids[x]]
        rng.shuffle(units)
        stack.extend(reversed(units))
    pos = {old: k + 1 for k, old in enumerate(order)}
    new = [0] * (n + 1)
    for d in range(1, n + 1):
        new[pos[d]] = pos[heads[d]] if heads[d] else 0
    return new, pos


def files_of(d):
    return sorted(glob.glob(os.path.join(d, "*.conllu")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=70)
    ap.add_argument("--only", default=None)
    ap.add_argument("--out", default=os.path.join(HERE, "out2"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    ud = os.path.join(DA, "ud-treebanks-v2.18")
    sud = os.path.join(DA, "sud-treebanks-v2.18")
    fl = os.path.join(DA, "french_latest")
    tasks = []
    # one unit per treebank name, pooling its UD and SUD versions
    names = set()
    for d in os.listdir(ud):
        if d.startswith("UD_"):
            names.add(d[3:])
    for d in os.listdir(sud):
        if d.startswith("SUD_"):
            names.add(d[4:])
    for name in sorted(names):
        srcs = []
        if files_of(os.path.join(ud, "UD_" + name)):
            srcs.append(("UD", files_of(os.path.join(ud, "UD_" + name))))
        if files_of(os.path.join(sud, "SUD_" + name)):
            srcs.append(("SUD", files_of(os.path.join(sud, "SUD_" + name))))
        if srcs:
            tasks.append((name, srcs, False))
    # latest French SUD + CEFC, and resegmented written corpora
    for tb in ("GSD", "Sequoia", "ParisStories", "Rhapsodie"):
        fs = files_of(os.path.join(fl, f"SUD_French-{tb}"))
        if fs:
            cf = files_of(os.path.join(fl, f"UD_French-{tb}@conv"))
            tasks.append((f"French-{tb}@latest", [("SUDlatest", fs, cf)], False))
            if tb in ("GSD", "Sequoia"):
                tasks.append((f"French-{tb}@reseg", [("SUDlatest", fs)], True))
    if os.path.exists(os.path.join(fl, "cefc-gold.conllu")):
        tasks.append(("French-CEFC@gold", [("CEFC", [os.path.join(fl, "cefc-gold.conllu")])], False))
    jobs = []
    for name, srcs, reseg in tasks:
        if args.only and args.only not in name:
            continue
        out = os.path.join(args.out, name + ".pkl")
        if os.path.exists(out):
            continue
        size = sum(os.path.getsize(f) for src in srcs for f in src[1])
        jobs.append((size, (name, srcs, out, zlib.crc32(name.encode()), reseg)))
    jobs.sort(key=lambda j: -j[0])
    print(f"{len(jobs)} units", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process, j[1]): j[1][0] for j in jobs}
        done = 0
        for fu in as_completed(futs):
            done += 1
            try:
                u, ns = fu.result()
                print(f"[{done}/{len(jobs)}] {u} {ns}", flush=True)
            except Exception as e:
                import traceback
                print(f"[{done}/{len(jobs)}] ERROR {futs[fu]} {e!r}\n{traceback.format_exc()}", flush=True)


if __name__ == "__main__":
    main()
