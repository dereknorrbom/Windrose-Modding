# Boar Loot

This is the active boar loot mod project.

## Configure AES key in shell

```powershell
powershell -ExecutionPolicy Bypass -File "..\..\.local\secrets.ps1"
```

Alternative (recommended): use `.local/.env` and let the CLI auto-load it.

```powershell
Copy-Item "..\..\.local\.env.example" "..\..\.local\.env"
```

## Prepare 3x hide overrides

```powershell
python "..\..\modding_tools\windrose_mod_cli.py" prepare-boar-hide-json-mod --project-dir ".\" --multiplier 3.0
```

## Config source

`scripts/build_install.ps1` uses this priority:

1. `..\..\.local\boar-loot.build.json`
2. `docs/build_config.local.json`
3. `docs/build_config.json`

These configs support tokens:

- `<REPO_ROOT>`
- `<WINDROSE_MODS_DIR>`

## Build + Install

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\build_install.ps1"
```

## Backup Mods

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\backup_mods.ps1"
```

## Restore Mods

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\restore_mods.ps1" -BackupDir ".\output\mods_backups\mods_backup_YYYYMMDD_HHMMSS"
```
