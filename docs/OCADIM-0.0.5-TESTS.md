# OcaDim 0.0.5 — Tests et mesures

Tous les réglages et toutes les optimisations de cette version ont été validés en jeu, à la main,
sur la même sauvegarde, la même zone et la même caméra. Ce document garde la trace des mesures,
y compris celles qui ont été **rejetées**.

## Machine de test

- CPU : AMD Ryzen 7 5800X (8 cœurs / 16 threads)
- RAM : 32 Go
- GPU : AMD Radeon RX 9070 XT, 16 Go (RDNA 4), pilote AMD 26.11.2
- Écran : 2560×1440 à 144 Hz
- API : Vulkan 1.4
- FSR : upscaler 4.1.2, frame generation 4.0.0

## Protocole

- Même sauvegarde, même zone (Forêt Kokiri), même caméra, **sans input**.
- Un test = un lancement, on marche jusqu'au même point, on laisse tourner quelques secondes.
- Relevés dans le log du jeu :
  - `N presents, X fps; a frame: D draws ...`
  - `a frame's replay time (ms): submit ... draw ... descriptors ...`
  - `GPU time X ms a frame`
- En replay parallèle, les temps CPU (`draw`, `descriptors`, `commands`…) sont des **sommes de
  threads** : les valeurs utiles pour comparer sont **fps** et **submit**.
- Un lot qui perd des fps est rejeté, même s'il paraît meilleur sur le papier.

## Résultats

| Configuration | fps | submit | draws |
|---|---|---|---|
| Base D (0.0.4 + RT), replay sur le thread du jeu | 53,8 | 15,39 ms | ~3 059 |
| workers=2 | 59,5-62,4 | 13,33-13,39 ms | ~3 119-3 189 |
| workers=4 | 60,2-61,5 | 11,27-11,94 ms | ~3 173-3 311 |
| **workers=4 + segments=32 (défaut 0.0.5)** | **63,9-66,0** | **10,6-10,7 ms** | ~3 100-3 117 |
| workers=4 + segments=32 + cache 4 programmes | 62,8-65,0 | 11,5-11,7 ms | ~3 166 |
| workers=6 + segments=32 | 63,1-64,7 | 9,9 ms | ~2 972-2 975 |
| workers=4 + segments=32 + préchargement des descripteurs | 58,8-62,4 | 11,7-12,4 ms | ~3 023-3 081 |
| workers=4 + segments=32, render thread coupé | 58,9-59,8 | 10,7-11,0 ms | ~3 113-3 134 |
| Lot « lift » amont (FPXKEEP, VECFP, float rapides) | 49,6 | 16,87 ms | ~3 016 |

Gain total mesuré par rapport à la base D : **environ +10 à +12 fps**, et submit de
**15,39 ms → 10,6-10,7 ms**.

## Ce qui est accepté

- **Threads du replay à 4** : le replay est découpé en segments enregistrés en parallèle.
  Gain majeur, submit de 15,4 → 11,3-11,9 ms.
- **Segments de 32 draws/dispatchs** (au lieu de 160) : +3 à +4 fps et submit encore en baisse.
  C'est le réglage par défaut de la 0.0.5.
- **Cache de 4 programmes par thread** (au lieu de 2) : gardé pour éviter une retraduction de
  shader dans les scènes qui alternent 3-4 programmes. Gain non démontré, risque faible, aucune
  régression constatée.
- **Threaded rendering (render thread + recorder)** : laissé **On**. Mesuré comme valant
  **+5 à +6 fps** (voir plus bas).

## Ce qui est rejeté

- **Lot « lift » amont** (FPXKEEP, VECFP, régions float rapides, fastvec/registres) : ~1,5 ms de
  CPU en plus, **~4 fps perdus**. Rejeté et conservé sur une branche séparée pour analyse.
- **Préchargement des descripteurs** : descripteurs +6 à +15 %, fps en baisse. Rejeté.
- **6 threads de replay** : mêmes fps, mais des cœurs pris au jeu et un ressenti moins bon.
  La limite du menu accepte 1 à 8, le défaut reste 4.
- **Render thread coupé** : 58,9-59,8 fps contre 63,9-66,0 avec un submit **identique**. Le replay
  coûte donc pareil : le gain du render thread vient du **recouvrement** avec le travail du jeu,
  pas d'un replay plus rapide.
- **Recorder coupé** : non testé, la mesure du recorder donne 54 ms d'attente du replay sur 10 s
  (0,5 %), il n'y a rien à y gagner.

## Où part le temps (profilage fin)

Mesure faite avec le profileur interne (`RX_VK_PROF_FINE=1`), en ms par frame cumulées sur les
4 threads de replay. Le profileur coûte lui-même 2 à 4 fps : ces chiffres servent à comparer les
postes entre eux, pas à établir une référence.

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

Conclusion : le coût est **étalé**, sans poste dominant. 97 % des draws reconstruisent leurs
descripteurs parce que leurs liaisons changent réellement. Il n'y a pas d'algorithme à corriger
ici, seulement du micro-polissage qui rapporterait 1 à 2 fps au mieux.

## Pistes non retenues pour cette version

- Culling des acteurs hors caméra : gros potentiel en ville, mais risque sur les scripts, la
  musique et les portes. À faire derrière une option, avec contrôle visuel.
- LTO / PGO / -O3 sur les fonctions chaudes : gain modeste, builds plus longs.
- Affinité CCX : sans objet sur un 5800X (un seul CCD).
- Précompilation au chargement pour les 1 % low : pas nécessaire, aucun gel constaté en
  déplacement.

## Reproduire une mesure

Dans le fichier d'options, les réglages testés sont :

```
threaded_rendering=1
replay_workers=4
replay_seg=1        (0 = 160, 1 = 32, 2 = 64, 3 = 160)
descriptor_prefetch=0
```

Les deux réglages de threads peuvent aussi être forcés par variable d'environnement pour un
lancement, sans modifier le fichier : `RX_VK_ASYNC=0` (render thread coupé) et
`RX_VK_RECORDER=0` (recorder coupé).
