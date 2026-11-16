# OcaDim 0.1.0 — mise à jour du 16 novembre 2026

Cette mise à jour rassemble le nouveau menu F1, les correctifs de la soirée et une passe de performance/mémoire
mesurée. Les notes ci-dessous sont prêtes à coller dans une release GitHub.

## Nouveau menu F1

Le menu a sa propre identité (bleu nuit et or), il ne reprend plus la mise en page du menu pause.

- **Display** arrive en premier : **Aspect ratio / widescreen en tête**, puis **Picture** (Output resolution,
  Custom output size), **Frame rate** (Game frame rate cap), **Screen** (Fullscreen, V-Sync, filtres, Ultrawide
  menus) et **HDR**.
- **Graphics** garde la qualité, l'upscaling, la frame generation, le détail et GPU/mémoire.
- **NVIDIA** regroupe DLSS model et NVIDIA Reflex. L'onglet **n'apparaît que là où une de ses lignes existe** :
  jamais sur une carte AMD, jamais dans une build sans DLSS.
- **Touche Run** dans Controls, le miroir de Walk : assignable, mode **Hold/Toggle**, elle pousse le stick gauche
  à fond sur les axes déjà poussés. Utile aussi à une manette dont le stick n'atteint plus le bord.
- Les lignes de test (`Frame pacing`, `Threaded rendering`) passent dans **Debug**. `Frame generation by`
  n'apparaît qu'avec la frame generation, `CRT lines` qu'avec un filtre CRT.

## DLSS

- Les builds embarquent désormais le **SDK DLSS de NVIDIA** (`ngx/nvngx_dlss.dll` et `nvngx_dlssg.dll`).
- Sur une RTX, l'**Upscaler** propose DLSS et `Frame generation by` propose **NVIDIA DLSS Frame Generation**.
- Rappel : sur une machine limitée par le CPU, DLSS est un gain de **qualité/choix**, pas de fps. Le frame est
  toujours limité par l'enregistrement des command buffers (~16 ms CPU contre ~1,9 ms GPU sur une 4070).

## Correctifs

- **Ombres verrouillées au 1600 du jeu.** Le réglage `Shadow resolution` est retiré : Auto choisissait 3072 sur
  une carte de 16 Go et coûtait **6 à 7 fps en ville**. Un fichier d'options qui garde `shadow_resolution` est lu
  et ignoré.
- **Identifiants d'options dédoublonnés** : Auto run et Shadow resolution partageaient l'id 56, Above-60 fixes et
  Transition autosave l'id 59. Une option de chaque paire ne recevait jamais sa valeur.
- **Gohma au-dessus de 60 fps (#1098)** : la rotation sauvegardée ne garde plus `rate × step²` ; elle atteint
  enfin son plafond, sans toucher à l'arithmétique du jeu à 60 fps ou en dessous.

## Performance

- **#994 — cibles de rendu réutilisées** : le jeu recréait ses cibles à chaque frame ; le renderer faisait une
  image Vulkan par cible puis la détruisait, **~20 % du temps du thread de rendu** dans le marché de Castle Town
  la nuit (`vkDestroyImage` 15 %, `vmaCreateImage` 5 %). Le pool de cibles reçoit maintenant ses cibles mortes à
  temps et les garde.
- **#1035 — pool de cibles à 3 paliers** : moitié à 90 % de ce que le pilote autorise, rendu à 97 %, au lieu d'un
  seul seuil à 90 %.
- **#472 — gap des uniformes** : la liste est lue sur place (plus de copie en vecteurs à chaque vérification).
- **#391 — coûts d'un draw** : `dyn_same` compare les mots et octets d'un coup (`memcmp`), le compteur de
  pipelines n'est lu que si le journal de vie le lit, la clé hexadécimale du journal push n'est formée qu'avec
  son commutateur.
- **Sans PR** : les submits ne sont plus copiés à chaque frame pour le benchmark `RX_VK_BENCH` quand il n'est pas
  demandé (une allocation et sa copie par submit, chaque frame, pour un log que personne n'imprime).
- Déjà en place depuis les passages précédents : descripteurs gardés par stage (#794), choix du programme qui
  garde ses slots (#795), uniformes indexés par page de 1 Ko (#796), buffer écrit une fois (#797), draw indexé
  direct qui garde son binding (#798), write-backs laissés aux seuls pools lus par le CPU (#799), un set layout
  partagé par signature de bindings (#800).

## Mémoire

- **BC3 scratch 160 → 20 Mo** : −140 Mo de VRAM.
- **Uploads ASTC** : budget quadruplé pendant une frame longue ; **1 303 → 571 textures repoussées** (−56 %).
- **Arenas de staging conservées** après un chargement, au lieu d'être refaites toutes les deux frames.
- **Vérification des trous zéro** : seules les pages qui portent des données sont lues.
- **Cache de pipelines écrit avant le titre** : chargement de zone **3,2 → 11,1 fps** (~27 s).
- **Notes DLSS/FSR** plus recalculées à chaque draw : **0,92 → 0,13 ms**.
- **Replay adaptatif** : 6 segments par command buffer au plancher, fps inchangés là où il s'engageait déjà.

## Vérifications

- **16/16** tests du menu (sections, README, i18n, raccourcis, redimensionnement, hit-test, champs de texte).
- Tests mémoire/textures : `target_image_pool`, `target_pool_cap`, `rt_pool_minimum`, `vram_pressure`,
  `vram_compact`, `bc_levels`, `astc_bc_policy`.
- Tests des correctifs : `walk_key`, `saved_turn_rate`, `high_fps_fixes`, `ub_gap`, `same_dyn`, `desc_keep`.
- Suite complète sur ce checkout Windows : **554 passés, 89 sautés, 42 échoués** ; les 42 échecs restants sont
  pré-existants (fixtures POSIX/Windows, dépôt `MagicBeanDev/Tooling` absent, deux fixtures upstream déjà
  désynchronisées), pas des régressions de cette mise à jour.

## Installation

- Met à jour l'installation existante en conservant saves et options ; aucun fichier de jeu n'est modifié.
- DLSS exige le dossier `ngx/` (les deux DLL NVIDIA) à côté de `longshot.exe`. Sans lui, l'Upscaler ne propose
  pas DLSS.
- L'onglet NVIDIA et DLSS restent absents sur AMD, par construction.

## Connu, à l'étude

- Un crash `0xc0000005` a été observé dans `ub_overlay` (overlay des uniformes) à **~142 fps**, sur une build
  antérieure à cette mise à jour. Deux rapports pointent la même fonction et le même storage de textures
  (`0x10002ad8800`), avec des uploads répétés « a GPU buffer wrote it ». Piste : textures écrites par le GPU /
  cibles de rendu. À retester avec cette build, à 60 puis à 144 fps ; si le crash revient, les correctifs
  #1162/#944/#332 et les bornes mémoire guest #1179 sont les prochains à intégrer.
