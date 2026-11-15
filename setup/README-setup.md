# OcaDim 0.0.1 — the setup, two ways

The name on screen is **OcaDim 0.0.1**. Two installers are ready; pick one.

## A. The pretty one (Inno Setup, ~3 MB, recommended for players)

1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php) (free, one click).
2. Build the payload: the playable folder as it is, e.g. `D:\Emulateur\Longshot-main`.
3. Compile:

```powershell
iscc setup\OcaDim.iss /DPayload="D:\Emulateur\Longshot-main"
```

→ `setup\dist\OcaDim-Setup-0.0.1.exe`

What the player gets: a modern wizard (English/French), install into `%LOCALAPPDATA%\OcaDim` (no admin prompt),
a desktop shortcut, a Start-menu entry, a proper uninstaller in *Settings → Apps*, and the game launched at the end.
Tuning: `OcaDim.iss` at the top — name, version, publisher, icon, license page.

Assets it wants (drop them in `assets\branding\` when you have them; the script skips them if absent):
`ocadim.ico` (256×256) and `ocadim-wizard.bmp` (164×314).

## B. The no-dependency one (PowerShell, for a USB stick or a quick share)

```powershell
# install (a payload folder beside the script, or -From <folder>)
powershell -ExecutionPolicy Bypass -File setup\OcaDim-Setup.ps1 -Install -From "D:\Emulateur\Longshot-main"

# play / uninstall
powershell -ExecutionPolicy Bypass -File setup\OcaDim-Setup.ps1 -Play
powershell -ExecutionPolicy Bypass -File setup\OcaDim-Setup.ps1 -Uninstall
```

It copies the folder to `%LOCALAPPDATA%\OcaDim`, writes `version.txt`, makes a desktop shortcut and a Start-menu
`.lnk`, and an uninstaller under `%LOCALAPPDATA%\OcaDim\OcaDim-Uninstall.ps1` (which also removes the shortcuts).
No registry, no admin, no tool to install.

## Why the files keep the longshot_* names

`longshot.exe`, `longshot_options.ini`, `longshot_log.txt`, `longshot_shaders.bin`, `longshot_env.txt` are what the
game, its caches and its saves are named inside. Renaming them would lose a player's settings and its prepared
shaders (a 30-minute rebuild), so only what the player **sees** says OcaDim: the window, the console, the log's
first line, the dialogs, the crash window and the start-up screen.

## Before you ship a payload

- Close the game; run the packaging (`nx2/make_game.py --update <folder> --fsr --fetch-fsr-runtime --accept-amd-license`).
- The folder must carry `romfs`, `.hookshot_exefs`, `prompts`, `user` (or a fresh one), `longshot_shaders.bin`,
  `longshot_pipeline_states_shipped.bin`, the `amd_fidelityfx_*_vk.dll` files and the SDL/wgpu DLLs.
- Never ship game data, keys or saves; the player builds from their own copy, or you ship a folder built on yours and
  say so (see the project's rule).
