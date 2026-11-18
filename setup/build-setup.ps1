# The OcaDim Setup's parcel: setup/dist/OcaDimSetup/ — the self-contained program (a folder, never one compressed exe:
# antivirus programs took the single file for a trojan) and source.zip, the game's sources the player's machine compiles.
# No game data, no tools: the tools come from tools.lock at the first start (docs/SETUP-OCADIM-DESIGN.md).
#
#   powershell -ExecutionPolicy Bypass -File setup/build-setup.ps1
#
# What is left out of source.zip: the working tree's outputs (work/, bin/, obj/), the repository's own history and
# paperwork, and the tests. Everything a build reads (nx2, host, gpu, third_party, assets, scripts, tools.lock) is in.
param(
    [string]$Configuration = "Release",
    [switch]$NoPublish
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$repo = (Get-Location).Path
$dist = Join-Path $PSScriptRoot "dist"
$app = Join-Path $dist "OcaDimSetup"

if (Test-Path $app) { Remove-Item $app -Recurse -Force }
New-Item -ItemType Directory -Force -Path $app | Out-Null

if (-not $NoPublish) {
    Write-Host "dotnet publish -> $app" -ForegroundColor Cyan
    dotnet publish (Join-Path $PSScriptRoot "OcaDimSetup\OcaDimSetup.csproj") -c $Configuration -o $app
    if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed" }
}

$exe = Join-Path $app "OcaDimSetup.exe"
if (-not (Test-Path $exe)) { throw "OcaDimSetup.exe is not in $app" }
if (-not (Test-Path (Join-Path $app "coreclr.dll"))) {
    throw "the publish is not self-contained (no coreclr.dll): test 6 needs it"
}

# (OcaDim) .NET's crash-dump tool ships with a self-contained publish and a player has no use for it: the setup writes its
# own log, and a dump taken by createdump was never asked for. Out of the parcel, with the other files nothing reads.
foreach ($junk in @("createdump.exe", "createdump", "OcaDimSetup.pdb")) {
    $p = Join-Path $app $junk
    if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
}

# ---------------------------------------------------------------- source.zip
$zip = Join-Path $app "source.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Write-Host "source.zip <- $repo" -ForegroundColor Cyan
$excludes = @(
    ".git", "work", "out", "dist",
    "setup/dist", "setup/OcaDimSetup/bin", "setup/OcaDimSetup/obj",
    "tests", "docs", "website", ".forgejo", ".claude", ".github",
    # (OcaDim) what a player's build never reads: the builder's own app, the wizard's sources, the CI plumbing and the
    # repository's paperwork. The game compiles from nx2, host, gpu, third_party, assets, scripts, tools.lock.
    "setup", "builder", ".chunk", ".circleci", ".pytest_cache",
    "mise.toml", "mise.lock", "cliff.toml", "RELEASING.md", "AGENTS.md", "CONTRIBUTING.md",
    ".pre-commit-config.yaml", ".gitattributes", ".gitignore",
    "__pycache__", "*.pyc", "*.log", "*.pdb", "*.zip",
    "build-ocadim.log", "package-ocadim.log"
)
$tarArgs = @("-a", "-c", "-f", $zip, "-C", $repo)
foreach ($e in $excludes) { $tarArgs += "--exclude=$e" }
$tarArgs += "."
& tar.exe @tarArgs
if ($LASTEXITCODE -ne 0) { throw "tar.exe could not make source.zip" }

# (a parcel without the script it runs, or the lock it fetches, is broken before a player sees it)
$probe = Join-Path $dist "source-probe"
if (Test-Path $probe) { Remove-Item $probe -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $probe
foreach ($needed in @("nx2\make_game.py", "tools.lock", "gpu\vk", "host", "third_party\a64-kit\tools\toolchain.py")) {
    if (-not (Test-Path (Join-Path $probe $needed))) { throw "source.zip has no $needed" }
}
Remove-Item $probe -Recurse -Force

Copy-Item (Join-Path $PSScriptRoot "LISEZMOI.txt") (Join-Path $dist "LISEZMOI.txt") -Force
Copy-Item (Join-Path $PSScriptRoot "LISEZMOI.txt") (Join-Path $app "LISEZMOI.txt") -Force

$size = [math]::Round((Get-Item $zip).Length / 1MB, 1)
$appSize = [math]::Round(((Get-ChildItem $app -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB, 1)
Write-Host ""
Write-Host ("OcaDim Setup {0} is ready: {1}" -f "0.0.2", $app) -ForegroundColor Green
Write-Host ("  OcaDimSetup.exe + .NET  ({0} Mo, self-contained)" -f $appSize) -ForegroundColor Gray
Write-Host ("  source.zip            ({0} Mo, the sources compiled on the player's machine)" -f $size) -ForegroundColor Gray
Write-Host ("  LISEZMOI.txt" ) -ForegroundColor Gray
Write-Host ""
Write-Host "Ship the folder as it is (zip it if a store needs one); nothing in it is game data." -ForegroundColor Gray
