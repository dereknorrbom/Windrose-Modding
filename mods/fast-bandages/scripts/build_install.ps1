param(
    [switch]$BackupFirst = $true
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModDir = Split-Path -Parent $ScriptDir
$ModsRoot = Split-Path -Parent $ModDir
$RepoRoot = Split-Path -Parent $ModsRoot
$SharedBuild = Join-Path $RepoRoot "modding_tools\scripts\build_mod.ps1"

& $SharedBuild -ModDir $ModDir -BackupFirst:$BackupFirst
