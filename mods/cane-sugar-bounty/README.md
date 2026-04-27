# Cane Sugar Bounty

Scaffolded Windrose mod project for `cane-sugar-bounty`.

Cane Sugar Bounty scales raw cane sugar quantities from known sugar source tables, including Highlands farm chests, Senkamati sugar pots, British supply containers, pickup bales, and sugar trade containers.

This first version intentionally leaves sugarcane alcohol, ship trade-good sugar cargo, recipes, vendors, and quest data unchanged.

## Preferred recipe workflow

```powershell
python ".\modding_tools\windrose_mod_cli.py" build-mod --project-dir ".\mods\cane-sugar-bounty" --backup-first
```

## Config Source Priority

`scripts/build_install.ps1` checks configs in this order:

1. `..\..\.local\cane-sugar-bounty.build.json`
2. `docs/build_config.local.json`
3. `docs/build_config.json`
4. `docs/build_config.example.json`

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

## Notes

- Place cooked override assets under `input/staged` using mount-relative paths.
- Keep machine-specific configs and secrets in `.local` or `docs/build_config.local.json`.
