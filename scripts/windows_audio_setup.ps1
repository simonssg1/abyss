# Étape administrateur de l'installeur Windows (lancée avec élévation par install_windows.ps1) :
# installe VB-CABLE si demandé, puis renomme son micro « CABLE Output » en « Abyss ».
# Code de sortie : 0 = renommé (ou déjà), 2 = micro pas encore visible (redémarrage requis), 1 = erreur.
param(
    [string]$CableSetup = "",
    [string]$Name = "Abyss"
)
$ErrorActionPreference = "Stop"
try {
    if ($CableSetup) {
        Write-Host "Installation de VB-CABLE (confirme la fenêtre de Windows si elle s'affiche)..."
        $p = Start-Process -FilePath $CableSetup -ArgumentList "-i", "-h" -Wait -PassThru
        Write-Host "Installeur VB-CABLE terminé (code $($p.ExitCode))."
    }
    Add-Type -Path (Join-Path $PSScriptRoot "windows_audio.cs")
    $result = "notfound"
    for ($i = 0; $i -lt 15; $i++) {          # le micro peut mettre quelques secondes à apparaître
        $result = [AbyssSetup.Endpoints]::RenameCable($Name)
        if ($result -ne "notfound") { break }
        Start-Sleep -Seconds 1
    }
    switch ($result) {
        "renamed" { Write-Host "Micro virtuel renommé : « $Name »."; exit 0 }
        "already" { Write-Host "Le micro virtuel s'appelle déjà « $Name »."; exit 0 }
        default   { Write-Host "Micro VB-CABLE pas encore visible : redémarre le PC puis relance l'installeur."; exit 2 }
    }
} catch {
    Write-Host "Erreur : $($_.Exception.Message)"
    exit 1
}
