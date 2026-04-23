# Cayenne Pepper Yield

Scaffolded Windrose mod project for `cayenne-pepper-yield`.

## Config Source Priority

`scripts/build_install.ps1` checks configs in this order:

1. `..\..\.local\cayenne-pepper-yield.build.json`
2. `docs/build_config.local.json`
3. `docs/build_config.json`
4. `docs/build_config.example.json`

## Build + Install

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\build_install.ps1"
```

## Prepare cayenne pepper overrides

```powershell
python "..\..\modding_tools\windrose_mod_cli.py" prepare-cayenne-pepper-json-mod --project-dir ".\" --multiplier 3.0
```

## Build multiple variants (2x, 3x, 5x, 10x)

```powershell
python "..\..\modding_tools\windrose_mod_cli.py" build-variants --config "docs\build_config.example.json" --multipliers "2,3,5,10" --project-dir "." --prepare-command-template "python ..\..\modding_tools\windrose_mod_cli.py prepare-cayenne-pepper-json-mod --project-dir {project_dir_quoted} --staged-root {variant_staged_dir_quoted} --multiplier {multiplier}" --install-multipliers "3" --backup-first
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
