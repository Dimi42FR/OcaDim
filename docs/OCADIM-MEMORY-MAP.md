# Où va la mémoire (mesuré sur l'installation, 16 Go, 16/11)

Source : `F:\test\logs\longshot_log.txt`, en jeu, 600 frames. But : savoir ce qui reste à gagner, et ce qui est déjà
réglé avec sa raison.

## VRAM : 10 080 Mo utilisés sur 13 123 autorisés

| Poste | Mesure | Ce que c'est |
|---|---|---|
| Textures | **3 994 Mo** / 1 953 textures | le jeu de travail du jeu (budget 11 000 Mo : ce n'est pas un plafond qui mord) |
| Miroirs de la mémoire invitée | **1 130 Mo** (98 pools, 88 sparse) | les pools dont le contenu vit dans le miroir (tables lues et écrites par le GPU) ; 217 Mo déjà rendus par les blocs sparse |
| FSR 4 | 87 Mo d'images + 180 Mo à lui | l'upscaler |
| Cache de pipelines (driver) | **1 400 Mo** | le fichier `longshot_vk_pipelines.bin`, lu entier au démarrage et gardé par le driver |
| Modules de shaders, swapchain, attachements | le reste | chez le driver |
| Espace libre dans les blocs VMA | 396 Mo | fragmentation de l'allocateur, pas du gaspillage récupérable |

Les plus grosses textures individuelles sont modestes (64 Mo, 16 Mo) : les 4 Go sont faits de beaucoup de textures
moyennes, pas d'une pièce unique.

## RAM : 7,6-8,4 Go de working set au pic

- `start` (le mode de cette installation, forcé par le marqueur `longshot_load_start.txt`) : tous les programmes avant le
  titre, **4-5 Go de plus** que `create` d'après `load_default.h`.
- `create` mesuré ici : **pic 6 290 Mo**, mais **crash driver** (`amdvlk64`, après une traduction de 3,5 s). Le mode n'est
  pas viable sur ce PC tant que ce plantage n'est pas réglé, et le marqueur est donc justifié.

## Les leviers déjà réglés (ne pas les rouvrir sans un nouveau chiffre)

| Levier | Réglage | Pourquoi il ne descend pas |
|---|---|---|
| Pool de cibles de rendu | 256-768 Mo (un douzième de ce que le driver autorise) | à 256 Mo, Castle Town détruisait ~22 000 images en 100 s pour dépassement, et le replay en refaisait autant |
| Textures finalisées gardées | 512 Mo | en dessous, des textures reviennent vides (issues 107 et 386 : herbe en plaques, sol noir) |
| BC3 scratch (160 Mo) | gardé une fois fait | rendu, des textures sortaient brouillées/arc-en-ciel (issue 993) |
| Miroirs des pools à tables | jamais rendus | rendus, cyan résiduel en jeu et sur le menu (RX 5500M) |

## Ce qui reste vraiment

1. **Le cache de pipelines : 1 400 Mo chez le driver**, dont la préparation a rempli 32 778 pipelines pour toutes les
   zones. Ce que le jeu en utilise par session, à côté : les fichiers de jeu pèsent **1,2 Mo** (« 6 play files merged
   (1265 KB) »). Un découpage par zone (l'idée 3 de la liste) est le seul poste à trois chiffres qui reste, et il
   demanderait que la préparation écrive des caches par zone — un projet, pas un réglage.
2. **Le mode `create`** : −1,3 Go de RAM, bloqué par un plantage driver sur une grosse traduction. C'est de la
   robustesse avant d'être de la mémoire.
3. Les 4 Go de textures sont le jeu de travail ; les réduire veut dire évincer ce qui sert, et on a mesuré ce que ça coûte
   (et que le blanc vient des uploads reportés, pas du budget).
