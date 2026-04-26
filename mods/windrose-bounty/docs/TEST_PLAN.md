# Windrose Bounty Test Plan

## Automated

- Run the shared CLI test suite.
- Build variants through `build-mod` and confirm reports include every included recipe.
- Confirm generated staging does not report bundle path conflicts.

## Manual

- Install one `WindroseBounty` variant at a time.
- Confirm boar, wolf, goat, crocodile, crab, cayenne, and sweet potato quantity changes behave like their matching standalone variant.
- Confirm drop chances still feel vanilla for rare or optional drops.
