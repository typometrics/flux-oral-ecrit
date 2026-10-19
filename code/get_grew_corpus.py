#!/usr/bin/env python3
"""
get_grew_corpus.py OUTDIR CORPUS BACKEND -- export a whole corpus from a grew-match backend as CoNLL-U parts.
grew-match returns at most 1000 sentences per search, so the corpus is partitioned by the end of the sent_id
(two final digits, then one final digit, then no final digit) and each part is exported to OUTDIR/partNNN.conllu.
Example: get_grew_corpus.py conv_parts/GSD "UD_French-GSD@conv" https://gmd-universal.grew.fr/
"""
import json, sys, time, urllib.request, os
B = sys.argv[3]
OUT = sys.argv[1]
CORPUS = sys.argv[2]
def post(service, data):
    req = urllib.request.Request(B + service, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))
regexes = [f".*{a}{b}" for a in range(10) for b in range(10)] + [".*[^0-9][0-9]", ".*[^0-9]"]
total = 0
for k, rx in enumerate(regexes):
    req = 'global { sent_id = re"%s" }\npattern { X [] } without { Y [] ; Y < X }' % rx
    r = post("search", {"corpus": CORPUS, "request": req,
                        "display": {"lemma": True, "upos": True, "xpos": False, "features": True, "tf_wf": False,
                                    "order": "init", "context": False, "pid": True}, "clust": {"dim": 0}})
    d = r["data"]
    if d["status"] != "complete":
        print("INCOMPLETE", rx, d); continue
    if d["nb_solutions"] == 0:
        continue
    post("conll_export", {"uuid": d["uuid"], "corpus": CORPUS})
    data = urllib.request.urlopen(B + f"data/{d['uuid']}/export.conllu", timeout=120).read()
    open(os.path.join(OUT, f"part{k:03d}.conllu"), "wb").write(data)
    total += d["nb_solutions"]
    time.sleep(0.3)
print("solutions", total)
