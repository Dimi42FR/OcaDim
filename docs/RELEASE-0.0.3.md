# OcaDim 0.0.3 — le menu français, le kit « petits PC » et le VRS

La plus grosse mise à jour d'OcaDim depuis la 0.0.2 : tout ce qui suit a été **conçu et codé de notre côté**,
pour rendre le jeu jouable et réglable sur une machine moyenne, pas seulement sur une carte haut de gamme.

## 1. Ce qu'on a ajouté nous-mêmes

### Une section OcaDim, dans un menu entièrement en français

Le menu F1 (rail des sections à gauche, en-tête OCADIM) est **intégralement traduit**. Une section
**OcaDim** regroupe nos réglages, séparés de ceux du jeu et de NVIDIA :

- **Ça rame ?** — lit une seconde de mesures (temps par image, 1 % low, VRAM, plafond, frame generation)
  et nomme **la** cause probable en français, avec **un** réglage proposé. Entrée analyse, encore pour
  appliquer, encore pour annuler.
- **Mode Petit PC** — un geste : moitié de résolution interne (720p depuis du 1440p), Lanczos, netteté 30,
  ombres du jeu, frame generation coupée. Le même geste remet exactement les réglages d'avant.
- **Résolution dynamique (DRS)** — la 3D suit une cible de 60, 120 ou 144 images/s, sur les paliers de
  l'upscaler, un changement toutes les 2 s au plus, jamais au-dessus du choix du joueur.
- **Garde-fou mémoire** — au-delà du seuil, la 3D baisse d'un cran ; le message dit pourquoi, et Entrée annule.
- **Budget VRAM** — Auto / 2 / 3 / 4 / 6 / 8 Go ; c'est le **seuil du garde-fou** (marge de 90 %).
- **Ombrage à taux variable (VRS)** — ombrage réduit à l'intérieur des surfaces, fin sur les contours ;
  le HUD et le texte restent nets. `VK_KHR_fragment_shading_rate`, chargé seulement si le pilote l'a.
- **Ordonnanceur de vcores** — Auto / Standard / Réactif (200 ms) / Ultra réactif (200 ms + préemption 1 ms).
- **Précompilation au chargement** — les pipelines de la zone sont construits pendant le chargement
  (mesuré : 3,4 s à froid), donc **plus rien n'est compilé en jeu** (`program census (play): created 0`).
- **Mips à la demande** — moins de VRAM et de bande passante, textures lointaines plus douces.
- **Compilation des shaders selon les cœurs** — en Auto, côte à côte dès 8 cœurs physiques.
- **Profil de performance** — les six presets, avec la machine détectée et le profil conseillé dans l'aide.

### Le reste de notre travail

- **FSR 4 (4.0.2)** et **FSR 3.1 (3.1.6)** au choix, applicables **à chaud**, sans redémarrer.
- **HDR corrigé** : les frames générées reçoivent la fonction de transfert PQ et la luminance ; plus d'image
  néon en HDR10.
- **OcaDim partout** : fenêtre, premier log, écran de démarrage, menu, Discord, rapports.
- **Fichiers renommés** : `ocadim.exe`, `ocadim_vk.dll`, `ocadim_options.ini`, `ocadim_env.txt`,
  `logs/ocadim_log.txt`, `cache/ocadim_*` ; les anciens `longshot_*` sont repris automatiquement.

## 2. Ce qu'on a récupéré de l'amont

- Les **barrières de jobs** du jeu attendent leur masque au lieu de dormir 20 µs (désactivable dans OcaDim).
- Les **résumés v2** du rapport de performance, avec les phases du replay.

## 3. Mise à jour

- Tes réglages, tes sauvegardes et tes caches sont **conservés**.
- Le nouveau Setup permet de **cocher NVIDIA lors d'une mise à jour** : un joueur en 0.0.2 peut activer
  DLSS en passant en 0.0.3, sans réinstaller.
- Sur les cartes AMD, la case NVIDIA ne change rien.

## 4. Vérifié

- RX 9070 XT, pilote 26.10.2 : FSR 4, FSR 3.1, bascule à chaud, HDR10, VRS chargé, précompilation 3,4 s,
  démarrage à chaque build testé.
- Place du marché : 48 images/s, 21,3 ms, 1 % low 47,8 ms (limité par le CPU).
- Plaine d'Hyrule : 67 images/s, 15,1 ms, 1 % low 21,7 ms, GPU 8,5 ms (56 %), VRAM 7,4 / 15,1 Go.

**Pas encore vérifié** : DLSS/DLAA sur une RTX, et le build joueur PGO du Setup.

**Aucune donnée de jeu n'est partagée.** Le Setup compile chez le joueur.
