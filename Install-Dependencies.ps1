[CmdletBinding()]
param(
    [switch]$IncludeDev,
    [string]$Python = "python",
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ProjectRoot

Write-Step "Verificando Python"
try {
    & $Python --version
} catch {
    throw "Python não foi encontrado. Instale Python 3.11 ou superior e tente novamente."
}

Write-Step "Criando ou reutilizando o ambiente virtual em $VenvPath"
if (-not (Test-Path $VenvPath)) {
    & $Python -m venv $VenvPath
}

$VenvPython = Join-Path $ProjectRoot "$VenvPath\Scripts\python.exe"
$VenvPip = Join-Path $ProjectRoot "$VenvPath\Scripts\pip.exe"
if (-not (Test-Path $VenvPython)) {
    throw "O ambiente virtual não foi criado corretamente: $VenvPython"
}

Write-Step "Atualizando pip, setuptools e wheel"
& $VenvPython -m pip install --upgrade pip setuptools wheel

Write-Step "Instalando dependências de execução"
& $VenvPip install --requirement (Join-Path $ProjectRoot "requirements.txt")

if ($IncludeDev) {
    Write-Step "Instalando dependências de desenvolvimento e testes"
    & $VenvPip install `
        "flet-cli>=0.86.5" `
        "flet-desktop>=0.86.5" `
        "flet-web>=0.86.5" `
        "pytest>=8.0" `
        "pytest-asyncio>=0.23"
}

Write-Step "Instalação concluída"
Write-Host "Ambiente: $VenvPath" -ForegroundColor Green
Write-Host "Para ativar: .\$VenvPath\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "Para executar: .\$VenvPath\Scripts\python.exe src\main.py" -ForegroundColor Green
if (-not $IncludeDev) {
    Write-Host "Para incluir ferramentas de desenvolvimento: .\Install-Dependencies.ps1 -IncludeDev" -ForegroundColor Yellow
}
