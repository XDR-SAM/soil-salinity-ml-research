param([string]$Compiler = 'tectonic')
$ErrorActionPreference = 'Stop'
$tool = Get-Command $Compiler -ErrorAction Stop
Push-Location (Join-Path $PSScriptRoot '../paper')
try {
    & $tool.Source --keep-logs main.tex
    if ($LASTEXITCODE -ne 0) { throw 'IEEEtran compilation failed' }
} finally {
    Pop-Location
}
