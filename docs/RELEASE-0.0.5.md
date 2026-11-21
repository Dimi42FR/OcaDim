# OcaDim 0.0.5

Mise à jour de performance, de confort et de transparence.

## Nouveautés

- **Menu F1 OcaDim en français par défaut**, avec l'onglet OcaDim complet.
- **Nouvel écran de démarrage OcaDim** : artwork, barre dorée, séparateur OcaDim, textes français, affichage minimum de 2,5 s.
- **Ray-Tracing marqué EXPÉRIMENTAL — NE FONCTIONNE PAS** : SSR et test BVH ne sont plus présentés comme fiables.
- **« Save my pipeline list » reste local** : le zip va dans Téléchargements, rien n'ouvre Chrome ni GitHub, rien n'est envoyé.
- **Graphe « Shaders built » corrigé** : les pipelines construits pendant la précompilation sont maintenant comptés.
- **FSR 4 Frame Generation** disponible et vérifiée (contexte AMD FSR 4, images générées comptées).
- **Configuration par défaut mesurée** : FSR 4 Native AA (AMD), DLSS Quality (NVIDIA), 92 %, cap 144, rendu thread, draw order, sampler cache, ombres 1600, Anti-Lag AMD.
- **Threads du replay à 4 et segments à 32 par défaut** : gain mesuré d'environ **10 à 12 fps** et submit de **15,4 → 10,6-10,7 ms**.

## Performances mesurées (Kokiri Forest, même sauvegarde)

| Réglage | fps | submit |
|---|---|---|
| Référence | 53,8 | 15,39 ms |
| workers=2 | 59,5-62,4 | 13,3 ms |
| **workers=4 (défaut)** | **60,2-61,5** | **11,3-11,9 ms** |

Lots testés et **rejetés** :

- lift amont (FPXKEEP, VECFP, fast float, fastvec/registres) : ~4 fps perdus ;
- préchargement des descripteurs : descripteurs +6 %.

## Compatibilité

- **AMD** : FSR 4 / FSR 4 FG / Anti-Lag 2 si les DLL AMD sont présentes.
- **NVIDIA** : DLSS Quality automatique, draw order, pas de FSR 4 imposé.
- Les DLL AMD (`amd_fidelityfx_*`) ne sont pas incluses dans le source ; elles doivent être placées à côté de `ocadim.exe`.

## Mise à jour

Remplacer `ocadim.exe`, `ocadim_vk.dll` et les DLL AMD. Le premier démarrage après mise à jour reconstruit les caches de shaders (plus long, une seule fois).

## Crédits

OcaDim — Dimi42FR. Basé sur Longshot (MagicBeanDev).
