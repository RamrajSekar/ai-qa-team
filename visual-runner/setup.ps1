param(
    [string]$Python = 'py',
    [string]$Version = '146.0.7680.31',
    [string]$InstallRoot = $PSScriptRoot
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($Version -notmatch '^\d+\.\d+\.\d+\.\d+$') { throw 'Use an exact Chrome for Testing version.' }
$runnerRoot = $PSScriptRoot
$venvPath = Join-Path $InstallRoot '.venv'
if ($Python -eq 'py') { $pythonVersion = & $Python -3.12 -c 'import sys; print(".".join(map(str,sys.version_info[:2])))' }
else { $pythonVersion = & $Python -c 'import sys; print(".".join(map(str,sys.version_info[:2])))' }
if ($LASTEXITCODE -ne 0 -or $pythonVersion -ne '3.12') { throw 'M1A setup requires Python 3.12.' }
if ($Python -eq 'py') { & $Python -3.12 -m venv $venvPath }
else { & $Python -m venv $venvPath }
if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
$runnerPython = Join-Path $venvPath 'Scripts/python.exe'
& $runnerPython -m pip install -r (Join-Path $runnerRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Pinned runner dependency installation failed.' }
& $runnerPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Runner dependency check failed.' }
$binaryRoot = Join-Path $InstallRoot "binaries/$Version"
New-Item -ItemType Directory -Path $binaryRoot -Force | Out-Null
foreach ($component in @('chrome', 'chromedriver')) {
    $zip = Join-Path $binaryRoot "$component.zip"
    Invoke-WebRequest -Uri "https://storage.googleapis.com/chrome-for-testing-public/$Version/win64/$component-win64.zip" -OutFile $zip
    Expand-Archive -LiteralPath $zip -DestinationPath $binaryRoot -Force
}
$chromeDirectory = Join-Path $binaryRoot 'chrome-win64'
# CfT is unpacked, not installed. Configure the downloaded directory's sandbox ACLs;
# this switch exits without installing/replacing the user's normal Chrome.
$configuration = Start-Process -FilePath (Join-Path $chromeDirectory 'setup.exe') -ArgumentList ('"--configure-browser-in-directory=' + $chromeDirectory + '"') -WindowStyle Hidden -Wait -PassThru
# Chromium InstallStatus: CONFIGURE_APP_CONTAINER_SANDBOX_SUCCESS = 78.
if ($configuration.ExitCode -notin @(0, 78)) { throw "CfT sandbox configuration failed (code $($configuration.ExitCode))." }
$chromeVersion = (Get-Item -LiteralPath (Join-Path $chromeDirectory 'chrome.exe')).VersionInfo.ProductVersion
$driverVersion = & (Join-Path $binaryRoot 'chromedriver-win64/chromedriver.exe') --version
if ($chromeVersion -ne $Version -or $driverVersion -notmatch ('^ChromeDriver ' + [regex]::Escape($Version) + ' ')) {
    throw 'Downloaded Chrome and ChromeDriver do not match the requested full version.'
}
Write-Output "CfT sandbox directory configured; browser/driver full versions match $Version."
Write-Output "Runner Python: $runnerPython"
Write-Output "Chrome: $(Join-Path $binaryRoot 'chrome-win64/chrome.exe')"
Write-Output "Driver: $(Join-Path $binaryRoot 'chromedriver-win64/chromedriver.exe')"
