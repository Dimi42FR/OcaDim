## Ce qui change — NVIDIA

**Le Setup ne demandait jamais le SDK de NVIDIA.** Le renderer était donc compilé **sans DLSS**, `ngx/` n'était pas
livré, et sur une carte RTX le F1 n'avait **aucun onglet NVIDIA** : pas de DLSS, pas de DLAA, pas de frame generation
NVIDIA (DLSS-G). Sur une 4070, tout ça restait muet.

Ce qui est corrigé :

- une case **« Compiler avec NVIDIA DLSS et la frame generation (cartes RTX : DLSS, DLAA, DLSS-G) »**, cochée par
  défaut, avec son explication dans le wizard ;
- le build passe **`--fetch-ngx-sdk --accept-nvidia-license`** : le SDK est téléchargé une fois, et `ngx/` (dont
  `nvngx_dlss.dll` et `nvngx_dlssg.dll`) part avec le jeu — à l'installation **comme à la mise à jour** ;
- en ligne de commande : `--ngx` / `--no-ngx`.

## Ce qu'il faut faire sur une RTX

**Recompiler avec ce Setup**, la case DLSS laissée cochée. Un jeu déjà compilé sans le SDK ne peut pas gagner DLSS
après coup : le code n'est pas dans `longshot_vk.dll`.

## AMD

Rien ne change. Sur AMD la case ne fait rien : l'onglet NVIDIA reste absent, comme il doit.

## Comment vérifier

Dans `logs/longshot_log.txt`, au démarrage :

```
vk: NVIDIA DLSS: <chemin>\ngx\nvngx_dlss.dll
```

et dans le F1, l'onglet **NVIDIA** apparaît, avec `Upscaler` qui propose **NVIDIA DLSS** et **NVIDIA DLAA**.

## Le reste

Tout ce que la 0.0.2 apporte est inchangé : le menu F1, la touche Run, les ombres au 1600, les deux lignes de perf dans
Debug, le diff des write-backs et le cache des notes réactivés, les petits PC pris en charge sans rien régler, et le
builder nettement plus rapide. Le détail est dans les notes de la 0.0.2.
