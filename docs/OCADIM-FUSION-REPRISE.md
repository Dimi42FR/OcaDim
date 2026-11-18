# Reprendre la fusion — la 0.0.2 comme base, la dernière version par-dessus

Ce document est pour la session qui reprend. Il dit **ce qui marche, ce qui a cassé, et dans quel ordre
avancer sans rien perdre**. La règle du projet tient en une phrase : **un build testé à la fois, jamais deux
changements sans mesure entre eux.**

## 1. Le point de départ : la 0.0.2

`F:\OcaDim-SAVE-17-11\build-0.0.2-1\` — `longshot.exe` + `longshot_vk.dll`, la version que le joueur connaît,
**avec la frame generation FSR 4 qui fonctionne**. C'est la référence : tout ce qu'elle fait doit se retrouver
dans le résultat final.

Sources : branche **`merge-amont`** (le travail de fusion, 184 commits de l'amont) ou le tag `v0.0.2-1`
(la 0.0.2 d'origine). Les deux sont dans `D:\Emulateur\Longshot-src\longshot-merge` (worktree) et
`D:\Emulateur\Longshot-src\longshot`.

## 2. Ce que la fusion a cassé, et pourquoi — à ne pas refaire

Quatre écrans noirs, quatre causes réelles, toutes trouvées **en comparant avec la 0.0.2** :

| Cause | État |
|---|---|
| `fg_amd_create_swapchain` appelé **sans condition** dans `create_swapchain` → sa swapchain prenait la surface | **corrigé** : `fg_amd_requested() ? … : échec` |
| `fg_amd_acquire` appelé avec `VK_NULL_HANDLE` (le moteur de l'amont acquiert avec un **fence**) | **corrigé** : un sémaphore d'acquisition dédié |
| Présentation remise au **thread présentateur**, qui ne connaît pas la swapchain d'AMD | **corrigé** : `&& !fg_amd_active()` |
| **`fg_amd_frame(...)` absent** de `present_image` : rien n'était jamais donné au générateur d'AMD | **corrigé** — c'était la vraie cause de l'écran noir |

Ces quatre corrections sont commitées sur `merge-amont`. Elles sont nécessaires, mais **pas suffisantes**.

## 3. Ce qui reste, et c'est le seul point ouvert

`create_fg` (la création du contexte de génération) **n'est jamais appelé** : le log ne montre ni
`create_fg`, ni `frame generation version`. Conséquence : le compteur affiche « FSR 3.1 FG » parce que
`fg_amd_major()` vaut 0 — ce n'est pas la 3.1 qui tourne, c'est **rien**.

Donc :

- la swapchain d'AMD est prise ; ✅
- les frames sont présentées (`present: 2560x1440`) ; ✅
- **la génération n'est jamais créée**. ❌

**Prochaine action, précise** : dans `fg_amd_frame` (`gpu/vk/vk_fg_amd.cpp`), loguer la raison de chaque
retour anticipé (`s.wanted`, le multiplicateur, `s.failed`, `s.gen_failed`) avant de les retourner, lancer
une fois avec `RX_VK_FG_AMD_FORCE=4`, et corriger la condition fausse. C'est un aller-retour, pas un chantier.

## 4. La méthode, pour ne rien casser

1. **Ne jamais installer un build non testé** dans `F:\test`. On construit, on copie, on lance, on **lit le
   log**, et seulement ensuite on dit que c'est bon.
2. **Sauvegarder avant chaque copie** : `F:\OcaDim-SAVE-17-11\build-<ce qui change>\`.
3. **Un changement à la fois.** Les quatre causes ci-dessus ont été trouvées parce qu'elles étaient isolées ;
   les trois premières ont été trouvées trop tard parce que plusieurs étaient empilées.
4. **Le log est la vérité** : `F:\test\logs\longshot_log.txt`. Il est écrit quel que soit le mode de lancement
   depuis la correction de `host/hos_main.c` (`HOS_LOG_STDERR=1` rend l'ancien comportement).
5. **Comparer avec la 0.0.2 avant de deviner** : `git show 35997471:gpu/vk/vk_replay.cpp | sed -n '5718,5960p'`
   a donné `fg_amd_frame` en une lecture, après trois suppositions fausses.
6. **Ne pas toucher** à DLSS ni à la FSR 3.1 upscaling : leur code est celui de l'amont et n'a pas de raison
   de bouger.

## 5. Ce que le résultat doit avoir, à la fin

- [ ] **Frame generation AMD FSR 4** : le compteur affiche `FSR 4 FG`, le log dit `create_fg: framegen_by=3`
      puis la version créée.
- [ ] **Choix 3.1 / 4** dans `Génération d'images par` (0..3), et le log nomme la version à chaque création.
- [ ] **Le F1 d'OcaDim** — à refaire **sur le `vk_menu.cpp` de l'amont** : notre fichier entier corrompt la
      pile de ce moteur (le tout premier écran noir, avant même la FG). À reprendre par petites touches :
      Display en premier, onglet NVIDIA conditionnel, touche Run + Run mode, ombres au 1600, les deux lignes
      Debug, ids uniques.
- [ ] **Ombres au 1600** (`vk_replay.cpp`, `HOS_OPT_SHADOW_RES` → 0) — déjà réappliqué.
- [ ] **Nos opti perdues** : seed de shaders mappé (539 Mo de RAM) et budget d'uploads ×4 en chargement.
- [ ] **Light passes OFF** par défaut (fait dans `nx2/build.py` : `LONGSHOT_LIGHT_PASSES=1` pour l'activer).
- [ ] Le **builder** de la 0.0.2-1 : chemins > 260 caractères, lift plus rapide, Setup qui demande le SDK
      NVIDIA.

## 6. L'état des fichiers, à l'ouverture de la session

| Chemin | Contenu |
|---|---|
| `D:\Emulateur\Longshot-src\longshot-merge` | branche `merge-amont` : moteur de l'amont + notre couche + les 4 corrections de la FG |
| `D:\Emulateur\Longshot-src\longshot` | la 0.0.2-1, base saine, `v0.0.2-1` |
| `F:\test` | le dernier build installé (moteur fusionné, FG off, image OK) |
| `F:\OcaDim-SAVE-17-11\build-0.0.2-1` | **la 0.0.2 qui marche, FG comprise** |
| `F:\OcaDim-SAVE-17-11\build-0.0.2-light` | la 0.0.2-1 avec light passes ON (comparaison) |

## 7. La première phrase à écrire à l'agent

> *« Reprends `merge-amont`. La FG FSR 4 présente mais `create_fg` n'est jamais appelé : logue les retours
> anticipés de `fg_amd_frame`, lance avec RX_VK_FG_AMD_FORCE=4, corrige la condition. Ne touche ni à DLSS ni à
> FSR 3.1. Sauvegarde `F:\test` avant chaque copie et lis le log avant de dire que c'est bon. »*
