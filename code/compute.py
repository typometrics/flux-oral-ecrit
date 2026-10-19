#!/usr/bin/env python3
"""
compute.py -- flux measures on UD / SUD 2.18, per treebank and per sentence length.

For every sentence we compute, at every inter-word position i (between word i and i+1,
i = 1..n-1, no position before the first or after the last word):

  len     dependency lengths |h-d| (one value per dependency, n-1 per sentence)
  flux    flux size: number of dependencies crossing position i
  weight  flux weight: max number of pairwise vertex-disjoint dependencies in the flux
          (maximum matching of the crossing arcs; Kahane, Yan & Botalla 2017)
  pot     potential flux (Kahane & Yan 2019): number of words <= i that can still be
          linked projectively to a word > i, given the arcs already built inside 1..i
          (= the stack of an incremental projective parser; a word leaves the stack when
          it is covered by an arc closed inside 1..i, or when its governor arrives on its
          right)
  lvert   number of distinct left endpoints of the observed flux (this is what the June
          2026 HTML pages called "potential flux")
  rvert   number of distinct right endpoints of the observed flux
  depwait arcs of the flux whose dependent is on the left (words waiting for their governor)
  govwait arcs of the flux whose governor is on the left (governors waiting for a dependent)
  maxlen, maxflux, maxweight, maxpot   one value per sentence: the sentence's peak

Views (which tokens are kept; removed tokens are contracted, their dependents being
re-attached to the nearest kept ancestor):
  all      every syntactic word (punctuation included) -- as in flux_html_analyses
  nopunct  punctuation removed (standard in DLM studies)                 [main view]
  content  UD only: function words removed too (deprel det, case, aux, cop, mark, cc,
           clf, and fixed/goeswith/flat parts of removed words), i.e. the flux between
           content words only

For the nopunct view we also compute the same measures on one random projective
re-linearisation of each tree (random order of each head and its dependents), the
baseline of Gildea & Temperley 2010 / Futrell et al. 2015.

Output: one pickle per treebank in out/<framework>/<treebank>.pkl containing
  counts[(view, kind, metric)] = Counter{(sent_len, value): count}
with kind in {"obs", "rnd"}, plus word-order counts and meta-data.
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

MAX_LEN = 300  # longer sentences are skipped (very rare; mostly segmentation errors)

UD_FUNC = {"det", "case", "aux", "cop", "mark", "cc", "clf"}
FOLLOW_REMOVED = {"fixed", "goeswith", "flat"}


def read_conllu(path):
    """Yield sentences as lists of (id, upos, head, deprel) for syntactic words."""
    sent = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                if sent:
                    yield sent
                sent = []
                continue
            if line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 8:
                continue
            tid = cols[0]
            if not tid.isdigit():
                continue
            try:
                head = int(cols[6])
            except ValueError:
                head = -1
            sent.append((int(tid), cols[3], head, cols[7]))
    if sent:
        yield sent


def contract(heads, keep):
    """heads: dict id->head (0 = root). keep: set of ids kept.
    Returns list new_heads (index 0 unused) over renumbered kept tokens, or None."""
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
                return None
        res[newid[old]] = newid[h] if h != 0 else 0
    return res


def is_tree(heads):
    """heads: list, heads[i] for i=1..n. Checks single root and acyclicity."""
    n = len(heads) - 1
    if sum(1 for i in range(1, n + 1) if heads[i] == 0) != 1:
        return False
    for i in range(1, n + 1):
        if heads[i] < 0 or heads[i] > n:
            return False
    state = [0] * (n + 1)
    for i in range(1, n + 1):
        path = []
        j = i
        while j != 0 and state[j] == 0:
            state[j] = 1
            path.append(j)
            j = heads[j]
        if j != 0 and state[j] == 1:
            return False
        for p in path:
            state[p] = 2
    return True


def forest_matching(arcs):
    """Maximum matching of a forest given as a list of edges (u, v)."""
    adj = defaultdict(list)
    for u, v in arcs:
        adj[u].append(v)
        adj[v].append(u)
    matched = set()
    visited = set()
    size = 0
    for root in list(adj):
        if root in visited:
            continue
        # iterative DFS to get a post-order with parents
        stack = [(root, 0)]
        order = []
        parent = {root: None}
        visited.add(root)
        while stack:
            v, _ = stack.pop()
            order.append(v)
            for w in adj[v]:
                if w not in visited:
                    visited.add(w)
                    parent[w] = v
                    stack.append((w, 0))
        for v in reversed(order):
            p = parent[v]
            if p is not None and v not in matched and p not in matched:
                matched.add(v)
                matched.add(p)
                size += 1
    return size


def measures(heads):
    """heads: list with heads[i] for i=1..n (0 = root). Returns dict metric -> list."""
    n = len(heads) - 1
    arcs = [(min(d, heads[d]), max(d, heads[d]), d) for d in range(1, n + 1) if heads[d] > 0]
    lens = [hi - lo for lo, hi, _ in arcs]

    # flux size via difference array; positions 1..n-1
    diff = [0] * (n + 2)
    for lo, hi, _ in arcs:
        diff[lo] += 1
        diff[hi] -= 1
    flux = []
    acc = 0
    for i in range(1, n):
        acc += diff[i]
        flux.append(acc)

    # left vertices: word w is a left endpoint at positions w..R(w)-1
    right_reach = [0] * (n + 1)
    for lo, hi, _ in arcs:
        if hi > right_reach[lo]:
            right_reach[lo] = hi
    diff = [0] * (n + 2)
    for w in range(1, n + 1):
        if right_reach[w] > w:
            diff[w] += 1
            diff[right_reach[w]] -= 1
    lvert = []
    acc = 0
    for i in range(1, n):
        acc += diff[i]
        lvert.append(acc)

    # flux weight: maximum matching of crossing arcs at each position
    starts = defaultdict(list)
    for lo, hi, _ in arcs:
        starts[lo].append((lo, hi))
    active = []
    weight = []
    for i in range(1, n):
        active = [a for a in active if a[1] > i]
        active.extend(starts.get(i, []))
        if len(active) <= 1:
            weight.append(len(active))
        else:
            weight.append(forest_matching(active))

    # potential flux: projective stack
    left_arcs = defaultdict(list)  # right endpoint -> list of left endpoints
    for lo, hi, _ in arcs:
        left_arcs[hi].append(lo)
    stack = []
    onstack = set()
    pot = []
    nonproj = 0
    for j in range(1, n + 1):
        lefts = left_arcs.get(j)
        if lefts:
            for a in lefts:
                if a not in onstack:
                    nonproj += 1
            m = min(lefts)
            while stack and stack[-1] > m:
                onstack.discard(stack.pop())
            if heads[m] == j and stack and stack[-1] == m:
                onstack.discard(stack.pop())
        stack.append(j)
        onstack.add(j)
        if j < n:
            pot.append(len(stack))

    # flux split by direction: arcs whose dependent is on the left (a word waiting for its
    # governor) vs arcs whose governor is on the left (a governor waiting for a dependent)
    diff = [0] * (n + 2)
    for lo, hi, d in arcs:
        if d == lo:
            diff[lo] += 1
            diff[hi] -= 1
    depwait = []
    acc = 0
    for i in range(1, n):
        acc += diff[i]
        depwait.append(acc)
    govwait = [f - d for f, d in zip(flux, depwait)]

    # right vertices: word w is a right endpoint at positions L(w)..w-1
    left_reach = [n + 1] * (n + 1)
    for lo, hi, _ in arcs:
        if lo < left_reach[hi]:
            left_reach[hi] = lo
    diff = [0] * (n + 2)
    for w in range(1, n + 1):
        if left_reach[w] < w:
            diff[left_reach[w]] += 1
            diff[w] -= 1
    rvert = []
    acc = 0
    for i in range(1, n):
        acc += diff[i]
        rvert.append(acc)

    hi_count = sum(1 for d in range(1, n + 1) if 0 < heads[d] < d)
    res = {"len": lens, "flux": flux, "weight": weight, "pot": pot, "lvert": lvert,
           "rvert": rvert, "depwait": depwait, "govwait": govwait}
    # sentence-level peaks (one value per sentence)
    for m in ("len", "flux", "weight", "pot"):
        res["max" + m] = [max(res[m])] if res[m] else []
    return res, nonproj, hi_count


def random_projective(heads, rng):
    """Random projective linearisation of the tree. Returns new heads list."""
    n = len(heads) - 1
    kids = defaultdict(list)
    root = 0
    for d in range(1, n + 1):
        if heads[d] == 0:
            root = d
        else:
            kids[heads[d]].append(d)
    order = []
    # iterative: stack of items, each item either ('node', x) to expand or ('emit', x)
    stack = [("expand", root)]
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
    return new


def process_treebank(args):
    tb_dir, framework, out_path, seed = args
    rng = random.Random(seed)
    counts = defaultdict(Counter)
    meta = Counter()
    wo = Counter()
    files = sorted(glob.glob(os.path.join(tb_dir, "*.conllu")))
    obj_rel = "obj" if framework == "UD" else "comp:obj"
    for path in files:
        for sent in read_conllu(path):
            meta["sentences_raw"] += 1
            heads = {t[0]: t[2] for t in sent}
            ids = [t[0] for t in sent]
            if ids != list(range(1, len(ids) + 1)) or any(h < 0 for h in heads.values()):
                meta["skipped_bad_ids"] += 1
                continue
            full = [0] + [t[2] for t in sent]
            if not is_tree(full):
                meta["skipped_not_tree"] += 1
                continue
            if len(sent) > MAX_LEN:
                meta["skipped_too_long"] += 1
                continue
            upos = {t[0]: t[1] for t in sent}
            rel = {t[0]: t[3].split(":")[0] for t in sent}
            fullrel = {t[0]: t[3] for t in sent}

            views = {}
            views["all"] = full
            keep_np = {i for i in ids if upos[i] != "PUNCT" and rel[i] != "punct"}
            if len(keep_np) == len(ids):
                views["nopunct"] = full
            elif keep_np:
                views["nopunct"] = contract(heads, keep_np)
            if framework == "UD":
                removed = {i for i in ids if i not in keep_np or rel[i] in UD_FUNC}
                changed = True
                while changed:
                    changed = False
                    for i in ids:
                        if i not in removed and rel[i] in FOLLOW_REMOVED and heads[i] in removed:
                            removed.add(i)
                            changed = True
                keep_c = set(ids) - removed
                if keep_c:
                    views["content"] = contract(heads, keep_c)

            for view, hv in views.items():
                if hv is None or (hv is not full and not is_tree(hv)):
                    meta["contract_fail_" + view] += 1
                    continue
                n = len(hv) - 1
                meta["sentences_" + view] += 1
                meta["words_" + view] += n
                if n < 2:
                    continue
                res, nonproj, hi_count = measures(hv)
                for metric, vals in res.items():
                    c = counts[(view, "obs", metric)]
                    for v in vals:
                        c[(n, v)] += 1
                meta["nonproj_arcs_" + view] += nonproj
                meta["hi_deps_" + view] += hi_count
                meta["deps_" + view] += n - 1
                if view == "nopunct":
                    rh = random_projective(hv, rng)
                    rres, _, _ = measures(rh)
                    for metric, vals in rres.items():
                        c = counts[(view, "rnd", metric)]
                        for v in vals:
                            c[(n, v)] += 1

            # word order (on original ids, punctuation irrelevant here)
            for i in ids:
                h = heads[i]
                if h <= 0:
                    continue
                r = fullrel[i].split("@")[0]
                base = r.split(":")[0]
                # SUD comp:obj also covers objects of adpositions: keep verbal governors only
                if (framework == "UD" and base == "obj") or (framework == "SUD" and r.startswith(obj_rel)
                                                             and upos.get(h) == "VERB"):
                    wo["obj_total"] += 1
                    if h < i:
                        wo["obj_vo"] += 1
                if base == "punct":
                    continue
                wo["deps_total"] += 1
                if h < i:
                    wo["deps_hi"] += 1
                if (framework == "UD" and base in ("nsubj",)) or (framework == "SUD" and base == "subj"):
                    wo["subj_total"] += 1
                    if h > i:
                        wo["subj_sv"] += 1
    result = {
        "treebank": os.path.basename(tb_dir.rstrip("/")),
        "framework": framework,
        "files": [os.path.basename(f) for f in files],
        "meta": dict(meta),
        "wo": dict(wo),
        "counts": {k: dict(v) for k, v in counts.items()},
    }
    with open(out_path, "wb") as f:
        pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)
    return result["treebank"], meta.get("sentences_nopunct", 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ud", default="/bigstorage/kim/typometrics/dataanalysis/ud-treebanks-v2.18")
    ap.add_argument("--sud", default="/bigstorage/kim/typometrics/dataanalysis/sud-treebanks-v2.18")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--workers", type=int, default=60)
    ap.add_argument("--only", default=None, help="substring filter on treebank names")
    args = ap.parse_args()

    tasks = []
    for framework, root in (("UD", args.ud), ("SUD", args.sud)):
        od = os.path.join(args.out, framework)
        os.makedirs(od, exist_ok=True)
        for k, tb in enumerate(sorted(os.listdir(root))):
            if args.only and args.only not in tb:
                continue
            tb_dir = os.path.join(root, tb)
            if not os.path.isdir(tb_dir) or not glob.glob(os.path.join(tb_dir, "*.conllu")):
                continue
            out_path = os.path.join(od, tb + ".pkl")
            if os.path.exists(out_path):
                continue
            size = sum(os.path.getsize(p) for p in glob.glob(os.path.join(tb_dir, "*.conllu")))
            tasks.append((size, (tb_dir, framework, out_path, zlib.crc32(tb.encode()))))
    tasks.sort(key=lambda t: -t[0])  # biggest first
    print(f"{len(tasks)} treebanks to process", flush=True)
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(process_treebank, t[1]) for t in tasks]
        for fu in as_completed(futs):
            done += 1
            try:
                tb, ns = fu.result()
                print(f"[{done}/{len(tasks)}] {tb} {ns} sentences", flush=True)
            except Exception as e:  # keep going
                print(f"[{done}/{len(tasks)}] ERROR {e!r}", flush=True)


if __name__ == "__main__":
    main()
