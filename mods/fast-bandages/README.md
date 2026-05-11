# Fast Bandages

Scaffolded Windrose mod project for `fast-bandages`.

Fast Bandages is an experimental cooked-asset override that makes basic bandages complete their healing faster while preserving the same total healing. The recipe currently builds both a 15-second variant and a 1-second variant.

The mod patches `CT_Alchemy_GE_Values`:

- `Alchemy_Bandages_T01_Duration`: `30.0 -> 15.0` or `30.0 -> 1.0`
- `Alchemy_Bandages_T01_HealthPerTick`: `15.0 -> 30.0` or `15.0 -> 450.0`
- `Alchemy_Bandages_T01_TickPeriod`: unchanged at `0.5`

## Preferred Workflow

```powershell
python ".\modding_tools\windrose_mod_cli.py" build-mod --project-dir ".\mods\fast-bandages" --install-multipliers "15"
```

The 15-second variant remains the default installed variant. The 1-second variant is built and packaged in `output/` for separate testing or publishing.

## Config Source Priority

`scripts/build_install.ps1` checks configs in this order:

1. `..\..\.local\fast-bandages.build.json`
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

- This cooked asset override must be installed as the full `.pak` / `.ucas` / `.utoc` trio.
- Place cooked override assets under `input/staged` using mount-relative paths.
- Keep machine-specific configs and secrets in `.local` or `docs/build_config.local.json`.
