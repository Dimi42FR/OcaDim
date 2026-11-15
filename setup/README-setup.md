# OcaDim 0.0.1 — the setup

The name on screen is **OcaDim 0.0.1**. Three ways to install it; the first is the product.

## C. The setup that builds on the player's machine (recommended)

`setup/OcaDimSetup` — a WinForms wizard, .NET 8, self-contained, no admin:

```
OcaDimSetup.exe  →  the player's .nup  →  tools fetched from tools.lock  →  nx2/make_game.py --prepare
                 →  %LOCALAPPDATA%\OcaDim  →  shortcuts  →  Jouer
```

- **Nothing of the game is in the parcel**: the player's own `.nup` (or `romfs` + `exefs`) is read, checked
  (program `0400486024DEC000`, build `e0f3ccfa`; another game is refused in plain words, with nothing created),
  and compiled by `nx2/make_game.py` — the same script the builder app runs. The interface has no build logic.
- **The tools** (~250 MB: Python, llvm-mingw, cpm, wgpu-native, emsdk, third_party) are fetched at the first start
  from the first URL `tools.lock` names, each checked by its size and SHA-256, and kept in `<install>\tools` for
  every later build. A tool whose stamp matches is not downloaded again.
- **One build at a time**: an exclusive `.lock` in the tools folder (the lesson of #630). A second setup says so.
- **Cancel** leaves the folder resumable; make_game.py picks up where it stopped. Closing the wizard during the
  build asks first (the shaders' preparation in progress is lost, a completed one is kept).
- **Errors are shown**, the last lines in clear, not hidden in a file.
- **Once installed**, the same exe offers **Jouer / Mettre à jour / Désinstaller**. The update is
  `make_game.py --update <folder>`: the sources, the tools and the compiled objects are reused, the player's
  settings and saves are untouched. `version.txt` says what is installed.

### Build the parcel

```powershell
powershell -ExecutionPolicy Bypass -File setup\build-setup.ps1
```

→ `setup\dist\OcaDimSetup\`: `OcaDimSetup.exe` + .NET's files (187 MB, self-contained — a **folder**, never one
compressed exe: antivirus programs took that for a trojan) and `source.zip` (42 MB, the sources: nx2, host, gpu,
third_party, assets, scripts, tools.lock; no tests, no docs, no history). **~230 MB in total**, no game data.
Ship the folder as it is (`setup\dist\LISEZMOI.txt` is written beside it).

### Command line (the six tests, scripts)

```powershell
# read the player's copy without building (tools are fetched if needed)
OcaDimSetup.exe --cli --check --nup "<game>.nup" --out "%LOCALAPPDATA%\OcaDim" --log check.log

# a whole install, headless
OcaDimSetup.exe --cli --nup "<game>.nup" --out "<folder>" --fsr --log build.log
```

Options: `--game <file|folder>`, `--romfs <d> --exefs <d>`, `--update`, `--check`, `--fsr` / `--no-fsr`,
`--tools-from <folder>` (a developer's tools, copied instead of downloaded), `--no-shortcuts`, `--log <file>`.

A developer's `--cli` run from the checkout uses the checkout's sources (no `source.zip` beside the exe).

### The six tests (docs/SETUP-OCADIM-DESIGN.md, "LES TESTS")

1. `dotnet publish -c Release` → a folder, `coreclr.dll` present, no single file — checked by `build-setup.ps1`.
2. A complete `.nup`: install, compile, play (≈40 min on the 5800X / 9070 XT).
3. Another game's `.nup`: refused, program and build shown, nothing of the game created.
4. An existing folder: the update reuses the tools (no download) and resumes.
5. Cancel during the compilation: the folder stays resumable, and a rerun finishes it.
6. A PC without .NET: the exe runs (self-contained; proven with `DOTNET_ROOT` pointing nowhere).

## A. The pretty one (Inno Setup, a payload already built)

For shipping a folder that was built on your machine:

1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php).
2. Compile:

```powershell
iscc setup\OcaDim.iss /DPayload="D:\Emulateur\Longshot-main"
```

→ `setup\dist\OcaDim-Setup-0.0.1.exe`. Modern wizard (English/French), install into `%LOCALAPPDATA%\OcaDim`
(no admin), desktop and Start-menu entries, an uninstaller in *Settings → Apps*, the game launched at the end.
Tuning: `OcaDim.iss` at the top. Assets it wants: `ocadim.ico` and `ocadim-wizard.bmp`.

## B. The no-dependency one (PowerShell, USB stick)

```powershell
powershell -ExecutionPolicy Bypass -File setup\OcaDim-Setup.ps1 -Install -From "D:\Emulateur\Longshot-main"
powershell -ExecutionPolicy Bypass -File setup\OcaDim-Setup.ps1 -Play
powershell -ExecutionPolicy Bypass -File setup\OcaDim-Setup.ps1 -Uninstall
```

Copies the folder to `%LOCALAPPDATA%\OcaDim`, writes `version.txt`, makes the shortcuts and an uninstaller.
No registry, no admin.

## Why the files keep the longshot_* names

`longshot.exe`, `longshot_options.ini`, `longshot_log.txt`, `longshot_shaders.bin`, `longshot_env.txt` are what
the game, its caches and its saves are named inside. Renaming them would lose a player's settings and its prepared
shaders (a 30-minute rebuild), so only what the player **sees** says OcaDim: the window, the console, the log's
first line, the dialogs, the crash window and the start-up screen.

## Before you ship a payload (A and B)

- Close the game; run the packaging (`nx2/make_game.py --update <folder> --fsr --fetch-fsr-runtime --accept-amd-license`).
- The folder must carry `romfs`, `.longshot_exefs`, `prompts`, `user` (or a fresh one), `longshot_shaders.bin`,
  `longshot_pipeline_states_shipped.bin`, the `amd_fidelityfx_*_vk.dll` files and the SDL/wgpu DLLs.
- Never ship game data, keys or saves (C ships none: the player builds from their own copy).
