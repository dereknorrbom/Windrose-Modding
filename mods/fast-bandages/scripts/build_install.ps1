param(
    [switch]$BackupFirst = $true
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModDir = Split-Path -Parent $ScriptDir
$ModsRoot = Split-Path -Parent $ModDir
$RepoRoot = Split-Path -Parent $ModsRoot
$Cli = Join-Path $RepoRoot "modding_tools\windrose_mod_cli.py"
$InputDir = Join-Path $ModDir "input\staged"
$OutputPak = Join-Path $ModDir "output\FastBandages_P.pak"
$ModsDir = $env:WINDROSE_MODS_DIR
if (-not $ModsDir) {
    $ModsDir = "c:\Program Files (x86)\Steam\steamapps\common\Windrose\R5\Content\Paks\~mods"
}

if ($BackupFirst) {
    $BackupDir = Join-Path $ModDir "output\mods_backups"
    python $Cli backup-mods --mods-dir $ModsDir --backup-dir $BackupDir
}

python $Cli prepare-bandage-speed-mod --project-dir $ModDir
python $Cli pack-iostore-mod --input-dir $InputDir --output-pak $OutputPak --install-to-mods $ModsDir
