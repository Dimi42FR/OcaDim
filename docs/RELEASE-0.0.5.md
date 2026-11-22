# OcaDim 0.0.5

Mise à jour de performance, de confort et de transparence.

## L'essentiel de cette version

- **Le replay tourne sur 4 threads, par segments de 32 draws** : c'est le gros du travail de cette
  version. Mesuré sur la même sauvegarde, même zone : **53,8 → 63,9-66,0 fps** (+10 à +12 fps) et
  submit de **15,39 → 10,6-10,7 ms**.
- **Cache de 4 programmes par thread** : plus de retraduction de shader dans les scènes qui
  alternent 3-4 programmes.
- **Tout est mesuré et documenté**, y compris ce qui a été rejeté (lot « lift » amont, préchargement
  des descripteurs, 6 threads de replay, render thread coupé). Voir les tableaux plus bas.

### Gains mesurés (Forêt Kokiri, même sauvegarde, même caméra)

| Réglage | fps | submit |
|---|---|---|
| Base D avant cette version | 53,8 | 15,39 ms |
| Replay 2 threads | 59,5-62,4 | 13,33-13,39 ms |
| Replay 4 threads, segments 160 | 60,2-61,5 | 11,27-11,94 ms |
| **Cette version : 4 threads + segments 32** | **63,9-66,0** | **10,6-10,7 ms** |

Testés et **rejetés** après mesure :

| Réglage rejeté | fps | Pourquoi |
|---|---|---|
| Lot « lift » amont (FPXKEEP, VECFP, float rapides) | 49,6 | ~1,5 ms de CPU en plus, ~4 fps perdus |
| Préchargement des descripteurs | 58,8-62,4 | descripteurs +6 à +15 % |
| 6 threads de replay | 63,1-64,7 | mêmes fps, cœurs pris au jeu, ressenti moins bon |
| Render thread coupé | 58,9-59,8 | submit identique : c'est le recouvrement qui compte |

## Nouveautés

- **Threads du replay à 4 et segments à 32 par défaut** : gain mesuré d'environ **10 à 12 fps** et submit de **15,4 → 10,6-10,7 ms**.
- **Cache de 4 programmes par thread** : évite une retraduction de shader dans les scènes qui alternent 3-4 programmes (aucune régression constatée).
- **Menu F1 OcaDim en français par défaut**, avec l'onglet OcaDim complet.
- **Nouvel écran de démarrage OcaDim** : artwork, barre dorée, séparateur OcaDim, textes français, affichage minimum de 2,5 s.
- **Ray-Tracing marqué EXPÉRIMENTAL — NE FONCTIONNE PAS** : SSR et test BVH ne sont plus présentés comme fiables.
- **« Save my pipeline list » reste local** : le zip va dans Téléchargements, rien n'ouvre Chrome ni GitHub, rien n'est envoyé.
- **Graphe « Shaders built » corrigé** : les pipelines construits pendant la précompilation sont maintenant comptés.
- **FSR 4 Frame Generation** disponible et vérifiée (contexte AMD FSR 4, images générées comptées).
- **Configuration par défaut mesurée** : FSR 4 Native AA (AMD), DLSS Quality (NVIDIA), 92 %, cap 144, rendu thread, draw order, sampler cache, ombres 1600, Anti-Lag AMD.

## Tests et mesures

Machine de test : **Ryzen 7 5800X** (8 cœurs / 16 threads), 32 Go, **Radeon RX 9070 XT** 16 Go
(RDNA 4, pilote AMD 26.11.2), 2560×1440 à 144 Hz, Vulkan 1.4.

Protocole : même sauvegarde, même zone (**Forêt Kokiri**), même caméra, sans input. Un test =
un lancement, on rejoint le même point, on laisse tourner. Les temps CPU en replay parallèle
sont des sommes de threads : les valeurs de comparaison sont **fps** et **submit**.

| Configuration | fps | submit | draws |
|---|---|---|---|
| Base D (0.0.4 + Ray-Tracing), replay sur le thread du jeu | 53,8 | 15,39 ms | ~3 059 |
| workers=2 | 59,5-62,4 | 13,33-13,39 ms | ~3 119-3 189 |
| workers=4 | 60,2-61,5 | 11,27-11,94 ms | ~3 173-3 311 |
| **workers=4 + segments=32 (défaut 0.0.5)** | **63,9-66,0** | **10,6-10,7 ms** | ~3 100-3 117 |
| workers=4 + segments=32 + cache 4 programmes | 62,8-65,0 | 11,5-11,7 ms | ~3 166 |
| workers=6 + segments=32 | 63,1-64,7 | 9,9 ms | ~2 972-2 975 |
| workers=4 + segments=32 + préchargement des descripteurs | 58,8-62,4 | 11,7-12,4 ms | ~3 023-3 081 |
| workers=4 + segments=32, render thread coupé | 58,9-59,8 | 10,7-11,0 ms | ~3 113-3 134 |
| Lot « lift » amont (FPXKEEP, VECFP, float rapides) | 49,6 | 16,87 ms | ~3 016 |

Gain total contre la base D : **environ +10 à +12 fps**, submit **15,39 → 10,6-10,7 ms**.

### Accepté

- **Threads du replay à 4** : le replay est découpé en segments enregistrés en parallèle.
- **Segments de 32 draws/dispatchs** (au lieu de 160) : +3 à +4 fps, submit encore en baisse.
- **Cache de 4 programmes par thread** : gardé, gain non démontré mais risque faible.
- **Threaded rendering (render thread + recorder) laissé On** : mesuré à **+5 à +6 fps**.

### Rejeté après mesure

- **Lot « lift » amont** (FPXKEEP, VECFP, régions float rapides, fastvec/registres) : ~1,5 ms de CPU en plus, **~4 fps perdus**.
- **Préchargement des descripteurs** : descripteurs +6 à +15 %, fps en baisse.
- **6 threads de replay** : mêmes fps, des cœurs pris au jeu, ressenti moins bon. Le menu accepte 1 à 8, le défaut reste 4.
- **Render thread coupé** : 58,9-59,8 fps contre 63,9-66,0, avec un submit **identique** (10,7-11,0). Le gain du render thread vient du **recouvrement** avec le travail du jeu, pas d'un replay plus rapide.
- **Recorder coupé** : non testé, sa mesure donne 54 ms d'attente du replay sur 10 s (0,5 %), rien à y gagner.

### Où part le temps (profilage fin interne)

En ms par frame, cumulées sur les 4 threads de replay. Le profileur coûte 2 à 4 fps : ces chiffres
servent à comparer les postes entre eux.

| Poste | ms |
|---|---|
| Résolution des textures dans les descripteurs | 3,33 |
| Draw calls | 1,89 |
| Bind des descripteurs (dont le push 0,83) | 1,58 |
| Uniform buffers utilisateur | 1,52 |
| Vertex + index | 1,13 |
| Storage buffers | 0,81 |
| Hazards + passes | 0,42 |
| Dynamic state | 0,41 |
| Banks | 0,38 |
| Bind pipeline | 0,26 |
| Push constants | 0,21 |

Le coût est **étalé**, sans poste dominant : 97 % des draws reconstruisent leurs descripteurs
parce que leurs liaisons changent réellement. Les micro-optimisations de ce chemin ont donc été
abandonnées (1 à 2 fps au mieux).

### Pistes non retenues pour cette version

- Culling des acteurs hors caméra : gros potentiel en ville, mais risque sur les scripts, la musique et les portes.
- LTO / PGO / -O3 sur les fonctions chaudes : gain modeste, builds plus longs.
- Affinité CCX : sans objet sur un 5800X (un seul CCD).
- Précompilation pour les 1 % low : non nécessaire, aucun gel constaté en déplacement.

Le détail complet (protocole, toutes les mesures, réglages à reproduire) est fourni dans
**`OCADIM-0.0.5-TESTS.md`**, joint à cette release.

## Compatibilité

- **AMD** : FSR 4 / FSR 4 FG / Anti-Lag 2 si les DLL AMD sont présentes.
- **NVIDIA** : DLSS Quality automatique, draw order, pas de FSR 4 imposé.
- Les DLL AMD (`amd_fidelityfx_*`) ne sont pas incluses dans le source ; elles doivent être placées à côté de `ocadim.exe`.

## Mise à jour

Remplacer `ocadim.exe`, `ocadim_vk.dll` et les DLL AMD. Le premier démarrage après mise à jour reconstruit les caches de shaders (plus long, une seule fois).

## Crédits

OcaDim — Dimi42FR. Basé sur Longshot (MagicBeanDev).
