# OcaDim 0.0.3 — la mise à jour des petits PC

**La plus grosse mise à jour d'OcaDim depuis la 0.0.2, et celle qui pense d'abord aux petites cartes et aux
portables.** Moins de VRAM, moins d'à-coups, des réglages qui s'adaptent au lieu de vous demander de deviner.

On fait de notre mieux : une seule machine de test (RX 9070 XT), beaucoup de cas difficiles, et tout ce qui
est annoncé ici a été mesuré et testé. Ce qui ne l'a pas été est écrit noir sur blanc à la fin. Vos retours
font le reste.

Tout ce qui suit a été **conçu, écrit et testé de notre côté** — pas repris, pas attendu : le menu est en
français, les réglages parlent, et le jeu s'adapte à la machine au lieu du contraire.

## 0. Sous le capot : ce qu'on a touché, et pourquoi

Des lignes, pas des promesses. Les endroits du moteur qu'on a modifiés pour les performances :

| Fichier | Ce qu'on y a fait |
|---|---|
| `gpu/vk/vk_main.cpp` | On demande `VK_KHR_fragment_shading_rate` et on chaîne `pipelineFragmentShadingRate` au device **seulement si le pilote l'a** ; chargement de `vkCmdSetFragmentShadingRateKHR` par `vkGetDeviceProcAddr`. |
| `gpu/vk/vk_draw.cpp` | `vrs_set()` applique **2x2 ou 4x4** au début de la frame et **1x1 juste avant le HUD** ; `precompile_zone()` construit **tous** les pipelines de la liste au chargement (`state_list_prepare` + `precompile_run`). |
| `gpu/vk/vk_replay.cpp` | `rec_cap()` : l'anneau d'enregistrement garde **24 frames au lieu de 48** en mode mémoire réduite, sans réallouer les tableaux. |
| `gpu/vk/vk_texture.cpp` | `low_vram_texture_mips()` obéit à la ligne **Mips à la demande** au lieu de ne servir que les petites cartes. |
| `gpu/vk/vk_menu.cpp` | Onze réglages OcaDim, le diagnostic **Ça rame ?**, le garde-fou qui pilote la résolution, la détection de la machine et le profil conseillé. Traduction **avant** troncature : plus aucun fragment anglais. |
| `host/hos_thread.c` | L'ordonnanceur lit `vcore_mode` dans l'ini : **Réactif** (escape 200 ms) et **Ultra réactif** (en plus, préemption 1 ms au lieu de 2). |
| `host/oot_barrier.c` | La ligne **Barrières de jobs** : masques du jeu au lieu de sommeils de 20 µs, réversible. |
| `gpu/vk/intel_compiles.h` | En Auto, la compilation des shaders passe **côte à côte dès 8 cœurs physiques**. |

Le détail qui compte : **rien de tout ça n'est actif par défaut sans mesure**, et chaque ligne se désactive.

## 1. Ce qu'on a ajouté nous-mêmes

### Ton PC, pas celui du voisin

Au démarrage, OcaDim regarde ta carte, ta VRAM, ton écran et tes cœurs, et il te le dit :

```
OcaDim: détection : AMD Radeon RX 9070 XT, 16304 MB of video memory, dedicated,
screen 2560x1440 at 144 Hz, 32694 MB of RAM, 16 threads
```

Le profil conseillé en découle, et la ligne **Profil de performance** l'applique d'un geste — avec l'ancien
réglage gardé sous « Personnalisé ».

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

### Les outils de compilation sont maintenant livrés avec le Setup

L'archive est plus grosse (**343 Mo**) parce qu'elle contient désormais **tous les outils de compilation**
(`clang`, `lld`, la bibliothèque standard, `python`, les dépendances). C'est un choix :

- **un seul téléchargement**, puis plus rien à récupérer pendant l'installation ;
- **plus de dépendance à des dépôts externes** : si un hébergement disparaît, OcaDim continue de compiler ;
- les empreintes de `tools.lock` vérifient chaque fichier.

Avant, le Setup téléchargeait ces mêmes ~450 Mo au moment du build. La différence, c'est *quand* : tout de
suite et une fois, au lieu de pendant les 40 minutes de compilation.

### Compilation légère (petit PC)

L'assistant propose **« Compilation légère »** : un seul compilateur à la fois. Beaucoup plus lent, mais une
machine avec peu de RAM ne tombe plus en panne pendant le build.

## 4. Vérifié

- RX 9070 XT, pilote 26.10.2 : FSR 4, FSR 3.1, bascule à chaud, HDR10, VRS chargé, précompilation 3,4 s,
  démarrage à chaque build testé.
- Place du marché : 48 images/s, 21,3 ms, 1 % low 47,8 ms (limité par le CPU).
- Plaine d'Hyrule : 67 images/s, 15,1 ms, 1 % low 21,7 ms, GPU 8,5 ms (56 %), VRAM 7,4 / 15,1 Go.

**Pas encore vérifié** : DLSS/DLAA sur une RTX, et le build joueur PGO du Setup.

**Aucune donnée de jeu n'est partagée.** Le Setup compile chez le joueur.
