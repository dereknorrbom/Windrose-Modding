# Ship Bounty

Scaffolded Windrose mod project for `ship-bounty`.

Ship Bounty scales ship piastre and sellable trade-good quantities from ship boarding/final reward tables and ship RSS trade-good tables. It covers piastre, contraband, luxuries, naval supplies, munitions, medicine, provisions, spirits, and related ship trade goods.

This first version intentionally leaves repair kits, Blackbeard signs, generic ship resources, quest data, unrelated water pickups, and non-ship loot tables unchanged. Guineas do not appear in ship loot tables; those are covered by Blackbeard Bounty's Sergeant loot.

## Preferred recipe workflow

```powershell
python ".\modding_tools\windrose_mod_cli.py" build-mod --project-dir ".\mods\ship-bounty" --backup-first
```

## Config Source Priority

`scripts/build_install.ps1` checks configs in this order:

1. `..\..\.local\ship-bounty.build.json`
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
