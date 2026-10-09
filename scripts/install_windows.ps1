# Installe Abyss sur Windows : uv (via winget si absent), dépendances, icône,
# raccourcis « Abyss » sur le Bureau et dans le menu Démarrer.
# Relançable sans effet de bord (les raccourcis sont remplacés).
# Usage : double-clic sur scripts\install_windows.cmd
#     ou : powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot

function Find-Uv {
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:USERPROFILE\.local\bin\uv.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Links\uv.exe",
        "$env:USERPROFILE\.cargo\bin\uv.exe"
    )
    foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
    $pkg = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter uv.exe -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($pkg) { return $pkg.FullName }
    return $null
}

Write-Host "Abyss : installation depuis $Repo"

# 1. uv
$Uv = Find-Uv
if (-not $Uv) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "uv et winget sont introuvables. Installe uv depuis https://docs.astral.sh/uv/ puis relance ce script."
    }
    Write-Host "uv introuvable : installation via winget..."
    winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    $Uv = Find-Uv
    if (-not $Uv) { throw "uv est installé mais introuvable : ferme cette fenêtre, rouvre-la et relance le script." }
}
Write-Host "uv : $Uv"

# 2. Dépendances (Python 3.11 géré par uv) et icône
Push-Location $Repo
try {
    & $Uv sync
    if ($LASTEXITCODE -ne 0) { throw "uv sync a échoué (voir les messages ci-dessus)." }
    $env:QT_QPA_PLATFORM = "offscreen"
    & $Uv run python scripts\build_icons.py
    if ($LASTEXITCODE -ne 0) { throw "La génération de l'icône a échoué." }
} finally {
    Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    Pop-Location
}
$Icon = Join-Path $Repo "src\abyss\ui\assets\icon\abyss.ico"

# 3. Cible des raccourcis : uvw (uv sans console) qui lance la commande sans console « abyss-gui ».
#    uv run garde l'environnement à jour après un git pull. Repli : l'exécutable de l'environnement.
$Uvw = Join-Path (Split-Path $Uv) "uvw.exe"
if (Test-Path $Uvw) {
    $Target = $Uvw
    $LnkArgs = "run --project `"$Repo`" abyss-gui"
} else {
    $Target = Join-Path $Repo ".venv\Scripts\abyss-gui.exe"
    $LnkArgs = ""
    Write-Host "uvw.exe absent : le raccourci lance directement $Target (refais 'uv sync' après une mise à jour)."
}

# 4. Raccourcis Bureau + menu Démarrer
$Shell = New-Object -ComObject WScript.Shell
$Folders = @([Environment]::GetFolderPath("Desktop"), [Environment]::GetFolderPath("Programs"))
foreach ($dir in $Folders) {
    $path = Join-Path $dir "Abyss.lnk"
    $lnk = $Shell.CreateShortcut($path)
    $lnk.TargetPath = $Target
    $lnk.Arguments = $LnkArgs
    $lnk.WorkingDirectory = $Repo
    $lnk.IconLocation = "$Icon,0"
    $lnk.Description = "Abyss : changeur de voix temps réel"
    $lnk.Save()
    Write-Host "Raccourci : $path"
}

Write-Host ""
Write-Host "Terminé. Lance Abyss depuis le Bureau ou le menu Démarrer."
Write-Host "Logs : $env:USERPROFILE\.abyss\logs\abyss.log"
