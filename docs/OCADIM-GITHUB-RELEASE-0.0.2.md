# OcaDim 0.0.2 — notes de mise à jour (prêtes pour GitHub)

## 1. Ce qu'OcaDim apporte — notre travail, sans copie

**Le menu F1, refait de zéro**
- Une identité propre : bleu nuit et or, canvas plein écran, en-tête **OCADIM**, rail vertical des sections,
  pastilles de valeur et barre or sur la ligne active. Ce n'est pas une copie du menu pause du jeu.
- **Display** en premier : Aspect ratio (le widescreen tout de suite), Picture, Frame rate, Screen, HDR.
- **NVIDIA** conditionnel : l'onglet n'apparaît que si une de ses lignes existe sur ce PC — jamais sur AMD.
- **Debug** allégé : Frame pacing et Threaded rendering y passent ; `Frame generation by` et `CRT lines` ne
  s'affichent que lorsqu'ils servent.
- **Touche Run**, le miroir de Walk : liaison, mode Hold/Toggle, stick gauche poussé à fond sur les axes déjà
  poussés.
- **Ombres verrouillées au 1600 du jeu** : la ligne Shadow resolution disparaît, `shadow_resolution` est ignoré.
  Auto prenait 3072 sur une 16 Go et coûtait 6-7 fps en ville.
- **Ids d'options uniques** : Auto run et Shadow resolution partageaient l'id 56, Above-60 fixes et Transition
  autosave l'id 59 — une option de chaque paire ne recevait jamais sa valeur.
- **Deux réglages de perf dans Debug** : `Write back diff` et `Upscaler notes cache`, On/Off, gardés dans
  `longshot_options.ini` (`write_back_diff`, `upscaler_notes_cache`).

**Perf et mémoire (de nous)**
- Le **budget d'uploads ×4 pendant les chargements** : 1 303 → 571 textures ASTC repoussées, la frame la plus
  lourde absorbée par le chargement.
- Le **seed de shaders mappé** au lieu d'être copié : 539 Mo hors du commit privé.
- Les **submits ne sont plus copiés à chaque frame** pour `RX_VK_BENCH` quand il n'est pas demandé.
- **Le diff des write-backs et le cache des notes DLSS/FSR sont réactivés par défaut** (fps max) ; ils avaient
  été coupés pendant la chasse au flash. Le vrai coupable était ailleurs.
- **#51 retiré** : notre replay parallèle adaptatif (segments 32→16→8 sur les buffers courts) exposait une
  course — textures, torches, ciel et bouclier faux une frame. Le marché fait ~2300 draws par buffer : cette
  optimisation ne servait pas là.
- **BC3 remis à 8 couches** (une copie multi-couches sortait rouge/blanche/jaune à 1) et **BC7 par défaut**
  pour les grosses ASTC (même mémoire, alpha et dégradés conservés).
- **Une texture dessinée par le GPU puis finalisée n'est plus ré-uploadée** depuis la mémoire guest (elle
  écrasait le dessin une frame).
- **Notes DLSS/FSR** : la caméra (UBO vue/projection) entre dans la comparaison, puis le cache est réactivé.

**Diagnostic et documentation**
- Le **bisect complet** de la 0.0.1 jusqu'au commit fautif (#51), écrit dans `docs/OCADIM-BISECT.md`.
- Les documents mémoire, coût par draw et chargement des programmes, mis à jour.
- Les tests du menu, de l'i18n et des fixtures recalés sur le nouveau F1.

## 2. Porté de l'amont (intégré et adapté par OcaDim)

- **#994** cibles de rendu réutilisées ; **#1035** pool à 3 paliers ; **#472/#391** coûts d'un draw.
- **#568** arenas de staging conservées ; **#790** trous zéro ; **#903** cache de pipelines avant le titre ;
  **#906** mesh fallback SoA.
- **#1083** fenêtre de collecte ; **#1121** jobs rejoués dès qu'ils arrivent.
- **#1098** Gohma au-dessus de 60 fps ; **#1106** lignes de test ; **#1242** clears ASTC ; **#1250** upload
  sparse à court de staging.
- Descripteurs gardés (#794-800), retry d'upload (`af1e8110`), cible dessinée/finalisée (`7c641b34`),
  écritures GPU trouvées sous une plus petite (`3a183492`).

## 3. Vérifications

- 16/16 tests du menu ; tests textures/mémoire (`target_image_pool`, `target_pool_cap`, `vram_pressure`,
  `vram_compact`, `bc_levels`, `astc_bc_policy`) ; `test_sparse_staging_failure`, `test_upload_retry`,
  `test_drawn_target`, `test_gpu_write_intervals`, `test_bc_scratch_layers`.
- Suite complète : les échecs restants sont pré-existants (fixtures POSIX/Windows, dépôt Tooling absent).

## 4. Installation et mises à jour

- Met à jour l'installation existante en gardant saves et options.
- **Les mises à jour restent disponibles** : le launcher/updater n'est pas modifié.
- DLSS exige le dossier `ngx/` à côté de `longshot.exe` ; l'onglet NVIDIA et DLSS restent absents sur AMD.

## Remerciements

- **@mrmimmmme** : pour la touche **Run** (pouvoir binder une touche pour la course), l'onglet **NVIDIA** (les
  reglages du constructeur au meme endroit) et le **widescreen** rendu visible des l'onglet Display.
- **@444nils** : pour la **nouvelle icone** OcaDim, desormais portee par l'executable.

## 5. Connu

- **Shaders manquants** : `cache/longshot_driver_faults.txt` mémorise les programmes sur lesquels le pilote a
  planté une fois et ne les redemande plus. Le supprimer (ou `RX_VK_DRIVER_FAULTS=0`) les redemande.
- **#1462** (libération des cibles finalisées, VRAM des longues sessions) n'est pas inclus : il demande le
  sweep des cibles mortes absent de cette base.
