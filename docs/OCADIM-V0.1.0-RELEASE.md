# OcaDim 0.1.0 — notes de version (prêtes pour GitHub)

> Brouillon à coller dans la release. Tout ce qui suit est mesuré ou vérifié dans le dépôt ; aucune promesse.

## En tête

**La base passe à l'amont du 16 novembre** (40+ commits) et **corrige une régression de 6-7 fps** en ville. Deux
chantiers ont été **écartés sur mesure** (dirty census, auto-batching) plutôt que codés à l'aveugle, et un **gouverneur de
budget** fait le lien entre le Breakdown et les réglages.

## 1. La fusion de l'amont

Base `f637b42` (15/11 20:38) → `bbe421` (16/11 04:24), en 3 voies fichier par fichier : **229 fichiers fusionnés
proprement**, 82 nouveaux, 40 régions de conflit tranchées (nos lignes gardées quand elles ne recouvraient pas la refonte
de l'amont).

Ce que ça apporte, sans que ce soit de nous :

- `1db4c290` — les cibles de rendu de la frame sont réutilisées au lieu d'être créées et détruites **deux fois par frame** ;
- `343a1dfa` — le thread de replay peut quitter son cœur quand un autre programme le prend (plus de blocages de 30-40 ms) ;
- `9f8958a5` — réglage **Shadow resolution** ;
- `1764fed2` — **compteur de FPS refait** (taille, page de détails, graphe plus stable) ;
- `5f3bb44b` — **choix du périphérique de sortie audio** ;
- `e4d035e9` — inversion horizontale de la souris (native et stick) ;
- et les tests qui vont avec.

## 2. Le correctif de régression (le plus important de la version)

À **nombre de draws égal**, la ville (Place du Château, ~2 300 draws) perdait 6-7 fps après la fusion :

| Draws | Avant | Après correctif | 0.0.1 |
|---|---|---|---|
| 2 000-2 600 | 40,6 fps (p10 36,7) | **46,2** (p10 **41,2**) | 47,2 (p10 31,2) |
| 2 600-3 400 | 38,1 (p10 27,3) | **45,6** (p10 21,3) | 44,8-48,0 |

Deux causes, deux lignes :

- **`shadow_res` par défaut à `1`** (les 1 600 du jeu) au lieu d'**Auto**, qui choisissait **3 072** sur une carte 16 Go ;
- **épinglage strict du thread de replay** par défaut, comme avant la fusion (`RX_VK_RT_STRICT_PIN=0` rend la liberté
  nouvelle).

## 3. Trois sondes (et deux chantiers écartés)

Toutes éteintes par défaut (un `bool` par événement quand elles ne servent pas).

| Sonde | Ce qu'elle mesure | Résultat | Décision |
|---|---|---|---|
| `RX_VK_DIRTY_CENSUS=1` | la passe de `mirror_sync` sur les pages sales | **4 µs par sync**, ~24 µs par frame | **#965 sans objet** |
| `RX_VK_DRAW_RUNS=1` | draws consécutifs au même programme | 1,32-1,59 draw/run | insuffisant seul |
| idem, clé stricte (+ push constants + descripteurs) | ce qu'un batch exigerait vraiment | **1,06-1,10** | **auto-batching écarté** : il faudrait bindless pour ~9 % au mieux |

## 4. Le gouverneur de budget

Nouvelle ligne dans l'onglet **Performance** : elle lit le Breakdown, compare à la cible du cap, désigne la **plus grosse
part** et le levier qui y répond (renderer → résolution/textures ; attente GPU → résolution/ombres ; pacing → cap/V-Sync ;
jeu → threaded rendering). Elle **n'applique rien toute seule** : les leviers utiles demandent un redémarrage, donc les
nommer est la partie honnête. Une ligne par pression dans `longshot_log.txt` (`menu: Budget governor: …`).

## 5. Documentation

- `README.md` : les 9 lignes du tableau des options qui manquaient entre les deux versions sont écrites, **dans l'ordre
  du menu** (`test_readme_menu_rows` 6/6).
- `docs/OCADIM-V0.0.2.md` : la fusion, les sondes et leurs verdicts, les pistes suivantes.

## Vérifications de la version

- Build `--standalone` : **0 échec**, exe 438 Mo + `longshot_vk.dll` 17,0 Mo.
- `test_readme_menu_rows` **6/6**, `test_menu_i18n` **OK**, `test_menu_sections` **OK**.
- Run de contrôle : 94 s, 4 920 présents, **aucun crash, aucun device lost**.
- Ville après correctif : **46,2 fps** médian (p10 41,2), soit le niveau de 0.0.1 avec de meilleures pires frames.

## Ce qui n'est **pas** dans cette version

- **Pas de batching** : mesuré, il exige bindless (cf. §3).
- **Pas de FSR 3.1 FG** : seul le chemin FSR 4 (RDNA 4) est livré.
- **Pas de lookahead** : les hoquets de 6,6 et 13,2 fps mesurés restent la prochaine cible.
- **Pas de bindless** : c'est le prérequis du batching et son gain propre (~2,4-3 ms), mais c'est un chantier long.

## 6. Ajouté après la rédaction (16/11, soir) — perf et mémoire

Même build, mesuré dans l'arbre de dev et sur l'installation (RX 9070 XT) ; à reprendre tels quels si la 0.1.0 n'est
pas encore publiée.

**Pour le joueur**

- **Moins de textures blanches au loin après un chargement de zone.** Les uploads ASTC repoussés faute de budget
  étaient dessinés avec un placeholder. Le budget quadruple désormais pendant une frame longue (aucun présent depuis
  100 ms) : mesuré sur un run, **1 303 → 571 textures repoussées**, la frame d'uploads la plus lourde de 115 à 256 ms
  (absorbée par un chargement qui dure déjà 2,8 s), et **fps de jeu inchangés** (61-62).
- **Le rendu parallèle s'engage sur les machines à command buffers courts.** La granularité réelle était le point du
  dry pass (un tous les 64 draws) : sous 64 draws, rien ne pouvait être découpé, quel que soit le réglage. Une session
  qui ne fait que des buffers courts abaisse maintenant les deux ensemble (segments 32→16→8, points 64→8). Mesuré :
  **6,0 segments par command buffer** au plancher, dry pass 0,34 ms, fps inchangés là où il s'engageait déjà. C'est le
  levier d'un PC à 6 cœurs qui enregistrait 18-21 ms sur un seul thread avec 3 workers inactifs (rapport RTX 2060).
- **~0,75 ms par frame de moins** : les notes DLSS/FSR n'étaient plus recalculées à chaque draw quand les cibles n'ont
  pas changé (0,92 → 0,12-0,17 ms).

**Mémoire**

- **Le seed de shaders (539 Mo sur une installation préparée) est mappé au lieu d'être copié en RAM.** Il n'est jamais
  écrit : ses pages sont celles du fichier, récupérables sous pression et hors du commit privé — celui qui règle le
  budget de textures sur les petites cartes.

**Diagnostic**

- Le log dit désormais **ce que le joueur a demandé pour le frame generation** :
  `vk: frame generation asked: on (3x), by AMD FSR FG`. Un rapport sur une carte où l'AMD FG manque ne permettait pas
  de savoir si l'option était allumée.

**Ce qui n'a pas changé**

- **Auto** pour le rendu threadé reste actif à partir de 12 processeurs : le premier rapport de crash (RX 6900 XT) a
  été rapproché du frame generation activé par le testeur, pas du rendu threadé, et la piste reste à confirmer.

