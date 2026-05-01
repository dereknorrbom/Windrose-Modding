param(
    [Parameter(Mandatory = $true)]
    [string]$ModDir,
    [switch]$BackupFirst = $true
)

$ErrorActionPreference = "Stop"

$ModDir = (Resolve-Path $ModDir).Path
$ModsRoot = Split-Path -Parent $ModDir
$RepoRoot = Split-Path -Parent $ModsRoot
$Cli = Join-Path $RepoRoot "modding_tools\windrose_mod_cli.py"
$Recipe = Join-Path $ModDir "docs\mod_recipe.json"
$Slug = Split-Path -Leaf $ModDir
$RootConfigLocal = Join-Path $RepoRoot ".local\$Slug.build.json"
$ConfigLocal = Join-Path $ModDir "docs\build_config.local.json"
$ConfigDefault = Join-Path $ModDir "docs\build_config.json"
$ConfigExample = Join-Path $ModDir "docs\build_config.example.json"
$Config = if (Test-Path $RootConfigLocal) {
    $RootConfigLocal
} elseif (Test-Path $ConfigLocal) {
    $ConfigLocal
} elseif (Test-Path $ConfigDefault) {
    $ConfigDefault
} else {
    $ConfigExample
}

if (Test-Path $Recipe) {
    if ($BackupFirst) {
        python $Cli build-mod --project-dir $ModDir --config $Config --backup-first
    } else {
        python $Cli build-mod --project-dir $ModDir --config $Config
    }
} else {
    if ($BackupFirst) {
        python $Cli build-install --config $Config --backup-first
    } else {
        python $Cli build-install --config $Config
    }
}
