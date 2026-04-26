# Blackbeard Bounty Test Plan

## Automated

Run toolkit tests:

```powershell
powershell -ExecutionPolicy Bypass -File ".\modding_tools\scripts\run_tests.ps1"
```

## Manual In-Game

1. Install one `BlackbeardBounty` variant, starting with 2x or 3x.
2. Kill Blackbeard Grenadiers, Musketeers, Sailors, and Sergeants.
3. Confirm supported drops are multiplied when they drop: gunpowder, bullets, rum, peanuts, guineas, and Blackbeard signs.
4. Confirm vanilla drop chances still apply, especially rows that include 0/0 no-drop entries.
5. Watch for quest progression issues around key-bearing pirate NPCs; this mod should not touch final/key tables.
6. Remove mod and confirm baseline behavior returns.

## Regression Checklist

- Build/install script still resolves config correctly.
- Backup/restore scripts still work.
- Staged files are in mount-correct paths under `input/staged`.
