# Crea un certificado autofirmado de code-signing en CurrentUser\My.
# No es de confianza para terceros: sirve para firmar el .exe y verificar la
# integridad, pero SmartScreen seguira advirtiendo en otras maquinas. Para
# distribucion real hace falta un certificado emitido por una CA.
param([string]$Sujeto = "Javier Alvarez Amado")
$ErrorActionPreference = "Stop"

if (-not (Get-Command New-SelfSignedCertificate -ErrorAction SilentlyContinue)) {
    throw "New-SelfSignedCertificate no disponible; ejecutar con pwsh 7"
}

$existente = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -like "*$Sujeto*" } | Select-Object -First 1
if ($existente) {
    Write-Host "Ya existe: $($existente.Subject) ($($existente.Thumbprint))"
    exit 0
}

$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=$Sujeto, O=$Sujeto, C=CL" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -KeyUsage DigitalSignature `
    -KeyExportPolicy Exportable `
    -HashAlgorithm SHA256 `
    -NotAfter (Get-Date).AddYears(3)

$cert | Select-Object Subject, Thumbprint, NotAfter | Format-List
Write-Host "Certificado autofirmado creado en CurrentUser\\My."
Write-Host "No es de confianza para terceros; para distribucion usar una CA."
