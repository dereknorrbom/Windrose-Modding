# Salt and Coffee Bounty Test Plan

## Automated

Run toolkit tests:

```powershell
powershell -ExecutionPolicy Bypass -File ".\modding_tools\scripts\run_tests.ps1"
```

## Manual In-Game

1. Install one `SaltAndCoffeeBounty` variant, starting with 2x or 3x.
2. Loot floating lost boat coffee/salt pickups and confirm raw salt/coffee quantities are multiplied.
3. Harvest or loot salt mineral/pickup sources and confirm raw salt quantities are multiplied.
4. Loot coffee bales/traveler coffee and confirm raw coffee quantities are multiplied.
5. Confirm vanilla chances/weights still apply, especially rows that include no-drop entries.
6. Confirm salt/coffee trade-good crates, vendors, recipes, quest data, and unrelated ship loot are not unexpectedly changed.
7. Remove mod and confirm baseline behavior returns.

## Regression Checklist

- Build/install script still resolves config correctly.
- Backup/restore scripts still work.
- Staged files are in mount-correct paths under `input/staged`.
