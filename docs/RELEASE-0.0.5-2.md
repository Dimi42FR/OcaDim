# OcaDim 0.0.5-2

Correction de mémoire. **Mêmes performances, 9 à 10 Go de RAM en moins.**

## Le problème

Le cache de programmes traduits (`cache/ocadim_programs.bin`) grossit avec les sessions : chez nous,
**7,2 Go** pour **47 798 programmes**. Et le réglage **Auto** de la ligne « Programmes avant le
titre » le chargeait **en entier en mémoire** au démarrage. Résultat mesuré en jeu :

- **18,7 Go** de RAM pour le jeu, sur 32 Go de machine — 6 Go libres pour tout le reste ;
- des ralentissements et des chargements interminables, sans qu'on comprenne pourquoi.

## Le correctif

La ligne **« Programmes avant le titre »** reste, mais **Auto** s'arrête maintenant à un budget :
au-delà de **2 Go** de cache, les programmes ne sont plus chargés avant le titre — ils se lisent à
leur première utilisation, directement dans le cache, sans retraduction.

- **« Activé »** force toujours le chargement complet (comportement d'avant) ;
- **`RX_VK_LOAD=start`** aussi, pour un lancement ;
- le journal dit lequel des deux s'applique :
  `vk: program cache 7322 MB: the programs are loaded at their first use, not before the title`.

## Mesures (même sauvegarde, même zone)

| | 0.0.5 | **0.0.5-2** |
|---|---|---|
| RAM en jeu | 17,8-18,7 Go | **8,6 Go** |
| fps (zone légère, 1 425-1 815 draws) | 75,3-77,4 | **75,3-77,4** |
| programmes recréés en jeu | 0 | **0** |
| programmes chargés au démarrage | 47 798 | **0** |

Aucun programme n'est retraduit : tout vient du cache, à la demande.

## À savoir

- **Rien d'autre ne change** : threads de replay (4), segments (32), FSR 4, frame generation,
  menu F1 OcaDim, tout est identique à la 0.0.5.
- Le premier démarrage après une mise à jour qui touche au traducteur de shaders retraduit les
  programmes : c'est le seul cas où le cache repart de zéro, et c'est déjà le cas depuis la 0.0.5.
- Pour les micro-freezes de pipelines : la ligne **« Précompilation au chargement »** (onglet
  OcaDim) construit les pipelines d'une zone pendant son écran de chargement au lieu de les
  construire en jeu.

## Mise à jour

Remplacer `ocadim.exe` et `ocadim_vk.dll`. Les réglages, les sauvegardes et les caches sont
conservés.

## Crédits

OcaDim — Dimi42FR. Basé sur Longshot (MagicBeanDev).
