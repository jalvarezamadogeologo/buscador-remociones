# Firma el ejecutable con un certificado de code-signing del almacen del usuario.
# Uso:  pwsh -File scripts\firmar_exe.ps1 [ruta_al_exe]
param(
    [string]$Exe = (Join-Path (Split-Path $PSScriptRoot -Parent) "dist\buscador-remociones\buscador-remociones.exe"),
    [string]$Sujeto = "Javier Alvarez Amado"
)
$ErrorActionPreference = "Stop"

if (-not (Test-Path $Exe)) { throw "No existe el ejecutable: $Exe" }
if (-not (Get-Command Set-AuthenticodeSignature -ErrorAction SilentlyContinue)) {
    throw "Set-AuthenticodeSignature no disponible; ejecutar con pwsh 7"
}

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -like "*$Sujeto*" } | Select-Object -First 1
if (-not $cert) {
    throw "No hay certificado de firma para '$Sujeto'. Ejecuta crear_certificado.ps1."
}

$firma = Set-AuthenticodeSignature -FilePath $Exe -Certificate $cert `
    -TimestampServer "http://timestamp.digicert.com"
$firma | Select-Object Status, StatusMessage, SignerCertificate | Format-List
if (-not $firma.SignerCertificate) { throw "La firma fallo" }

Write-Host "Firmado: $Exe"
Write-Host "Nota: un certificado autofirmado no es de confianza en otras maquinas."
