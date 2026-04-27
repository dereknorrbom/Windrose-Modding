# Cane Sugar Bounty Test Plan

## Automated

Run toolkit tests:

```powershell
powershell -ExecutionPolicy Bypass -File ".\modding_tools\scripts\run_tests.ps1"
```

## Manual In-Game

1. Install one `CaneSugarBounty` variant, starting with 2x or 3x.
2. Loot Highlands farm chests, Senkamati sugar pots, British supply containers, pickup bales, and sugar trade containers.
3. Confirm raw cane sugar quantities are multiplied when those rows appear.
4. Confirm vanilla drop chances/weights still apply.
5. Confirm sugarcane alcohol, ship trade-good sugar cargo, vendors, recipes, and quest data are not affected.
6. Remove mod and confirm baseline behavior returns.

## Regression Checklist

- Build/install script still resolves config correctly.
- Backup/restore scripts still work.
- Staged files are in mount-correct paths under `input/staged`.
