# OcaDim

**La version PC d'*Ocarina of Time* (Switch 2), compilée depuis le `.nup` de ta propre copie du jeu — par Dimi42FR.**

OcaDim est un fork de [Longshot](https://longshot.magicbean.dev/) (lui-même un fork de
[Hookshot](https://github.com/NotRexed/Hookshot)) : il repart de son meilleur état et embarque en propre ce qui y a été
appris, mesuré et codé.

## Les pages

| Page | Ce qu'elle contient |
|---|---|
| **[README.md](README.md)** | la présentation complète : ce qu'OcaDim ajoute à la base, les preuves mesurées, puis le manuel de l'amont |
| **[CREDITS.md](CREDITS.md)** | la généalogie, ce que nous avons écrit fichier par fichier, tous les composants tiers et leur licence |
| **[docs/OCADIM.md](docs/OCADIM.md)** | la carte technique : le fine-profile du replay, le prefetch des descripteurs, les leçons d'implémentation |
| **[docs/SETUP-OCADIM-DESIGN.md](docs/SETUP-OCADIM-DESIGN.md)** | le design du Setup qui compile chez le joueur |

## En deux lignes

La **frame generation du SDK d'AMD** (FSR) tourne dans le jeu, alimentée par la vraie profondeur, les vrais vecteurs de
mouvement, le jitter et la caméra de la scène, et se choisit dans le menu (*Frame generation by*). Des correctifs
**au-delà de 60 fps**, des **leviers CPU** mesurés (batched submits, prefetch des descripteurs, affinité CCX, workers et
segments du replay), et un **Setup** qui compile le jeu chez le joueur sans aucune donnée de jeu dans le paquet.

## Compiler

Double-clic sur **`OcaDim - COMPILER.bat`** (ou glisse-dépose ton `.nup` dessus). La première compilation : de 10 minutes
à plus d'une heure — les outils se téléchargent seuls, le jeu se traduit, se compile, puis prépare ses shaders en
s'ouvrant tout seul. **Ne le ferme jamais pendant cette préparation.**

## La règle, sans exception

Le `.nup` et le jeu construit ne se partagent pas. Chacun compile depuis SA copie. Ce qui se partage : ces sources, ce
compilateur.

## Licence

GPL-3.0 ([LICENSE](LICENSE)). Le socle est celui de Longshot et de la scène des récompilations : le mérite en est le leur,
ce dépôt en est un prolongement personnel, à jour, avec ses propres ajouts documentés dans [CREDITS.md](CREDITS.md).
