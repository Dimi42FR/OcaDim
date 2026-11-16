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
profondeur, et leur deuxième chose est de constater que la frame a déjà noté sa plus grande cible et de sortir — après
un verrou chacune. Deux draws consécutifs visent presque toujours les mêmes cibles : l'appel est un no-op, et on le
saute maintenant avant le verrou, en gardant la dernière (couleur, profondeur, largeur, hauteur, frame) du thread. Une
cible plus grande change les dimensions, donc la règle « la plus grande gagne » est préservée ; la frame entre dans la
comparaison, donc la caméra est bien re-notée au premier draw de chaque frame.

Mesuré au profil fin, même scène, même build à une ligne près :

| | avant | après |
|---|---|---|
| `of it: dlss/skin notes` | 0,92 ms/frame | **0,12-0,17 ms** |

Soit ~0,75 ms repris, 4 % d'une frame de 18,1 ms. Vérifié que l'upscaler suit : `AMD FSR 4: 600 frames drawn` et un
jitter non nul dans le status, comme avant.

## Les textures : ce qui a été essayé, et pourquoi c'est écarté

Le plus gros poste nommé (2,43 ms) est la résolution des descripteurs de texture : ~4,6 par draw, dont la vue coûte
0,85 ms (67 ns par vue). Le mécanisme de réutilisation par étage existe (`kept_tex_holds`, `ks->tex_on`), mais il ne
touche que **0,16 binding par draw**. La raison est dans le code, pas dans une mesure : `desc_keep_textures` refuse un
étage dont un descripteur passe par un **programme de handles** (`d.handle_program != ~0U`), donc tous les étages qui
lisent leurs textures dans une table (OoT en est plein) n'y ont jamais droit.

Essai fait et **écarté** : remplacer l'invalidation globale (`dgen`, qui bouge à chaque texture retirée, les cibles
transitoires comprises) par un contrôle par texture (même objet via son `serial`, non retirée, `view_gen` inchangée).
Mesuré : `stages' textures kept` reste à 0,16 et `textures` à 2,59 ms — aucun gain. Reverti, l'arbre est propre.

Pour rouvrir ce poste il faudrait **versionner les tables de handles** (le tampon que lit le programme de handles) pour
que le kept puisse s'appliquer aux étages à table : c'est un changement de conception, pas une clé plus permissive, et
c'est le même terrain que l'issue 1126 (vues périmées), donc à faire avec des captures à chaque étape.


## Sur l'installation de référence (`F:\test`, après l'update du 16/11)

Même profil fin, même build, sauvegarde et scène de l'installation (ce n'est **pas** un A/B avec l'arbre de dev : les
scènes diffèrent ; c'est ce que voient les joueurs) :

| | arbre de dev | `F:\test` |
|---|---|---|
| `draw()` par frame | 16,2 ms | **20,4-20,7 ms** |
| dont textures | 2,43 ms | **5,3-5,7 ms** |
| dont résolution de vue | 0,85 ms | **3,4-3,8 ms** |
| dont notes DLSS/FSR | 0,12-0,17 ms | **0,21 ms** (le saut tient) |
| draws par frame | 2 750 | 2 000-2 600 |
| textures résidentes | ~2 800 Mo | **2 081 / 4 573 Mo** |
| uploads par frame | 0,1 Mo | 0,5 (2-3 Mo) |
| pipelines | 1 123 | 44 276 (11 513 ms) |
| fps | 53-56 | 52-62 |

Sur l'installation réelle, **les textures sont le double** de l'arbre de dev et la résolution de vue à elle seule fait
3,4-3,8 ms : ~28 % d'une frame de 19 ms. C'est le poste le plus rentable du projet pour les joueurs, et il est fermé
par les étages à table de handles (section précédente).


## Le kept étendu aux tables de handles : net zéro (16/11, session 2)

`desc_keep_textures` refusait tout étage dont un descripteur vient d'un **programme de handles**. L'ouvrir demande de
relire la table à chaque réutilisation (son contenu peut changer sans que rien ne le signale) et de comparer aux handles
gardés. Fait, plus le contrôle par texture (au lieu de la génération de destruction globale) pour ne pas jeter
l'ensemble quand une cible transitoire disparaît.

Résultat mesuré, même scène, profil fin :

| | avant | après |
|---|---|---|
| `stages' textures kept` par draw | 0,16 | **0,25** (62 % des étages) |
| `textures` | 2,43-2,53 ms | **2,43-2,52 ms** |
| `of tex: view` | 0,83 | 0,74-0,83 |

Les compteurs ajoutés nomment les refus restants : « its key moved » 0,13, « never whole » 0,02-0,05, « a slot moved » 0,
« a view moved » 0. Autrement dit : **le kept coûte à peu près ce qu'il économise**, parce que le coût n'est pas la
résolution de vue mais la copie des `VkDescriptorImageInfo` et des writes, qu'il faut de toute façon refaire à chaque
build. Changé puis **reverti** : pas de gain, donc pas de risque à prendre sur des vues gardées entre frames (terrain de
l'issue 1126).

## `create` au lieu de `start` : la mémoire ne se gagne pas là (16/11, session 2)

L'installation force `start` (marqueur `longshot_load_start.txt`) : tous les programmes avant le titre, 4-5 Go de RAM et
~5 min de préparation. Mesure d'une session en `create` sur `F:\test` :

- pic de working set **6 290 Mo** (contre ~7,6-8,4 Go avec `start`) — le gain de RAM est réel ;
- mais **crash** : `0xc0000005 (read 0xffffffffffffffff)` dans `amdvlk64.dll` après une traduction de 3,5 s
  (`slow submit 894 ms, programs 3518.7`), à ~23 000 présents, sur l'écran-titre.

Le marqueur est donc justifié sur ce PC, et `start` reste. Une session en `create` n'a pas sa place ici sans régler
d'abord le plantage du driver sur les grosses traductions.


## Ce que les fps ne disent pas

Les comparaisons de fps entre deux runs ne valent rien ici : la sauvegarde et la zone ont changé plusieurs fois pendant
la session, et la même scène donne 53 à 56 fps d'un run à l'autre (les runs `mem-census*`, `draw-cost*`, `notes-skip2`
le montrent). Un run peut aussi finir sur un écran de menu (le run `tex-keep` a passé la moitié du sien sur l'écran
Load : sa capture le montre). Les chiffres qui tiennent sont ceux du profil (ms par frame), et même eux ne valent que
si le run a réellement joué : filtrer les lignes `draw all (exact)` au-dessus de 5 ms.


