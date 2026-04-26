# Fish Bounty Test Plan

## Automated

Run toolkit tests:

```powershell
powershell -ExecutionPolicy Bypass -File ".\modding_tools\scripts\run_tests.ps1"
```

## Manual In-Game

1. Install one `FishBounty` variant, starting with 2x or 3x.
2. Catch coast small fish and confirm actual fish item quantities are multiplied.
3. Catch ocean medium and large fish and confirm actual fish item quantities are multiplied.
4. Confirm fishing chance/weights still feel vanilla; this mod should only change Min/Max quantities.
5. Confirm junk catches, pouch coins, and the fish club weapon are not multiplied.
6. Confirm butchering a fish still gives vanilla fish meat unless a separate butchering mod is added later.
7. Remove mod and confirm baseline behavior returns.

## Regression Checklist

- Build/install script still resolves config correctly.
- Backup/restore scripts still work.
- Staged files are in mount-correct paths under `input/staged`.
