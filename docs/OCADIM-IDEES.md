# OcaDim — idées et décisions (après la 0.0.3)

Ce document garde les idées validées, l'endroit où chaque réglage doit vivre, et l'ordre de
développement. La règle du projet ne change pas : **un seul changement testé à la fois**, avec un
build sauvegardé et un tag avant de passer au suivant.

## La grosse mise à jour (0.0.4) — tout le catalogue, en vagues

Objectif : **toutes les idées de ce document dans une seule version**, sans régression. La 0.0.3
reste la version sûre et publiable ; la 0.0.4 est celle qui doit dépasser Longshot.

La règle : **une vague = un build testé, sauvegardé et tagué**. Une vague ne commence pas avant que
la précédente soit stable en jeu (mêmes trois scènes de référence, 60 s, temps de frame, 1 % low,
VRAM). Tout est désactivable dans OcaDim, et rien n'est actif par défaut avant d'être mesuré.

### Vague 1 — Mémoire et fluidité (le cœur pour les petits PC)
- `Résolution dynamique` (DRS) : Désactivée / 60 / 120 / 144 fps, minimum 65 %.
- `Budget VRAM` : Auto / 2 / 3 / 4 / 6 / 8 Go, éviction LRU, formats compacts, « ASTC en RGBA8 »
  coupé tout seul, dédup des textures.
- `Garde-fou mémoire` : RAM ou VRAM au-delà de 90 %, baisse d'un cran, message clair, Annuler.
- `Mode Petit PC` : un interrupteur qui embarque la DRS, le budget VRAM, 720p/FSR Qualité, ombres
  moyennes, pas de FG sous 40 fps.

### Vague 2 — Rendu (dessiner moins)
- `Ombrage à taux variable` (VRS).
- `Occlusion` (ne pas dessiner ce qui est derrière un mur).
- `Lots statiques` (géométrie fixe d'une salle en une soumission).
- `Prépasse de profondeur` (scènes à fort recouvrement : herbe, eau).
- `Tri des rendus` (par pipeline, à la soumission).

### Vague 3 — Chargement et CPU (supprimer les à-coups)
- `Mips à la demande`.
- `Mode mémoire réduite` (buffers audio et capture/replay plus courts, pas de rewind).
- `Compilation selon les cœurs` pilotée automatiquement.
- `Précompilation au chargement` avec barre de progression.
- `Ordonnanceur de vcores` en work-stealing (nos logs prouvent des attentes de 100-200 ms).

### Vague 4 — Confort de jeu
- `Auto-FG` : couper la génération dans les menus, cinématiques, chargements et la carte.
- `Cadencement VRR` adaptatif (138 sur 144 Hz, 57 sur 60).
- `Profils par zone` (réglages mémorisés par scène, bascule en fondu).
- `Sauvegarde de secours` avant chaque chargement, reprise après crash.
- `Mode photo / cinéma` (HUD masqué, FOV libre, ralenti, captures en supersampling).
- `Rapport de diagnostic` en un clic, en français, prêt à coller.
- `Export / import de profil` en un fichier.

### Vague 5 — Qualité et distribution
- `Cache de pipelines partagé` (zéro saccade de compilation dès la première partie).
- `Assistant de premier lancement` (GPU, écran, manette, trois profils, test de 10 s).
- `Vérificateur de build` (rejouer des inputs, comparer images et temps par frame).
- `Mise à jour intégrée` avec le journal des versions en français.

### Ce qui définit « fini » pour la 0.0.4
- Les cinq vagues passées, chacune avec son build sauvegardé et son tag.
- Aucune régression : mêmes scènes, mêmes sauvegardes, FSR 4 et 3.1 toujours à chaud.
- Le menu reste entièrement en français, avec une aide par ligne.
- Un tableau avant/après dans les notes de version : temps de frame, 1 % low, VRAM, sur une carte
  faible et sur la 9070 XT.

## Décisions prises

- **La résolution dynamique (DRS) s'active et se désactive dans la section OcaDim** du F1, pas dans
  Affichage. Une seule ligne maîtresse : `Résolution dynamique` (Désactivée / 60 fps / 120 fps /
  144 fps), avec un minimum (65 % par défaut) et un maximum (100 %). Aucun doublon dans Affichage :
  « Format d'image » et « Résolution de sortie » y restent tels quels.
- **FSR 4 reste dans Graphismes** (« Génération d'images par ») : on n'y touche pas.
- La section **OcaDim** ne contient que nos options : les quatre interrupteurs actuels, puis la DRS
  et les suivantes. Les lignes de l'amont restent dans Débogage.
- Tout ce qui est visible dans le jeu est **en français** (libellés traduits **avant** d'être coupés).

## Priorité 1 — « Ça rame ? » (dépannage en un clic) — **fait**

Une ligne d'action dans OcaDim. Elle lit l'état réel et propose **une** cause et **une** action
expliquée, avec annulation (Entrée : analyser, encore : appliquer, encore : annuler). Testée en jeu
par Dimi.

Ce qu'elle regarde, dans cet ordre :

- VRAM proche du plafond → proposer « ASTC en RGBA8 » coupé, sinon les ombres au niveau du jeu ;
- plafond d'images qui bride (temps d'attente dans le pacing) → proposer le cran au-dessus ;
- temps passé dans le jeu (CPU) → proposer le rendu threadé (après redémarrage) ;
- frame generation coupée sous 50 images/s → la proposer en Auto ;
- à-coups (1 % low sous la moitié de la moyenne) → expliquer les shaders du premier passage ;
- sinon, dire que rien n'est anormal, avec les chiffres.

Build : `F:\OcaDim-SAVE-17-11\build-0.0.3-ca-rame`, tag `v0.0.3-ca-rame`.

## Priorité 2 — Résolution dynamique (DRS), dans OcaDim

- Cible = temps de frame de la fréquence choisie, moins une petite marge.
- Paliers internes entre le minimum (65 %) et 100 %, **baisse rapide, remontée lente** (anti-pompage).
- Gelée pendant les menus, cinématiques et chargements.
- Le compteur FPS affiche la résolution interne courante (`DRS 82 %`) pour que ce soit vérifiable.
- Compatible FSR 4 et frame generation (les motion vectors restent à la résolution interne).

## Priorité 3 — Budget VRAM

Un plafond de mémoire vidéo, mesurable et réglable dans OcaDim (`Budget VRAM` : Auto / 2 Go / 3 Go /
4 Go / 6 Go / 8 Go) :

- les textures vraiment utilisées restent, les autres sont évincées (LRU) et rechargées au besoin ;
- à l'approche du plafond, on préfère un format plus compact (BC7 pour la couleur, BC5 pour les
  normales) au lieu de tout garder en RGBA8 ;
- « ASTC en RGBA8 » se coupe tout seul quand la VRAM est juste (c'est un contournement qui coûte
  très cher en mémoire) ;
- déduplication des textures identiques entre scènes.

Mesure à chaque étape : **temps de frame, VRAM utilisée, 1 % low** — avant/après, sur la même zone.

## Priorité 4 — Mode « Petit PC »

Un interrupteur qui applique un paquet cohérent : 720p interne + FSR Qualité, ombres moyennes,
budget VRAM 2 Go, pas de FG sous 40 fps, workers = cœurs physiques − 1, pas de rewind.
Il embarque la **DRS** (activée, cible 60) et le **budget VRAM** ci-dessus, pour qu'un seul geste
suffise sur une GTX 1060 ou un Steam Deck.

## Priorité 5 — Garde-fou mémoire (RAM et VRAM)

Un veilleur qui lit la mémoire toutes les secondes :

- au-delà de 90 % de RAM **ou** de VRAM : baisse d'un cran (textures d'abord, puis résolution
  interne), avec un message clair et **un bouton Annuler** qui remet les réglages précédents ;
- jamais silencieux : on écrit ce qui a été changé et pourquoi ;
- si la baisse ne suffit pas, on propose de quitter proprement plutôt que de laisser la machine
  swapper.

## Priorité 6 — Le catalogue des leviers de performance (tous dans OcaDim)

Ta liste, **dédoublonnée** : tu avais répété trois fois l'ordonnanceur de vcores, deux fois le
prépasse de profondeur et deux fois le tri des draws. Il reste **dix leviers uniques**, tous
désactivables dans OcaDim (`Désactivé` = comportement actuel, aucune n'est active par défaut avant
mesure).

| Ligne (OcaDim) | Effet | Réglage | État dans le projet |
|---|---|---|---|
| `Ombrage à taux variable` (VRS) | ombrage fin sur les contours, réduit à l'intérieur des surfaces | Désactivé / Auto / 2x / 4x | **à faire** : rien aujourd'hui (`primitiveFragmentShadingRateMeshShader` à `VK_FALSE`, vk_main.cpp:730) |
| `Occlusion` | ne pas dessiner ce qui est caché derrière un mur | Désactivé / Activé | **partiel** : le jeu culle lui-même ; `RX_VK_NOCULL` et `RX_VK_MESH_NOCULL` existent pour **désactiver** ce culling. L'occlusion GPU par-dessus reste à faire |
| `Lots statiques` | la géométrie fixe d'une salle en une seule soumission | Désactivé / Activé | **à faire** |
| `Prépasse de profondeur` | remplir la profondeur d'abord sur les scènes à fort recouvrement (herbe de la Plaine, eau) | Désactivé / Auto | **partiel** : le jeu a déjà son z-prepass (les draws « z-prepass » d'OoT, vk_draw.cpp:7548, le compteur d'occlusion de vk_replay.cpp:413) ; un prépasse **du renderer** par-dessus reste à faire |
| `Tri des rendus` | trier les draws par pipeline pour réduire les changements d'état | Désactivé / Activé | **à faire** : le `stable_sort` de vk_draw.cpp:6624 ne trie que le **rapport** `draw_stats`, pas la soumission |
| `Mips à la demande` | ne charger que les niveaux réellement affichés | Désactivé / Auto | **partiel** : le « mip trimming » existe dans le mode « Set up for a weak laptop » (`opts.budget`) |
| `Mode mémoire réduite` | buffers audio plus courts, buffers de capture/replay plus petits, pas de rewind | Désactivé / Activé | **à faire** (les buffers de capture sont généreux) |
| `Compilation selon les cœurs` | étaler la compilation des shaders sur les cœurs disponibles | Auto / Côte à côte / Un à la fois | **existe** : ligne « Intel shader compiles » (`opts.intel_compiles`, `intel_compiles.h`), à **piloter automatiquement** selon le nombre de cœurs |
| `Précompilation au chargement` | compiler les shaders pendant l'écran de chargement, avec une barre de progression | Désactivé / Activé | **partiel** : `shaders_preparing()`, `programs_in_load()`, `jobs_pending()` ; la barre et le blocage au chargement restent à faire |
| `Ordonnanceur de vcores` | un cœur libre prend la tâche suivante (work-stealing) au lieu d'attendre son tour | Désactivé / Activé | **partiel** : les vcores existent avec priorité et threads affamés (`host/hos_thread.c`, `vc_starved`, `HOS_VCORE_*`), et nos logs montrent des attentes de 100-200 ms ; le vol de tâches reste à faire |

Règles communes :

- chaque levier se mesure **seul**, sur la même zone et 60 s : temps de frame, **1 % low**, temps
  GPU, VRAM — build sauvegardé et tag avant le suivant ;
- une ligne sur « Désactivé » ne change **rien** au rendu ni au comportement ;
- le mode « Petit PC » les active ensemble, une fois qu'ils sont prouvés ;
- tout est écrit en français, avec une aide qui dit ce que ça fait et ce que ça coûte.

## Priorité 7 — Cache de pipelines partagé

L'amont demande au joueur d'envoyer son cache à la main. OcaDim : un cache signé, proposé au premier
lancement (opt-in), pour supprimer les saccades de compilation dès la première partie.

## Priorité 8 — Assistant de premier lancement

Détection GPU / VRAM / écran HDR / manette, trois profils français (Qualité, Équilibré,
Performances), test de 10 s, application. Il pose aussi la DRS et le mode Petit PC.

## Idées suivantes (notées, pas planifiées)

- **Auto-FG** : couper la génération dans les menus, cinématiques, chargements et la carte, la
  rallumer en jeu.
- **Cadencement VRR adaptatif** (138 sur 144 Hz, 57 sur 60) avec marge anti-déchirure.
- **Profils par zone** : réglages mémorisés par scène, bascule en fondu.
- **Sauvegarde de secours** avant chaque chargement, reprise après crash.
- **Mode photo / cinéma** : HUD masqué, FOV libre, ralenti, captures en supersampling.
- **Diagnostic 1 clic** : rapport français prêt à coller (GPU, pilote, scène, 30 s de métriques).
- **Vérificateur de build** : rejouer une séquence d'inputs et comparer images et temps par frame.
- **CPU** : affinité et priorité du thread de rendu, workers = cœurs physiques − 1, audio sans
  rééchantillonnage en 48 kHz.
- **Export / import de profil** en un fichier.

## Leçon du 2026-11-18 : les champs d'options vont à la fin

La DRS avait ajouté `int drs` **au milieu** de `struct Options` (`vk_menu.h`, juste après
`resolution`). Avec ce build, le jeu reste à la première image (écran noir), trois lancements sur
trois ; sans lui, il démarre à chaque fois. Le mutex `nn.npln` du log est un symptôme.

**Règle : tout nouveau champ de `Options` s'ajoute à la fin de la structure, jamais au milieu.**
Les features suivantes (budget VRAM, garde-fou, Petit PC) suivent cette règle, et la DRS sera
retentée ainsi.



### Interblocage `nn.npln` au démarrage (écran noir)

Vu le 2026-11-18 en testant la DRS : le jeu reste à `frame 1, state intro`, écran noir, et le log
montre

```
[hos nn.npln.Worker] mutex 0x100ac110c8 (obj ...): nn.npln.Worker waiting 10 s;
held by nn.npln.Worker (count 2, 1 waiting)
```

puis des attentes de 2 s des autres threads (`PreActorModelCompose`, `rmbl::VibrationThread`) qui
tournent sans cœur. Le thread réseau se bloque lui-même (mutex récursif, compte 2) et les vcores
affament le reste. Ce n'est pas un crash : le processus vit, mais rien n'est présenté.

- **Reproductible** avec le build DRS (3 lancements sur 3), **pas** avec le build `ca-rame`
  (7 lancements sur 7). Le timing du build semble exposer la course ; le bug est dans l'hôte, pas
  dans le menu.
- **Contournement** : relancer le jeu ; il démarre alors normalement.
- **Piste** : `host/nn_os_sync.c:496` (le log du mutex) et les fibres de `host/hos_thread.c:1528`
  (`nn::async` sur les threads `nn.npln`). À traiter avec la vague « ordonnanceur de vcores ».
- **La DRS v1 a été retirée** : avec elle, le jeu restait à la première image ; sans elle, il
  démarre (13 498 images au dernier essai). Le mutex `nn.npln` est un symptôme, pas la cause : la
  DRS touchait le menu et les options pendant la première image. À reprendre plus tard, autrement.
- **Levier ajouté** : `HOS_POLL_INF_ERR=1` (`host/nn_applet.c`, `switches.def`) répond `POLLERR` à
  un `Poll` infini hors ligne, pour que le moteur gRPC du jeu prenne sa branche d'erreur au lieu de
  tourner avec son mutex. Neutre sur les démarrages normaux (3 sur 3), gardé pour la suite.



- Base testée : `F:\OcaDim-SAVE-17-11\build-0.0.3-ocadim-tab` (commit `5061c946`, tag
  `v0.0.3-ocadim-tab`) : section OcaDim (4 interrupteurs), menu entièrement en français,
  FSR 4 inchangé dans Graphismes.
- Le texte de release est prêt dans `docs/RELEASE-0.0.3.md`, la liste avant publication dans
  `docs/RELEASE-0.0.3-A-FINIR.md`. **Rien n'est poussé, tagué `v0.0.3` ni publié.**

## Piste du 2026-11-18 (soir) : build incremental et vk_menu.h

Les deux builds qui bloquent au demarrage (DRS, garde-fou) sont les seuls qui modifient `vk_menu.h` ;
ceux qui ne touchent que `vk_menu.cpp` demarrent. Les objets dependent des en-tetes d'apres build.py, mais
un build **propre** (tout recompiler) n'a pas encore ete essaye : a faire en premier avant de conclure.
Code du garde-fou : `git stash` - « Garde-fou memoire (a retester en build propre: blocage au demarrage) ».

