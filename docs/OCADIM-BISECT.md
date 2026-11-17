# Bisect du flash de textures (17/11/2026)

But : trouver le commit qui introduit les flashs de 0,1 s (textures, ciel, drapeaux, bouclier), absents de la 0.0.1.

Intervalle : `8ca4dba1..HEAD` (88 commits, premier parent). Méthode : build du commit dans l'arbre
`longshot-001`, `make_game.py --update F:\test`, test visuel au marché. Le flash est **intermittent** : un
résultat « propre » n'est fiable qu'après plusieurs minutes.

| Commit | Index | Résultat |
|---|---|---|
| `8ca4dba1` (0.0.1) | base | **propre** |
| `31495bc6` (FG P4) | 21 | **propre** |
| `3309f921` (ordre README) | 32 | **propre** |
| `2a845863` (async mesuré) | 38 | **propre** |
| `e490b62f` (sonde MEM_CENSUS) | 41 | **propre** |
| `3ac201c5` (notes DLSS/FSR) | 44 | flash observé — **mais ce commit ne change que docs + un test** : le flash vient d'un commit antérieur (42/43) ou d'un faux positif |

Dernier intervalle : 42..43 (43 touche le chemin du draw : `RX_VK_PROF_FINE`, scopes de mesure).
Prochain test : build complet (HEAD) pour confirmer le retour du flash, puis revert de 42/43 s'il revient.
