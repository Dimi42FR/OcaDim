# Reprendre la fusion — notre base `v0.0.2-fusion-base`, la 0.0.2 comme référence

Ce document est pour la session qui reprend. Il dit **ce qui marche, ce qui a cassé, et dans quel ordre
avancer sans rien perdre**. La règle du projet tient en une phrase : **un build testé à la fois, jamais deux
changements sans mesure entre eux.**

## 1. Notre base, et la référence d'origine

**La base est maintenant `F:\OcaDim-SAVE-17-11\build-fg-final-ok\`** (`longshot.exe` + `longshot_vk.dll`),
posée le 2026-11-18 : le moteur fusionné **avec la frame generation AMD FSR 4 qui tourne**, vérifiée en jeu.
Son commit est `588da818` sur `merge-amont`, **tagué `v0.0.2-fusion-base`** ; ses empreintes, sa commande de
build, ses preuves et ses limites sont dans `build-fg-final-ok\BASE.md`.

`F:\OcaDim-SAVE-17-11\build-0.0.2-1\` reste la **référence d'origine** : la 0.0.2 que le joueur connaît, avec
la FSR 4 qui fonctionne. Tout ce qu'elle fait doit se retrouver dans le résultat final ; on la compare quand
un comportement surprend.

Sources : branche **`merge-amont`** (le travail de fusion, 184 commits de l'amont) ou le tag `v0.0.2-1`
(la 0.0.2 d'origine). Les deux sont dans `D:\Emulateur\Longshot-src\longshot-merge` (worktree) et
`D:\Emulateur\Longshot-src\longshot`.

## 2. Ce que la fusion a cassé, et pourquoi — à ne pas refaire

Quatre écrans noirs, quatre causes réelles, toutes trouvées **en comparant avec la 0.0.2** :

| Cause | État |
|---|---|
| `fg_amd_create_swapchain` appelé **sans condition** dans `create_swapchain` → sa swapchain prenait la surface | **corrigé** : `fg_amd_requested() ? … : échec` |
| `fg_amd_acquire` appelé avec `VK_NULL_HANDLE` (le moteur de l'amont acquiert avec un **fence**) | **corrigé** : le **fence du moteur** (`image_free` l'attend). Un sémaphore dédié fut le premier essai : jamais attendu, donc l'image restait gardée et la fenêtre noire |
| Présentation remise au **thread présentateur**, qui ne connaît pas la swapchain d'AMD | **corrigé** : `&& !fg_amd_active()` |
| **`fg_amd_frame(...)` absent** de `present_image` : rien n'était jamais donné au générateur d'AMD | **corrigé** — c'était la vraie cause de l'écran noir |

Ces quatre corrections sont commitées sur `merge-amont`. Elles sont nécessaires, mais **pas suffisantes**.

## 3. `create_fg` : trouvé, corrigé, la FSR 4 génère (commit `68cb062a`)

Le log a répondu, en deux temps — aucun des deux n'était la condition de `fg_amd_frame` soupçonnée :

1. **`present_image` n'arrivait jamais à `fg_amd_frame`.** La fenêtre était noire (« l'image n'a pas été
   rendue en 250 ms ») : `image_free` attendait le fence d'acquisition, alors qu'AMD recevait un sémaphore
   qui n'était jamais attendu. Chaque présent gardait son image. **Corrigé** : AMD acquiert avec le fence du
   moteur, comme la swapchain simple (`fg_amd_acquire(sc, timeout, fence, &index)`). La fenêtre s'affiche.
2. **La chaîne ne publiait aucun depth/motion** : `fg_amd_frame` disait « no depth and motion published yet ».
   Le build de test n'avait pas **`LONGSHOT_FSR=1`** : FSR 4 était en stub, l'upscaler retombait sur celui du
   jeu, et `temporal_fg_publish` (dans `temporal_upscale`, chemin d'un moteur) n'était jamais atteint. Ce
   n'était **pas** un bug de code : le build était faux. Le log le disait :
   `Auto (this PC) would be: ... the game's own upscaler (this build has no FSR 4)`.
   **Un build de test doit passer `LONGSHOT_FSR=1`** (`make_game.py --fsr` le fait pour le joueur).

Avec les deux :

```
vk: AMD FG: create_fg: framegen_by=3, so AMD FSR 4's generation
vk: AMD FG: frame generation version ... is "4.0.2"
vk: AMD FG: AMD's frame generation 4.0.2 made for 1600x900 (render up to 2560x1440), 14066 ms of CPU, 93 MB
vk: AMD FG: 39600 presents by AMD's swapchain, 44530 shown, 4932 generated
```

Mesuré en jeu (RX 9070 XT, pilote 26.10.2, `Market_Child`, 2560x1440) : image juste, HUD compris, compteur
nommé par `g_fg_major()==4`. La création du contexte coûte ~14 s une fois (au premier passage en jeu).

**La 3.1 reste refusée par AMD** : avec `RX_VK_FG_AMD_FORCE=3`, `create_fg` choisit bien `3.1.6` (le log le
nomme) mais le contexte est refusé (`return 6`, paramètre invalide), même avec la fenêtre et l'image à la même
taille (1600x900). Le choix, le log et la sélection de version sont en place ; c'est le fournisseur 3.1 du SDK
livré qui ne crée pas. À rouvrir seulement si un joueur demande la 3.1.

Les switches de test sont déclarés dans `switches.def` : `RX_VK_FG_AMD` et `RX_VK_FG_AMD_FORCE` (3|4, 2x,
`env_override` : l'ini du joueur n'est pas touché). Chaque retour anticipé de `fg_amd_frame` et la première
publication de `temporal_fg_publish` disent leur raison, une fois.

## 3 bis. Les commits à NE PAS remettre

Deux choses ont été identifiées comme nuisibles pendant la chasse de la 0.0.2, et elles ne doivent pas revenir :

| Commit | Ce qu'il faisait | Pourquoi il reste dehors |
|---|---|---|
| **#51** `757531a0` — replay parallèle adaptatif | segments 32→16→8 sur les buffers courts, points de dry pass 64→8 | course sur les buffers courts : **textures, torches, ciel et bouclier faux une frame** (les flashs). Le marché fait ~2300 draws par buffer, l'optimisation n'y servait pas. Retiré par `57dfbe96`. |
| **`LONGSHOT_LIGHT_PASSES`** #1002 `208d3bda` | 56 des 75 chunks compilés **sans les passes de module de -O1** (dont l'inliner) | échange temps de compilation contre code : ~15 % de build en moins, **+3-5 % de code**. Dans un build qu'on veut le plus rapide possible, il est **opt-in** : `LONGSHOT_LIGHT_PASSES=1` pour l'activer, rien par défaut (`nx2/build.py`, `light_passes_kb`). |

Et un troisième, plus discret : le **cache des notes upscaler** comparait les cibles et la frame mais **pas la
caméra** ; réactivé, il faut que `s.ubo[0][0]` (vue/projection) entre dans la comparaison, sinon l'upscaler
dessine avec les mauvaises matrices une frame ou deux.

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

- [x] **Frame generation AMD FSR 4** : le compteur affiche `FSR 4 FG`, le log dit `create_fg: framegen_by=3`
      puis `4.0.2`, et les frames sont générées (`... generated`).
- [x] **Choix 3.1 / 4** dans `Génération d'images par` (0..3), et le log nomme la version à chaque création.
      La 3.1.6 est nommée puis refusée par AMD (`return 6`) : voir §3.
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
| `D:\Emulateur\Longshot-src\longshot-merge` | branche `merge-amont` : moteur de l'amont + notre couche + la FG qui marche (`588da818`, tag `v0.0.2-fusion-base`) |
| `D:\Emulateur\Longshot-src\longshot` | la 0.0.2-1, base saine, `v0.0.2-1` |
| `F:\test` | le même build que la base, installé ; ini du joueur intact |
| `F:\OcaDim-SAVE-17-11\build-fg-final-ok` | **NOTRE BASE** : binaires + `BASE.md` + le log qui la valide |
| `F:\OcaDim-SAVE-17-11\build-fg-fsr4-ok` | l'étape où la FSR 4 a généré pour la première fois (+ logs 3.1 refusée) |
| `F:\OcaDim-SAVE-17-11\build-fg-avant-diag`, `build-fg-diag1`, `build-fg-diag2`, `build-fg-compteur-avant` | les étapes : avant diagnostics, sans FSR 4, avant le compteur juste |
| `F:\OcaDim-SAVE-17-11\build-0.0.2-1` | **la 0.0.2 d'origine, FG comprise** (référence de comportement) |
| `F:\OcaDim-SAVE-17-11\build-0.0.2-light` | la 0.0.2-1 avec light passes ON (comparaison) |

## 7. La première phrase à écrire à l'agent (session suivante)

> *« Reprends `merge-amont` : la FSR 4 FG tourne (commit `68cb062a`), vérifiée en jeu. Prochaine étape : le F1
> d'OcaDim, à refaire par petites touches sur le `vk_menu.cpp` de l'amont (Display, onglet NVIDIA conditionnel,
> Run + Run mode, ombres au 1600, les deux lignes Debug, ids uniques), un changement à la fois. Build de test :
> `LONGSHOT_FSR=1`. Ne touche ni à DLSS ni à la FSR 3.1 upscaling. Sauvegarde `F:\test` avant chaque copie et
> lis le log avant de dire que c'est bon. »*

## 8. Journal de la session (2026-11-18)

- `fg_amd_frame` : chaque retour anticipé dit sa raison, une fois ; `temporal_fg_publish` dit sa première
  publication et un frame sans depth/motion.
- `fg_amd_acquire` prend un `VkFence` ; `present_image` lui donne `acquire_fence` (plus de sémaphore dédié) :
  la fenêtre s'affiche, `image_free` passe.
- `RX_VK_FG_AMD_FORCE=3|4` : 2x pour un run, version imposée, `env_override` ; lignes ajoutées à
  `switches.def`.
- Build de test corrigé : `LONGSHOT_FSR=1` (sans lui, FSR 4 en stub → aucun depth/motion → pas de `create_fg`).
- Essais : FSR 4, 4932 frames générées sur 39600 présents, image juste ; 3.1.6 nommée puis refusée par AMD
  (`return 6`), même à 1600x900.
- Sauvegardes : `build-fg-avant-diag`, `build-fg-diag1`, `build-fg-diag2`, `build-fg-fsr4-ok`,
  `build-fg-compteur-avant`.
- **Base posée** : `build-fg-final-ok` (+ `BASE.md`), commit `588da818`, tag `v0.0.2-fusion-base`. Le
  compteur nomme la génération du contexte créé (`FSR 4 FG` sur `4.0.2`), et ne nomme rien si le contexte
  est refusé.
