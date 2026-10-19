# Summary

A Universal Dependencies corpus for spoken French.

# Introduction

The corpus was automatically converted from the [Rhapsodie treebank](https://rhapsodie.modyco.fr/) and then underwent many manual corrections and improvements.

# Development

The corpus is maintained in the [SUD](https://surfacesyntacticud.github.io/) format and is available in the [SUD_French-Rhapsodie](https://github.com/surfacesyntacticud/SUD_French-Rhapsodie) repository.

Prosodic annotations from the original project were imported into the SUD data in 2025.
This work is described in the TLT paper:

> Maria Paz Botero-Garcia, Emmett Strickland, Bruno Guillaume, Sylvain Kahane, and Anne Lacheret-Dujour. 2025. [An intonosyntactic treebank for spoken French: What is new with Rhapsodie?](https://aclanthology.org/2025.tlt-1.13/). In Proceedings of the 23rd International Workshop on Treebanks and Linguistic Theories (TLT, SyntaxFest 2025), pages 111–118, Ljubljana, Slovenia. Association for Computational Linguistics.

The richest annotations are available in the `prosody_pauses` folder in the [SUD repository](https://github.com/surfacesyntacticud/SUD_French-Rhapsodie).
Several other versions are automatically built from it.

The table below outlines the various available formats and their production methods.

| Treebanks | Desc | Files | Production |
|-----------|------|-------|------------|
| [pSUD_French-Rhapsodie@pauses](https://universal.grew.fr/?corpus=pSUD_French-Rhapsodie@pauses) | SUD Syntax + Prosody (including pauses) | `prosody_pauses/*.conllu` | Source data |
| [pSUD_French-Rhapsodie@latest](https://universal.grew.fr/?corpus=pSUD_French-Rhapsodie@latest) | SUD Syntax + Prosody | `prosody/*.conllu` | `grs/remove_pauses.grs` |
| [SUD_French-Rhapsodie@p_words](https://universal.grew.fr/?corpus=SUD_French-Rhapsodie@p_words) | SUD Syntax (on phonological words) ${}^1$ | `p_words/*.conllu` | `grs/remove_syllables.grs` |
| [SUD_French-Rhapsodie@latest](https://universal.grew.fr/?corpus=SUD_French-Rhapsodie@latest) | SUD Syntax | `*.conllu` | `grs/split_amalgam.grs` |
| [UD_French-Rhapsodie@conv](https://universal.grew.fr/?corpus=UD_French-Rhapsodie@conv) | UD Syntax | `*.conllu` in [UD repo](https://github.com/UniversalDependencies/UD_French-Rhapsodie) | [`fr_SUD_to_UD.grs` in converter](https://github.com/surfacesyntacticud/tools/tree/master/converter) |

$^1$ We called phonogical words, the version in which the almagams (like `au` or `du`) are not split into *syntactic words* (`à`+`le` or `de`+`le`) as expected in UD.
