param()
$ErrorActionPreference = 'Stop'
$reportRoot = $PSScriptRoot
foreach ($programName in @('xelatex', 'bibtex')) {
    if (-not (Get-Command $programName -ErrorAction SilentlyContinue)) {
        throw "Khong tim thay $programName. Cai MiKTeX/TeX Live va mo lai PowerShell, hoac bien dich goi ZIP tren Overleaf voi XeLaTeX."
    }
}
Push-Location -LiteralPath $reportRoot
try {
    & xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error main.tex
    if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX pass 1 failed; see main.log.' }
    & bibtex main
    if ($LASTEXITCODE -ne 0) { throw 'BibTeX failed; see main.blg.' }
    for ($passNumber = 2; $passNumber -le 3; $passNumber++) {
        & xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error main.tex
        if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass $passNumber failed; see main.log." }
    }
    Write-Output (Join-Path $reportRoot 'main.pdf')
} finally {
    Pop-Location
}
