<#
  OcaDim 0.0.1 ??? the no-dependency installer (option B of setup/README-setup.md)
  Usage:
    -Install [-From <payload folder>]   copy the game to %LOCALAPPDATA%\OcaDim, desktop + Start-menu shortcuts
    -Play                               start the installed game
    -Uninstall                          remove the installed copy, its shortcuts and its uninstaller
  No registry, no admin, no tool to install. The longshot_* file names are kept on purpose (see the readme).
#>
[CmdletBinding()]
param([switch]$Install, [switch]$Play, [switch]$Uninstall, [string]$From)

$ErrorActionPreference = 'Stop'
$name = 'OcaDim'
$version\ = '0.0.3'
$exe = 'ocadim.exe'
$root = Join-Path $env:LOCALAPPDATA $name

function Banner {
    $c = 'DarkYellow'
    Write-Host ''
    Write-Host '        .--------------------------------------------.' -ForegroundColor $c
    Write-Host '        |            O  C  A  D  I  M               |' -ForegroundColor $c
    Write-Host ("        |        native port  ??  {0}              |" -f $version) -ForegroundColor $c
    Write-Host '        ''--------------------------------------------''' -ForegroundColor $c
    Write-Host ''
}

function Shortcut([string]$path) {
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut($path)
    $lnk.TargetPath = Join-Path $root $exe
    $lnk.WorkingDirectory = $root
    $lnk.IconLocation = (Join-Path $root $exe) + ',0'
    $lnk.Description = "$name $version"
    $lnk.Save()
}

function Install-It([string]$src) {
    Banner
    if (-not $src) {
        $src = Join-Path $PSScriptRoot 'payload'
        if (-not (Test-Path $src)) {
            $src = Read-Host "Folder of the built game (the one with $exe)"
        }
    }
    if (-not (Test-Path (Join-Path $src $exe))) {
        throw "no $exe in $src ??? build the game first (nx2/make_game.py --update)"
    }
    Write-Host "  from : $src" -ForegroundColor Gray
    Write-Host "  into : $root" -ForegroundColor Gray
    if (Test-Path $root) {
        $answer = Read-Host "  $root exists. Replace it? The saves and settings in it are lost (y/N)"
        if ($answer -notmatch '^(y|o)') { Write-Host '  cancelled.' -ForegroundColor Yellow; return }
        Remove-Item -LiteralPath $root -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $root | Out-Null
    Write-Host '  copying the game...' -NoNewline
    Copy-Item -Path (Join-Path $src '*') -Destination $root -Recurse -Force
    Write-Host " done" -ForegroundColor Green
    ("{0} {1}`ninstalled {2:yyyy-MM-dd HH:mm}`nfrom {3}" -f $name, $version, (Get-Date), $src) |
        Set-Content -Encoding ASCII (Join-Path $root 'version.txt')
    # (the uninstaller travels with the copy)
    Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $root "$name-Uninstall.ps1") -Force
    $desktop = [Environment]::GetFolderPath('Desktop')
    Shortcut (Join-Path $desktop "$name $version.lnk")
    $menu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$name"
    New-Item -ItemType Directory -Force -Path $menu | Out-Null
    Shortcut (Join-Path $menu "$name $version.lnk")
    Write-Host '  shortcuts: desktop + Start menu' -ForegroundColor Green
    Write-Host ''
    Write-Host "  $name $version is installed." -ForegroundColor Green
    if ((Read-Host '  Play now? (Y/n)') -notmatch '^(n|non)') { Play-It }
}

function Play-It {
    $p = Join-Path $root $exe
    if (-not (Test-Path $p)) { throw "$name is not installed (no $p)" }
    Start-Process -FilePath $p -WorkingDirectory $root
    Write-Host "  started $p" -ForegroundColor Green
}

function Uninstall-It {
    Banner
    if (-not (Test-Path $root)) { Write-Host '  not installed.' -ForegroundColor Yellow; return }
    $answer = Read-Host "  Remove $root (saves and settings included)? (y/N)"
    if ($answer -notmatch '^(y|o)') { Write-Host '  cancelled.' -ForegroundColor Yellow; return }
    Remove-Item -LiteralPath $root -Recurse -Force
    $desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) "$name $version.lnk"
    if (Test-Path $desktop) { Remove-Item -LiteralPath $desktop -Force }
    $menu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$name"
    if (Test-Path $menu) { Remove-Item -LiteralPath $menu -Recurse -Force }
    Write-Host "  $name removed." -ForegroundColor Green
}

if ($Install) { Install-It $From }
elseif ($Play) { Play-It }
elseif ($Uninstall) { Uninstall-It }
else {
    Banner
    Write-Host '  -Install [-From <folder>]   install the built game' -ForegroundColor Gray
    Write-Host '  -Play                       start it' -ForegroundColor Gray
    Write-Host '  -Uninstall                  remove it' -ForegroundColor Gray
}
