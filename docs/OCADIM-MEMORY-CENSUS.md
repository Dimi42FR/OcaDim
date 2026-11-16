# Le chantier mémoire, mesuré avant d'être codé : le magasin zstd n'est pas le levier

Date : 16/11/2026. Branche `v0.1.0-amont`. Sonde : `RX_VK_MEM_CENSUS=1`.

La conception retenue dans la passation était : à la ré-éviction d'une texture, garder une copie zstd des octets
décodés en RAM CPU, et décompresser au lieu de re-décoder. Ce document mesure ce que cela pourrait rapporter. Réponse :
**0,05 % du temps de frame au pire**. Le chantier est écarté avant d'avoir coûté une ligne de cache.

## Ce que la sonde mesure

- les textures **refaites après une éviction** (« made again ») : combien, combien d'octets, et **combien de frames
  après** leur sortie (0-5, 6-30, 31-60, 61-300, plus de 300) ;
- la route **ASTC sur le GPU** (celle qui décode et ré-encode : le seul décodage cher du moteur) séparée en
  **premier upload** et **refait** : nombre, octets, millisecondes ;
- les mêmes chiffres par frame, dans la ligne `a frame's uploads took …` quand une frame dépasse 50 ms d'uploads.

Éteinte, elle ne coûte qu'un `bool` statique par création de texture. La table
`evicted_from_memory` (`vk_texture.cpp`, la même que la règle « refaite, uploadée depuis la mémoire ») porte désormais
la frame de l'éviction, ce qui donne l'âge du retour sans structure nouvelle.

## Résultats (même sauvegarde, 90 s, fenêtre, `RX_VK_VRAM_MB=<n>`)

| Budget | fps en fin de run | textures résidentes | re-makes | ASTC premier | ASTC refait | uploads (profil) |
|---|---|---|---|---|---|---|
| 4096 (défaut) | 55,6 | 3 723 Mo | **0** | 994 (405 Mo, 390 ms) | 0 | ~0,00 ms/frame |
| 2048 | 53,6 | 2 805 Mo | 1 084 (227 Mo) | 995 (404 Mo) | 466 (126 Mo) | 0,03-0,05 ms/frame |
| 1024 | 53,0 | 2 835 Mo | 1 639 (352 Mo) | 978 (401 Mo, 361 ms) | 717 (205 Mo, **43 ms**) | 0,03-0,05 ms/frame |
| 512 | 52,8 | 2 793 Mo | 1 733 (371 Mo) | 1 020 (413 Mo, 381 ms) | 761 (209 Mo, **42 ms**) | 0,03-0,05 ms/frame |

Âges des retours à 1 Go : 0-5 frames : 211 ; 6-30 : 299 ; 31-60 : 252 ; 61-300 : 717 ; plus de 300 : 160.

## Verdict

1. **Le plafond du magasin zstd est le temps des « refaits »**, et il est de 39-43 ms sur un run entier de 90 s, soit
   0,05 % du temps de frame à 1 Go. Même en supposant la décompression gratuite, on ne récupère pas 1 %.
2. **Le décodage n'est pas ce que coûte la mémoire ici.** La colonne `uploads` du profil est à 0,03-0,05 ms/frame à
   1 Go : la route ASTC entière (premiers inclus) fait 0,4 % du temps de frame.
3. **La courbe fps est plate** : 55,6 → 52,8 fps de 4 Go à 512 Mo. Le chiffre fondateur du chantier (32,1 fps contre
   43-46) ne se reproduit pas : le run `vram2g` avait 3,4 Go de textures et 2,3 Mo d'uploads par frame, la sauvegarde
   actuelle donne 2,8 Go et 0,1-0,2 Mo. Comparer deux sessions différentes n'est pas une mesure.
4. **`RX_VK_VRAM_MB` ne simule pas une petite carte** : les textures résidentes restent à ~2,8 Go à 512 Mo de budget,
   parce que l'éviction ne prend pas ce qui a servi dans les 60 dernières frames. On force des re-makes, on ne fait
   jamais payer la pression au driver. Pour approcher une vraie petite carte il faudrait `RX_VK_TEST_ALLOWED_MB`
   (ce que le driver *dit* autoriser, `vk_vma.cpp`), et même ainsi les allocations ne échouent pas.
5. Les uploads lents (15-48 ms pour 0,1-0,6 Mo) n'apparaissent **qu'à budget serré** et frappent une texture différente
   chaque fois : c'est le coût d'allocation (staging de 64 Mo, image) sous pression, pas le décodage. Dix occurrences
   par run.

## Ce qui reste ouvert

- **La vraie petite carte** : le mode d'échec est le driver qui pagine (soumissions de plusieurs secondes), pas notre
  éviction. À reproduire avec `RX_VK_TEST_ALLOWED_MB=6144` **et** un budget de textures cohérent, en regardant les
  soumissions, avant de conclure quoi que ce soit sur les 6-8 Go.
- **La scène qui donnait 32 fps** : elle est perdue avec la sauvegarde. Si elle compte, il faut la retrouver (ou la
  refaire) et refaire l'A/B budget dans la même session.
- **Le chargement** : 390 ms d'ASTC contre 1 581 ms de `programs` (265 pipelines neufs). Le chantier suivant est là,
  et la question reste celle de la passation : ces 265 pipelines étaient-ils prévisibles depuis le pipeline tour ?

## Réparé au passage

`tests/test_readback_timeout_reuse.py` était **cassé à HEAD** (indépendamment de cette sonde) : il découpe la fin de
l'éviction, qui nomme `tex_tombstones` depuis le pool de tombstones de la fusion, et la fixture ne le déclarait pas.
Une ligne ajoutée, il repasse — et il vérifie donc de nouveau la reprise après un read-back expiré.
