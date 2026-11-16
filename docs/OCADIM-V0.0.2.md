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

### Mesuré : le dirty census (16/11, scène chargée, 2 820 draws, 49,9 fps)
`
512 syncs, 350 720 pages scanned (2 718 dirty), 4 us a sync, 5-6 ns a page
```

**4 µs par sync, ~630 pages par sync.** À 6 submits par frame : **~24 µs par frame en tout**, soit 0,024 ms. Même en
comptant un iGPU trois fois plus lent sur ce code : ~0,07 ms.

**Donc #965 est sans objet chez nous :** les 7-15 ms que NX2navi mesure viennent de leur propre parcours (leur census
d'import), pas de cette passe. La sonde reste dans le code (éteinte par défaut) pour re-vérifier après un gros changement
de mémoire.

### Mesuré : la sonde de runs (`RX_VK_DRAW_RUNS=1`)

`draw_runs_note()` (`gpu/vk/vk_draw.cpp`) compte les draws consécutifs qui partagent un programme — le majorant de ce
qu'un auto-batching pourrait fusionner. Run de 90 s, scène chargée (2 360 draws par frame, 39,7 fps) :

```
6 553 000 draws, 4 680 000 runs → moyenne 1,40 draw par run, plus long 406
```

**Un programme change toutes les 1,4 draws.** Le plafond de fusion est donc de 1,87 M de draws sur 6,55 M, soit **28,6 %**
— et c'est avec la clé la plus optimiste (le programme seul ; un vrai batch demande aussi les mêmes formats et layouts).
Sur les 4,3 ms de binds + draw : **1,2 ms au mieux, ~5 %**.

**Verdict : l'auto-batching ne vaut pas son chantier.** Avec la clé stricte (programme + push constants + descripteurs),
la moyenne tombe à **1,06-1,10** : deux draws consécutifs du même programme lient presque toujours des **textures
différentes**. Fusionner exige donc bindless, et le plafond resterait ~1,5 draw par run (~9 %). Ce n'est pas un prototype
d'un jour, c'est un chantier de plusieurs semaines pour un gain borné.

Prochaines pistes, dans l'ordre : **le gouverneur de budget** (une page de menu, zéro risque), puis **le lookahead** (les
hoquets de 6,6 et 13,2 fps mesurés), puis **bindless** si on veut vraiment dépasser +10 %.

``

## Le lookahead, mesure : mauvaise cible

Les pires frames des journaux de Dimi (RX_VK_SLOW_LOG=30, ville et chargements) :

| Frame | total | draw | submit | descripteurs | commands | pipelines | memory sync |
|---|---|---|---|---|---|---|---|
| 14739 | 6512 ms | 1469 | 908 | 534 | 512 | 339 | 1,1 |
| 14751 | 2765 ms | 610 | 288 | 143 | 139 | 71 | 0,6 |
| 187067 | 3926 ms | 449 | 651 | 255 | 99 | 55 | 1,3 |

**La memoire ne coute rien** (memory sync ~1 ms) : anticiper les textures ne reglerait pas ces hoquets. Ils sont faits du **cout par draw de l enregistrement** (draw + descripteurs + submit + commands) quand 3 300 a 5 300 draws arrivent dans une frame, plus, pour les 6,5 s, ~4 s hors des postes mesures (le chargement du jeu).

Conclusion : le lookahead de ressources est ecarte. La cible est le **cout par draw de la preparation d etat** (idee 4) : memes chemins en frame normale (2,5 ms de binds) et en chargement.

## Les cles d etat, mesure : memoisation ecartee

RX_VK_STATE_KEYS=1 (avec RX_VK_DRAW_RUNS=1, qui calcule les hachages) compte les cles distinctes (programme + push + descripteurs) par fenetre de 2 000 draws :

`
2000 draws, 138 cles (14,49)   <- ecran repetitif, 236 fps
2000 draws, 1152 cles (1,74)
2000 draws, 1589 cles (1,26)
2000 draws, 1835 cles (1,09)
2000 draws, 1856 cles (1,08)
`

Mesure refaite proprement (la premiere avait plante : mon unordered_set n etait pas protege contre les threads de replay ; mutex ajoute). Scene lourde confirmee (2 797 draws max, 42,9 fps) : **1,21-1,28 draw par cle**. Un cache d etat eviterait donc au mieux ~20 % de la preparation par draw, soit ~0,5 ms (~2 %) : faible, garde pour plus tard.

Conclusion : ce stream est **unique par draw**, ce qui explique que batching, fusion de runs et cache d etat echouent tous. Le seul levier restant qui attaque la frame normale ET le chargement est **l enregistrement parallele / async** (le projet a le rendu threade ; voir docs/MINAGE-NX2NAVI.txt, PR #543 et son gate d ordre des evenements).

## Threaded rendering (async), mesure : pas de gain, et un cout deplace

Session en ville, async **On** contre la session d hier (Off), meme machine :

| Session | pire frame | submit | draw | programs | nouveaux pipelines |
|---|---|---|---|---|---|
| Off | 6512 ms | 908 | 1469 | 54 | 60 |
| On | **9804 ms** | **9415** | 2995 | **1581** | 265 |

Aucun flash (bonne nouvelle pour la stabilite du chemin), mais **le cout n est pas enleve : il est deplace dans submit** (9,4 s d attente), et la frame de chargement est pire. Les frames suivantes sont plus legeres (draw 20-200 ms).

Ce que la mesure designe : **programs 1581 ms** et 265 nouveaux pipelines sur cette frame -> c est la **traduction / compilation de programmes** au chargement, pas l enregistrement. Piste suivante : pre-traduire a partir du pipeline tour / des etats prepares, pas l async.

## La VRAM simulee a 2 Go, mesure : le chantier memoire est justifie

RX_VK_VRAM_MB=2048 (comme une carte 4-6 Go), meme scene, meme build :

| | 16 Go | 2 Go simules |
|---|---|---|
| fps | ~43-46 | **32,1** |
| uploads par frame | ~1-2 | **7,5** (2,3 Mo) |

**~25 % de fps perdus** par le thrashing. Mais la bande passante est negligeable (2,3 Mo) : le cout est dans le **decodage/deswizzle** de chaque re-upload (et la traduction, programs 5,5-9,9 s sur les frames lentes).

Donc l idee 1 est justifiee, dans sa version utile : garder la texture **deja decodee**, compressee en RAM (zstd, third_party/zbic), pour qu une re-mise en VRAM soit un decompresser + copier au lieu d un decodage complet.

Note : a 2 Go, le journal affiche 3 404 Mo de textures : le budget ne couvre pas tout ce que le renderer garde (a verifier).
