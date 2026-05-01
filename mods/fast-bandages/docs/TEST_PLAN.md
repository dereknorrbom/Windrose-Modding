# Fast Bandages Test Plan

## Automated

Run toolkit tests:

```powershell
powershell -ExecutionPolicy Bypass -File ".\modding_tools\scripts\run_tests.ps1"
```

## Manual In-Game

1. Install `FastBandages_P.pak` by itself, without other bandage/consumable mods.
2. Use a basic bandage after taking damage.
3. Confirm the healing-over-time effect completes in about 15 seconds instead of about 30 seconds.
4. Confirm the total healing feels comparable to vanilla, not half strength.
5. Confirm bandages still remove/ignore bleed behavior as vanilla does.
6. Confirm no startup/load crashes after install.
7. Remove mod and confirm baseline 30-second behavior returns.

## Regression Checklist

- Build/install script still resolves config correctly.
- Backup/restore scripts still work.
- Staged files are in mount-correct paths under `input/staged`.
