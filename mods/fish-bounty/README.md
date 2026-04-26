# Fish Bounty

Scaffolded Windrose mod project for `fish-bounty`.

Fish Bounty scales the number of actual fish items caught from fishing loot tables. It covers small coast fish plus medium and large ocean fish, while leaving junk catches, pouch coins, the fish club weapon, butchering yields, recipes, and quest collection data unchanged.

Fish currently covered:

- Reef Snapper
- Blue Tang
- Pink Wrasse
- Sapphire Wrasse
- Moon Angelfish
- Queen Angelfish
- Emerald Bluefish
- Red Snapper
- Giant Mackerel
- Great Barracuda

## Preferred recipe workflow

```powershell
python ".\modding_tools\windrose_mod_cli.py" build-mod --project-dir ".\mods\fish-bounty" --backup-first
```

## Config Source Priority

`scripts/build_install.ps1` checks configs in this order:

1. `..\..\.local\fish-bounty.build.json`
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
