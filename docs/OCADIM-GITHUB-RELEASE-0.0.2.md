# OcaDim 0.0.2 — notes de mise à jour (prêtes pour GitHub)

## En bref

- **Un menu F1 qui n'existe nulle part ailleurs** : bleu nuit et or, en-tête OCADIM, rail des sections,
  **Display en premier** (le widescreen tout de suite), **NVIDIA seulement s'il sert** sur ce PC, Debug allégé.
  Ce n'est pas une copie du menu pause du jeu.
- **Touche Run** : la course se lie comme Walk, en Hold ou Toggle.
- **Ombres verrouillées au 1600 du jeu** : Auto prenait 3072 et coûtait **6-7 fps en ville**.
- **Deux réglages de perf dans Debug** : `Write back diff` et `Upscaler notes cache`, gardés dans l'ini.
- **Plus de flashs** : #51 retiré, une texture finalisée n'est plus ré-uploadée, le cache des notes compare la caméra.
- **Plus rapide que la 0.0.1** : le diff des write-backs est réactivé par défaut, plus #1242 et #1250.
- **Un builder réparé et plus rapide** : les dossiers de plus de 260 caractères passent, le lift Windows est
  ~un tiers plus rapide, 1,2 Go de moins, -O2 découpé en parties.
- **Petits PC pris en charge, sans rien régler** : budget de VRAM par carte, pool vidé à 90/97 %, uploads ×4 en
  chargement, 539 Mo de RAM en moins (section 2).
- **Une identité** : icône OcaDim dans l'exe (merci **@444nils**), « OcaDim » dans le FPS Dev et le rapport de bug.

## 1. Ce qu'OcaDim apporte — notre travail, sans copie

**Le menu F1, refait de zéro**
- Une identité propre : bleu nuit et or, canvas plein écran, en-tête **OCADIM**, rail vertical des sections,
  pastilles de valeur et barre or sur la ligne active.
- **Display** en premier : Aspect ratio (le widescreen tout de suite), Picture, Frame rate, Screen, HDR.
- **NVIDIA** conditionnel : l'onglet n'apparaît que si une de ses lignes existe sur ce PC — jamais sur AMD.
- **Debug** allégé : Frame pacing et Threaded rendering y passent ; `Frame generation by` et `CRT lines` ne
  s'affichent que lorsqu'ils servent.
- **Touche Run**, le miroir de Walk : liaison, mode Hold/Toggle, stick gauche poussé à fond sur les axes déjà
  poussés.
- **Ombres verrouillées au 1600 du jeu** : la ligne Shadow resolution disparaît, `shadow_resolution` est ignoré.
- **Ids d'options uniques** : Auto run et Shadow resolution partageaient l'id 56, Above-60 fixes et Transition
  autosave l'id 59 — une option de chaque paire ne recevait jamais sa valeur.
- **Deux réglages de perf dans Debug** : `Write back diff` et `Upscaler notes cache`, On/Off, gardés dans
  `longshot_options.ini` (`write_back_diff`, `upscaler_notes_cache`).

**Perf et mémoire (de nous)**
- **Le budget d'uploads ×4 pendant les chargements** : **1 303 → 571 textures ASTC repoussées**, la frame la plus
  lourde absorbée par le chargement.
- **Le seed de shaders mappé** au lieu d'être copié : **539 Mo de RAM hors du commit privé**, à chaque lancement.
- **Le diff des write-backs et le cache des notes DLSS/FSR réactivés par défaut** (fps max) ; ils avaient été
  coupés pendant la chasse au flash. Le vrai coupable était ailleurs.
- **#51 retiré** : notre replay parallèle adaptatif (segments 32→16→8 sur les buffers courts) exposait une
  course — textures, torches, ciel et bouclier faux une frame. Le marché fait ~2300 draws par buffer : cette
  optimisation ne servait pas là.
- **BC3 remis à 8 couches** (une copie multi-couches sortait rouge/blanche/jaune à 1) et **BC7 par défaut** pour
  les grosses ASTC (même mémoire, alpha et dégradés conservés).
- **Une texture dessinée par le GPU puis finalisée n'est plus ré-uploadée** depuis la mémoire guest (elle
  écrasait le dessin une frame).
- **Notes DLSS/FSR** : la caméra (UBO vue/projection) entre dans la comparaison, puis le cache est réactivé.
- Les **submits ne sont plus copiés à chaque frame** pour `RX_VK_BENCH` quand il n'est pas demandé.

**Le builder et le lift, nettement plus rapides**

C'est le chantier qui répond à « je n'arrive pas à compiler » : sur un petit PC, c'est le lift et la compilation
qui coûtent, pas le rendu.

- **On peut builder depuis un dossier profond.** Le build tourne **depuis, dans et vers des chemins de plus de
  260 caractères** (#1132) : c'était le cas d'un launcher portable dans `Téléchargements`, où le builder échouait
  avec `FileNotFoundError` — et où un dossier trop profond n'était même pas listé, donc ses sources manquaient
  sans un mot.
- **Le lift Windows ~un tiers plus rapide**, le même C en sortie (#1116) : les vérifications de flottants lues
  dans le texte, les recherches de découverte, et les processus d'émission démarrés plus tôt.
- **1,2 Go de moins dans le processus du lift**, donc **plus de workers d'émission** démarrent : environ un
  cinquième de mieux, même C (#1128).
- **La découverte se fait dans des processus séparés** : environ un quart plus rapide sur un PC occupé (#1131).
- **Les gros morceaux compilent avec leurs fonctions géantes découpées** (#1146) et **les chunks d'un build
  tout en -O2 sont coupés en parties** (#1431) : moins d'attente devant un seul fichier énorme.
- **Les chunks à petites fonctions compilent sans les passes de module de -O1** (`LONGSHOT_LIGHT_PASSES`, actif
  par défaut, #1002) : même code, moins de passe du compilateur.

**Le setup (le wizard qui lit le `.nup`)**

- **Le nombre de compilateurs suit la RAM**, pas seulement les cœurs : un quart des threads sous **12 Go**, la
  moitié sous **16 Go**, tous sauf un au-dessus (`--jobs`). Avant, un PC de 8 Go partait sur `cœurs − 1`.
- **2 Go laissés au bureau** sous 16 Go de RAM (`LONGSHOT_MEM_RESERVE_GB`), et le build tourne en priorité
  *BelowNormal* : le PC reste utilisable pendant la compilation.
- **Les shaders en échec sont redemandés à chaque mise à jour** : le setup met de côté
  `cache/longshot_driver_faults.txt`, la liste où le jeu garde **pour toujours** les programmes sur lesquels le
  pilote a fauté (clé : carte + version du pilote). C'est ce qui se voyait comme « les shaders ne se compilent
  pas » : le jeu sautait ces shaders sans un mot, et une mise à jour ne les redemandait jamais. Si le pilote
  fautait encore, la liste revient avec les mêmes lignes.
- La **préparation des shaders** respectait déjà la RAM : 4 Go réservés au reste du PC, 768 Mo par worker.

**Identité et diagnostic**
- Icône **OcaDim** dans l'exécutable (générée dans `work/longshot_game.res`), « OcaDim » dans le pied du FPS Dev
  et dans le rapport de bug.
- Le **bisect complet** de la 0.0.1 jusqu'au commit fautif (#51), écrit dans `docs/OCADIM-BISECT.md`.
- Les documents mémoire, coût par draw et chargement des programmes, mis à jour ; tests du menu, de l'i18n et des
  fixtures recalés sur le nouveau F1.

## 2. Petits PC d'abord — rien à régler, tout est automatique

OcaDim ne demande pas de choisir un preset « petit PC » : les réglages se prennent tout seuls sur la carte et la
mémoire de la machine.

- **La VRAM des textures suit la carte, pas un preset.** 2,2 Go sur une carte de 4,5 Go ou moins, 3,6 Go sur 6 Go,
  4,8 Go sur 8 Go, 7,2 Go sur 12 Go, 11 Go sur 16 Go — et **4 Go quand le pilote n'expose pas de heap dédié**.
  Sous **12 Go de RAM**, une carte de plus de 6,75 Go passe à **45 % de ce que le pilote autorise** (3,3 Go sur une
  8 Go), plafonné à 6 Go. C'est ce plafond qui évite le cas où le pilote pagine la VRAM pour de bon (une RTX 3060 Ti
  tombée à **14 fps** avec 5,1 Go de cache).
- **Le pool se vide avant la limite**, à **90 % puis 97 %** de ce que le pilote autorise : le jeu rétrécit d'abord.
- **Le budget d'uploads ×4 pendant les chargements** absorbe la frame la plus lourde d'une arrivée de zone — le
  hoquet qu'on sent sur un CPU ou un disque lent.
- **Les ombres au 1600** économisent la mémoire et 6-7 fps en ville.
- **Les grosses textures ASTC restent en BC7, 1 octet par texel.** Pas de bascule en RGBA8 (4 octets par texel,
  soit **4× plus de VRAM**) : la mémoire d'une petite carte ne double pas au chargement d'une zone.
- **#1242 : plus de clear des textures gardées en blocs ASTC.** Une session réelle montre une
  **12288×12288 (288 Mo) lue en 21,7 ms puis effacée sur le GPU** — ce travail ne se refait plus.
- **#1250 : un upload sparse à court de staging lie ce qu'il a déjà mis en file.** Quand la VRAM est pleine — le cas
  des petites cartes — on ne récupère plus de textures vides ou périmées.
- **#906 : le mesh fallback en SoA**, pour les GPU sans mesh shaders (cartes anciennes et iGPU).

**Pas encore là, prévu pour la suite (0.0.3)** : le plafond de **2 Go** sur les textures libérées (#960), le
`heap_lazy` qui ne tombe plus à 12 fps (#923), et un **preset « OcaDim minimal »** qui règle aussi les lignes du
moteur (segments, prefetch, barrières) au lieu de laisser le joueur deviner. Le dirty census (#965) a été mesuré
inutile ici : **4 µs par sync, 0,024 ms par frame**.

## 3. Porté de l'amont (intégré et adapté par OcaDim)

- **#994** cibles de rendu réutilisées ; **#1035** pool à 3 paliers ; **#472/#391** coûts d'un draw.
- **#568** arenas de staging conservées ; **#790** trous zéro ; **#903** cache de pipelines avant le titre ;
  **#906** mesh fallback SoA.
- **#1083** fenêtre de collecte ; **#1121** jobs rejoués dès qu'ils arrivent (86,95 → 92,4 fps à Kokiri,
  53,6 → 58,0 au marché).
- **#1098** Gohma au-dessus de 60 fps ; **#1106** lignes de test ; **#1242** clears ASTC ; **#1250** upload
  sparse à court de staging.
- Descripteurs gardés (#794-800), retry d'upload (`af1e8110`), cible dessinée/finalisée (`7c641b34`),
  écritures GPU trouvées sous une plus petite (`3a183492`).

## 4. Vérifications

- 16/16 tests du menu ; tests textures/mémoire (`target_image_pool`, `target_pool_cap`, `vram_pressure`,
  `vram_compact`, `bc_levels`, `astc_bc_policy`, `texture_budget`) ; `test_sparse_staging_failure`,
  `test_upload_retry`, `test_drawn_target`, `test_gpu_write_intervals`, `test_bc_scratch_layers`.
- Suite complète : les échecs restants sont pré-existants (fixtures POSIX/Windows, dépôt Tooling absent).

## 5. Installation et mises à jour

- Met à jour l'installation existante en gardant saves et options.
- **Les mises à jour restent disponibles** : le launcher/updater n'est pas modifié.
- DLSS exige le dossier `ngx/` à côté de `longshot.exe` ; l'onglet NVIDIA et DLSS restent absents sur AMD.

## Remerciements

- **@mrmimmmme** : pour la touche **Run** (pouvoir binder une touche pour la course), l'onglet **NVIDIA** (les
  réglages du constructeur au même endroit) et le **widescreen** rendu visible depuis l'onglet Display.
- **@444nils** : pour la **nouvelle icône** OcaDim, désormais portée par l'exécutable.

## 6. Connu

- **Shaders manquants** : `cache/longshot_driver_faults.txt` mémorise les programmes sur lesquels le pilote a
  planté une fois et ne les redemande plus. Le supprimer (ou `RX_VK_DRIVER_FAULTS=0`) les redemande.
- **#1462** (libération des cibles finalisées, VRAM des longues sessions) n'est pas inclus : il demande le
  sweep des cibles mortes absent de cette base.
- **Un crash au démarrage a été vu une fois** sur RX 9070 XT (`amdvlk64.dll+0xef61f`, pendant l'import des pools,
  FSR 4.1.2 chargé) : non reproduit sur les lancements suivants. Si ça revient, `RX_VK_FSR4=0` ou
  `RX_VK_PARALLEL=1` isolent la cause.
