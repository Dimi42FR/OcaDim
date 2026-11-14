@echo off
setlocal enabledelayedexpansion
title OcaDim Compiler - By dimi42FR

rem ============================================================================
rem  OCADIM COMPILER - By dimi42FR
rem  Compile la version PC de Zelda Ocarina of Time (Switch 2) depuis TON
rem  propre fichier .nup, depuis les sources OcaDim de ce dossier.
rem
rem  Glisse-depose ton .nup sur ce .bat, ou lance-le et colle le chemin.
rem ============================================================================

echo(
echo   ============================================================
echo                 O C A D I M
echo              By dimi42FR
echo   ============================================================
echo(

cd /d "%~dp0"

rem ---- le .nup : en argument (glisser-deposer) ou demande ----
set "NUP=%~1"
if "%NUP%"=="" (
    set /p "NUP=   Chemin de TON fichier .nup du jeu : "
)
if not exist "%NUP%" (
    echo   [ERREUR] Fichier introuvable : "%NUP%"
    echo            (C'est TON propre fichier .nup du jeu qu'il faut.)
    pause
    exit /b 1
)
echo(
echo   Jeu : "%NUP%"
echo(

rem ---- les dossiers de sortie ----
set "OUT=%~dp0jeu"
echo   Le jeu PC sera construit dans : "%OUT%"
echo(

rem ---- les outils de compilation ----
rem (1) un dossier tools a cote, (2) ceux du Longshot Builder installe,
rem (3) sinon ils se telechargent seuls depuis tools.lock.
set "TOOLS="
if exist "%~dp0tools\llvm-mingw\bin\clang.exe" set "TOOLS=%~dp0tools"
if not defined TOOLS (
    for /d %%D in ("%LOCALAPPDATA%\HookshotBuilder\versions\*") do (
        if not defined TOOLS if exist "%%D\HookshotBuilder\tools\llvm-mingw\bin\clang.exe" set "TOOLS=%%D\HookshotBuilder\tools"
    )
)
if not defined TOOLS (
    echo   [1/3] Les outils de compilation ne sont pas la : telechargement...
    echo         ^(llvm-mingw, python, cpm, wgpu-native - quelques Go, une fois^)
    where py >nul 2>nul
    if errorlevel 1 (
        echo   [ERREUR] Python n'est pas installe : installe-le ^(python.org^),
        echo            puis relance ce compilateur.
        pause
        exit /b 1
    )
    if not exist "%~dp0tools" mkdir "%~dp0tools"
    pushd "%~dp0"
    py -I scripts/tools.py install "%~dp0tools" --system windows-x64
    if errorlevel 1 (
        echo   [ERREUR] Le telechargement des outils a echoue ^(reseau ?^).
        popd
        pause
        exit /b 1
    )
    popd
    set "TOOLS=%~dp0tools"
)

set "PY=%TOOLS%\python\python.exe"
if not exist "%PY%" (
    echo   [ERREUR] Python des outils introuvable dans "%TOOLS%\python"
    pause
    exit /b 1
)

echo   Outils : "%TOOLS%"
echo(
echo   [2/3] Compilation - de 10 minutes a plus d'une heure la premiere
echo         fois ^(le lift du jeu + les shaders a la fin : LAISSE LE JEU
echo         SE FERMER TOUT SEUL, ne le tue jamais^).
echo(

set "PATH=%TOOLS%\llvm-mingw\bin;%TOOLS%\python;%PATH%"
set "RX_CPM=%TOOLS%\cpm"
set "WGPU_NATIVE=%TOOLS%\wgpu-native"
set "LONGSHOT_MINGW=%TOOLS%\llvm-mingw"

"%PY%" -I nx2/make_game.py --game "%NUP%" --out "%OUT%"
set "RC=%ERRORLEVEL%"

echo(
if "%RC%"=="0" (
    echo   ============================================================
    echo    OCADIM EST PRET - By dimi42FR
    echo    Le jeu PC est dans : "%OUT%"
    echo    Env de jeu conseille ^(a copier dans le dossier du jeu en
    echo    longshot_env.txt^): voir default-env-OcaDim.txt ici.
    echo   ============================================================
) else (
    echo   ============================================================
    echo    COMPILATION INTERROMPUE - By dimi42FR
    echo    Code %RC%. Reessaie ; si ca rebute, envoie le log a dimi42FR.
    echo   ============================================================
)
pause
exit /b %RC%
