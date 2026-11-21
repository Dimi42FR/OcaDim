# OcaDim 0.0.5 — passation, tests et outils (2026-11-22)

## Identité de la version

- Produit : **OcaDim 0.0.5**
- Branche : `ocadim-0.0.5`
- Commit : `c5cb462d` (threads du replay à 4 par défaut)
- Tag : `v0.0.5`
- Base : `merge-amont` / `95b6736c` (source de la build D 0.0.4 + RT mesh)
- Sauvegardes : `v0.0.5-save`, `backup-0.0.5-2026-11-21`, `F:\OcaDim-SAVE-17-11\build-0.0.5-final`
- Branche du lot lift rejeté : `lift-rejete-2026-11-22`

## Binaires

- `ocadim.exe` (≈ 506 Mo)
- `ocadim_vk.dll` (≈ 16 Mo)
- DLL AMD : `amd_fidelityfx_loader_vk.dll`, `amd_fidelityfx_upscaler_vk.dll`, `amd_fidelityfx_framegeneration_vk.dll`
- Emplacements actuels :
  - `D:\ocarina3` (référence de jeu)
  - `D:\ocadim-0.0.5` (installation de test)
  - `C:\Users\Administrator\Desktop\Nouveau dossier (9)\OcaDim\build-0.0.5`
  - `F:\OcaDim-SAVE-17-11\build-0.0.5-workers4`

## Réglages par défaut (AMD RDNA 4 / NVIDIA compatible)

- FSR 4 Native AA (auto RDNA 4) ; DLSS Quality (auto NVIDIA)
- `resolution=9` (92 %), `frame_rate_cap=3` (144), `upscaling=2` (Lanczos)
- `threaded_rendering=1`, `sampler_cache=1`, `draw_order=1`
- `replay_workers=4` (verrouillé après mesure), `replay_seg=3` (160)
- `descriptor_prefetch=0` (rejeté après mesure)
- `above60_fixes=1`, `aniso=4`, `shadow_resolution=0` (= 1600 du jeu)
- `amd_anti-lag_2=1` (AMD uniquement), frame generation par défaut : désactivée
- Menu F1 en français, écran de démarrage OcaDim (fond, barre dorée, 2,5 s mini)

## Protocole de mesure

- Même sauvegarde, même zone (Kokiri Forest), même caméra, sans input.
- Relevé dans `logs/ocadim_log.txt` :
  - ligne `N presents, X fps; a frame: D draws ...`
  - `a frame's replay time (ms)`
  - `GPU time X ms a frame`
- Les valeurs CPU en replay parallèle sont des **sommes de threads** ; le temps mural utile est `submit` + fps.

## Résultats

### Référence D (0.0.5 validée, sans lot lift)

- ~3 059 draws : **53,8 fps**, GPU **7,8 ms**, submit **15,39 ms**, draw **9,94 ms**, descripteurs **4,11 ms**.

### Lot lift amont (rejeté)

Commits testés : `A64_FPXKEEP`, `A64_VECFP`, régions float rapides, `fastvec`/registres en locaux, profils shader device + `maxComputeWorkgroupSubgroups`.

- ~3 016 draws : **49,6 fps**, GPU **7,9-8,0 ms**, submit **16,87 ms**, draw **10,88 ms**, descripteurs **4,62 ms**, programs **1,98 ms**.
- Décision : **rejeté** (CPU ~1,5 ms plus lent, ~4 fps perdus).
- Build conservé : `D:\ocadim-0.0.5-lift` ; branche `lift-rejete-2026-11-22`.
- Note : la table mesh-draw amont n'a pas été portée : elle dépend du sous-système `RX_VK_MESH_CONV=2` absent de la base D.

### Préchargement des descripteurs (`descriptor_prefetch=1`)

- ~3 121 draws : **52,1 fps**, submit **15,9 ms**, draw **10,2-10,4 ms**, descripteurs **4,38-4,44 ms**.
- Décision : **rejeté** (descripteurs +6 % par draw).

### Replay workers = 2

- ~3 119-3 189 draws : **59,5-62,4 fps**, submit **13,33-13,39 ms**, descripteurs **4,66 ms**, 4,7 segments/buffer.
- Décision : accepté comme candidat, sans artefact constaté.

### Replay workers = 4 (défaut actuel)

- ~3 173-3 311 draws : **60,2-61,5 fps**, submit **11,27-11,94 ms**, 6,0 segments/buffer, verrou attendu 0,35 ms.
- Décision : **accepté**, verrouillé par défaut (`replay_workers=4`).
- Aucun artefact signalé par le testeur.

## Chemins et outils

### Dépôt et worktree

- Dépôt principal : `D:\Emulateur\Longshot-src\longshot`
- Worktree de travail : `D:\Emulateur\Longshot-src\longshot-merge`
- Branches utiles : `ocadim-0.0.5`, `merge-amont`, `backup-merge-amont`, `lift-rejete-2026-11-22`
- Remotes : `origin` = git.magicbean.dev/MagicBeanDev/Longshot ; `ocadim` = github.com/Dimi42FR/OcaDim

### Outils de compilation (v2.1.0)

Base : `C:\Users\Administrator\AppData\Local\HookshotBuilder\versions\v2.1.0\HookshotBuilder\tools`
- `llvm-mingw`
- `emsdk`
- `cpm`
- Python 3.12 (`py -3.12 -I`)

Variables utilisées :
```
EMSDK=<tools>\emsdk
LONGSHOT_MINGW=<tools>\llvm-mingw
RX_CPM=<tools>\cpm
LONGSHOT_FSR=1
RX_RELEASE=1   (build release : précompilation + écran de démarrage)
```

### Recompilation complète du jeu

```
py -3.12 -I nx2/make_game.py \
  --romfs D:\ocarina3\romfs \
  --exefs D:\ocarina3\.ocadim_exefs \
  --out <dossier> --work work --jobs 8 --fsr
```

Le dossier de sortie ne doit pas être sur le même disque dur lent si possible (SSD recommandé).

### Recompilation renderer seule (après changement C++)

```
py -3.12 -I nx2/build.py --standalone --jobs 8
```
Sorties : `work\sa\build\ocadim.exe` + `ocadim_vk.dll`. Toujours avec `RX_RELEASE=1` et `LONGSHOT_FSR=1`.

### source.zip

Script temporaire : `C:\Users\Administrator\AppData\Local\Temp\make_source_zip.py` (git archive + entrées zip en `\`).
Sortie : `D:\ocadim-0.0.5-source.zip` (1 563 fichiers, ~19 Mo).

### Lancement / mesure

Direct :
```
Start-Process D:\ocarina3\ocadim.exe -WorkingDirectory D:\ocarina3
```
Avec bridge (contrôle, sans input) :
```
py -3.12 -I scripts/longshot_ctl.py --sock "\\.\pipetest" launch <dir> --exe <dir>\ocadim.exe --ready play
py -3.12 -I scripts/longshot_ctl.py --sock "\\.\pipe\test" status
```

## Projet Desktop / GitHub

Dossier : `C:\Users\Administrator\Desktop\Nouveau dossier (9)\OcaDim`
- `source.zip` = source 0.0.5 (SSR/RT/FSR 4 FG inclus)
- `build-0.0.5` = binaires + DLL AMD
- `OcaDimSetup.exe/.dll` = Setup 0.0.5.0
- `recomplauncher.json`, `tools.lock`, `requirements.txt`

**Rien n'a été poussé sur GitHub.** Pour publier :
```
git push ocadim ocadim-0.0.5
git push ocadim v0.0.5
```
Puis joindre le `source.zip` et le Setup à la release 0.0.5.

## Prochains tests prévus

1. `replay_seg=32` avec workers=4 (référence actuelle : 160).
2. `replay_workers=6` avec le meilleur segment.
3. `descriptor_prefetch=1` avec workers=4.
4. `RX_VK_ASYNC=0` puis `RX_VK_RECORDER=0` pour isoler render thread / recorder.
5. Précompilation au chargement pour les 1 % low.
6. Culling des acteurs hors caméra (risque scripts/musique/portes).
7. LTO / PGO / -O3 sur fonctions chaudes.
8. CCX split : inutile sur Ryzen 7 5800X (un seul CCD).

## Tests complémentaires (22/11, Kokiri Forest)

| Configuration | fps | submit | descripteurs |
|---|---|---|---|
| workers=4, seg=160 | 60,2-61,5 | 11,3-11,9 ms | 5,58 ms |
| **workers=4, seg=32** | **63,9-66,0** | **10,6-10,7 ms** | 5,58 ms |
| workers=4, seg=32 + prefetch=1 | 58,8-62,4 | 11,7-12,4 ms | 6,0-6,45 ms |
| workers=6, seg=32 | 63,1-64,7 | 9,9 ms | 6,9 ms |

Décisions :
- **seg=32 accepté** : +3 à +4 fps, submit en baisse. Défaut passé à `replay_seg=1` (32).
- **prefetch avec workers rejeté** : descripteurs +8 à +15 %, fps en baisse.
- **workers=6 rejeté** : même fps, consomme des cœurs au jeu, ressenti moins bon. Défaut reste 4.
- La ligne « Threads du replay » accepte désormais 1 à 8 (limite du moteur) mais le défaut est 4.

## Règles à conserver

- Toujours mesurer **même zone, même caméra, même draw count** ; noter fps, GPU, submit, draw, descripteurs.
- Rejeter un lot qui perd des fps, même s'il « semble » meilleur.
- Sauvegarder avant chaque lot : branche + binaires + source.zip.
- Ne pas toucher `D:\ocarina3` sans copie préalable.
- FSR 4 : DLL AMD obligatoires, sinon le build dit « no FSR 4 ».
- `RX_RELEASE=1` obligatoire pour la précompilation et l'écran de démarrage.
