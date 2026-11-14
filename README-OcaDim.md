# OcaDim

La version PC de *Zelda: Ocarina of Time* (Switch 2), compilée depuis le
`.nup` de ta propre copie du jeu — **By dimi42FR**.

OcaDim est né du travail de la session du 2026-11-14 sur Longshot : le
dépôt repart de son meilleur état et embarque en propre ce qui y a été
appris et codé (voir [docs/OCADIM.md](docs/OCADIM.md) pour la carte
technique complète).

## Ce qu'OcaDim a de plus que la base

| | |
|---|---|
| **Le prefetch des descripteurs** | un thread helper pré-résout, pendant le replay, les bytes des uniform buffers que le record demande : moins de travail sur le chemin critique, les fps montent dans les scènes lourdes. Off par défaut, `RX_VK_DESC_PREFETCH=1` |
| **Le cache négatif** | le record saute ses scans de listes d'updates (~2600 descripteurs par buffer, deux fois) sur le tampon du helper |
| **Le play profile committé** | le renderer compilé avec le profil de jeu : ~3-5 % de frame time |
| **Le render thread** (#588) | off par défaut ici (`RX_VK_ASYNC=0` dans l'env de jeu conseillé), à tester à part |

## Compiler

Double-clic sur **`OcaDim - COMPILER.bat`** (ou glisse-dépose ton `.nup`
dessus). La première compilation : de 10 minutes à plus d'une heure —
les outils se téléchargent seuls, le jeu se traduit, se compile, puis
prépare ses shaders en s'ouvrant tout seul. **Ne le ferme jamais
pendant cette préparation.**

## La règle, sans exception

Le `.nup` et le jeu construit ne se partagent pas. Chacun compile
depuis SA copie. Ce qui se partage : ces sources, ce compilateur.

## La généalogie

Le code vient du projet Longshot (et, avant lui, des récompilations de
la scène) — le mérite du socle est le leur ; ce dépôt en est un
prolongement personnel, à jour, avec ses propres ajouts documentés.
Licences : [LICENSE](LICENSE) et les notes des tiers embarqués.
