# Blackbeard Bounty

Scaffolded Windrose mob bounty mod for `blackbeard-bounty`.

Scales Blackbeard pirate RSS loot quantities for gunpowder, bullets, rum, peanuts, guineas, and Blackbeard signs. It intentionally avoids final/key-bearing loot tables so quest-specific drops are not modified.

## Build all variants

```powershell
python ".\modding_tools\windrose_mod_cli.py" build-mod --project-dir ".\mods\blackbeard-bounty" --backup-first
```

## Discover matching loot tables

```powershell
python ".\modding_tools\windrose_mod_cli.py" discover-mob-loot --keyword "blackbeard"
```
