# OcaDim 0.0.6

Correctifs et effets. **Mêmes performances**, un écran de démarrage qui ne se bloque plus,
un cache maîtrisé et un onglet **Effets** entièrement nouveau.

## Les correctifs

- **Écran de démarrage débloqué.** Quand la fenêtre du jeu était recouverte au lancement
  (une vidéo, une autre application), l'écran OcaDim pouvait rester affiché à **100 %** devant
  le jeu qui tournait derrière. Il ne peut plus revenir une fois fermé.
- **Plafond du cache de programmes.** Le cache des programmes traduits grossissait sans limite
  (7,2 Go chez nous). Une nouvelle ligne du F1, **« Plafond du cache de programmes »**, choisit
  sa taille maximale : **Auto (2 Go)**, 1, 2, 4, 8 Go, **Illimité**, ou **Vider** (efface le
  cache au prochain démarrage, puis revient sur Auto). Au-delà du plafond, les nouveaux
  programmes ne sont plus enregistrés — rien n'est retraduit pour autant.
- **Mémoire** (déjà livrée en 0.0.5-2, rappelée ici) : le jeu passe de **18,7 Go à 8,6 Go** de
  RAM en jeu, mêmes images par seconde.

## L'onglet Effets

L'ancien onglet *Ray-Tracing* devient **Effets**. Tous ces réglages sont dessinés **par-dessus**
l'image, sans y toucher : aucun ne peut la corrompre, et ils ne coûtent rien de mesurable.

| Réglage | Ce qu'il fait |
|---|---|
| **Style** | un préréglage complet : **Défaut**, Nuit, Coucher de soleil, Donjon, Cinéma, Pluie, Rétro, **Net et propre** |
| **Lampe torche** | l'écran s'assombrit, un halo éclaire le centre |
| **Cadre cinéma** | barres noires en haut et en bas |
| **Halo** | une lueur douce au centre |
| **Sépia** | un voile brun, ambiance vieux film |
| **Bougie** | la luminosité respire lentement |
| **Vieille télé** | coins arrondis et fines lignes |
| **Vignette** | bords assombris |
| **Teinte (chaud / froid)** | 50 = neutre, en dessous bleuté, au-dessus orangé |
| **Grain** | texture de pellicule, fixe |
| **Brillance et scintillements** | les sols paraissent humides |

Le style **« Net et propre »** imite le *rendu* d'un upscaler moderne (halo léger, vignette
discrète, aucun grain). **Ce n'est pas du DLSS** : aucun upscaler neuronal n'est utilisé. La
netteté elle-même vient de la ligne **Netteté** de l'upscaler (onglet Graphismes).

## Ce qui n'est pas dans cette version

- **Le SSR (reflets écran) n'est pas livré.** Le shader et le pipeline sont écrits, mais le
  reflet grésille sur l'image upscalée : sans accumulation temporelle, il n'est pas stable. Le
  code reste en place, désactivé, pour une reprise.
- Le **culling** a été mesuré et abandonné : 0,9 % des draws sont réellement hors champ en
  forêt, 5,2 % en ville — le jeu culle déjà lui-même.

## Compatibilité

- **AMD** : FSR 4 / FSR 4 FG / Anti-Lag 2 si les DLL AMD sont présentes.
- **NVIDIA** : DLSS Quality automatique, pas de FSR 4 imposé.
- Les DLL AMD (`amd_fidelityfx_*`) ne sont pas incluses dans le source.

## Mise à jour

Remplacer `ocadim.exe` et `ocadim_vk.dll`. Les réglages, les sauvegardes et les caches sont
conservés.

## Crédits

OcaDim — Dimi42FR. Basé sur Longshot (MagicBeanDev).
