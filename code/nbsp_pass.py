#!/usr/bin/env python3
"""nbsp_pass.py FILE... -- French non-breaking spaces (U+00A0) in markdown files, idempotent; code spans and URLs untouched."""
import re
import sys

NB = " "
UNITS = ("mots?", "positions?", "dépendances?", "unités?", "corpus", "locuteurs", "phrases?", "énoncés?", "niveaux", "relecteurs",
         "réplicats", "degrés", "sous-corpus", "erreurs", "fois", "h", "caractères", "morceaux", "propositions", "coupures", "exemples")


def nbsp(text):
    out = []
    for i, seg in enumerate(re.split(r"(`[^`]*`|https?://\S+)", text)):
        if i % 2 == 1:
            out.append(seg)
            continue
        seg = re.sub(r" ([:;!?»])", NB + r"\1", seg)
        seg = re.sub(r"« ", "«" + NB, seg)
        seg = re.sub(r"(\d) %", r"\1" + NB + "%", seg)
        seg = re.sub(r"(\d) (" + "|".join(UNITS) + r")\b", r"\1" + NB + r"\2", seg)
        seg = re.sub(r"(\d) (\d{3})\b", r"\1" + NB + r"\2", seg)
        out.append(seg)
    return "".join(out)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        s = open(p, encoding="utf-8").read()
        t = nbsp(s)
        if t != s:
            open(p, "w", encoding="utf-8").write(t)
        print(p, "NBSP:", t.count(NB))
