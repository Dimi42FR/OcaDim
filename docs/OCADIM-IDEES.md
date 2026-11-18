# OcaDim — idées et décisions (après la 0.0.3)

Ce document garde les idées validées, l'endroit où chaque réglage doit vivre, et l'ordre de
développement. La règle du projet ne change pas : **un seul changement testé à la fois**, avec un
build sauvegardé et un tag avant de passer au suivant.

## Décisions prises

- **La résolution dynamique (DRS) s'active et se désactive dans la section OcaDim** du F1, pas dans
  Affichage. Une seule ligne maîtresse : `Résolution dynamique` (Désactivée / 60 fps / 120 fps /
  144 fps), avec un minimum (65 % par défaut) et un maximum (100 %). Aucun doublon dans Affichage :
  « Format d'image » et « Résolution de sortie » y restent tels quels.
- **FSR 4 reste dans Graphismes** (« Génération d'images par ») : on n'y touche pas.
- La section **OcaDim** ne contient que nos options : les quatre interrupteurs actuels, puis la DRS
  et les suivantes. Les lignes de l'amont restent dans Débogage.
- Tout ce qui est visible dans le jeu est **en français** (libellés traduits **avant** d'être coupés).

## Priorité 1 — « Ça rame ? » (dépannage en un clic)

Une ligne d'action dans OcaDim. Elle lit l'état réel et propose **une** cause et **une** action
expliquée, avec annulation :

- VRAM proche du plafond → proposer le budget textures / couper « ASTC en RGBA8 » ;
- shaders en compilation (« Shaders built », « Draws left out ») → proposer le cache de pipelines ;
- frame generation coupée alors que le GPU a de la marge → la proposer ;
- cap d'images trop bas ou vsync incohérent avec l'écran → proposer la bonne valeur ;
- résolution de sortie très supérieure à l'écran / upscaler désactivé → proposer l'upscaler ;
- temps « Game » (CPU) très supérieur au temps GPU → proposer le mode Petit PC.

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

## Priorité 6 — Cache de pipelines partagé

L'amont demande au joueur d'envoyer son cache à la main. OcaDim : un cache signé, proposé au premier
lancement (opt-in), pour supprimer les saccades de compilation dès la première partie.

## Priorité 7 — Assistant de premier lancement

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
- **RAM** : plafond du cache d'assets, buffers audio plus courts, pas de rewind en mode réduit.
- **VRAM** : BC7/BC5 par texture, dédup entre scènes, mips à la demande, cibles transitoires aliasées.
- **CPU** : affinité et priorité du thread de rendu, workers = cœurs physiques − 1, audio sans
  rééchantillonnage en 48 kHz.
- **Export / import de profil** en un fichier.

## Où en est la 0.0.3

- Base testée : `F:\OcaDim-SAVE-17-11\build-0.0.3-ocadim-tab` (commit `5061c946`, tag
  `v0.0.3-ocadim-tab`) : section OcaDim (4 interrupteurs), menu entièrement en français,
  FSR 4 inchangé dans Graphismes.
- Le texte de release est prêt dans `docs/RELEASE-0.0.3.md`, la liste avant publication dans
  `docs/RELEASE-0.0.3-A-FINIR.md`. **Rien n'est poussé, tagué `v0.0.3` ni publié.**
