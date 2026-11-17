# Bisect du flash de textures (17/11/2026) — RÉSOLU

Symptôme : flashs d'une frame (0,1 s) sur les textures, le ciel, les drapeaux, le bouclier et les torches,
absents de la 0.0.1, intermittents.

Méthode : builds successifs dans l'arbre `longshot-001`, `make_game.py --update F:\test`, sessions longues.

| Commit | Index | Résultat |
|---|---|---|
| `8ca4dba1` (0.0.1) | base | **propre** |
| `31495bc6` (FG P4) | 21 | **propre** |
| `3309f921` (ordre README) | 32 | **propre** |
| `2a845863` (async mesuré) | 38 | **propre** |
| `e490b62f` (MEM_CENSUS) | 41 | **propre** |
| `3ac201c5` (notes DLSS/FSR) | 44 | **propre** |
| `3ac201c5` + look F1 (`ff06b68a`) | 44+58 | **propre** |
| `001f3fdd` (FG dans le log) | 50 | **propre** |
| `757531a0` (#51, replay parallèle adaptatif) | 51 | **FLASH** |
| `e9c3460c` (HEAD complet) | 88 | **FLASH** |

## Cause

`757531a0` — le replay parallèle abaisse ses segments (32 → 16 → 8) et les points du dry pass (64 → 32 → 16 → 8)
sur les buffers de commandes courts. Ce découpage plus fin expose une course : une texture/un sprite (torches, ciel,
bouclier) est lu par un segment pendant qu'un autre l'écrit, une frame.

Le marché fait ~2300 draws par buffer : l'optimisation ne servait pas sur cette machine.

## Correctif

`757531a0` est retiré du build (revert). Tout le reste est gardé : F1 complet, #994, #1035, #472/#391, #1106,
#1098, #1083/#1121, correctifs textures, DLSS.

## Versions sauvegardées

- `ocadim-clean-44-f1-17-11` (`0157aefc`) : base 44 + look F1, sans flash, ancien menu ;
- le build complet sans #51 est le candidat final (à taguer après validation).
