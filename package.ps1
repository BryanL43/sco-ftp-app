param(
  [string]$Version
)

$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$appConfigPath = Join-Path $projectRoot "application.ini"
$distDir = Join-Path $projectRoot "dist"
$packageDir = Join-Path $distDir "package"
$applicationDir = Join-Path $packageDir "application"
$updaterDir = Join-Path $packageDir "updater"

if (-not (Test-Path $appConfigPath)) {
  throw "Application config not found: $appConfigPath"
}

if (-not (Test-Path $distDir)) {
  throw "dist directory not found. Build the application and updater first."
}

$appConfig = @{}
$section = $null

foreach ($line in Get-Content $appConfigPath) {
  $trimmed = $line.Trim()

  if (-not $trimmed -or $trimmed.StartsWith(";")) {
    continue
  }

  if ($trimmed -match "^\[(.+)\]$") {
    $section = $Matches[1]
    continue
  }

  if ($section -and $trimmed -match "^([^=]+)=(.*)$") {
    $appConfig["$section`_$($Matches[1].Trim())"] = $Matches[2].Trim()
  }
}

$appName = $appConfig["app_name"]
$appMajor = $appConfig["app_major"]
$appMinor = $appConfig["app_minor"]

if (-not $appName) {
  throw "app_name not found in application.ini"
}

if (-not $Version) {
  if (-not $appMajor -or -not $appMinor) {
    throw "Version was not provided and app_major/app_minor were not found in application.ini"
  }

  $Version = "$appMajor.$appMinor.0"
}

$appExe = Join-Path $distDir "$appName.exe"
$updaterExe = Join-Path $distDir "updater.exe"
$binDir = Join-Path $projectRoot "bin"
$packageName = "$appName-$Version.zip"
$packagePath = Join-Path $distDir $packageName
$manifestPath = Join-Path $distDir "manifest.json"

if (-not (Test-Path $appExe)) {
  throw "Application executable not found: $appExe"
}

if (-not (Test-Path $updaterExe)) {
  throw "Updater executable not found: $updaterExe"
}

Remove-Item $packageDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $packagePath -Force -ErrorAction SilentlyContinue
Remove-Item $manifestPath -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path $applicationDir | Out-Null
New-Item -ItemType Directory -Force -Path $updaterDir | Out-Null

Copy-Item $appExe $applicationDir
Copy-Item $updaterExe $updaterDir

if (Test-Path $binDir) {
  Copy-Item $binDir (Join-Path $applicationDir "bin") -Recurse
}

Compress-Archive `
  -Path (Join-Path $packageDir "*") `
  -DestinationPath $packagePath

$packageHash = Get-FileHash -Algorithm SHA256 -Path $packagePath
$updaterHash = Get-FileHash -Algorithm SHA256 -Path (Join-Path $updaterDir "updater.exe")

$manifest = [ordered]@{
  app_name = $appName
  version = $Version
  package_name = $packageName
  package_sha256 = $packageHash.Hash.ToLowerInvariant()
  app_dir = "application"
  updater_path = "updater/updater.exe"
  updater_sha256 = $updaterHash.Hash.ToLowerInvariant()
  preserve = @("logs", "uninstall.exe")
  created_at = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
}

$json = $manifest | ConvertTo-Json -Depth 3
$json = $json -replace '":\s+', '": '

$preserveJson = (($manifest.preserve | ConvertTo-Json -Compress) -replace '","', '", "')
$json = $json -replace '(?s)"preserve":\s*\[.*?\]', "`"preserve`": $preserveJson"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($manifestPath, $json, $utf8NoBom)

"Created local update package: $packagePath"
"Created local update manifest: $manifestPath"
