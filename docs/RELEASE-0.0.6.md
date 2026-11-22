# OcaDim 0.0.6 — le démarrage ne se bloque plus, et vos jeux changent d'ambiance

Cette version, c'est d'abord **deux ennuis en moins** et **un plaisir en plus** : un écran de
démarrage qui ne reste plus coincé, un cache qui ne grossit plus sans fin, et un onglet
**Effets** pour donner à Ocarina of Time l'ambiance que vous voulez, en un geste.

## L'écran de démarrage ne se bloque plus

Vous connaissez le tableau : vous lancez le jeu, une vidéo ou une autre fenêtre passe devant,
et l'écran OcaDim reste affiché à **100 %** — alors que le jeu tourne très bien derrière.
C'était un vrai bug, il est corrigé : une fois fermé, l'écran de démarrage ne revient plus.

## Un cache qui ne mange plus votre disque

Le cache des programmes traduits grossissait sans limite (7,2 Go chez nous, chargés en RAM au
démarrage). Une nouvelle ligne du F1, **« Plafond du cache de programmes »**, fixe sa taille
maximale : **Auto (2 Go)**, 1, 2, 4, 8 Go, **Illimité**, ou **Vider**.

- au-delà du plafond, les nouveaux programmes ne sont plus enregistrés — **rien n'est retraduit** ;
- **Vider** efface le cache au prochain démarrage, puis la ligne revient sur Auto ;
- rappel : depuis la 0.0.5-2, le jeu consomme **8,6 Go de RAM au lieu de 18,7**, mêmes images
  par seconde.

## Nouvel onglet Effets

L'ancien onglet *Ray-Tracing* devient **Effets**. Tout est dessiné **par-dessus** l'image, sans
y toucher : rien ne peut l'abîmer, et le coût est négligeable.

| Réglage | L'ambiance |
|---|---|
| **Style** | un préréglage complet : Défaut, Nuit, Coucher de soleil, Donjon, Cinéma, Pluie, Rétro, **Net et propre** |
| **Lampe torche** | l'écran s'assombrit, un halo éclaire le centre — parfait pour les donjons |
| **Cadre cinéma** | des barres noires, comme au cinéma |
| **Halo** | une lueur douce au centre |
| **Sépia** | l'ambiance d'un vieux film |
| **Bougie** | la lumière respire lentement |
| **Vieille télé** | coins arrondis et fines lignes |
| **Vignette** | les bords s'assombrissent |
| **Teinte (chaud / froid)** | bleuté la nuit, orangé au couchant |
| **Grain** | une texture de pellicule |
| **Brillance et scintillements** | les rues et les dalles paraissent humides |

Le style **« Net et propre »** imite le *rendu* d'un upscaler moderne (halo léger, vignette
discrète, aucun grain).

**Ce n'est pas du DLSS** : aucun upscaler neuronal n'est utilisé, c'est un traitement d'image
par-dessus le jeu. La netteté, elle, vient de la ligne **Netteté** de l'upscaler (onglet
Graphismes) — FSR 4 sur AMD, DLSS sur NVIDIA.

## Ce qui n'est pas dans cette version

Dire ce qu'on ne fait pas fait partie du contrat :

- **les reflets écran (SSR) ne sont pas livrés** : le shader est écrit, mais le reflet grésille
  sur une image upscalée sans accumulation temporelle. Le code reste en place, désactivé ;
- **le culling a été mesuré et abandonné** : 0,9 % des draws sont réellement hors champ en
  forêt, 5,2 % en ville — le jeu cull déjà très bien lui-même.

## Compatibilité

- **AMD** : FSR 4, FSR 4 Frame Generation et Anti-Lag 2 si les DLL AMD sont présentes.
- **NVIDIA** : DLSS Quality automatique, aucun FSR 4 imposé.
- Les DLL AMD (`amd_fidelityfx_*`) ne sont pas incluses dans le source : placez-les à côté de
  `ocadim.exe`.

## Mise à jour

Remplacer `ocadim.exe` et `ocadim_vk.dll`. Vos réglages, sauvegardes et caches sont conservés.

## Crédits

OcaDim — Dimi42FR. Basé sur Longshot (MagicBeanDev).
