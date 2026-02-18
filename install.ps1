param(
    [string]$RepoUrl = "git+https://github.com/cen447/stupidshit.git"
)

$ErrorActionPreference = "Stop"

if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
    $PythonBaseArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
    $PythonBaseArgs = @()
} else {
    Write-Error "Python 3 is required."
    exit 1
}

function Invoke-Python([string[]]$Args) {
    & $PythonExe @PythonBaseArgs @Args
}

Invoke-Python @("-m", "pip", "install", "--user", "--upgrade", "pip", "pipx")
Invoke-Python @("-m", "pipx", "ensurepath") | Out-Null
Invoke-Python @("-m", "pipx", "install", "--force", $RepoUrl)

Write-Host ""
Write-Host "Install complete."
Write-Host "If command is not found yet, open a new terminal."
Write-Host ""
Write-Host "Run from anywhere:"
Write-Host "  fuck asad 1"
Write-Host "  fuck asad 10"
