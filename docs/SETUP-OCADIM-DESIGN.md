SETUP OCAdim — LE DESIGN (pour la prochaine session)
=====================================================

LE BUT
------
Un seul .exe pour le joueur : OcaDimSetup.exe. Il prend SON fichier .nup (ou ses
dossiers romfs + exefs), il récupère les outils, il COMPILE le jeu sur sa machine,
et il lance. Plus jamais de dossier de 37 Go à distribuer, plus jamais de données
de jeu dans le paquet (règle du projet, et du GPL).

Ce n'est pas le builder sans fenêtre : c'est l'interface. Le moteur existe déjà.

CE QUI EXISTE DÉJÀ (vérifié le 15/11)
-------------------------------------
|x| nx2/make_game.py --prepare --nup <fichier> --out <dossier>
    -> "for RecompLauncher: no window, progress lines, --out ~/Games/Longshot"
    -> écrit des lignes @@progress 0.000 .. 1.000 et @@done <dossier>
|x| builder/LongshotBuilder (C#, WinExe, net8.0-windows) : le CLI qui lance ce
    script avec des pipes et remonte la progression (Program.cs)
|x| tests/builder_cli/BuilderCliTests.csproj : la preuve que la voie est testée
|x| Setup de HookshotBuilder v2.1.0 installé (les outils : llvm-mingw, python,
    cpm, wgpu-native) : c'est ce que le Setup téléchargera/télécharge
|x| assets/branding/ocadim.ico + ocadim-wizard.bmp (faits)
|x| Le nom visible : OcaDim 0.0.1 (host/hos.h : HOS_PRODUCT_NAME/VERSION)

CE QUI MANQUE
-------------
1. .NET SDK 8 sur la machine de dev (le projet cible net8.0-windows ; seul 6.0.428
   est installé).   winget install --id Microsoft.DotNet.SDK.8   (ou dotnet-install.ps1 -Channel 8.0)
2. Le projet setup/OcaDimSetup (WinForms, net8.0-windows, x64).

LES PAGES DU WIZARD (dans l'ordre)
----------------------------------
1. ACCUEIL — le blason, "OcaDim 0.0.1", trois lignes : "Il vous faut votre propre
   copie du jeu (programme 0400486024DEC000, build e0f3ccfa), ~60 Go libres, et
   Windows 10/11 x64". Bouton Continuer.
2. LE JEU — deux boutons : "Choisir un .nup" / "Choisir romfs + exefs".
   Vérification du programme et du build AVANT tout (make_game.py --check, ou la
   même lecture que nx2/dump.py). Refus clair sinon ("cette version n'est pas
   supportée"), avec le programme et le build lus affichés.
3. LE DOSSIER — où installer (défaut %LOCALAPPDATA%\OcaDim), et le dossier des
   OUTILS (défaut %LOCALAPPDATA%\OcaDim\tools, réutilisé d'une mise à jour à
   l'autre). Cases : raccourci bureau, menu Démarrer.
4. LA COMPILATION — la barre des @@progress, l'étape en cours ("traduction",
   "compilation", "shaders 3 644 / 4 058", "~12 min"), le temps écoulé/restant,
   un bouton Annuler qui laisse le dossier reprenable (make_game.py reprend).
   Le joueur garde sa machine utilisable (priorité BELOW_NORMAL sur les enfants).
5. FINI — "Jouer" / "Ouvrir le dossier" / "Fermer" ; écrire version.txt.
6. AUX LANCEMENTS SUIVANTS — même exe : si l'install existe, l'écran devient
   "Jouer / Mettre à jour / Désinstaller" (la mise à jour = recompiler dans le
   même dossier, make_game.py --update le fait déjà depuis les fichiers gardés).

LA TECHNIQUE (pour ne pas réinventer)
-------------------------------------
- WinForms (pas WPF : plus simple, et c'est ce que fait leur builder).
- 100 % du travail passe par le CLI existant : Process.Start("python.exe",
  "nx2/make_game.py --prepare --nup ... --out ..."), stdout redirigé,
  chaque ligne @@progress -> la barre, @@done -> la fin.
  => aucune logique de build dans l'interface. Si le script change, l'interface suit.
- Les outils : au premier lancement, télécharger l'archive des outils (la même que
  HookshotBuilder v2.1.0 : llvm-mingw + python + cpm + wgpu-native + third_party,
  ~250 Mo) dans <outils>, avec un SHA-256 par fichier (le tools.lock du dépôt) et
  une reprise si le téléchargement casse. Pas de single-file exe : les antivirus
  le prennent pour un trojan (c'est écrit dans le csproj du builder).
- Les raccourcis : WScript.Shell (comme setup/OcaDim-Setup.ps1), icône
  assets/branding/ocadim.ico.
- Désinstallation : supprimer le dossier + les raccourcis + l'entrée
  HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\OcaDim (facultatif :
  la version PowerShell n'écrit rien dans le registre).

LES GARDE-FOUS (ce qu'on a appris cette session)
------------------------------------------------
- UN SEUL BUILD À LA FOIS : un verrou (fichier .lock dans le dossier des outils),
  comme #630 côté jeu, sinon "Another build is using the work folder".
- Ne JAMAIS tuer la préparation des shaders (cache perdu = 30 min).
- Le dossier du jeu n'est jamais écrasé sans confirmation ; les saves et l'ini
  sont sauvegardés dans <dossier>\user\save.backup-<date> avant une mise à jour.
- Les erreurs du build sont affichées EN CLAIR (les dernières lignes), pas dans un
  fichier que personne ne lit.

LES TESTS (avant de livrer)
---------------------------
1. dotnet publish -c Release -> un dossier (pas un single-file), l'exe + les DLL.
2. Un .nup complet : installer, compiler, jouer (40 min sur cette machine).
3. Un .nup refusé (mauvais programme) : message clair, rien de créé.
4. Un dossier existant : la mise à jour réutilise les outils et reprend.
5. Annuler en pleine compilation : le dossier reste reprenable.
6. Sur une machine sans .NET : l'exe est self-contained (le publish le fait).

L'ORDRE DE LA PROCHAINE SESSION
-------------------------------
1. Installer le SDK 8 (2 min) et créer setup/OcaDimSetup (csproj + Program.cs).
2. Page 2 (la lecture du .nup) + page 4 (le CLI + @@progress) : le cœur.
3. Les raccourcis, version.txt, l'écran "Jouer / Mettre à jour / Désinstaller".
4. Les tests 2 à 5.
5. Le packager (setup/dist) et l'écrire dans OcaDim (re-synchro).

CE QU'ON NE FAIT PAS
--------------------
- Pas de conversion de saves (Triforce le fait ; on a déjà les dossiers qui
  correspondent, et le joueur copie s'il vient de NX2navi).
- Pas de mise à jour automatique en ligne (pas de serveur) : "Mettre à jour" =
  recompiler avec le .nup que le joueur a déjà.
- Pas de télémétrie, rien ne sort de la machine.
