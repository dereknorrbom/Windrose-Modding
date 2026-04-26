# Windrose Bounty

Combined Windrose bounty mod that builds one `.pak` containing all current bounty recipes.

This does not replace the individual mods. Each standalone mod can still be built and published separately; this bundle is only a convenience option for players who want one install.

## Preferred recipe workflow

```powershell
python ".\modding_tools\windrose_mod_cli.py" build-mod --project-dir ".\mods\windrose-bounty" --backup-first
```

The recipe lives in `docs/mod_recipe.json` and builds the 2x, 3x, 5x, and 10x combined variants with zipped release packages.

## Included mods

- `boar-loot`
- `blackbeard-bounty`
- `cayenne-pepper-yield`
- `crab-bounty`
- `crocodile-bounty`
- `dodo-bounty`
- `goat-bounty`
- `sweet-potato-bounty`
- `wolf-bounty`

## Notes

- Install only one `WindroseBounty` variant at a time.
- Do not install this bundle alongside the individual bounty mods unless you intentionally want to test override conflicts.
- Drop chances and weights remain unchanged; only configured quantity values are multiplied.
