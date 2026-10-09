# Installe Abyss sur Windows : uv (via winget si absent), dépendances, icône,
# raccourcis « Abyss » sur le Bureau et dans le menu Démarrer, puis le micro virtuel :
# VB-CABLE téléchargé depuis le site officiel si absent, et son micro renommé « Abyss ».
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

# 5. Micro virtuel : VB-CABLE (site officiel) + micro renommé « Abyss » (une seule demande admin)
$CableUrl = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"
$MicName = "Abyss"
try {
    Add-Type -Path (Join-Path $PSScriptRoot "windows_audio.cs")
    $captures = [AbyssSetup.Endpoints]::ListCaptures()
} catch {
    Write-Host "Impossible de lister les micros ($($_.Exception.Message)) : étape micro virtuel tentée quand même."
    $captures = @()
}
$cableMics = @($captures | Where-Object { $_ -like "*|*VB-Audio Virtual Cable*" })
$cableDriver = Get-PnpDevice -FriendlyName "*VB-Audio*" -ErrorAction SilentlyContinue
$setupArgs = $null
$needRestart = $false

try {
if ($cableMics.Count -eq 0 -and -not $cableDriver) {
    Write-Host "VB-CABLE absent : téléchargement depuis vb-audio.com..."
    $tmp = Join-Path $env:TEMP "abyss-vbcable"
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $zip = Join-Path $tmp "VBCABLE_Driver_Pack.zip"
    Invoke-WebRequest -Uri $CableUrl -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $exeName = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "*arm64*.exe" } elseif ([Environment]::Is64BitOperatingSystem) { "VBCABLE_Setup_x64.exe" } else { "VBCABLE_Setup.exe" }
    $exe = Get-ChildItem $tmp -Filter $exeName -Recurse | Select-Object -First 1
    if (-not $exe) { throw "Installeur VB-CABLE introuvable dans l'archive téléchargée." }
    $setupArgs = @("-CableSetup", "`"$($exe.FullName)`"")
} elseif ($cableMics.Count -gt 0 -and -not ($cableMics | Where-Object { $_ -like "$MicName|*" })) {
    Write-Host "VB-CABLE présent : renommage de son micro en « $MicName »..."
    $setupArgs = @()
} elseif ($cableMics.Count -eq 0) {
    Write-Host "VB-CABLE est installé mais son micro n'est pas encore visible : redémarre le PC puis relance l'installeur."
    $needRestart = $true
} else {
    Write-Host "Micro virtuel « $MicName » déjà prêt."
}
} catch {
    Write-Host "Téléchargement de VB-CABLE impossible ($($_.Exception.Message)). Installe-le depuis https://vb-audio.com/Cable/ puis relance l'installeur."
    $setupArgs = $null
}

if ($null -ne $setupArgs) {
    Write-Host "Windows va demander l'autorisation administrateur (installation du pilote / renommage du micro)."
    try {
        $argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$(Join-Path $PSScriptRoot 'windows_audio_setup.ps1')`"", "-Name", $MicName) + $setupArgs
        $p = Start-Process powershell -Verb RunAs -ArgumentList $argList -Wait -PassThru
        switch ($p.ExitCode) {
            0 { Write-Host "Micro virtuel prêt : dans Discord, choisis « $MicName (VB-Audio Virtual Cable) » comme périphérique d'entrée." }
            2 { Write-Host "VB-CABLE installé. Redémarre le PC puis relance l'installeur pour nommer le micro « $MicName »."; $needRestart = $true }
            default { Write-Host "L'étape micro virtuel a échoué (code $($p.ExitCode)). Abyss fonctionne quand même ; tu peux installer VB-CABLE à la main." }
        }
    } catch {
        Write-Host "Autorisation administrateur refusée : micro virtuel non installé/renommé. Relance l'installeur pour réessayer."
    }
}

Write-Host ""
if ($needRestart) { Write-Host "Pense à redémarrer le PC avant d'utiliser Abyss avec Discord." }
Write-Host "Terminé. Lance Abyss depuis le Bureau ou le menu Démarrer."
Write-Host "Logs : $env:USERPROFILE\.abyss\logs\abyss.log"
