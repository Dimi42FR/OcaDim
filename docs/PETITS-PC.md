# OcaDim et les petits PC

Rien à régler : OcaDim lit la carte et la mémoire de la machine et prend ses réglages tout seul. Ce document dit **ce qui
est fait**, **ce que ça vaut**, **ce qui reste** — et quoi nous envoyer quand ça ne tient pas.

## Ce qui est automatique

**La VRAM des textures suit la carte**, pas un preset. Le cache de textures prend 7/12 de la mémoire de la carte (ou
tout sauf 5 Go), avec les tailles des presets :

| Carte | Cache de textures |
|---|---|
| 4 Go | **2,2 Go** |
| 6 Go | **3,6 Go** |
| 8 Go | **4,8 Go** |
| 12 Go | **7,2 Go** |
| 16 Go | **11 Go** |
| pas de heap dédié | **4 Go** |
| moins de 12 Go de RAM, carte de plus de 6,75 Go | **45 % de ce que le pilote autorise**, plafonné à 6 Go |

C'est ce plafond qui évite le cas réel où le pilote pagine la VRAM pour de bon : une RTX 3060 Ti tombée à **14 fps** avec
5,1 Go de cache. Le pool se vide de lui-même à **90 % puis 97 %** de la limite du pilote : le jeu rétrécit avant de
demander trop.

**Le budget d'uploads ×4 pendant les chargements** : **1 303 → 571 textures ASTC repoussées**. La frame la plus lourde
d'une arrivée de zone est absorbée par le chargement au lieu de tomber en jeu — c'est le hoquet qu'on sent sur un CPU ou
un disque lent.

**Les ombres sont verrouillées au 1600 du jeu.** Auto prenait **3072** sur une carte de 16 Go : **6-7 fps en ville** et de
la mémoire pour rien.

**Les grosses textures ASTC restent en BC7, 1 octet par texel** — pas de bascule en RGBA8, qui serait **4 fois plus de
VRAM** et doublerait la mémoire au chargement d'une zone.

**#1242** ne refait plus le clear des textures gardées en blocs ASTC (une session réelle montre une 12288×12288 de 288 Mo
lue puis effacée sur le GPU). **#1250** lie ce qu'un upload sparse a déjà mis en file quand le staging manque — le cas
d'une carte pleine. **#906** passe le mesh fallback en SoA pour les GPU sans mesh shaders.

**Le seed de shaders est mappé, plus copié** : **539 Mo de RAM en moins** à chaque lancement.

**La préparation des shaders respecte déjà la mémoire** : 4 Go réservés au reste du PC, 768 Mo par worker.

## Ce qui reste à faire

- **#960** — les textures libérées gardent au plus **2 Go** : c'est le plus gros gain restant sur une carte de 8 Go.
- **#923** — le `heap_lazy` qui tombe à **12 fps**.
- **#1462** — la libération des cibles finalisées (VRAM des longues sessions).
- **#989** — le mesh fallback batché, pour les GPU sans mesh shaders.
- Un **preset « OcaDim minimal »** dans le F1, qui règle d'un coup les lignes du moteur (segments, prefetch, barrières).

Le dirty census (#965) a été mesuré ici : **4 µs par sync, 0,024 ms par frame**. Il n'y a rien à gagner de ce côté.

## Ce qu'on a besoin de tes chiffres

Si ça tient mal sur ta machine, ce qui aide le plus :

1. **`longshot_log.txt`** (dans `logs/`, à côté du jeu) — la première ligne dit la version, et les compteurs de mémoire y
   sont déjà.
2. **Ta carte et ta RAM** — la ligne `Auto (this PC) would be: ...` du log les donne, avec le palier choisi.
3. **Où** ça tient mal : le village, le marché, un donjon, un chargement.
4. **Les fps** au même endroit, avant et après avoir changé une seule ligne du F1.

Un retour qui dit *où ça casse* vaut dix « c'est bien ».
