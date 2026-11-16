# v0.0.2 — ce qui entre, dans quel ordre

## Fait (branche `v0.0.2`)

**La fusion de l'amont.** Base `f637b42` (15/11 20:38, l'état dont on est parti) → `bbe421` (16/11 04:24). En 3 voies,
fichier par fichier : **229 fichiers fusionnés proprement**, 82 nouveaux, 40 régions de conflit (nos lignes + les leurs).

Ce que ça apporte, sans que ce soit de nous :

- `1db4c290` **perf** : les cibles de rendu de la frame sont réutilisées au lieu d'être créées et détruites deux fois par
  frame.
- `343a1dfa` **fix** : le render thread peut quitter son cœur quand un autre programme le prend — plus de blocages de
  30-40 ms. **Ça touche directement notre CPU affinity (CCX)** : à vérifier ensemble.
- `9f8958a5` : un réglage **Shadow resolution** (les ombres fines près de Link).
- `1764fed2` : **FPS counter overhaul 2** (taille, page de détails, graphe plus stable).
- `5f3bb44b` : **choix du périphérique de sortie audio**.
- `e4d035e9` : inversion horizontale de la souris (native et stick).
- Plus les tests qui vont avec : c'est eux qui diront si notre fusion a tenu.

## Les PR de NX2navi qu'on n'a pas encore (classées par public)

| PR | Ce qu'elle fait | Pourquoi elle est là |
|---|---|---|
| **#965** fermée | le *dirty census* d'import coûtait **7-15 ms aux GPU intégrés** | petits PC, le plus gros gain en vue |
| **#960** fermée | les textures relâchées gardent au plus **2 Go** | petits PC, VRAM |
| **#923** ouverte | garder les chunks du *lazy heap* dans une map : `heap_lazy=1` ne tombe plus à **12 fps** | petits PC |
| **#989** ouverte | batcher le *mesh fallback* par passe (GPU sans mesh shaders) | petits PC sans mesh shaders |
| **#1003** ouverte | les variantes de sommets de la dernière frame pour les **motion vectors** | qualité de **notre** FG |
| **#961** / **#958** ouvertes | cadence de la FG à la fréquence de l'écran | le P3 qu'on avait laissé de côté |
| **#1001** ouverte | `tools/bench.py`, un **banc d'essai reproductible** | la base de toute mesure |

## Mes idées, dans l'ordre

1. **Le banc d'essai avant tout.** Une scène, un parcours, N runs, la médiane : sans ça, on ne saura pas ce que la
   fusion de l'amont a changé (et on risque de « gagner » en croyant perdre).
2. **Les trois PR petits PC** (#965, #960, #923) : c'est ce qui répond au formulaire de retour, et ça se mesure.
3. **La FG : les motion vectors de #1003**, puis la cadence (#961/#958). C'est notre fonctionnalité la plus visible.
4. **FSR 3.1 FG**: le chemin existe dans le SDK ; il faut le valider (ou dire clairement dans le menu qu'il n'est pas
   encore là — c'est déjà écrit dans le README).
5. **Le HUD sans capture** : le SDK compose le HUD et ça n'a pas plu. L'autre voie : **laisser la FG générer l'image
   seule, puis dessiner le HUD par-dessus, en 2D, après** — la capture compute marche, c'est la composition qui était en
   cause.
6. **Petits PC, côté réglages** : un preset « OcaDim minimal » qui règle aussi nos lignes (segments 32, prefetch off,
   barrières off) au lieu de laisser le joueur deviner.

## La règle

Un seul build à la fois ; on ne tue jamais la préparation des shaders ; chaque étape se mesure avant d'être gardée.

## Sonde : `RX_VK_DIRTY_CENSUS=1`

Ce que NX2navi appelle son *dirty census* n'existe pas ici sous ce nom : l'équivalent logique est la passe de `mirror_sync()`
(`gpu/vk/vk_memory.cpp`), qui scanne les pages d'un pool et cherche, pour chaque page sale, son entrée de capture. C'est
elle qui coûterait 7-15 ms par frame sur un GPU intégré chez eux.

La sonde compte, sur place et sans rien changer au rendu : les pages vues, les pages sales, et le temps, cumulés sur
512 syncs, puis écrit une ligne :

```
vk: dirty census (RX_VK_DIRTY_CENSUS=1): 512 syncs, 4100 pages scanned (37 dirty), 41 us a sync, 5 ns a page
```

Lecture : si `us a sync` reste sous la dizaine, la passe n'est pas le problème et il n'y a rien à optimiser là. Si elle
monte à plusieurs centaines de µs (ou plus) sur un iGPU, on a notre 7-15 ms — et la suite est de remplacer le scan par une
liste de pages écrites par pool, au lieu de reparcourir les régions.

Coût quand la sonde est éteinte : un `bool` par sync.

### Mesuré (16/11, RX 9070 XT, scène chargée : 2 820 draws, 49,9 fps)

```
512 syncs, 350 720 pages scanned (2 718 dirty), 4 us a sync, 5-6 ns a page
```

**4 µs par sync, ~630 pages par sync.** À 6 submits par frame : **~24 µs par frame en tout**, soit 0,024 ms. Même en
comptant un iGPU trois fois plus lent sur ce code : ~0,07 ms.

**Donc #965 est sans objet chez nous :** les 7-15 ms que NX2navi mesure viennent de leur propre parcours (leur census
d'import), pas de cette passe. La sonde reste dans le code (éteinte par défaut) pour re-vérifier après un gros changement
de mémoire.

