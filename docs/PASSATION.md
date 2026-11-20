# Passation OcaDim — 20 novembre 2026

Tout ce qu'il faut pour reprendre sans rien perdre : où sont les dossiers, comment on construit,
ce qui est fait, ce qui reste, et les règles du projet.

---

## 1. Les dossiers

| Dossier | Ce que c'est |
|---|---|
| `D:\Emulateur\Longshot-src\longshot-merge` | **Notre dépôt**. Branche `merge-amont`. Tout le travail OcaDim est ici. |
| `D:\Emulateur\Longshot-src\longshot` | Miroir de **l'amont** (MagicBeanDev/Longshot), pour lire et porter leurs commits. |
| `D:\Emulateur\Longshot-src\longshot-001` | Ancienne base (branche `base-44-f1`), historique seulement. |
| `F:\test` | **Installation de test** (notre build de dev). |
| `F:\test-prefetch` | **Copie de test jetable** (~2,8 Go, `romfs` en jonction vers `F:\test`, profil `test`) : c'est là que se lancent les essais risqués (SSAO, SSR). Ne jamais y mettre une sauvegarde qu'on veut garder. |
| `D:\ocarina3` | **Installation de jeu** (celle du Setup, celle qu'utilisent les joueurs de test). C'est « l'Oca » qui tourne. |
| `F:\OcaDim-SAVE-17-11` | **Toutes les sauvegardes de build** (`build-0.0.4`, `build-0.0.3-*`, `build-0.0.4-loadstart-auto`, …) + `old-name-backups`. |
| `C:\Users\Administrator\Desktop\Nouveau dossier (9)\OcaDim` | **Le paquet du Setup** : `OcaDimSetup.exe`, runtime .NET, `source.zip`, `tools-seed/`. C'est ce dossier qu'on zippe pour la release. |
| `C:\Users\Administrator\AppData\Local\HookshotBuilder\versions\v2.1.0\HookshotBuilder\tools` | **Les outils de compilation** (emsdk, llvm-mingw, cpm, python, wgpu-native, third_party, et **glslang** depuis le 20/11). Source de `tools-seed`. |

**Les builds du 20/11, dans `F:\OcaDim-SAVE-17-11`** (du plus récent au plus ancien) : `build-0.0.4-ssr` (les réflexions écran), `build-0.0.4-loadstart-auto` (le déployé), `build-0.0.4-loadstart`, `build-0.0.4-onglet-rt`, `build-0.0.4-bg-titre`, `build-0.0.4-liste-20-11`, `build-0.0.4-lignes-ocadim`. Chacun contient `ocadim.exe` + `ocadim_vk.dll` (certains aussi la liste de pipelines livrée).

## 2. Construire le jeu (build de dev)

```powershell
cd D:\Emulateur\Longshot-src\longshot-merge
$b="C:\Users\Administrator\AppData\Local\HookshotBuilder\versions\v2.1.0\HookshotBuilder\tools"
$env:EMSDK="$b\emsdk"; $env:LONGSHOT_MINGW="$b\llvm-mingw"; $env:RX_CPM="$b\cpm"
$env:LONGSHOT_FSR="1"                      # FSR 4/3.1 : OBLIGATOIRE
Remove-Item Env:LONGSHOT_NGX_SDK -ErrorAction SilentlyContinue   # pas de DLSS en dev
$env:PATH="$b\llvm-mingw\bin;$b\emsdk\upstream\bin;$env:PATH"
py -3.12 -I nx2/build.py --standalone --jobs 8
```

Sorties : `work\sa\build\ocadim.exe` + `ocadim_vk.dll`. Copier les deux dans `F:\test` (et/ou `D:\ocarina3`).

**Nouveau shader** (Ray-Tracing, SSR…) : il faut `glslang`, ajouté le 20/11 dans les outils :
```powershell
$g="$b\glslang\bin\glslang.exe"
& $g -V --target-env vulkan1.2 -o s.spv gpu\vk\shaders\s.comp
```
puis un header `const uint32_t NOM_SPV[] = {...};` (modèle : `gpu\vk\shaders\ssao_comp_spv.h`).

**Toujours** : build → démarrage (vérifier `frame N, state play/menu`) → capture si visuel → sauvegarde du build dans `F:\OcaDim-SAVE-17-11\build-...` → commit → tag.

## 3. Lancer et tester

```powershell
cd D:\Emulateur\Longshot-src\longshot-merge
py -3.12 -I scripts/longshot_ctl.py --sock "\\.\pipe\ocadim-test" launch "F:\test" --exe "F:\test\ocadim.exe"
py -3.12 -I scripts/longshot_ctl.py --sock "\\.\pipe\ocadim-test" status
py -3.12 -I scripts/longshot_ctl.py --sock "\\.\pipe\ocadim-test" quit
```

- Le jeu écrit tout dans `logs/ocadim_log.txt` (rotation `.1`, `.2`, …).
- **F1** ouvre le menu. Le compteur FPS se règle dans le menu (Breakdown pour tout voir).
- Pour un test propre : couper tous les `ocadim.exe` avant de lancer (sinon écran noir).

## 4. Publier une version

1. **Paquet** : dans `Desktop\Nouveau dossier (9)\OcaDim`, mettre à jour `source.zip` depuis notre dépôt (les dossiers `assets`, `gpu`, `host`, `nx2`, `scripts`, `third_party` + `CREDITS.md`, `LICENSE`, `README*.md`, `recomplauncher.json`, `requirements.txt`, `tools.lock`). **Ne pas** inclure `builder`, `setup`, `tests`, `website`, `.github`.
2. Vérifier qu'il n'y a **ni `createdump.exe` ni `.dmp`**.
3. Recompiler le Setup si son code a changé :
   `dotnet publish setup\OcaDimSetup\OcaDimSetup.csproj -c Release -r win-x64 --self-contained true`
   puis copier `OcaDimSetup.exe/.dll/.deps.json` dans le dossier du paquet.
4. Zipper tout le dossier → `OcaDimSetup-<version>.zip` (~365 Mo).
5. `git tag -a v<version>` + `git push ocadim v<version>` + `git push ocadim merge-amont:main`
6. `gh release create v<version> -R Dimi42FR/OcaDim --title "..." --notes-file notes.md <zip>`

**Notes de release** : fichier UTF-8 **sans BOM**, accents corrects (écrire avec `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))`, jamais `>` qui réencode).

## 5. Où vit le code OcaDim

| Fichier | Ce qu'on y a mis |
|---|---|
| `gpu/vk/vk_menu.cpp` | Les lignes **OcaDim** (dont les six remises : Préchargement des descripteurs, Barrières d'ordre des rendus, Correctifs au-dessus de 60 fps, Threads/Segments du replay, Affinité CPU (CCX)), Ça rame, Petit PC, garde-fou, DRS, VRS, mips, profil, précompilation (+ **en arrière-plan**), compteur FG, **onglet Ray-Tracing** (dont **Réflexions écran (SSR)**), aide/traductions. |
| `gpu/vk/vk_menu.h` | `struct Options` — **tout nouveau champ va À LA FIN**. |
| `gpu/vk/menu_i18n.h` | Table française (et 12 autres langues). Une aide renvoie `k==0 ? texte : nullptr`. |
| `gpu/vk/vk_draw.cpp` | `vrs_set`/`vrs_rate`, `precompile_zone`, **`precompile_run` (budget d'arrière-plan)**, `precompile_warm` (tranche, `.done`), diagnostic pipeline/frame lente, `build_graphics`, `jobs_wait`, **`ssr_after_pass` (réflexions écran : calcul + blit, images gardées)**. |
| `gpu/vk/vk_main.cpp` | Extension et fonctionnalité VRS, chargement de `vkCmdSetFragmentShadingRateKHR`. |
| `gpu/vk/vk_replay.cpp` | `rec_cap` (mode mémoire réduite), déclencheur de précompilation, `vrs_set` par frame, **prefetch de descripteurs** (`fg_lost_note`, `pf_*`), **`par_threads`/`par_pin_upper_half`/`per`**, `device_lost`. |
| `gpu/vk/vk_fg_amd.cpp` | FG AMD, compteur `generated`, `fg_amd_generated()`, **garde `opts.framegen == 0`** (le secours FG). |
| `gpu/vk/vk_texture.cpp` | `low_vram_texture_mips` (ligne mips), **`game_order()`/`pass_start_barrier`** (barrières d'ordre des rendus). |
| `gpu/vk/vk_temporal.cpp` | **`temporal_scene_camera()`** (la projection et les plans de la scène, pour le SSR ; la caméra est aussi prise quand `ssr` est actif), chaîne temporelle du jeu. |
| `host/oot_high_fps.c` | **`above60_fixes()`** (`rx_option(HOS_OPT_ABOVE60_FIXES)`), le solveur au-dessus de 60 fps. |
| `gpu/vk/shaders/` | Les shaders du renderer en GLSL + leur SPIR-V (`*_spv.h`). **`ssr.comp`** (réflexions écran), **`ssao.comp`, `ssao_apply.comp`** (SSAO, essai abandonné) ; **`ssao_blit.vert/.frag`** (triangle plein écran, corrigé pour le SSR). |
| `tools\glslang` | **glslang 16.6**, ajouté le 20/11 : aucun compilateur GLSL n'existait. `bin\glslang.exe -V --target-env vulkan1.2 -o s.spv s.comp`. |
| `gpu/vk/vk_crash_window.cpp`, `host/hos_crash_dialog.c` | Fenêtre de crash **OcaDim** + texte « poster sur le ticket ou le Discord dimiviveamd ». |
| `host/hos_thread.c` | Ordonnanceur de vcores (mode Réactif/Ultra) + `barrier_mode`. |
| `host/oot_barrier.c` | Barrières de jobs (`HOS_OOT_BARRIER_WAIT`). |
| `gpu/vk/intel_compiles.h` | Compilation des shaders selon les cœurs (8+). |
| `setup/OcaDimSetup` | Setup C#/WPF : cases NVIDIA / FSR / Compilation légère / Build optimisé / **Télécharger les outils en ligne**, outils locaux (`tools-seed`), version. |
| `assets/pipeline_states/` | Listes de pipelines livrées (fusionnées par `make_game.py`) ; **`contrib/dimi42fr-tour-teleports-2026-11-20`** (1 121 pipelines). |

## 6. État publié

- **Dernière release** : `v0.0.4-2` — « NVIDIA réparé (merci Qeviin) », archive `OcaDimSetup-0.0.4.zip`.
- `v0.0.4`, `v0.0.3-2` (test), `v0.0.3` (stable, **étiquetée `0.0.3-TEST` par erreur**).
- `main` = commit du correctif VRS (`790cbcd8`), **non mis à jour depuis** : `merge-amont` est en avance de 10 commits (tout le travail du 20/11, SSR compris), et rien n'a été poussé.
- Installations : `D:\ocarina3` et `F:\test` = build du 20/11 20:40 (onglet Ray-Tracing, précompilation en arrière-plan sur Désactivé). Le build du **SSR** est seulement dans `F:\OcaDim-SAVE-17-11\build-0.0.4-ssr` et sur `F:\test-prefetch`.

## 7. Problèmes connus, et ce qu'on sait

1. **Device lost avec la frame generation** (AMD et NVIDIA). Dernier log utile : `submit 912 failed (-4)` après 120 images. Causes écartées : `low_mem`, VRS désactivé, barrières, PGO (chez Dimi c'est le build de dev).
   **Correctif immédiat appliqué** : plus d'appel VRS quand la ligne est sur Désactivé → réglé chez Qeviin (RTX 4070 SUPER).
   **Reste** : les device lost avec la FG **active**. Piste : la swapchain dédiée (AMD) / DLSS-G (NVIDIA). Le 20/11, Dimi n'a **pas reproduit** en 2x fixe — à confirmer sur une session longue.
2. **HUD étiré avec la FG** : le HUD est encore dans l'image générée (`HUD included` dans le log). Passe à faire : picture sans HUD → génération → HUD.
3. **Textures qui clignotent** (0,1 s, rare) : 4 pistes notées (mips, ASTC en RGBA8, éviction, upload streaming). Il manque un log par événement.
4. **`Shaders built`** : **+1 121 pipelines** livrés le 20/11 (30 destinations enfant/adulte), 67 694 au total. Pour le reste : `python -I scripts/pipeline_tour.py tour --game <copie du jeu> --out <dir> --publish` (des heures).
5. **Précompilation** : le découpage multi-démarrages est **abandonné** (voir 8 ter) ; remplacé par l'**arrière-plan après le titre**, Désactivé par défaut. Le tout-avant-le-titre reste le défaut.
6. **Pas de corrections** sur : LTO (build), aliasing mémoire, constantes de spécialisation (gros).
7. **Prefetch de descripteurs** : remis, mais **0,05 % de coups** (320 sur 622 028) — la valeur est dans les négatifs. Éteint par défaut, et il faut ≥ 2 threads du replay.
8. **SSAO** : shaders prêts, premier branchement **retiré** (crash, voir 8 quater). Aucune option active.
9. **SSR (TEST)** : branché le 20/11 (voir 8 quater bis), désactivé par défaut. Coût mesuré **~4,4 ms à 2560×1440** sur la 9070 XT. Reste : confirmer la stabilité sur une session longue, une passe à demi-résolution si le coût gêne, et le comportement avec les threads du replay (sans effet pour l'instant).

## 8. Le mode de secours FG (codé)

- **`device_lost()`** (`gpu/vk/vk_replay.cpp`, ~4522) : si `opts.framegen >= 1`, `fg_lost_note()` écrit `cache/ocadim_fg_lost.txt` **avant** `perf_report_final` (le réglage qui a planté survit à un rapport qui n'aboutit pas) : réglage (`Auto` ou `Nx`), procédé (DLSS / intégrée / FSR 3.1 / FSR 4), cause. Une ligne de log.
- **`menu_init()`** (`gpu/vk/vk_menu.cpp`, ~6002) : le fichier existe → `env_release(&opts.framegen)`, `opts.framegen = 0`, suppression du fichier, log. Placé après les réglages d'environnement (la désactivation gagne sur `RX_VK_FG_AMD_FORCE` / `RX_VK_FRAMEGEN_MULT`) et avant `restart_init()` (pas de faux « redémarrage nécessaire »).
- **Trouvé par le test** : `fg_amd_requested()` (`gpu/vk/vk_fg_amd.cpp`) ne regardait que `framegen_by` → sur AMD, la ligne Frame generation sur **Désactivé** laissait FSR 3.1/4 FG demander son contexte (confirmé : contexte créé, log `AMD FG: create_fg`). Ajout de `if (opts.framegen == 0) return false;` **avant** les interrupteurs, pour que le secours gagne aussi sur `RX_VK_FG_AMD_FORCE` et `RX_VK_FG_AMD`. La ligne « par » garde le choix du joueur pour quand il rallume.
- Testé : marqueur posé à la main + `frame_generation=2` → log `menu: OcaDim : perte du GPU…`, `option get frame_generation` = `0 Off`, marqueur supprimé, et **aucune ligne `AMD FG`** dans le log (le contexte n'est plus créé).
- Reste : un device lost réel avec la FG active (le marqueur doit apparaître au moment du crash).

## 8 bis. Les lignes OcaDim remises (20/11)

Toutes dans l'onglet **OcaDim** du F1, en français, avec leur clé ini ASCII dans `ini_key` :

| Ligne | Moteur |
|---|---|
| Préchargement des descripteurs | `vk_replay.cpp` (helper, file, négatifs, seqlock) + `vk_menu.cpp` |
| Barrières d'ordre des rendus | `vk_texture.cpp` `game_order()`/`pass_start_barrier`, `vk_draw.cpp` (dispatch sans barrière) |
| Correctifs au-dessus de 60 fps | `host/oot_high_fps.c` (`above60_fixes()`, `rx_option(HOS_OPT_ABOVE60_FIXES)`), servi par `vk_replay.cpp` |
| Threads du replay | `vk_replay.cpp` `par_threads()` |
| Segments du replay | `vk_replay.cpp` `per` |
| Affinité CPU (CCX) | `vk_replay.cpp` `par_pin_upper_half()` |
| Programmes avant le titre | `vk_programs.cpp` `programs_load_decide` (force `start` sur `menu_load_start()`) |

- **Mesure sur la 4070 du testeur (RTX 4070, pilote 621.24, 3440×1440 DLSS Quality, 20/11)** : `program loads at create` = **7 038 chargements, 14 s cumulées, pire 1 443 ms**, et **12 850 pipelines construits en jeu (7,3 s)**. Sur NVIDIA le mode par défaut est « au chargement » (mesh shaders), d'où l'écart avec nos 1 586 sur la 9070 XT. La nouvelle ligne **force le mode « avant le titre »** : mesuré ici à 45,5 s de démarrage, mais plus de chargements en partie. `RX_VK_LOAD` reste prioritaire, et le log dit quand c'est la ligne qui a décidé.

- **Défauts neutres, mesurés le 20/11** : Auto = **désactivé** pour le préchargement, les threads du replay et le CCX (4 threads + le helper donnaient moins de fps, plus de régularité) ; segments Auto = **160** (comme avant la ligne) ; barrières Auto = **NVIDIA seulement** ; correctifs 60 fps **activés** (défaut d'origine).
- **Toujours perdu** : la ligne « Batched submits » (devenue une politique, `device_policy.h`) ; le volet « eau à pas fixes » des correctifs 60 fps (l'amont a réécrit le hook en `hos_oot_solver_steps`) ; l'outillage « demande de test » (`.claude/skills`, `scripts/test_requests.py`, `docs/test-requests.md`, `tests/test_test_requests.py`).
- **Pour rouvrir** : `git show mine-a-before-upstream:gpu/vk/...` ; le prefetch et les lignes ci-dessus ont été reportés depuis `dfd1bdeb^1`.

## 8 ter. Liste de pipelines, prefetch et précompilation en arrière-plan (20/11)

- **Liste** : session de téléportations (30 destinations, enfant et adulte) sur une **copie** de la sauvegarde, `--profile test` : **+1 121 pipelines neufs** (`assets/pipeline_states/contrib/dimi42fr-tour-teleports-2026-11-20`). Liste fusionnée : 67 694 pipelines de 22 844 programmes. Le jeu les embarque au build suivant (`make_game.py`).
- **Prefetch** : la clé (vue, soumission) est maintenant capturée **à l'empilement**, pas quand le helper traite. Mesure après correctif, Market, 2 threads : **320 servis sur 622 028** (0,05 %), 2 879 publiés. Donc la cause est ailleurs (`lim` ou l'adresse demandée). Le prefetch reste **éteint par défaut**, et **exige ≥ 2 threads du replay** (`replay_handle` sort par le chemin simple sinon).
- **Tranche multi-démarrages : abandonnée.** Le 2e démarrage ne retrouve plus les variantes des programmes restants (1 790 notes « non gardées »), et `.built` est écrit quand même. Le garde-fou (empreinte du préfixe dans `.done`) est en place mais ne règle pas la rétention.
- **Précompilation en arrière-plan (le design retenu)** : ligne OcaDim **Précompilation en arrière-plan**, **Désactivé par défaut**, 15 s ou 30 s (`precompile_background`). Le titre s'affiche après ce temps et la compilation continue derrière, **quatre threads en priorité basse** ; en mode `RX_VK_LOAD=create`, la préparation est lancée derrière le jeu. Mesure sur cache vraiment froid (fichier du jeu **et** cache du pilote AMD vides) : **187,8 s** tout avant le titre, **32,7 s** avec 15 s. `RX_VK_PRECOMPILE_BACKGROUND_S` reste prioritaire. Attention : la valeur est lue **sans static** — `precompile_run` est appelé une première fois avant que le fichier d'options et `ocadim_env.txt` ne soient lus.

## 8 quater. Ray-Tracing (TEST) — état au 20/11

- **Onglet** « Ray-Tracing » dans le F1, entre OcaDim et NVIDIA : titre + ligne d'attente en français (`0ff189fc`).
- **Outillage shader** : `glslang 16.6` installé dans `tools\glslang` (il n'y en avait **aucun** sur la machine ; tout nouveau shader en dépend). Commande : `tools\glslang\bin\glslang.exe -V --target-env vulkan1.2 -o s.spv gpu\vk\shaders\s.comp`, puis un header `const uint32_t ...[]` (modèle : `gpu\vk\shaders\ssao_comp_spv.h`).
- **SSAO** : `gpu\vk\shaders\ssao.comp` écrit et **compilé** (12 directions en spirale de Vogel sur la profondeur ; pas de kernel au hasard, donc pas de débruiteur). **Pas encore branché.**
- **Où le brancher** : `end_pass()` (`vk_draw.cpp:6228`), le seul endroit qui a **la couleur et la profondeur de la scène** en même temps, avant le HUD et avant FSR 4. Sur cet install, **c'est FSR 4 qui upscale** : ni TAAU ni `temporal_stand_in` ne conviennent.
- **SSAO : abandonné (deux crashes).** Premier essai : une **copie** dans la cible (`vkCmdCopyImage`) — les cibles n'ont pas `TRANSFER_DST`, la carte a lâché. Deuxième essai : sortie **dessinée** dans la cible (bonne méthode), mais mes images étaient **détruites** à chaque changement de taille ; la résolution dynamique alternait 2560×1440 / 1280×720, et `vkDestroyImageView` a bloqué **24,7 s** en attendant le GPU, puis crash de la carte. Le code, les shaders et les deux crashs restent dans l'historique (`fad54e64`, `08d7e5bb`, `7b249e30`). **Ne pas refaire** : détruire une vue pendant que le GPU l'utilise.
- **La bonne conception (apprise à la dure), pour le SSR et la suite** :
  1. **une image par (taille, format)**, gardées jusqu'à la fin du run, jamais détruites (un petit tableau, comme `old_hist` de TAAU) ;
  2. **sortie dessinée dans la cible** par le triangle plein écran (`ssao_blit.vert/.frag`, déjà compilés et commités), pas de copie ;
  3. **garde de taille** : `w >= 1024 && h >= 576` seulement (la scène, jamais une shadow map) ;
  4. **désactivé par défaut**, testé uniquement sur une **copie** de l'installation (`F:\test-prefetch`), avec `ctl shot` avant/après.

## 8 quater bis. SSR (réflexions écran) — fait le 20/11 (TEST)

- **Ligne** : onglet Ray-Tracing, **Réflexions écran (SSR)**, **Désactivée par défaut**, puis l'intensité par pas de 5 % (5 à 100 %) ; clé ini ASCII `ssr` (0 = désactivée, sinon le pour cent), aide en français.
- **Où** : `end_pass()` (`vk_draw.cpp`, `ssr_after_pass`), à la fin d'une passe qui rend dans **la couleur et la profondeur de la scène**, avant le HUD et avant FSR 4. La passe est reconnue par la **caméra de l'upscaler sur la même profondeur** (`temporal_scene_camera`, `vk_temporal.cpp`) et par sa taille, pas par un programme : une shadow map ou une passe de menus ne passe pas.
- **Caméra de l'image** : l'upscale invalide `cam` pendant l'image ; `frame_cam` (`vk_temporal.cpp`) en garde une copie pour toute l'image. La scène peut finir en **plusieurs passes** : le SSR s'applique à chaque fin de passe de cette profondeur, la **dernière gagne**. Sans ça, la passe finale n'avait plus de caméra et **rien ne s'appliquait en jeu** (l'écran de chargement, lui, marchait).
- **Calcul** (`gpu/vk/shaders/ssr.comp`) : couleur + profondeur de la scène, positions reconstruites en espace vue avec la **projection du jeu** (p00/p11/p22/p23 + jitter), normales reconstruites de la profondeur (pas de G-buffer), rayon réfléchi marché en 32 pas + 6 dichotomies, épaisseur de 1,5 pas, fondu aux bords et au loin. **Fresnel** (F0 = 0,02, Schlick^5) : reflet faible de face, fort en incidence rasante — sans lui, à 85 %, **tous les murs deviennent des miroirs**. Écrit couleur + reflet dans une image temporaire RGBA16F.
- **Sortie** : triangle plein écran `ssao_blit.vert/.frag`, **dessiné** dans la cible par un rendu — jamais de copie (les cibles n'ont pas `TRANSFER_DST`, c'est le crash du SSAO). **`uv = p`, pas `1 - y`** : le jeu dessine avec un viewport retourné, mais le blit a un viewport en hauteur positive ; le `1 - y` retournait toute l'image (le SSR « ne faisait rien » de visible).
- **Ressources** : une image RGBA16F **par taille**, gardée jusqu'à la fin du run et **jamais détruite** (plafond 8 tailles) ; vues d'échantillonnage créées à part (une vue d'attachement n'a pas `SAMPLED`) ; pipelines calcul/blit une fois par (format, échantillons).
- **Gardes** : ligne active, mono-échantillon, couleur RGBA16F ou B10G11R11, `w >= 1024 && h >= 576`, niveau/couche 0, pas d'images BC, caméra de cette image-ci, rien avec les threads du replay (`par_active`).
- **Debug** (`RX_VK_SSR_DEBUG=n` au lancement, pas dans `ocadim_env.txt` pour l'instant) : 1 = magenta partout où un reflet est trouvé, 2 = le reflet seul, 3 / 6 = les normales, 5 = la profondeur, 7 = profondeur (R) + normales (G/B). C'est ce qui a montré que les intersections étaient bonnes quand l'image, elle, ne bougeait pas.
- **Mesures (20/11, `F:\test-prefetch`, 2560×1440, RX 9070 XT)** : **GPU 8,9 ms sans SSR, 13,2-13,5 ms avec** (~4,4 ms pour la passe + le blit) ; Market ~45-55 fps contre ~60, Zora ~70 fps. À 85 % avec Fresnel, l'eau et le sol lointain se reflètent, les murs de face restent mats ; à 100 % c'est un miroir. Captures : `ssr-real-85.png`, `ssr-real-0.png`, `ssr-fresnel-85.png`, `ssr-fresnel-100.png`, `ssr-zora-final.png`, et les masques `ssr-debug*.png`, dans `F:\test-prefetch`.
- **À confirmer** : la **session longue** est en cours avec le SSR qui s'applique vraiment (les 15 min d'avant ne testaient rien : la caméra manquait). Le premier lancement du jour a disparu sans perte GPU après ~3 min ; rien reproduit depuis. L'intensité est le curseur de la ligne.
- **Limites connues** : pas de débruitage ; reflets pris dans la couleur déjà éclairée ; rien hors écran (bords) ; le coût est en pleine résolution (une demi-résolution serait la première optimisation).

## 8 quinquies. Ombres ray-tracées — après le SSR

- **Ce que ça demande, et pourquoi c'est un autre chantier** : une **BVH** de la scène. Le replay n'a pas de graphe de scène : il faudrait une BLAS **par maillage** (à partir des vertex/index buffers du invité, mise en cache par identité) et une TLAS **par image**, puis un rayon par pixel vers le soleil, et un **débruitage** (temporel + spatial) — sinon c'est du bruit.
- **Premier pas concret** : vérifier qu'un maillage dessiné expose ses buffers au moment du rendu (ils sont liés), construire **une** BLAS pour un maillage, et tracer **un** rayon par pixel en vue debug. Si ce pas tient, le reste est de l'ingénierie ; sinon, on s'arrête là.

## 8 sexies. Ce qui reste, dans l'ordre

1. **Session longue SSR** (30 min et plus, Zora) avec captures avant/après : confirmer la stabilité et régler l'intensité/la portée.
2. **A/B perf** 0.0.4 contre le build courant, même sauvegarde et même scène.
3. **Session longue FG 2x** pour retrouver le device lost ; le marqueur `cache/ocadim_fg_lost.txt` le consigne.
4. **HUD hors de la FG** (picture sans HUD → génération → HUD).
5. **Release** : tag, push, Setup, `OcaDimSetup-0.0.4-3.zip`. Tout est local aujourd'hui.

## 9. Les règles du projet

- **Un changement à la fois**, build + test + sauvegarde + tag.
- **Aucune option par défaut sans mesure** ; « Désactivé » = comportement d'avant.
- **Tout est en français** dans ce que voit le joueur, accents compris.
- **Rien n'est envoyé automatiquement** : le rapport est copié, le joueur le colle.
- Les identifiants internes `longshot_*` et `LONGSHOT_*` restent (ce ne sont pas des textes visibles) ; le `romfs` contient les objets du jeu, on n'y touche pas.

## 10. Pièges déjà rencontrés (ne pas les refaire)

- Un champ ajouté **au milieu** de `Options` → écran noir au démarrage.
- Une fonction d'aide qui ne renvoie pas `nullptr` → boucle infinie au premier dessin du menu → écran noir.
- Écrire un fichier avec `>` en PowerShell → accents cassés (`�`) sur GitHub.
- Deux instances du jeu en même temps → écran noir.
- Les aides de ligne : le panneau d'aide mesure la plus longue, sinon le texte est coupé.
