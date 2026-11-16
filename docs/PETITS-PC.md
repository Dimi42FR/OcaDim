# Petits PC : ce qui est déjà là, et ce qu'on veut mesurer

**Statut : rien n'est décidé.** Cette page dit ce qui aide déjà sur une machine modeste, ce qu'on veut savoir avant de
coder, et dans quel ordre on essaiera les pistes. Aucun réglage par défaut ne changera sans tes chiffres.

## 1. La règle

- Un levier ne reste que s'il **se voit dans les mesures** et s'il **ne casse rien** (artefacts, plantages, incohérences).
- Pas de preset « magique » qui baisse la qualité en douce.
- Pas de télémétrie : tu envoies ce que tu veux, quand tu veux.

## 2. Ce qui aide déjà, et qui est en Auto sur une petite machine

| Réglage | Ce qu'il fait sur une machine modeste | État |
|---|---|---|
| **Quality preset : Minimum (4GB)** | Le preset de l'amont pour les cartes à 4 Go et les iGPU : budget vidéo de 2,2 Go, upscaler du jeu | À choisir une fois |
| **Output resolution / Render resolution** | Baisser la résolution interne est le levier le plus direct : 50-67 % avec FSR 3.1 ou 4 | Manuel |
| **La taille réduite 2048x1152** | 80 % de l'image du jeu (2560x1440), proposée dans la liste des résolutions de sortie | Manuel |
| **Batched submits** | Une frame de soumissions envoyée en une seule fois : sur RADV, Kokiri Forest est passé de 33-41 à 46-61 fps | Auto (RADV) |
| **Descriptor prefetch** | Les descripteurs lus à l'avance sur un thread helper : ~215 000 scans sautés par fenêtre, zéro artefact | Auto à partir de 6 processeurs logiques |
| **Replay workers / Replay segments** | Les threads du replay et la taille des tranches (32 par défaut) | Auto (1 thread pour 4 disponibles, max 4, jamais sous 6) |
| **CPU affinity (CCX)** | Les workers du replay sur la moitié haute des CPU logiques, pour que le thread du jeu garde son cache | Auto à partir de 12 processeurs logiques |
| **Threaded rendering** | Le rendu sur ses propres threads : désactivé sous 12 threads, où il n'aide pas | Auto (Off sous 12) |
| **Above-60 fixes** | Sans effet sous 60 fps : ce sont des réparations de logique au-dessus de 60 | On |
| **Frame generation** | N'augmente **pas** un débit limité par le GPU ; elle lisse quand c'est le CPU qui limite | Off |

## 3. Ce qu'on veut savoir : 4 chiffres et 3 noms

Sans ça, « c'est lent » peut vouloir dire quatre problèmes différents.

**Les 4 chiffres** (menu → Gameplay → FPS counter, niveau **Breakdown**, 60 à 90 secondes dans la scène) :

1. les fps ;
2. le frame time ;
3. le 1 % low ;
4. ce que le Breakdown attribue au GPU et au CPU (et les gros postes : textures, sommets/indices, replay, attente).

**Les 3 noms** : la scène (map + ce que tu fais), le preset, et l'upscaler avec les deux résolutions.

**Le journal** : le dossier `bug-reports/<date>_<time>` que le jeu écrit (menu → Gameplay → Bug report). Il enlève ton
nom d'utilisateur et contient ce qu'il faut.

## 4. Les pistes, dans l'ordre

Les mesures du projet ([docs/OCADIM.md](OCADIM.md)) donnent déjà la hiérarchie des coûts sur une scène lourde.

| # | Piste | Pourquoi d'abord | Comment on saura que ça marche |
|---|---|---|---|
| 1 | **Les textures du replay** (5,6-6,8 ms par frame, dont 4,1-5,2 pour les vues) | C'est le poste le plus cher du replay, et celui qui punit le plus un petit CPU | Le Breakdown avant/après, même scène, même preset |
| 2 | **Les binds de sommets et d'indices** (2,5-2,7 ms) | Deuxième poste : moins de travail par draw, sans toucher au rendu | Idem |
| 3 | **La mémoire vidéo** | Un portable partage la RAM ; les presets de l'amont visent 4/6/8 Go, et le dépassement se paie en saccades, pas en fps | Les compteurs du log + les saccades, sur une carte à 4 Go |
| 4 | **Le premier lancement** (traduction, compilation, préparation des shaders) | Ce n'est pas du fps, mais sur un petit CPU c'est une heure ; et une préparation tuée est une heure perdue | Le temps total, et le fait qu'« Annuler » reprenne |
| 5 | **La frame generation quand le GPU limite** | Elle aide si le CPU limite ; elle ne crée pas de puissance GPU. Le Breakdown le dit déjà | Un run GPU à 100 % avec et sans FG |
| 6 | **La résolution interne sous 50 %** | La dernière carte à jouer quand tout le reste est déjà réglé ; l'amont propose déjà 80 % (2048x1152) | La qualité perçue et les fps, sur une carte à 4 Go |

Rien de cette liste n'est commencé. Chaque ligne sera soit mesurée et gardée, soit abandonnée avec sa raison écrite ici.

## 5. Ce qu'on ne fera pas

- Pas de réglage par défaut qui ne profite qu'à une marque de carte.
- Pas de baisse de qualité silencieuse pour afficher un chiffre plus haut.
- Pas de collecte de données : le jeu ne sort rien de ta machine.

## 6. Comment envoyer tes chiffres

Ouvre le formulaire **[Retour sur un petit PC](https://github.com/Dimi42FR/OcaDim/issues/new?template=retour-petit-pc.yml)**.
Il demande les 4 chiffres, les 3 noms, et le dossier `bug-reports`. Rien d'autre n'est nécessaire, et surtout **pas** ton
`.nup`, tes clés ou tes sauvegardes.
