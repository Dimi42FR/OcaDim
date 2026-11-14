# OCADIM — la carte technique

*(ce que la session du 2026-11-14 a mesuré, codé et appris — le cap des
prochaines)*

## Le replay, où passe le temps (le fine-profile, la donnée)

Par frame de scène lourde (~2850 draws, 5800X + RX 9070 XT) :

| morceau | ms/frame | état |
|---|---|---|
| **textures** | **5,6-6,8** | **le prochain chantier** — dont `of tex: view` 4,1-5,2 (texture_view_of) |
| vertex+index binds | 2,5-2,7 | deuxième |
| user uniform buffers | 1,4-2,0 | ✅ le prefetch est passé par là |
| draw call | 1,7 | |
| bind descriptors | 1,0 (le push 0,64) | |
| storage buffers | 0,7 | |
| banks c0/c2 | 0,28 | ✅ le cache marche |
| hazards+pass / dynamic state / push constants | 0,31 / 0,34 / 0,11 | |

## Le prefetch des descripteurs (landé, off par défaut)

**Le principe** : le dry pass du replay passe AVANT les workers — il
empile ses points ; un helper BELOW_NORMAL re-marche chaque tronçon,
miroir des binds UBO et des updates inline du stream, et publie dans
une table seqlock les bytes de chaque overlay que le record demandera :
les pages de la capture, les updates du lieu par-dessus, clé
`(addr, take, lim, view, rec)`.

**Trois pièces** :
1. **Les bytes** : le record les memcpy au lieu de relire la mémoire
   guest au travers de la capture (le mutex des pools + la recherche de
   page + le scan d'updates, par descripteur, par worker)
2. **Les asks apprises** : le record note ce qu'il demande
   (`pf_learned`) — les tables du programme connaissent la taille
   *utilisée*, le helper publie le plus grand ask vu par borne
3. **Le négatif** : « pas d'update sur cette borne à ce lieu » —
   `ub_overlay` ET `ub_read` sautent leurs scans (~2600/buffer × 2)

**La justesse** : clé auto-vérifiante (un ask non couvert = un miss =
le chemin d'avant, mot pour mot), seqlock (une réécriture sous une
copie est vue), les stamps `view`/`rec` couvrent le helper en retard.
Un miss ne coûte que ce que le code coûtait avant.

**En jeu** : 357-682 overlays servis par fenêtre, ~215k scans sautés,
zéro artefact.

## Les leçons d'implémentation (celles qui coûtent une soirée quand on les saute)

- Un helper **sans recording ne doit pas créer de texture**
  (`texture_get` enclenche l'upload dans le recording courant)
- Les tests du projet **coupent le source par son texte** : pas de
  `case NOP_*` dans du code neuf plus haut dans le fichier, des
  placeholders de fixture délimités (`@SYNC@` était caché dans
  `RX_VK_ASYNC`)
- Le prune de `ub_updates` n'arrive qu'entre soumissions ; les updates
  d'avant un buffer voyagent en **copies** dans l'item de départ
- La ligne de log du helper (les compteurs de gate) a trouvé en un run
  ce que trois hypothèses n'avaient pas trouvé : **instrumente
  d'abord**

## Le cap des prochaines

1. **Les vues de textures** (4-5 ms) : les touches d'epoch
   (`texture_touch_quick` qui échoue → `ParLock`, la contention avec
   les workers), les views hors cache — la même question que le
   prefetch UBO : pré-résoudre dans le helper ce que le record refait
2. **Les commands** (le P4 du design) : les hazards/barriers
   pré-calculés, le même pattern seqlock
3. **Le verdict fps propre** : la même route, le flag on/off, deux runs
4. Si le render thread est un jour activé et que les flashs reviennent :
   le port fidèle de la capture au signal (la faisabilité est
   verrouillée — les ranges UB vivent dans `s.ubo[stage][index]`)

## La recette de build (celle qui marche)

```
python -I nx2/lift.py --standalone --write      (une fois, ~2 min)
python -I nx2/build.py --standalone --jobs 14   (incrémental)
python -I nx2/make_game.py --update <jeu>       (le packaging)
python -I -B tests/run_all.py                   (les tests)
```

Avec, avant chaque commande : `PATH` des outils (llvm-mingw + python),
`RX_CPM`, `WGPU_NATIVE`, `LONGSHOT_MINGW` posés — le compilateur
`OcaDim - COMPILER.bat` le fait pour toi.
