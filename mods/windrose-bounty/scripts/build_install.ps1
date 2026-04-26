param(
    [switch]$BackupFirst = $true
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModDir = Split-Path -Parent $ScriptDir
$ModsRoot = Split-Path -Parent $ModDir
$RepoRoot = Split-Path -Parent $ModsRoot
$Cli = Join-Path $RepoRoot "modding_tools\windrose_mod_cli.py"

if ($BackupFirst) {
    python $Cli build-mod --project-dir $ModDir --backup-first
} else {
    python $Cli build-mod --project-dir $ModDir
}
