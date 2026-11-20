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
| `D:\ocarina3` | **Installation de jeu** (celle du Setup, celle qu'utilisent les joueurs de test). |
| `F:\OcaDim-SAVE-17-11` | **Toutes les sauvegardes de build** (`build-0.0.4`, `build-0.0.3-*`, etc.) + `old-name-backups`. |
| `C:\Users\Administrator\Desktop\Nouveau dossier (9)\OcaDim` | **Le paquet du Setup** : `OcaDimSetup.exe`, runtime .NET, `source.zip`, `tools-seed/`. C'est ce dossier qu'on zippe pour la release. |
| `C:\Users\Administrator\AppData\Local\HookshotBuilder\versions\v2.1.0\HookshotBuilder\tools` | **Les outils de compilation** (emsdk, llvm-mingw, cpm, python, wgpu-native, third_party). Source de `tools-seed`. |

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
| `gpu/vk/vk_menu.cpp` | Les 14 lignes de la section **OcaDim**, Ça rame, Petit PC, garde-fou, DRS, VRS, mips, profil, précompilation, compteur FG, aide/traductions. |
| `gpu/vk/vk_menu.h` | `struct Options` — **tout nouveau champ va À LA FIN**. |
| `gpu/vk/menu_i18n.h` | Table française (et 12 autres langues). Une aide renvoie `k==0 ? texte : nullptr`. |
| `gpu/vk/vk_draw.cpp` | `vrs_set`/`vrs_rate`, `precompile_zone`, diagnostic pipeline/frame lente, `build_graphics`, `jobs_wait`. |
| `gpu/vk/vk_main.cpp` | Extension et fonctionnalité VRS, chargement de `vkCmdSetFragmentShadingRateKHR`. |
| `gpu/vk/vk_replay.cpp` | `rec_cap` (mode mémoire réduite), déclencheur de précompilation, `vrs_set` par frame. |
| `gpu/vk/vk_fg_amd.cpp` | FG AMD, compteur `generated`, `fg_amd_generated()`. |
| `gpu/vk/vk_texture.cpp` | `low_vram_texture_mips` (ligne mips). |
| `gpu/vk/vk_crash_window.cpp`, `host/hos_crash_dialog.c` | Fenêtre de crash **OcaDim** + texte « poster sur le ticket ou le Discord dimiviveamd ». |
| `host/hos_thread.c` | Ordonnanceur de vcores (mode Réactif/Ultra) + `barrier_mode`. |
| `host/oot_barrier.c` | Barrières de jobs (`HOS_OOT_BARRIER_WAIT`). |
| `gpu/vk/intel_compiles.h` | Compilation des shaders selon les cœurs (8+). |
| `setup/OcaDimSetup` | Setup C#/WPF : cases NVIDIA / FSR / Compilation légère / Build optimisé, outils locaux (`tools-seed`), version. |
| `assets/pipeline_states/` | Listes de pipelines livrées (fusionnées par `make_game.py`). |

## 6. État publié

- **Dernière release** : `v0.0.4-2` — « NVIDIA réparé (merci Qeviin) », archive `OcaDimSetup-0.0.4.zip`.
- `v0.0.4`, `v0.0.3-2` (test), `v0.0.3` (stable, **étiquetée `0.0.3-TEST` par erreur**).
- `main` = commit du correctif VRS (`790cbcd8`).

## 7. Problèmes connus, et ce qu'on sait

1. **Device lost avec la frame generation** (AMD et NVIDIA). Dernier log utile : `submit 912 failed (-4)` après 120 images. Causes écartées : `low_mem`, VRS désactivé, barrières, PGO (chez Dimi c'est le build de dev).
   **Correctif immédiat appliqué** : plus d'appel VRS quand la ligne est sur Désactivé → réglé chez Qeviin (RTX 4070 SUPER).
   **Reste** : les device lost avec la FG **active**. Piste : la swapchain dédiée (AMD) / DLSS-G (NVIDIA).
2. **HUD étiré avec la FG** : le HUD est encore dans l'image générée (`HUD included` dans le log). Passe à faire : picture sans HUD → génération → HUD.
3. **Textures qui clignotent** (0,1 s, rare) : 4 pistes notées (mips, ASTC en RGBA8, éviction, upload streaming). Il manque un log par événement.
4. **`Shaders built` monte encore** : la liste livrée couvre nos zones. Pour tout le jeu : `python -I scripts/pipeline_tour.py tour --game <copie du jeu> --out <dir> --publish` (des heures).
5. **Précompilation incrémentale** (4 pipelines/frame) : `precompile_run` est tout-ou-rien (120 lignes avec marqueurs de reprise). Découpage non fait.
6. **Pas de corrections** sur : LTO (build), aliasing mémoire, constantes de spécialisation (gros).

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

- **Défauts neutres, mesurés le 20/11** : Auto = **désactivé** pour le préchargement, les threads du replay et le CCX (4 threads + le helper donnaient moins de fps, plus de régularité) ; segments Auto = **160** (comme avant la ligne) ; barrières Auto = **NVIDIA seulement** ; correctifs 60 fps **activés** (défaut d'origine).
- **Toujours perdu** : la ligne « Batched submits » (devenue une politique, `device_policy.h`) ; le volet « eau à pas fixes » des correctifs 60 fps (l'amont a réécrit le hook en `hos_oot_solver_steps`) ; l'outillage « demande de test » (`.claude/skills`, `scripts/test_requests.py`, `docs/test-requests.md`, `tests/test_test_requests.py`).
- **Pour rouvrir** : `git show mine-a-before-upstream:gpu/vk/...` ; le prefetch et les lignes ci-dessus ont été reportés depuis `dfd1bdeb^1`.

## 8 ter. Liste de pipelines, prefetch et précompilation en arrière-plan (20/11)

- **Liste** : session de téléportations (30 destinations, enfant et adulte) sur une **copie** de la sauvegarde, `--profile test` : **+1 121 pipelines neufs** (`assets/pipeline_states/contrib/dimi42fr-tour-teleports-2026-11-20`). Liste fusionnée : 67 694 pipelines de 22 844 programmes. Le jeu les embarque au build suivant (`make_game.py`).
- **Prefetch** : la clé (vue, soumission) est maintenant capturée **à l'empilement**, pas quand le helper traite. Mesure après correctif, Market, 2 threads : **320 servis sur 622 028** (0,05 %), 2 879 publiés. Donc la cause est ailleurs (`lim` ou l'adresse demandée). Le prefetch reste **éteint par défaut**, et **exige ≥ 2 threads du replay** (`replay_handle` sort par le chemin simple sinon).
- **Tranche multi-démarrages : abandonnée.** Le 2e démarrage ne retrouve plus les variantes des programmes restants (1 790 notes « non gardées »), et `.built` est écrit quand même. Le garde-fou (empreinte du préfixe dans `.done`) est en place mais ne règle pas la rétention.
- **Précompilation en arrière-plan (le design retenu)** : ligne OcaDim **Précompilation en arrière-plan**, **Désactivé par défaut**, 15 s ou 30 s (`precompile_background`). Le titre s'affiche après ce temps et la compilation continue derrière, **quatre threads en priorité basse** ; en mode `RX_VK_LOAD=create`, la préparation est lancée derrière le jeu. Mesure sur cache vraiment froid (fichier du jeu **et** cache du pilote AMD vides) : **187,8 s** tout avant le titre, **32,7 s** avec 15 s. `RX_VK_PRECOMPILE_BACKGROUND_S` reste prioritaire. Attention : la valeur est lue **sans static** — `precompile_run` est appelé une première fois avant que le fichier d'options et `ocadim_env.txt` ne soient lus.

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
