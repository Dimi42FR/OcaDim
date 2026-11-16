# OcaDim — crédits, provenance et licences

OcaDim n'est pas parti de zéro : c'est un **fork personnel de Longshot**, qui est lui-même un fork de Hookshot. Tout le
socle — le traducteur AArch64 → C, le renderer Vulkan, la couche système recompilée, l'outillage de build — vient de ces
projets et de la scène des récompilations. Ce document dit, sans mélanger, **ce qui est de nous**, **ce qui est de
l'amont** et **ce qui vient de tiers**, avec la licence de chaque morceau.

Si un crédit manque ici, c'est un oubli et non une revendication : ouvre une issue, on corrige.

## 1. La généalogie

| Projet | Qui | Ce qu'OcaDim lui doit |
|---|---|---|
| [Hookshot](https://github.com/NotRexed/Hookshot) | NotRexed | le point de départ : un jeu console recompilé en C et rendu sur Vulkan, et les outils `a64-kit` |
| [Longshot](https://longshot.magicbean.dev/) | MagicBeanDev et ses contributeurs | **le socle d'OcaDim** : renderer Vulkan, hôte, réimplémentation du système, upscalers (DLSS, FSR 3.1 / 4, XeSS), réglages, menu, documentation, tests |
| **OcaDim** | **Dimi42FR** | les ajouts du §2, l'identité du projet, le Setup, l'artwork |

OcaDim repart de l'état de Longshot au 2026-11-16, les commits de l'amont fusionnés dedans, et vit ensuite sa vie.
L'historique du dépôt garde la trace de cette fusion.

## 2. Ce que nous avons écrit

| Ce que c'est | Où | Origine |
|---|---|---|
| La **frame generation du SDK AMD** : swapchain du SDK, préparation par frame, ligne de menu, suivi de la résolution | `gpu/vk/vk_fg_amd.cpp`, `vk_fg_amd.h`, et les points d'accroche dans `vk_main.cpp`, `vk_replay.cpp`, `vk_framegen.cpp`, `vk_temporal.cpp`, `vk_internal.h`, `vk_menu.cpp` | **nôtre**, écrit au-dessus des en-têtes MIT d'AMD (`third_party/fidelityfx`) |
| Le **portage** de deux correctifs de logique de jeu au-dessus de 60 fps (les sols qui portent un personnage, les surfaces d'eau à pas fixe) et la ligne de menu qui les coupe | `nx2/oot_patches.py` (`patch_floor_carry`, `patch_sim_steps`), `host/oot_high_fps.*`, `gpu/vk/vk_menu.cpp`, `vk_api.h` | les correctifs sont de **NX2navi** (domaine public / MIT) ; le portage en hooks, l'interrupteur et le reste du fichier sont **nôtres** pour ces deux-là, le reste du fichier étant de l'amont |
| Les **leviers CPU** du menu : Descriptor prefetch, CPU affinity (CCX), Draw order barriers, Batched submits | `gpu/vk/vk_menu.cpp`, `vk_replay.cpp` | **nôtre** ; le design et les mesures sont dans [`docs/OCADIM.md`](docs/OCADIM.md) |
| Le **prefetch des descripteurs** : le helper, les tables *seqlock*, les *asks* apprises (`pf_learned`), le cache négatif | `gpu/vk/vk_replay.cpp` | **nôtre** — l'amont n'en a aucune trace (zéro occurrence de `prefetch`, `pf_learned` ou `seqlock` dans son replay) |
| L'**auto-échelle petite config** : workers, segments et prefetch selon le processeur | `gpu/vk/par_scale.h` | **nôtre** — le fichier n'existe pas chez l'amont |
| Les lignes **Replay workers** et **Replay segments** | `gpu/vk/vk_menu.cpp` | les mécanismes viennent de l'amont (`RX_VK_PARALLEL`, `RX_VK_PARALLEL_SEG`) ; les lignes, les valeurs et l'Auto sont **nôtres** |
| Le **Setup** qui compile chez le joueur | `setup/OcaDimSetup/`, `setup/build-setup.ps1`, `setup/OcaDim.iss`, `setup/OcaDim-Setup.ps1` | **nôtre**, en s'appuyant sur le CLI de l'amont (`nx2/make_game.py`) |
| Le **statut Discord « OcaDim »**, le nom et la version du produit, le dossier de sauvegarde | `host/discord_rpc.c`, `host/hos.h` | **nôtre** |
| Les **traductions** du menu (12 langues) et l'aide des lignes ajoutées | `gpu/vk/menu_i18n.h` | les lignes ajoutées sont **nôtres**, le reste vient de l'amont |
| L'**artwork** : blason, backdrop du menu, icônes, image du wizard | `assets/branding/`, `assets/ocadim-backdrop.png` | **Dimi42FR** |
| Les **docs OcaDim** | `docs/OCADIM.md`, `docs/SETUP-OCADIM-DESIGN.md` | **nôtre** |

Tout le reste — et c'est l'immense majorité du code — est de l'amont. Voir le §3.

## 3. Les composants tiers, un par un

| Composant | Auteur | Licence | Ce qu'on en utilise |
|---|---|---|---|
| **Longshot** | MagicBeanDev et ses contributeurs | GPL-3.0 | le socle entier |
| **Hookshot** | NotRexed | GPL-3.0 | l'ancêtre direct du socle |
| **a64-kit** (le lifter et ses outils) | NotRexed | GPL-3.0 | la traduction AArch64 → C et l'outillage de build |
| ↳ traducteur AArch64 de suyu (fork `mk8-recomp`) | suyu / dougchansan | GPL-2.0-or-later | `a64-kit/lift/suyu/`, non modifié |
| ↳ recompilateur de shaders suyu / yuzu (backend WGSL de Rexcomp) | suyu, yuzu, Rexcomp | GPL-2.0 / GPL-3.0 selon le fichier | `a64-kit/gpu/third_party/suyu/` |
| ↳ types de l'API NVN | h1k421, adaptés par jhaizhou | MIT | `a64-kit/gpu/render/nvn_api.h` |
| ↳ conception de la couche NVN native | jhaizhou (`d2r-mobile`, `MacNativeGames`) | MIT | `nvn_native.c`, `rx_nvn.*` |
| **Eden** / **Eglantine** | Eden, Eglantine | voir leurs dépôts | le recompilateur de shaders et le travail shaders Switch 2 |
| **suyu** | suyu | voir son dépôt | les décodeurs graphiques et le traducteur AArch64 |
| **nxnative** | seedds | voir son dépôt | référence sur les *task* et *mesh shaders* |
| **EvilOOT** | EvilBoyce / evilmfkr | GPL-3.0 | le culling GPU qui rend le feuillage (arbres, fougères, herbe, feuilles, lucioles), les sondes de lumière ambiante, l'eau de l'étang, le brouillard du jeu, le gel après *Load* et le correctif du scintillement d'exposition |
| **Lichii** | zortos293 | voir son dépôt | référence pour l'abaissement des shaders Ampere, et son correctif de *compare-exchange* ; sa PR #1289 (auz466) a donné la porte à 60 Hz du gestionnaire de son, qui est dans l'amont |
| **NX2navi** | tangerineturtle1 | domaine public / MIT (son `recomp/patches-v111.txt`) | les correctifs au-dessus de 60 fps que l'amont n'a pas — `ofollow` (les sols qui portent un personnage), `owater` (les surfaces d'eau à pas fixe), `orecord` (l'horloge de l'ocarina) — portés ici par nous : `nx2/oot_patches.py`, `host/oot_high_fps.*` |
| **Triforce** | voir son dépôt | voir son dépôt | la fusion des patches ci-dessus, qui a servi de référence |
| **llvm-mingw** | mstorsjo | Apache-2.0 avec les exceptions LLVM | le compilateur Windows embarqué (pas besoin de Visual Studio) |
| **FidelityFX SDK v2.4.0** (en-têtes) | AMD | MIT | l'upscaler FSR 4 via la FSR API, et **la frame generation qu'OcaDim utilise** |
| **FSR 3.1** | AMD | MIT (shaders du SDK) | l'upscaler présent dans tous les builds |
| **DLSS SDK** | NVIDIA | licence NVIDIA | DLSS Super Resolution, DLAA, Reflex et DLSS Frame Generation — **jamais embarqué**, récupéré par chaque build |
| **XeSS-SR** (en-têtes seulement) | Intel | MIT | `libxess.dll` reste celui d'Intel, fourni par le joueur |
| **zbic** | kinnay | GPL-2.0 | la décompression |
| **Opus** | Xiph.Org, Skype, Octasic, et al. | BSD | l'audio |
| **SDL 3.4.20** + **sdl2-compat 2.32.74** | Sam Lantinga et ses contributeurs | zlib | la fenêtre et les manettes (y compris les récentes) |
| **zstd** | Meta | BSD | la compression |
| **Dear ImGui** | Omar Cornut et ses contributeurs | MIT | l'overlay et le menu |
| **Kenney Input Prompts 1.5A** | Kenney | CC0 | les polices d'icônes de touches |
| **Libertinus 7.051** | alerque / Libertinus | OFL-1.1 | la police de secours du menu |
| **crt-lottes**, **crt-hyllian-fast** | Timothy Lottes (domaine public) ; Hyllian, cgwg, DariusG, hunterk (MIT) | domaine public / MIT | les shaders CRT |
| **ocarina-recomp** | sostenesfreitas | voir son dépôt | la mise en page de ce README, et une note qui a confirmé la section de contrôle du *mesh stage* |
| **Orchid** | MythosOfs | voir son dépôt | le contournement brouillard / exposition |
| **Mesa (NAK)** | Mesa | MIT | référence pour l'encodage des instructions Ampere |
| **Les paquets d'outils** | MagicBeanDev (CDN) | — | `tools.lock`, chaque fichier vérifié par son SHA-256 |

Un mot pour ne pas confondre, sur les correctifs au-dessus de 60 fps : ceux qui sont **dans l'amont** (le gestionnaire
de son ramené à 60 Hz, le nombre de pas du solveur physique, `patch_whole_frames`) sont de **Longshot**. Les deux que
**nous** ajoutons (`ofollow`, `owater`) viennent de **NX2navi**, et le portage est à nous.

Chaque dossier de `third_party/` porte son `PROVENANCE.md` et/ou sa licence ; ce sont eux qui font foi.

Les correctifs envoyés par la communauté de l'amont (SkippySteve, monsterlag, hckrman101, madebyjordan, N3oTraX,
shayderrr, gab9281, Wpif, nicholasgower, ZurielAtr, Joey-Magnus, Zorkats, d3zessete, chrispository, vzeol,
leonidasmark, Segmentree, ShyVortex, hiKareeem, i900gaming, et d'autres) sont crédités dans le manuel de l'amont, plus
bas dans ce README.

## 4. Marques et jeu

- **Nintendo** et les noms des jeux cités sont des marques de Nintendo. OcaDim n'est ni affilié à Nintendo, ni approuvé
  par Nintendo.
- Ce dépôt **ne contient pas le jeu, ni de clés, ni d'exécutable de jeu**, et n'explique pas comment se les procurer. Il
  faut ta propre copie.
- Tout ce que le build produit (`longshot.exe`, le code traduit, les caches de shaders, tes sauvegardes) vient de **ton**
  jeu et reste sur **ta** machine. Ne partage jamais ces fichiers.
- **AMD**, **Radeon**, **FidelityFX** et **FSR** sont des marques d'Advanced Micro Devices, Inc. **NVIDIA**, **DLSS** et
  **Reflex** sont des marques de NVIDIA Corporation. **Intel** et **XeSS** sont des marques d'Intel Corporation.

## 5. Licence du dépôt

OcaDim est distribué sous **GPL-3.0** ([LICENSE](LICENSE)), comme le socle dont il descend. Les composants tiers gardent
leur propre licence, listée au §3 et présente dans `third_party/`.
