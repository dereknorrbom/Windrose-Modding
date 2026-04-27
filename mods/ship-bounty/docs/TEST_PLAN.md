# Ship Bounty Test Plan

## Automated

Run toolkit tests:

```powershell
powershell -ExecutionPolicy Bypass -File ".\modding_tools\scripts\run_tests.ps1"
```

## Manual In-Game

1. Install one `ShipBounty` variant, starting with 2x or 3x.
2. Sink or board Ketch, Cutter, Brig, and Frigate ships across a few areas.
3. Confirm piastre quantities are multiplied.
4. Confirm sellable ship trade goods are multiplied when they appear, including contraband, luxuries, naval supplies, munitions, medicine, provisions, and spirits.
5. Confirm vanilla chances/weights still apply, especially rows that include 0/0 no-drop entries.
6. Confirm repair kits, Blackbeard signs, generic ship resources, and unrelated water pickups are not unexpectedly multiplied.
7. Remove mod and confirm baseline behavior returns.

## Regression Checklist

- Build/install script still resolves config correctly.
- Backup/restore scripts still work.
- Staged files are in mount-correct paths under `input/staged`.
