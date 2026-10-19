# Le flux de dépendance, une mesure de la complexité syntaxique : l'oral et l'écrit en français

Sylvain Kahane et Kim Gerdes, 2026. Site compagnon : https://typometrics.github.io/flux-oral-ecrit/ (miroir : https://typometrics.elizia.net/flux-oral-ecrit/).

- `article/` : l'article (HTML, docx, source Markdown, figures)
- `data/treebanks/` : les corpus aux versions analysées (SUD French GSD, Sequoia, ParisStories, Rhapsodie, leurs conversions UD `@conv`, CEFC-gold)
- `data/derived/` : les unités illocutoires analysées et leurs composantes illocutoires (CoNLL-U)
- `code/` : les scripts Python ; `results/` : leurs sorties (JSON) et la liste des unités de poids 4 et 5
- `maths/` : les statistiques de l'article expliquées pas à pas (en anglais)

Licences : code sous licence MIT (`LICENSE`) ; les corpus gardent leur licence (CC BY-SA 4.0 pour GSD, ParisStories et Rhapsodie ; LGPL-LR pour Sequoia ; conditions du projet Orféo pour CEFC-gold).
