# Unités et composantes illocutoires

Pour chaque corpus, deux fichiers CoNLL-U, ponctuation conservée, colonnes de la source conservées, identifiants renumérotés :

- `*_unites_illocutoires.conllu` : les unités d'au moins trois mots analysées dans l'article (GSD et Sequoia après segmentation des coordinations et parataxes de propositions principales, `sent_id` suffixé `.1`, `.2`… ; les modifieurs antéposés au sujet réétiquetés `mod:periph` ; dans CEFC-gold, les `periph` nominaux réétiquetés `dislocated`).
- `*_composantes_illocutoires.conllu` : les composantes obtenues en coupant les dépendances macrosyntaxiques (`discourse`, `dislocated`, `vocative`, `parataxis`, `mod:periph` ; CEFC-gold : `dm`, `parenth`, `periph`) ; un segment détaché d'au moins trois mots devient une composante (`sent_id` suffixé `.c2`, `.c3`…), un segment plus court est retiré ; la composante hôte porte le suffixe `.c1`.

- GSD : 18456 unités, 22100 composantes
- Sequoia : 3185 unités, 3986 composantes
- ParisStories : 2594 unités, 3072 composantes
- Rhapsodie : 2699 unités, 3156 composantes
- CEFC : 17638 unités, 19037 composantes
