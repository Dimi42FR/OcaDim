# OcaDim — passation de session (état au 16/11/2026, fin de session)

Tout ce qu'il faut pour reprendre sans rien redécouvrir : où sont les choses, ce qui est fait, ce qui est mesuré,
ce qui reste, et les pièges qui ont coûté du temps.

## 1. Les trois dossiers, et à quoi ils servent

| Dossier | Ce que c'est | État |
|---|---|---|
| `D:\Emulateur\Longshot-src\longshot` | **l'arbre de développement** (le vrai travail) | branche **`v0.1.0-amont`**, ~14 commits au-dessus de `mine-a` |
| `C:\Users\Administrator\Desktop\Nouveau dossier (9)\OcaDim` | **le dépôt public** (ce que GitHub voit) | `main` = la 0.0.1 + les pages + `CREDITS.md` ; **pas encore la 0.1.0** |
| `F:\test` | **l'installation du jeu** (launcher + `image.bin` + DLL) | à jour avec la 0.1.0 + gouverneur (exe 514 126 336, DLL 17 020 928) |

`F:\test` n'est pas un dossier de dev : `longshot.exe` y est un **launcher** qui vérifie `​.longshot_installed.json` et
écrit depuis `image.bin`. Copier un exe et une DLL à la main **ne marche pas** (voir pièges) : il faut `make_game.py --update`.

## 2. L'environnement de build

```
LONGSHOT_MINGW=C:\Users\Administrator\AppData\Local\HookshotBuilder\versions\v2.1.0\HookshotBuilder\tools\llvm-mingw
LONGSHOT_FSR=1
RX_VK_PGO=D:\Emulateur\Longshot-src\longshot\work\longshot_vk.shipped.profdata
RX_CPM=C:\Users\Administrator\AppData\Local\HookshotBuilder\versions\v2.1.0\HookshotBuilder\tools\cpm
```

- Python : `C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe`
- Git : `D:\Emulateur\MinGit\cmd\git.exe` (pas sur le PATH)
- gh CLI : `C:\Program Files\GitHub CLI\gh.exe` (compte **Dimi42FR**, scope repo)

**Build** (dans l'arbre de dev) :

```
python -I nx2/build.py --standalone --jobs 4
```

**Test automatique** (90 s, journal dans `work/runs/<nom>/log.txt`) :

```
powershell -File scripts\run-vk.ps1 -Window -Seconds 90 -Name <nom> -ShotEvery 100000 -Force -Env "..."
```

**Mettre à jour l'installation** (le seul chemin propre) :

```
python -I nx2/make_game.py --update "F:\test"
```

Dépendances Python : `pip install -r requirements.txt` (il faut **lz4** et **numpy**, oubliés au départ).

## 3. Ce qui a été livré (v0.1.0)

1. **Fusion de l'amont** : base `f637b42` (15/11 20:38) → `bbe421` (16/11 04:24), en 3 voies, 229 fichiers propres,
   82 nouveaux, 40 régions de conflit. `vk_menu.cpp` tranché en faveur de la refonte du compteur de FPS ; notre onglet
   **Performance** (`perf_*`) réinséré ; `tabs[]` complété ; 8 fichiers de test repris de l'amont ; `menu_i18n.h` repris
   + « Playing Longshot » → « Playing OcaDim ».
2. **Correctif de régression** (le plus important) : en ville, à draws égaux, 40,6 → **46,2 fps** (p10 36,7 → 41,2).
   Deux lignes : `shadow_res = 1` par défaut (1 600 du jeu, pas Auto 3 072) et **épinglage strict** du thread de replay
   (`RX_VK_RT_STRICT_PIN=0` pour rendre la liberté nouvelle).
3. **Le gouverneur de budget** : ligne dans l'onglet **Performance**, bouton **« Check »**, lit le Breakdown, désigne la
   plus grosse part et le levier. N'applique rien seul.
4. **Documentation** : `docs/OCADIM-V0.0.2.md` (fusion, sondes, verdicts) et `docs/OCADIM-V0.1.0-RELEASE.md`
   (**notes de release prêtes à coller**). `README.md` : les 9 lignes manquantes du tableau, dans l'ordre du menu
   (`test_readme_menu_rows` 6/6, `test_menu_i18n` et `test_menu_sections` verts).

## 4. Les sondes (toutes éteintes par défaut)

| Variable | Ce qu'elle mesure | Coût éteinte |
|---|---|---|
| `RX_VK_DIRTY_CENSUS=1` | la passe de `mirror_sync` sur les pages sales | un `bool` par sync |
| `RX_VK_DRAW_RUNS=1` | draws consécutifs au même programme (+ hache push et descripteurs) | un `bool` par draw |
| `RX_VK_STATE_KEYS=1` | clés d'état distinctes (nécessite `RX_VK_DRAW_RUNS=1`) | un `bool` par draw |
| `RX_VK_SLOW_LOG=<ms>` | décomposition des frames lentes (existant) | un timer par frame |
| `RX_VK_VRAM_MB=<MB>` | plafond de textures (simule une petite carte) | — |

**Les sondes ne sont jamais laissées dans `F:\test\longshot_env.txt`** (erreur faite une fois) : on les passe par `-Env`.

## 5. Ce qui est mesuré, et ce qui est donc écarté (ne pas y revenir sans un nouveau chiffre)

| Piste | Mesure | Verdict |
|---|---|---|
| #965 dirty census | **4 µs/sync**, ~24 µs/frame | sans objet ici |
| Auto-batching | 1,32-1,59 par programme, **1,06-1,10** avec descripteurs | mort : exige bindless |
| Lookahead ressources | `memory sync` **~1 ms** sur des frames de 2-6 s | mort |
| Cache d'état | **1,21-1,28** draw/clé | ~2 % au mieux, plus tard |
| Async (Threaded rendering On) | submit 9,4 s, pire frame 9,8 s contre 6,5 | **aucun flash**, mais **aucun gain** |
| **VRAM simulée à 2 Go** | **32,1 fps** contre 43-46 (uploads 7,5/frame) | **le chantier mémoire est justifié (~25 %)** |

Deux mesures transversales :
- les **hoquets** (2-9 s) sont faits de `draw` + `descriptors` + `submit` + `commands`, et de **`programs`
  (1,5-9,9 s)** au chargement — c'est de la **traduction/compilation de programmes**, pas de l'enregistrement ;
- à 2 Go simulés, le coût est le **décodage/deswizzle** des re-uploads (2,3 Mo/frame seulement), pas la bande passante.

## 6. Le prochain chantier : mémoire (conception arrêtée)

**On ne peut pas relire une texture décodée depuis la VRAM** : elle n'existe sur le CPU qu'à l'upload (staging). D'où la
conception retenue :

1. **Premier upload** : rien de plus (ne pas alourdir le chargement).
2. **Évincée puis redemandée** (le cas du thrashing) : on est de nouveau dans le chemin d'upload avec les octets décodés →
   **là**, on garde une copie **zstd** (`third_party/zbic` est déjà là).
3. Les fois suivantes : **décompresser + copier** au lieu de re-décoder.

Points d'entrée : `gpu/vk/vk_texture.cpp`, les `vkCmdCopyBufferToImage` (lignes ~1831 et ~1990), l'éviction dans le
budget (~4572), `RX_VK_VRAM_MB` pour tester à 2 Go.

À comptabiliser dans le journal : `compressed / rebuilt / ms de décompression`.

## 7. Le second chantier : la traduction de programmes au chargement

`programs` = 1 581 ms sur une frame de chargement (9,9 s sur une autre), avec 265 nouveaux pipelines. Piste : pré-traduire
à partir du **pipeline tour** (les 33 000 pipelines préparés). Question ouverte, à mesurer avant de coder : les 265
programmes étaient-ils **prévisibles** depuis le tour, ou sont-ce des variantes imprévues ?

## 8. Publier la 0.1.0 (quand on décide)

1. Synchroniser `v0.1.0-amont` vers `C:\Users\Administrator\Desktop\Nouveau dossier (9)\OcaDim` (décider : un commit
   « v0.1.0 » ou l'historique).
2. Refaire le parcel : `setup/build-setup.ps1` (le `source.zip` doit venir du commit publié, `jeu/` est exclu).
3. Rééditer le Setup (le paquet de 164 Mo / `source.zip` ~20 Mo) et **créer la release `v0.1.0`** avec
   `docs/OCADIM-V0.1.0-RELEASE.md` en notes.
4. Ne pas oublier : la prévisualisation sociale du dépôt (Settings → Social preview, `assets/branding/ocadim-social-preview.png`).

## 9. Les pièges qui ont coûté du temps (à ne pas refaire)

- **PowerShell `>` écrit en UTF-16** : ne jamais rediriger la sortie de git vers un fichier avec `>` ; passer par Python
  (`read_bytes`/`write_bytes`) ou `-Encoding utf8`. Un fichier UTF-16 se comporte comme un binaire pour git.
- **`String.Replace` en PowerShell remplace TOUTES les occurrences** : a causé une duplication de bloc et un build cassé.
- **Les `` `n `` dans une chaîne PowerShell simple-quote** ne sont pas des retours à la ligne : ils s'écrivent littéralement
  dans le fichier. Symptôme : `expected expression` sur une ligne contenant `` `n ``.
- **`-I` (python) ignore `PYTHONIOENCODING`** : écrire dans un fichier ou `sys.stdout.reconfigure` pour les accents.
- **L'union des conflits casse du code** : elle a dupliqué des fonctions (`vk_fps.cpp`, `vk_replay.cpp`, `vk_menu.cpp`) —
  toujours recompiler juste après, et préférer une clé **stricte** pour les mesures.
- **Une sonde partagée entre threads de replay doit être verrouillée** : mon `unordered_set` sans mutex a planté le jeu
  en 23 s.
- **Copier exe+DLL dans `F:\test` ne marche pas** : le launcher vérifie le manifeste et écrit depuis `image.bin`. Utiliser
  `make_game.py --update`. Un exe/DLL désaccordés donnent `CRASH … read 0xffff…` au démarrage.
- **`shadow_res` en Auto = 3 072 sur 16 Go** : coûtait 6-7 fps en ville. Resté à 1 (1 600) par défaut dans notre fork.
- **Ne jamais laisser les variables de mesure dans `F:\test\longshot_env.txt`** (le fichier est vidé, avec un commentaire).

## 10. Les chiffres de référence (pour comparer)

- Ville, scène lourde : **46,2 fps** (p10 41,2), 2 300-2 800 draws, 6 submits, ~180 passes.
- 0.0.1 : 47,2 fps (p10 31,2) — même moyenne, **pires frames moins bonnes**.
- VRAM simulée 2 Go : **32,1 fps**.
- Réglages de référence : `shadow_res=1`, `threaded_rendering=0`, cap 60.
