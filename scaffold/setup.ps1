<#
.SYNOPSIS
  Set up the Remotion + three.js scaffold for the cartoon-3D shorts and prove it with one smoke-test still.

.DESCRIPTION
  1. checks node, npm, python and ffmpeg (clear error if one is missing)
  2. npm install (pinned versions in package.json)
  3. picks a big-drive temp folder for Remotion bundles and sets TEMP/TMP/REMOTION_TMP for this session
  4. COPIES upstream templates/bridge -> src/videos/bridge and templates/scripts -> scripts
     (never moves or edits the originals; an existing copy is kept unless -Refresh), then applies
     patches/apply.mjs to the copy (our fixes on top of upstream, e.g. the 6 TS2322 in Bridge.tsx)
  5. fetch-kenney.ps1: the Kenney CC0 models world.ts loads, into public/bridge/kenney (skip: -SkipKenney)
  6. renders one smoke-test still with scripts/bridge-stills.mjs

  Idempotent: safe to run twice. A second run skips what is already in place.

.EXAMPLE
  .\setup.ps1 -RepoPath ..\upstream -TempDrive D:\remotion-tmp
#>
param(
  [string]$RepoPath = (Join-Path $PSScriptRoot "..\upstream"),
  [string]$TempDrive = "",
  [int]$Frame = 100,
  [switch]$Refresh,
  [switch]$SkipStill,
  [switch]$SkipKenney
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Need($name, $hint) {
  $c = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $c) { throw "$name not found on PATH. $hint" }
  Write-Host ("  ok  {0,-8} {1}" -f $name, $c.Source)
}

Write-Host "[1/6] tools"
Need "node"   "Install Node 18+ from https://nodejs.org"
Need "npm"    "It ships with Node."
Need "ffmpeg" "Install ffmpeg and add its bin folder to PATH."
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) {
  throw "python not found on PATH. Install Python 3 (the audio and QA templates are Python)."
}
Write-Host "  ok  python"
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"   # bridge-stills.mjs uses this path
if (-not (Test-Path $chrome)) { throw "Chrome not found at $chrome -- scripts/bridge-stills.mjs renders through it." }
Write-Host "  ok  chrome   $chrome"

$RepoPath = (Resolve-Path $RepoPath).Path
if (-not (Test-Path (Join-Path $RepoPath "templates\bridge\Bridge.tsx"))) {
  throw "$RepoPath is not the upstream repo (templates\bridge\Bridge.tsx missing). Clone it: git clone --depth 1 https://github.com/mromidev/claude-animated-shorts upstream"
}

Write-Host "[2/6] npm install"
if ((Test-Path "node_modules\remotion\package.json") -and (Test-Path "node_modules\three\package.json") -and -not $Refresh) {
  Write-Host "  node_modules already in place (use -Refresh to reinstall)"
} else {
  # Windows PowerShell 5.1 turns a native command's stderr into an error record when output is
  # redirected, and under "Stop" the first "npm warn" line ends the script. Judge npm by its exit code.
  $ErrorActionPreference = "Continue"
  npm install --no-audit --no-fund
  $code = $LASTEXITCODE; $ErrorActionPreference = "Stop"
  if ($code -ne 0) { throw "npm install failed ($code). EBUSY on esbuild.exe is antivirus holding the new file: run setup.ps1 -Refresh again." }
}

Write-Host "[3/6] temp folder for Remotion bundles"
# Every bundle copies public/ into TEMP and never deletes it (60+ GB filled C: in the upstream bridge
# passes), so bundles go to a big drive. In JS the path must use forward slashes: "\r" is a carriage return.
if (-not $TempDrive) {
  $default = if (Test-Path "D:\") { "D:\remotion-tmp" } else { Join-Path $env:TEMP "remotion-tmp" }
  if ([Environment]::UserInteractive -and $Host.Name -eq "ConsoleHost" -and -not $env:CI) {
    $answer = Read-Host "Big-drive temp folder for Remotion bundles [$default]"
    $TempDrive = if ($answer) { $answer } else { $default }
  } else { $TempDrive = $default }
}
New-Item -ItemType Directory -Force $TempDrive | Out-Null
$tmpFwd = (Resolve-Path $TempDrive).Path -replace "\\", "/"
$env:TEMP = $tmpFwd; $env:TMP = $tmpFwd; $env:REMOTION_TMP = $tmpFwd
Write-Host "  TEMP=TMP=REMOTION_TMP=$tmpFwd (this session only)"

Write-Host "[4/6] copy templates (originals untouched)"
$pairs = @(
  @{ src = Join-Path $RepoPath "templates\bridge";  dst = Join-Path $PSScriptRoot "src\videos\bridge" },
  @{ src = Join-Path $RepoPath "templates\scripts"; dst = Join-Path $PSScriptRoot "scripts" }
)
foreach ($p in $pairs) {
  if ((Test-Path $p.dst) -and -not $Refresh) {
    Write-Host "  keep  $($p.dst) (exists; -Refresh overwrites it with a fresh copy)"
  } else {
    New-Item -ItemType Directory -Force $p.dst | Out-Null
    Copy-Item -Path (Join-Path $p.src "*") -Destination $p.dst -Recurse -Force
    Write-Host "  copy  $($p.src) -> $($p.dst)"
  }
}
# the copy is regenerated and gitignored, so our fixes to it live in patches/ and are re-applied on every run
$ErrorActionPreference = "Continue"
node patches/apply.mjs
$code = $LASTEXITCODE; $ErrorActionPreference = "Stop"
if ($code -ne 0) { throw "patches/apply.mjs failed ($code): upstream changed under a patch; re-check the edit it names" }
New-Item -ItemType Directory -Force (Join-Path $PSScriptRoot "public\bridge") | Out-Null   # staticFile() root

Write-Host "[5/6] Kenney CC0 models"
# world.ts drops a model that 404s without a word, so an empty public\bridge\kenney renders a town with no
# stalls, carts, lanterns, windmill, canoes, lilies or flowers and nothing fails. Fetch them; warn loudly if not.
if ($SkipKenney) { Write-Host "  skipped (-SkipKenney): the town renders without its props" }
else {
  try { & (Join-Path $PSScriptRoot "fetch-kenney.ps1"); if ($LASTEXITCODE) { throw "some models missing" } }
  catch { Write-Warning "Kenney models incomplete ($_). The smoke still renders anyway, without the props. Fix: .\fetch-kenney.ps1" }
}

Write-Host "[6/6] smoke-test still"
if ($SkipStill) { Write-Host "  skipped (-SkipStill)"; exit 0 }
New-Item -ItemType Directory -Force "out\smoke" | Out-Null
$ErrorActionPreference = "Continue"   # same 5.1 stderr rule as npm install above
node scripts/bridge-stills.mjs out/smoke/x_ $Frame 0.5
$code = $LASTEXITCODE; $ErrorActionPreference = "Stop"
if ($code -ne 0) { throw "smoke-test still failed ($code)" }
$still = Get-Item "out\smoke\x_$Frame.jpg"
Write-Host ("SMOKE TEST OK  {0}  {1:N0} bytes" -f $still.FullName, $still.Length)
