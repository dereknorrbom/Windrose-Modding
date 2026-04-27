# Mods Directory

Each folder here is either a Windrose mod project or a scaffold template for future mods.

## Current Mods

- `boar-loot/` - boar leather, meat, and tusk quantity variants.
- `blackbeard-bounty/` - Blackbeard pirate loot quantity variants.
- `cane-sugar-bounty/` - raw cane sugar quantity variants.
- `cayenne-pepper-yield/` - cayenne pepper harvest quantity variants.
- `crab-bounty/` - crab, Thorn Fiddler, and drowned crab loot variants.
- `crocodile-bounty/` - crocodile and corrupted crocodile loot variants.
- `dodo-bounty/` - dodo and female dodo loot variants.
- `fish-bounty/` - fishing catch quantity variants.
- `goat-bounty/` - goat loot variants.
- `sweet-potato-bounty/` - sweet potato harvest quantity variants.
- `wolf-bounty/` - wolf and alpha wolf loot variants.
- `windrose-bounty/` - combined bundle that includes all current bounty mods in one pak.

## Templates

- `new-mod-template/` - scaffold source used by `init-mod`.

## Standard Layout

When adding new mods, use:

- `mods/<mod-name>/docs`
- `mods/<mod-name>/input`
- `mods/<mod-name>/output`
- `mods/<mod-name>/scripts`

The preferred recipe file is:

```text
mods/<mod-name>/docs/mod_recipe.json
```

Use `init-mob-bounty` for new standalone mob loot mods, and use a `bundle` recipe when combining multiple existing mod recipes into one pak.
