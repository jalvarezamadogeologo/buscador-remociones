# Construye el ejecutable portable en dist\buscador-remociones\ (carpeta onedir).
# Uso:  pwsh -File scripts\build_exe.ps1
$ErrorActionPreference = "Stop"
$Raiz = Split-Path $PSScriptRoot -Parent
Set-Location $Raiz

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt pyinstaller

Remove-Item build, dist -Recurse -Force -ErrorAction SilentlyContinue
& $py -m PyInstaller --noconfirm --clean --onedir --noupx --name buscador-remociones `
    --collect-data tzdata `
    --add-data "config.yaml;." `
    --add-data "semilla;semilla" `
    launcher.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo" }

$firmar = Join-Path $PSScriptRoot "firmar_exe.ps1"
if (Test-Path $firmar) {
    try {
        & $firmar
    } catch {
        Write-Warning "No se pudo firmar: $($_.Exception.Message)"
    }
}

# El arbol intermedio (spec, TOC, binarios temporales) no se conserva.
Remove-Item build -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "buscador-remociones.spec" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Listo: dist\buscador-remociones\buscador-remociones.exe"
Write-Host "Comparte la carpeta dist\buscador-remociones completa."
