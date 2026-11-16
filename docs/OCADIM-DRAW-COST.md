# Où passent les 5,9 µs d'un draw (mesuré, pas supposé)

Date : 16/11/2026. Sonde : `RX_VK_PROF_FINE=1` (existante), étendue de huit sections pour fermer le compte.

## Méthode

`RX_VK_PROF_FINE` chronométrait déjà les sections du `draw()` : banques de descripteurs, c1, UBO utilisateur, storage
buffers, textures, hazards+passe, bind pipeline, bind descriptors (dont le push), push constants, état dynamique, binds
vertex/index, appel de draw — et comptait, par draw, les pushes (pleins/delta/vides), les writes poussés, les binds.
Il ne couvrait que 12,2 ms des 16,6 ms de `draw()` par frame. Quatre sections ont été ajoutées pour trouver le reste :
`draw all (exact)`, `program pick`, `pipeline pick`, `sampled targets`, puis `targets`, `skip checks`, `dlss/skin notes`
et `the rest (tail)`. Le compte est fermé à 0,8 ms près — le coût des scopes eux-mêmes (20 lectures d'horloge par draw).

## Le bilan (55,3 fps, 2 753 draws, frame de 18,1 ms)

| Section | ms/frame | Par draw |
|---|---|---|
| Descripteurs : textures | 2,43 | 0,88 µs |
| Appel de draw (`vkCmdDraw*`) | 1,80 | 0,65 µs |
| Sélection de programme | 1,48 | 0,54 µs |
| Bind descripteurs (dont push 1,27 / 0,66) | 1,27 | 0,87 push |
| Binds vertex + index | 1,20 | 0,54 + 0,97 binds |
| UBO utilisateur | 1,05 | 2,31 appels |
| Notes DLSS/FSR (par draw) | 0,92 | — |
| Storage buffers | 0,50 | — |
| État dynamique | 0,44 | 0,93 pris du draw d'avant |
| Sélection de pipeline | 0,42 | 0,33 bind |
| Hazards + passe | 0,33 | — |
| Bind pipeline | 0,28 | — |
| Banques, c1, constantes, cibles, skips, échantillonnées | 0,79 | — |
| Tête et queue non instrumentées | 0,79 | — |
| **`draw()` entier (exact)** | **16,22** | **5,9 µs** |

Le GPU fait 1,6 ms de travail par frame : la frame est **entièrement** du CPU d'enregistrement, et `draw()` en est 90 %.

## Ce que l'enregistreur fait déjà bien

Par draw : **0,68 push de descripteurs en delta** contre 0,19 pleins (les writes ne sont pas tous renvoyés), **0,33 bind
de pipeline** (deux draws sur trois le sautent), **0,39 commande de bind d'index** (0,97 appels, le reste sauté),
**0,93 état dynamique pris du draw précédent**. Les optimisations évidentes sont donc déjà là : le coût est réparti, pas
concentré sur une bêtise.

## Le vrai levier : le découpage du replay

Le replay est parallèle (4 threads) mais par **segments de ~32 draws**, et un command buffer de moins de `2 × per`
draws est enregistré **séquentiellement** sur le thread de replay. Le log le dit :

```
vk: parallel replay: 2000 command buffers were too small for segments of ~32 draws and dispatches,
    so it has not engaged
```

Le plancher du réglage était codé à 32 (`std::max(32, ...)`). Mesures :

| Réglage | fps |
|---|---|
| défaut (4 threads, segments 32) | 55,3-55,6 |
| `RX_VK_PARALLEL=8` | 53,7 |
| `RX_VK_PARALLEL_SEG=8` (plancher descendu à 8) | 53,3 |

Les deux réglages sont **pires** : plus de threads ne sert à rien, et un découpage plus fin paie le surcoût des segments
(chaque segment est un command buffer et une soumission) plus qu'il ne reprend. La segmentation est à son optimum pour ce
jeu ; c'est une piste fermée, pas une piste ouverte.

## Le gain pris : les notes DLSS/FSR par draw

`temporal_note_scene_draw` et `fsr3_inputs::note_scene_draw` sont appelées pour **chaque** draw qui a une couleur et une
profondeur (0,92 ms par frame, deux verrous par draw), et leur deuxième chose est de constater que la frame a déjà noté
sa plus grande cible et de sortir. Deux draws consécutifs visent presque toujours les mêmes cibles : l'appel est un
no-op, et on le saute maintenant avant le verrou, en gardant la dernière (couleur, profondeur, largeur, hauteur) du
thread. Une cible plus grande change les dimensions, donc la règle « la plus grande gagne » est préservée.

