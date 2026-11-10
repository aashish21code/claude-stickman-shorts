<#
.SYNOPSIS
  Fetch the Kenney CC0 kits the bridge town needs and copy the models it loads into public\bridge\kenney\.

.DESCRIPTION
  world.ts loads 26 GLBs by name from public/bridge/kenney/ and drops any that 404 without a word, so a
  copy with no models renders a town with no stalls, carts, lanterns, windmill, canoes, lilies or flowers
  -- and nothing says so. Upstream does not ship the models (they are Kenney's, CC0, ~14 MB of zips), and
  setup.ps1 used to create the folder empty. This script fills it:

  1. downloads kenney_nature-kit.zip and kenney_fantasy-town-kit.zip from kenney.nl (once; kept in
     ..\kenney\, gitignored) -- kenney.nl hands out a signed link per page visit, so the page is fetched first
  2. extracts them there
  3. copies every model world.ts asks for into public\bridge\kenney\ under the exact name it asks for,
     plus the texture atlas the Fantasy Town models reference by relative path

  Idempotent: a zip already on disk is not downloaded again, an extracted kit is not extracted again,
  and a model already in place is left alone unless -Refresh. Ends with a line per missing model, if any.

.EXAMPLE
  .\fetch-kenney.ps1
#>
param(
  [string]$KitDir = (Join-Path $PSScriptRoot "..\kenney"),
  [switch]$Refresh
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # PS 5.1's progress bar slows Invoke-WebRequest by an order of magnitude

# kenney.nl answers 403 to the default PowerShell / curl user agent
$UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
$KITS = @("nature-kit", "fantasy-town-kit")

# the names world.ts loads (const KENNEY), and the kit each comes from. Trees, bushes, hedges and banners
# are drawn procedurally by build.ts (VEG / bannerProp) and never read these files, but world.ts still asks
# for them, so they are copied too: a 404 in the console should mean something is really missing.
$MODELS = [ordered]@{
  "tree_oak" = "nature-kit"; "tree_default" = "nature-kit"; "tree_detailed" = "nature-kit"; "tree_fat" = "nature-kit"
  "tree_cone" = "nature-kit"; "plant_bushLarge" = "nature-kit"; "plant_bushDetailed" = "nature-kit"; "plant_bush" = "nature-kit"
  "flower_redA" = "nature-kit"; "flower_yellowA" = "nature-kit"; "flower_purpleA" = "nature-kit"
  "grass_large" = "nature-kit"; "grass" = "nature-kit"; "lily_large" = "nature-kit"; "canoe" = "nature-kit"
  "tree-high-round" = "fantasy-town-kit"; "tree" = "fantasy-town-kit"; "hedge" = "fantasy-town-kit"
  "lantern" = "fantasy-town-kit"; "cart" = "fantasy-town-kit"; "stall-red" = "fantasy-town-kit"
  "stall-green" = "fantasy-town-kit"; "stall-bench" = "fantasy-town-kit"; "banner-red" = "fantasy-town-kit"
  "banner-green" = "fantasy-town-kit"; "windmill" = "fantasy-town-kit"
}

New-Item -ItemType Directory -Force $KitDir | Out-Null
$KitDir = (Resolve-Path $KitDir).Path
$dst = Join-Path $PSScriptRoot "public\bridge\kenney"
New-Item -ItemType Directory -Force $dst | Out-Null

foreach ($k in $KITS) {
  $zip = Join-Path $KitDir "kenney_$k.zip"
  if (-not (Test-Path $zip)) {
    Write-Host "  get   $k (kenney.nl, CC0)"
    $page = "https://kenney.nl/assets/$k"
    $sess = $null
    Invoke-WebRequest -UseBasicParsing -UserAgent $UA -Uri $page -SessionVariable sess | Out-Null
    $id = -join ([Text.Encoding]::ASCII.GetBytes("assets/$k") | ForEach-Object { $_.ToString("x2") })
    $link = Invoke-RestMethod -UserAgent $UA -WebSession $sess -Headers @{ Referer = $page } -Uri "https://kenney.nl/download-link/$id"
    if (-not $link.url) { throw "kenney.nl gave no download link for $k. Download it by hand from $page into $KitDir\kenney_$k.zip and re-run." }
    $part = "$zip.part"
    Invoke-WebRequest -UseBasicParsing -UserAgent $UA -WebSession $sess -Headers @{ Referer = $page } -Uri $link.url -OutFile $part
    Move-Item -Force $part $zip
  }
  $out = Join-Path $KitDir $k
  if (-not (Test-Path $out)) {
    Write-Host "  unzip $k"
    Expand-Archive -Path $zip -DestinationPath $out
  }
  Write-Host ("  ok    {0}  {1:N0} bytes" -f $zip, (Get-Item $zip).Length)
}

$missing = @()
$textures = @{}
foreach ($name in $MODELS.Keys) {
  $kit = Join-Path $KitDir $MODELS[$name]
  $src = Get-ChildItem -Path $kit -Recurse -File -Filter "$name.glb" | Where-Object { $_.FullName -match "\\Models\\GL(B|TF) format\\" } | Select-Object -First 1
  if (-not $src) { $missing += $name; continue }
  $to = Join-Path $dst "$name.glb"
  if ($Refresh -or -not (Test-Path $to)) { Copy-Item -Force $src.FullName $to }
  # a model that references an external texture (Fantasy Town's colour atlas) looks for it next to itself
  $tex = Join-Path $src.DirectoryName "Textures"
  if (Test-Path $tex) { $textures[$tex] = $true }
}
foreach ($tex in $textures.Keys) {
  $to = Join-Path $dst "Textures"
  New-Item -ItemType Directory -Force $to | Out-Null
  Get-ChildItem $tex -File | ForEach-Object { if ($Refresh -or -not (Test-Path (Join-Path $to $_.Name))) { Copy-Item -Force $_.FullName $to } }
}

$have = $MODELS.Count - $missing.Count
Write-Host "  models in $dst : $have / $($MODELS.Count)"
foreach ($m in $missing) { Write-Host "  MISSING $m.glb -- not in kenney_$($MODELS[$m]).zip; world.ts will skip it" }
if ($missing.Count -gt 0) { exit 1 }
