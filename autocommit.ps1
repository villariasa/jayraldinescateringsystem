# PowerShell wrapper for autocommit.sh
[CmdletBinding()]
param(
    [switch]$NoPush,
    [switch]$DryRun
)

$scriptDir = $PSScriptRoot
$shScript = Join-Path $scriptDir "autocommit.sh"

$argsList = @()
if ($NoPush) { $argsList += "--no-push" }
if ($DryRun) { $argsList += "--dry-run" }

$bashCandidates = @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Program Files\Git\usr\bin\bash.exe",
    "C:\Program Files (x86)\Git\bin\bash.exe",
    "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe"
)

$bashPath = $bashCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $bashPath) {
    $cmd = Get-Command bash -ErrorAction SilentlyContinue
    if ($cmd) { $bashPath = $cmd.Source }
}

if (-not $bashPath) {
    $cmd = Get-Command sh -ErrorAction SilentlyContinue
    if ($cmd) { $bashPath = $cmd.Source }
}

if (-not $bashPath) {
    Write-Error "Git Bash was not found. Please install Git for Windows or ensure bash is in your PATH."
    exit 1
}

& $bashPath $shScript @argsList
exit $LASTEXITCODE
