# Les programmes au chargement, mesurés (chantier 2) : rien ne se traduit, tout se crée

Date : 16/11/2026. Sonde : `RX_VK_LOG_PROGRAM_LIFE=1` (existante), run `prog-warm`, 75 s, cache de programmes
chaud (1 068 clés, 154 Mo), cache de pipelines 71 Mo.

## Ce que la question supposait, et ce que le log dit

La passation supposait 265 programmes traduits au chargement, à pré-traduire depuis le « pipeline tour ». Le journal
des premières utilisations dit autre chose :

```
first uses 786:  program ready 108, loaded 668, translated 0, failed 10
                pipeline ready 51, from a cache 90, compiled 0, made 209, left out 426
in play: 717 program records loaded (344 ms), 1 033 new graphics pipelines
```

**Zéro traduction.** Les 668 programmes viennent du cache de programmes (`longshot_programs.bin`, 158 Mo) ; le coût
est de les lire (344 ms au total). Le reste est du pipeline : 209 créés, 90 sortis du cache du driver.

## Où passent les 1 931 ms de premières utilisations

| Groupe | n | total | médiane | p90 | pire |
|---|---|---|---|---|---|
| programme lu + pipeline **créé** | 196 | 674 ms | 0,73 ms | 5,4 | 147,8 |
| programme lu + pipeline **du cache** | 47 | 210 ms | 0,73 ms | 4,3 | 67,0 |
| programme lu + dessin **laissé de côté** | 424 | 869 ms | 1,62 ms | 3,7 | 22,6 |
| programme **prêt** + pipeline cache | 43 | 55 ms | 0,17 ms | 2,4 | 15,6 |

La médiane est sous la milliseconde : le chargement n'est pas cher par unité, il est cher par **une vingtaine de cas**.
23 premières utilisations dépassent 10 ms et font **749 ms à elles seules (39 %)**.

## Le fait qui change la conclusion

Ces cas chers ne sont pas tous des compilations : **67,0 ms et 42,1 ms sont des pipelines sortis du cache** du driver.
Un pipeline « déjà là » peut donc coûter aussi cher qu'un pipeline créé. Pré-construire les pipelines pendant le tour
(ce que proposait le chantier) ne supprime donc pas la classe de coût : elle déplace au mieux les 400 ms des cas
« made », pas les 110 ms des cas « cache ».

## Et sur cette installation, rien n'a jamais été prédit

`work/sa/build/cache` n'a **pas** de `longshot_pipelines.bin.predicted_keys` : `predict_run` n'a pas produit de clés
ici, donc aucun pipeline n'a été pré-construit. Le cache du driver y fait 73 Mo, contre 1,4 Go dans l'installation de
`F:\test`. Autrement dit : **nos mesures de chargement sont celles d'une installation sans préparation**, pas celles
d'un joueur.

## Ce qu'il faut décider

1. **Mesurer l'installation de référence** (`F:\test`, caches de 1,4 Go, préparation faite) avec la même sonde : si
   les cas chers y disparaissent, le chantier est déjà réglé pour les joueurs et ne concerne que les builds de dev.
2. **Faire la préparation ici** (`RX_VK_PREPARE_AGAIN=1`, 20-30 min d'après `prepare_workers.h`) puis re-mesurer :
   c'est la seule façon de chiffrer le plafond du pré-construit.
3. Si les cas chers survivent aux deux, ils ne sont pas des compilations : il faudra identifier ce que coûtent ces
   quelques clés (module, layout, premier enregistrement) avant tout code.
