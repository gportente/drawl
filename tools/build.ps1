# Produces the two distributable artefacts in dist/:
#   drawl-<version>-portable.zip   self-contained folder, unzip and run
#   drawl-<version>-setup.exe      installer, with shortcuts and uninstall
#
#   .\tools\build.ps1
#
# The ASR model (640 MB) is in neither: it downloads on first launch into
# %LOCALAPPDATA%\drawl\models.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Native {
    <#
      In PowerShell 5.1 every line an executable writes to stderr becomes an
      ErrorRecord, and with ErrorActionPreference set to Stop it aborts the
      script even when the program exited successfully. PyInstaller and ISCC
      write their progress there, so only the exit code is checked here.
    #>
    param([string]$Exe, [string[]]$Arguments, [string]$What)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Exe @Arguments
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) { throw "$What failed (exit code $code)" }
}

$version = (Select-String -Path "drawl\__init__.py" -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value
Write-Host "drawl $version" -ForegroundColor Cyan

# --- 1. icon ----------------------------------------------------------------
Write-Host "`n[1/4] icon" -ForegroundColor Cyan
Invoke-Native ".\.venv\Scripts\python.exe" @("tools\make_icon.py") "icon generation"

# --- 2. PyInstaller bundle ---------------------------------------------------
Write-Host "`n[2/4] PyInstaller bundle" -ForegroundColor Cyan
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
Invoke-Native ".\.venv\Scripts\python.exe" `
    @("-m", "PyInstaller", "drawl.spec", "--noconfirm", "--log-level", "WARN") "PyInstaller bundle"
if (-not (Test-Path "dist\drawl\drawl.exe")) { throw "the bundle was not produced" }
$mb = [math]::Round((Get-ChildItem "dist\drawl" -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 0)
Write-Host "  dist\drawl: $mb MB"

# --- 3. portable archive ---------------------------------------------------------
Write-Host "`n[3/4] portable archive" -ForegroundColor Cyan
$zip = "dist\drawl-$version-portable.zip"
Compress-Archive -Path "dist\drawl" -DestinationPath $zip -CompressionLevel Optimal
$zipMb = [math]::Round((Get-Item $zip).Length / 1MB, 0)
Write-Host "  $zip : $zipMb MB"

# --- 4. installer ------------------------------------------------------------
Write-Host "`n[4/4] installer" -ForegroundColor Cyan
# winget installs Inno Setup for the current user, so it lands under
# LOCALAPPDATA rather than Program Files: look in both.
$iscc = @(
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
  Write-Warning "Inno Setup not found: skipping the installer."
  Write-Warning "Install it with:  winget install --id JRSoftware.InnoSetup"
} else {
  Invoke-Native $iscc @("packaging\drawl.iss", "/Qp") "installer compilation"
  $setup = "dist\drawl-$version-setup.exe"
  if (Test-Path $setup) {
    $setupMb = [math]::Round((Get-Item $setup).Length / 1MB, 0)
    Write-Host "  $setup : $setupMb MB"
  } else { throw "the installer was not produced" }
}

Write-Host "`ndone. Artefacts in dist\:" -ForegroundColor Green
Get-ChildItem "dist" -File | ForEach-Object {
  "  {0,-38} {1,6} MB" -f $_.Name, [math]::Round($_.Length / 1MB, 0)
}
