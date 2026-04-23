#!/usr/bin/env python3
"""Reusable CLI helpers for Windrose UE container investigations."""

from __future__ import annotations

import argparse
import json
import mmap
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

PATH_PATTERN = re.compile(rb"/Game/[A-Za-z0-9_./]+?(?=/Game/|$)")
LT_PATTERN = re.compile(rb"(?:/Game)?/R5BusinessRules/LootTables/Mobs/DA_LT_Mob_[A-Za-z0-9_]+")
ODL_PATTERN = re.compile(rb"(?:/Game)?/R5BusinessRules/LootTablesOverrides/Mobs/DA_ODL_Mob_[A-Za-z0-9_]+")
DEFAULT_GAME_MODS_DIR = Path(
    r"c:\Program Files (x86)\Steam\steamapps\common\Windrose\R5\Content\Paks\~mods"
)
BOAR_LEATHER_JSON_PATTERN = re.compile(
    r"^R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Boar(?:F|Mega)?_Leather(?:_[0-9]+)?\.json$"
)
BOAR_RSS_JSON_PATTERN = re.compile(
    r"^R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Boar(?:F|Mega)?_(?P<resource>[A-Za-z]+)(?:_[0-9]+)?\.json$"
)
SUPPORTED_BOAR_RESOURCE_TYPES = {"leather", "meat", "fat", "tusk", "boarhead"}


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def workspace_root() -> Path:
    return repo_root().parent


def bin_dir() -> Path:
    return repo_root() / "bin"


def load_local_env() -> None:
    """
    Load repo-local environment variables from .local/.env if present.
    Existing process env vars take precedence.
    """
    env_path = workspace_root() / ".local" / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_path(s: str) -> str:
    s = s.strip()
    if s.startswith("/R5BusinessRules/"):
        return "/Game" + s
    return s


def iter_ucas_files(paks_dir: Path, include_files: list[str] | None = None) -> list[Path]:
    if include_files:
        selected = [paks_dir / name for name in include_files]
        return [p for p in selected if p.exists()]

    preferred = paks_dir / "pakchunk0_s3-Windows.ucas"
    if preferred.exists():
        return [preferred]

    return sorted(paks_dir.glob("*.ucas"))


def extract_game_paths(blob: bytes) -> set[str]:
    cleaned: set[str] = set()
    for match in PATH_PATTERN.finditer(blob):
        text = normalize_path(match.group().decode("ascii", "replace"))
        if not text.startswith("/Game/"):
            continue
        # Keep only plausible object-path characters.
        if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./" for ch in text):
            continue
        cleaned.add(text)
    return cleaned


def extract_targeted_mob_tables_from_file(path: Path, mob_keyword: str) -> tuple[set[str], set[str]]:
    keyword = mob_keyword.lower()
    lt_paths: set[str] = set()
    odl_paths: set[str] = set()
    with path.open("rb") as handle:
        mm = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            for match in LT_PATTERN.finditer(mm):
                text = normalize_path(match.group().decode("ascii", "replace"))
                if keyword in text.lower():
                    lt_paths.add(text)
            for match in ODL_PATTERN.finditer(mm):
                text = normalize_path(match.group().decode("ascii", "replace"))
                if keyword in text.lower():
                    odl_paths.add(text)
        finally:
            mm.close()
    return lt_paths, odl_paths


@dataclass
class LootEntry:
    loot_table: str
    override_table: str
    source_paths: list[str]


def path_leaf(path: str) -> str:
    return path.split("/")[-1]


def mob_key_from_lt(path: str) -> str:
    leaf = path_leaf(path)
    if leaf.startswith("DA_LT_Mob_"):
        raw = leaf.removeprefix("DA_LT_Mob_")
        return raw.removesuffix("_Final")
    return leaf


def mob_key_from_odl(path: str) -> str:
    leaf = path_leaf(path)
    if leaf.startswith("DA_ODL_Mob_"):
        return leaf.removeprefix("DA_ODL_Mob_")
    return leaf


def correlate_mob_loot_paths(all_paths: Iterable[str], mob_keyword: str) -> list[LootEntry]:
    mob_keyword_lower = mob_keyword.lower()
    paths = list(all_paths)
    results: list[LootEntry] = []

    for idx, path in enumerate(paths):
        if "/R5BusinessRules/LootTables/Mobs/DA_LT_Mob_" not in path:
            continue
        if mob_keyword_lower not in path.lower():
            continue

        window = paths[max(0, idx - 2) : min(len(paths), idx + 3)]
        candidate_override = ""
        for candidate in window:
            if "/R5BusinessRules/LootTablesOverrides/Mobs/DA_ODL_Mob_" in candidate:
                candidate_override = candidate
                break

        results.append(
            LootEntry(
                loot_table=path,
                override_table=candidate_override,
                source_paths=window,
            )
        )

    # Deduplicate by loot table path
    unique: dict[str, LootEntry] = {}
    for item in results:
        unique[item.loot_table] = item
    return sorted(unique.values(), key=lambda x: x.loot_table.lower())


def cmd_init_project(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir)
    for rel in ("input", "output", "docs"):
        (project_dir / rel).mkdir(parents=True, exist_ok=True)

    manifest_path = project_dir / "docs" / "project_manifest.json"
    if not manifest_path.exists():
        manifest_path.write_text(
            json.dumps(
                {
                    "project_name": project_dir.name,
                    "created_utc": utc_now_iso(),
                    "notes": "Standardized Windrose modding project scaffold.",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    print(f"Initialized project layout at: {project_dir}")
    return 0


def cmd_search_paths(args: argparse.Namespace) -> int:
    paks_dir = Path(args.paks_dir)
    ucas_files = iter_ucas_files(paks_dir, args.ucas_file)
    contains = [c for c in args.contains]

    matches: dict[str, list[str]] = {}
    for ucas in ucas_files:
        with ucas.open("rb") as handle:
            mm = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                paths = sorted(extract_game_paths(mm))
            finally:
                mm.close()
        filtered = []
        for path in paths:
            if all(term.lower() in path.lower() for term in contains):
                filtered.append(path)
        if filtered:
            matches[str(ucas)] = filtered

    payload = {
        "generated_utc": utc_now_iso(),
        "paks_dir": str(paks_dir),
        "contains": contains,
        "match_file_count": len(matches),
        "matches": matches,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote search output: {out_path}")
    return 0


def cmd_loot_manifest(args: argparse.Namespace) -> int:
    paks_dir = Path(args.paks_dir)
    mob_keyword = args.mob_keyword
    ucas_files = iter_ucas_files(paks_dir, args.ucas_file)

    per_file_count: dict[str, int] = {}
    lt_all: set[str] = set()
    odl_all: set[str] = set()
    for ucas in ucas_files:
        lt_hits, odl_hits = extract_targeted_mob_tables_from_file(ucas, mob_keyword)
        lt_all |= lt_hits
        odl_all |= odl_hits
        per_file_count[str(ucas)] = len(lt_hits) + len(odl_hits)

    odl_by_key = {mob_key_from_odl(x): x for x in sorted(odl_all)}
    correlated = []
    for lt in sorted(lt_all):
        key = mob_key_from_lt(lt)
        correlated.append(
            LootEntry(
                loot_table=lt,
                override_table=odl_by_key.get(key, ""),
                source_paths=[],
            )
        )

    payload = {
        "generated_utc": utc_now_iso(),
        "mob_keyword": mob_keyword,
        "paks_dir": str(paks_dir),
        "ucas_files_scanned": [str(p) for p in ucas_files],
        "path_counts_by_file": per_file_count,
        "loot_targets": [
            {
                "loot_table": item.loot_table,
                "override_table": item.override_table,
                "context_window": item.source_paths,
            }
            for item in correlated
        ],
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote loot manifest: {out_path}")
    return 0


def resolve_tool(name: str, explicit_path: str | None = None) -> Path:
    if explicit_path:
        p = Path(explicit_path)
        if not p.exists():
            raise FileNotFoundError(f"Tool not found: {p}")
        return p
    candidate = bin_dir() / name
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Could not resolve '{name}'. Put it in '{bin_dir()}' or pass an explicit tool path."
    )


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    completed = subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(cmd)}")


def run_cmd_capture(cmd: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(cmd)}\n{completed.stderr}"
        )
    return completed.stdout


def run_shell_command(command: str, cwd: Path | None = None) -> None:
    completed = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False, shell=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Shell command failed ({completed.returncode}): {command}")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def token_values() -> dict[str, str]:
    return {
        "<REPO_ROOT>": str(workspace_root()),
        "<WORKSPACE_ROOT>": str(workspace_root()),
        "<MODDING_TOOLS_ROOT>": str(repo_root()),
        "<WINDROSE_MODS_DIR>": os.environ.get("WINDROSE_MODS_DIR", str(DEFAULT_GAME_MODS_DIR)),
        "<WINDROSE_PAKS_DIR>": os.environ.get("WINDROSE_PAKS_DIR", ""),
    }


def resolve_config_string(raw: str, config_path: Path, field_name: str) -> str:
    value = raw
    for token, replacement in token_values().items():
        if token in value:
            if replacement == "":
                raise ValueError(
                    f"Config field '{field_name}' uses {token} but corresponding environment value is not set."
                )
            value = value.replace(token, replacement)
    value = os.path.expandvars(value)
    return value


def resolve_config_path(raw: str, config_path: Path, field_name: str) -> Path:
    value = resolve_config_string(raw, config_path, field_name)
    path = Path(value)
    if not path.is_absolute():
        path = (config_path.parent / path).resolve()
    return path


def slugify_mod_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def pak_name_from_mod_name(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name)
    return "".join(p[:1].upper() + p[1:] for p in parts)


def apply_template_tokens(raw: str, tokens: dict[str, str]) -> str:
    value = raw
    for token, replacement in tokens.items():
        value = value.replace(token, replacement)
    return value


def scaffold_mod_from_template(template_dir: Path, target_dir: Path, tokens: dict[str, str]) -> None:
    if not template_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    for src in sorted(template_dir.rglob("*")):
        rel = src.relative_to(template_dir)
        rel_text = apply_template_tokens(rel.as_posix(), tokens)
        dst = target_dir / Path(rel_text)

        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            copy_file(src, dst)
            continue
        dst.write_text(apply_template_tokens(text, tokens), encoding="utf-8")


def cmd_tools_info(args: argparse.Namespace) -> int:
    names = ["repak.exe", "u4pak.exe", "retoc.exe"]
    payload: dict[str, str] = {}
    for name in names:
        p = bin_dir() / name
        payload[name] = str(p) if p.exists() else ""
    print(json.dumps(payload, indent=2))
    return 0


def cmd_init_mod(args: argparse.Namespace) -> int:
    name = args.name.strip()
    if not name:
        raise ValueError("Mod name is required.")

    slug = args.slug.strip() if args.slug else slugify_mod_name(name)
    if not slug:
        raise ValueError("Unable to derive slug from mod name; pass --slug explicitly.")
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise ValueError("Slug must contain only lowercase letters, numbers, and dashes.")

    pak_name = pak_name_from_mod_name(name)
    if not pak_name:
        raise ValueError("Unable to derive pak name from mod name.")

    mods_root = Path(args.mods_root)
    target_dir = mods_root / slug
    template_dir = workspace_root() / "mods" / "new-mod-template"

    if target_dir.exists() and any(target_dir.iterdir()) and not args.force:
        raise FileExistsError(
            f"Target mod directory already exists and is not empty: {target_dir}. "
            "Use --force to overwrite files."
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    tokens = {
        "__MOD_NAME__": name,
        "__MOD_SLUG__": slug,
        "__MOD_PAK_NAME__": pak_name,
    }
    scaffold_mod_from_template(template_dir, target_dir, tokens)

    build_config_path = target_dir / "docs" / "build_config.json"
    if not build_config_path.exists():
        write_json(
            build_config_path,
            {
                "name": pak_name,
                "input_dir": f"<REPO_ROOT>\\mods\\{slug}\\input\\staged",
                "output_pak": f"<REPO_ROOT>\\mods\\{slug}\\output\\{pak_name}_P.pak",
                "mods_dir": "<WINDROSE_MODS_DIR>",
                "mount_point": "../../../",
                "version": "V11",
                "compression": "",
                "backup_dir": f"<REPO_ROOT>\\mods\\{slug}\\output\\mods_backups",
            },
        )

    print(f"Initialized mod scaffold at: {target_dir}")
    print(f"Slug: {slug}")
    print(f"Pak name: {pak_name}")
    return 0


def cmd_pack_pak(args: argparse.Namespace) -> int:
    repak = resolve_tool("repak.exe", args.repak_path)
    input_dir = Path(args.input_dir)
    output_pak = Path(args.output_pak)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    output_pak.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(repak),
        "pack",
        "--mount-point",
        args.mount_point,
        "--version",
        args.version,
    ]
    if args.compression:
        cmd.extend(["--compression", args.compression])
    cmd.extend([str(input_dir), str(output_pak)])
    run_cmd(cmd)

    if args.install_to_mods:
        mods_dir = Path(args.install_to_mods)
        mods_dir.mkdir(parents=True, exist_ok=True)
        target = mods_dir / output_pak.name
        target.write_bytes(output_pak.read_bytes())
        print(f"Installed pak to: {target}")

    print(f"Packed mod pak: {output_pak}")
    return 0


def cmd_unpack_iostore(args: argparse.Namespace) -> int:
    retoc = resolve_tool("retoc.exe", args.retoc_path)
    utoc = Path(args.utoc)
    output_dir = Path(args.output_dir)
    if not utoc.exists():
        raise FileNotFoundError(f".utoc not found: {utoc}")
    output_dir.mkdir(parents=True, exist_ok=True)
    run_cmd([str(retoc), "unpack", str(utoc), str(output_dir)])
    print(f"Unpacked IoStore to: {output_dir}")
    return 0


def cmd_setup_boar_template(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir)
    staged = project_dir / "input" / "staged"
    docs = project_dir / "docs"
    output = project_dir / "output"
    for folder in (staged, docs, output):
        folder.mkdir(parents=True, exist_ok=True)

    # Staged directory skeleton where cooked replacement assets should be placed.
    for rel in (
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss",
        "R5/Plugins/R5BusinessRules/Content/LootTablesOverrides/Mobs",
        "R5BusinessRules/LootTables/Mobs",
        "R5BusinessRules/LootTables/Mobs/Rss",
        "R5BusinessRules/LootTablesOverrides/Mobs",
        "Game/R5BusinessRules/LootTables/Mobs",
        "Game/R5BusinessRules/LootTablesOverrides/Mobs",
    ):
        (staged / rel).mkdir(parents=True, exist_ok=True)

    requirements = {
        "created_utc": utc_now_iso(),
        "required_assets": [
            "/R5BusinessRules/LootTables/Mobs/DA_LT_Mob_Boar_Final",
            "/R5BusinessRules/LootTablesOverrides/Mobs/DA_ODL_Mob_Boar",
            "/R5BusinessRules/LootTables/Mobs/DA_LT_Mob_BoarF_Final",
            "/R5BusinessRules/LootTablesOverrides/Mobs/DA_ODL_Mob_BoarF",
            "/R5BusinessRules/LootTables/Mobs/DA_LT_Mob_BoarMega_Final",
            "/R5BusinessRules/LootTablesOverrides/Mobs/DA_ODL_Mob_BoarMega",
            "/R5BusinessRules/LootTables/Mobs/Rss/DA_LT_Mob_Boar_Leather",
            "/R5BusinessRules/LootTables/Mobs/Rss/DA_LT_Mob_BoarMega_Leather",
        ],
        "notes": [
            "Place cooked replacement assets in input/staged preserving mount-relative layout.",
            "For plugin-origin assets under R5/Plugins/R5BusinessRules/Content, stage files under input/staged/R5/Plugins/R5BusinessRules/Content/...",
            "If an object path starts with /R5BusinessRules, this usually maps to plugin content under R5/Plugins/R5BusinessRules/Content/...",
            "For paths starting with /Game, stage files under input/staged/Game/...",
            "Do not place placeholders in staged when building final mod.",
        ],
    }
    write_json(docs / "boar_required_assets.json", requirements)

    build_config = {
        "created_utc": utc_now_iso(),
        "name": "BoarLoot",
        "input_dir": str(staged),
        "output_pak": str(output / "BoarLoot_P.pak"),
        "mods_dir": str(DEFAULT_GAME_MODS_DIR),
        "mount_point": "../../../",
        "version": "V11",
        "compression": "",
        "backup_dir": str(project_dir / "output" / "mods_backups"),
    }
    write_json(docs / "build_config.json", build_config)

    readme_path = docs / "staging_instructions.txt"
    if not readme_path.exists():
        readme_path.write_text(
            "\n".join(
                [
                    "boar-loot staging instructions",
                    "",
                    "1) Put edited cooked assets into input/staged following /Game/... paths.",
                    "2) Confirm staged files are real cooked assets (.uasset/.uexp/etc), not notes.",
                    "3) Run build-install command using docs/build_config.json.",
                ]
            ),
            encoding="utf-8",
        )

    print(f"Boar template ready in: {project_dir}")
    return 0


def cmd_backup_mods(args: argparse.Namespace) -> int:
    mods_dir = Path(args.mods_dir)
    backup_root = Path(args.backup_dir)
    if not mods_dir.exists():
        raise FileNotFoundError(f"Mods dir not found: {mods_dir}")
    backup_root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_root / f"mods_backup_{stamp}"
    target.mkdir(parents=True, exist_ok=False)

    copied = 0
    for item in mods_dir.iterdir():
        dst = target / item.name
        if item.is_file():
            copy_file(item, dst)
            copied += 1
        elif item.is_dir():
            shutil.copytree(item, dst)
            copied += 1

    print(f"Backed up {copied} entries to: {target}")
    return 0


def cmd_restore_mods(args: argparse.Namespace) -> int:
    mods_dir = Path(args.mods_dir)
    backup_dir = Path(args.backup_dir)
    if not backup_dir.exists():
        raise FileNotFoundError(f"Backup dir not found: {backup_dir}")
    mods_dir.mkdir(parents=True, exist_ok=True)

    if args.clear_existing:
        for item in mods_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    restored = 0
    for item in backup_dir.iterdir():
        dst = mods_dir / item.name
        if item.is_file():
            copy_file(item, dst)
            restored += 1
        elif item.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(item, dst)
            restored += 1

    print(f"Restored {restored} entries from: {backup_dir}")
    return 0


def cmd_build_install(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    input_dir = resolve_config_path(config["input_dir"], config_path, "input_dir")
    output_pak = resolve_config_path(config["output_pak"], config_path, "output_pak")
    if "mods_dir" in config:
        mods_dir = resolve_config_path(config["mods_dir"], config_path, "mods_dir")
    else:
        mods_dir = DEFAULT_GAME_MODS_DIR
    mount_point = resolve_config_string(str(config.get("mount_point", "../../../")), config_path, "mount_point")
    version = resolve_config_string(str(config.get("version", "V11")), config_path, "version")
    compression = resolve_config_string(str(config.get("compression", "")), config_path, "compression")

    if args.backup_first:
        if "backup_dir" in config:
            backup_root = resolve_config_path(config["backup_dir"], config_path, "backup_dir")
        else:
            backup_root = output_pak.parent / "mods_backups"
        backup_args = argparse.Namespace(mods_dir=str(mods_dir), backup_dir=str(backup_root))
        cmd_backup_mods(backup_args)

    pack_args = argparse.Namespace(
        input_dir=str(input_dir),
        output_pak=str(output_pak),
        mount_point=mount_point,
        version=version,
        compression=compression,
        install_to_mods=str(mods_dir),
        repak_path=args.repak_path or "",
    )
    cmd_pack_pak(pack_args)
    return 0


def parse_multipliers(raw: str) -> list[float]:
    values: list[float] = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        value = float(token)
        if value <= 0:
            raise ValueError("Multipliers must be > 0.")
        values.append(value)
    if not values:
        raise ValueError("At least one multiplier is required.")
    return values


def multiplier_label(multiplier: float) -> str:
    if float(int(multiplier)) == float(multiplier):
        return str(int(multiplier))
    text = f"{multiplier:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", "p")


def run_prepare_template(
    template: str,
    multiplier: float,
    project_dir: Path,
    variant_staged_dir: Path,
    variant_output_pak: Path,
) -> None:
    project_dir_str = str(project_dir)
    variant_staged_dir_str = str(variant_staged_dir)
    variant_output_pak_str = str(variant_output_pak)
    command = template.format(
        multiplier=multiplier,
        multiplier_label=multiplier_label(multiplier),
        project_dir=project_dir_str,
        variant_staged_dir=variant_staged_dir_str,
        variant_output_pak=variant_output_pak_str,
        project_dir_quoted=f'"{project_dir_str}"',
        variant_staged_dir_quoted=f'"{variant_staged_dir_str}"',
        variant_output_pak_quoted=f'"{variant_output_pak_str}"',
    )
    run_shell_command(command, cwd=workspace_root())


def clear_matching_paks(mods_dir: Path, stem_prefix: str) -> int:
    if not mods_dir.exists():
        return 0
    removed = 0
    for path in mods_dir.glob(f"{stem_prefix}*.pak"):
        if path.is_file():
            path.unlink()
            removed += 1
    return removed


def cmd_build_variants(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    input_dir = resolve_config_path(config["input_dir"], config_path, "input_dir")
    output_pak = resolve_config_path(config["output_pak"], config_path, "output_pak")
    if "mods_dir" in config:
        mods_dir = resolve_config_path(config["mods_dir"], config_path, "mods_dir")
    else:
        mods_dir = DEFAULT_GAME_MODS_DIR
    if "backup_dir" in config:
        backup_root = resolve_config_path(config["backup_dir"], config_path, "backup_dir")
    else:
        backup_root = output_pak.parent / "mods_backups"

    project_dir = Path(args.project_dir) if args.project_dir else input_dir.parent.parent
    multipliers = parse_multipliers(args.multipliers)
    install_multiplier_labels = {multiplier_label(x) for x in parse_multipliers(args.install_multipliers)} if args.install_multipliers else set()
    mount_point = resolve_config_string(str(config.get("mount_point", "../../../")), config_path, "mount_point")
    version = resolve_config_string(str(config.get("version", "V11")), config_path, "version")
    compression = resolve_config_string(str(config.get("compression", "")), config_path, "compression")
    generated_root = Path(args.generated_root) if args.generated_root else (output_pak.parent / "generated")

    has_safe_placeholder = ("{variant_staged_dir}" in args.prepare_command_template) or (
        "{variant_staged_dir_quoted}" in args.prepare_command_template
    )
    if args.prepare_command_template and not has_safe_placeholder and not args.allow_unsafe_prepare_template:
        raise ValueError(
            "prepare-command-template must include {variant_staged_dir} or {variant_staged_dir_quoted} "
            "for safe variant generation. "
            "Use --allow-unsafe-prepare-template to bypass."
        )

    report: dict[str, object] = {
        "generated_utc": utc_now_iso(),
        "config": str(config_path),
        "project_dir": str(project_dir),
        "generated_root": str(generated_root),
        "multipliers": multipliers,
        "variants": [],
    }

    backup_done = False
    for mult in multipliers:
        label = multiplier_label(mult)
        variant_staged_dir = generated_root / f"x{label}" / "staged"
        if variant_staged_dir.exists():
            shutil.rmtree(variant_staged_dir)
        shutil.copytree(input_dir, variant_staged_dir)
        variant_output = output_pak.with_name(f"{output_pak.stem}_x{label}{output_pak.suffix}")

        if args.prepare_command_template:
            run_prepare_template(
                args.prepare_command_template,
                mult,
                project_dir,
                variant_staged_dir,
                variant_output,
            )

        should_install = label in install_multiplier_labels
        if should_install and args.backup_first and not backup_done:
            cmd_backup_mods(argparse.Namespace(mods_dir=str(mods_dir), backup_dir=str(backup_root)))
            backup_done = True
        if should_install:
            removed = clear_matching_paks(mods_dir, output_pak.stem)
            if removed:
                print(f"Removed {removed} existing variant pak(s) from mods dir")

        pack_args = argparse.Namespace(
            input_dir=str(variant_staged_dir),
            output_pak=str(variant_output),
            mount_point=mount_point,
            version=version,
            compression=compression,
            install_to_mods=str(mods_dir) if should_install else "",
            repak_path=args.repak_path or "",
        )
        cmd_pack_pak(pack_args)
        report["variants"].append(
            {
                "multiplier": mult,
                "label": label,
                "variant_staged_dir": str(variant_staged_dir),
                "output_pak": str(variant_output),
                "installed": should_install,
            }
        )

    report_path = Path(args.report_path) if args.report_path else (output_pak.parent / "variant_build_report.json")
    write_json(report_path, report)
    print(f"Wrote variant build report: {report_path}")
    return 0


def scale_value(value: int, multiplier: float) -> int:
    if value <= 0:
        return 0
    return max(1, int(round(value * multiplier)))


def parse_resource_types(raw: str) -> set[str]:
    values = {part.strip().lower() for part in raw.split(",") if part.strip()}
    if not values:
        raise ValueError("At least one resource type is required.")
    invalid = sorted(values - SUPPORTED_BOAR_RESOURCE_TYPES)
    if invalid:
        valid = ", ".join(sorted(SUPPORTED_BOAR_RESOURCE_TYPES))
        raise ValueError(f"Unsupported boar resource type(s): {', '.join(invalid)}. Valid: {valid}")
    return values


def cmd_prepare_boar_hide_json_mod(args: argparse.Namespace) -> int:
    repak = resolve_tool("repak.exe", args.repak_path)
    aes_key = args.aes_key or os.environ.get("WINDROSE_AES_KEY", "").strip()
    if not aes_key:
        raise ValueError("AES key is required. Pass --aes-key or set WINDROSE_AES_KEY.")
    target_resource_types = parse_resource_types(args.resource_types)
    pak_path_input = Path(args.pak_path)
    if pak_path_input.is_absolute():
        pak_path = pak_path_input
    else:
        paks_dir_env = os.environ.get("WINDROSE_PAKS_DIR", "").strip()
        if paks_dir_env:
            pak_path = Path(paks_dir_env) / pak_path_input
        else:
            pak_path = (Path.cwd() / pak_path_input).resolve()
    project_dir = Path(args.project_dir)
    staged_root = Path(args.staged_root) if args.staged_root else (project_dir / "input" / "staged")
    report_path = project_dir / "docs" / "boar_hide_edit_report.json"

    if not pak_path.exists():
        raise FileNotFoundError(f"Pak not found: {pak_path}")
    staged_root.mkdir(parents=True, exist_ok=True)

    list_out = run_cmd_capture([str(repak), "--aes-key", aes_key, "list", str(pak_path)])
    candidates = []
    for line in list_out.splitlines():
        path = line.strip()
        match = BOAR_RSS_JSON_PATTERN.match(path)
        if not match:
            continue
        resource = match.group("resource").lower()
        if resource in target_resource_types:
            candidates.append(path)

    if not candidates:
        raise RuntimeError("No matching boar resource JSON entries found in pak.")

    edited = []
    for path in sorted(set(candidates)):
        raw = run_cmd_capture([str(repak), "--aes-key", aes_key, "get", str(pak_path), path])
        data = json.loads(raw)
        loot_data = data.get("LootData", [])
        file_edits = []
        for item in loot_data:
            if not isinstance(item, dict):
                continue
            if "Min" not in item or "Max" not in item:
                continue
            old_min = int(item["Min"])
            old_max = int(item["Max"])
            new_min = scale_value(old_min, args.multiplier)
            new_max = scale_value(old_max, args.multiplier)
            item["Min"] = new_min
            item["Max"] = new_max
            file_edits.append(
                {
                    "old_min": old_min,
                    "old_max": old_max,
                    "new_min": new_min,
                    "new_max": new_max,
                }
            )

        out_file = staged_root / Path(path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        edited.append(
            {
                "path": path,
                "output_file": str(out_file),
                "edits": file_edits,
            }
        )

    report = {
        "generated_utc": utc_now_iso(),
        "pak_path": str(pak_path),
        "multiplier": args.multiplier,
        "resource_types": sorted(target_resource_types),
        "edited_file_count": len(edited),
        "edited_files": edited,
    }
    write_json(report_path, report)
    print(f"Prepared boar hide JSON overrides in: {staged_root}")
    print(f"Wrote report: {report_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windrose reusable modding CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-project", help="Create standard mod project folders")
    p_init.add_argument("--project-dir", required=True, help="Path to project root folder")
    p_init.set_defaults(func=cmd_init_project)

    p_init_mod = sub.add_parser("init-mod", help="Create a new mod from template scaffold")
    p_init_mod.add_argument("--name", required=True, help="Mod display name, example: Better Boar Loot")
    p_init_mod.add_argument("--slug", default="", help="Optional folder slug, example: better-boar-loot")
    p_init_mod.add_argument(
        "--mods-root",
        default=str(workspace_root() / "mods"),
        help="Directory containing all mod folders",
    )
    p_init_mod.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into an existing non-empty target directory",
    )
    p_init_mod.set_defaults(func=cmd_init_mod)

    p_search = sub.add_parser("search-paths", help="Search Unreal object paths by substrings")
    p_search.add_argument("--paks-dir", required=True, help="Path containing .ucas files")
    p_search.add_argument(
        "--ucas-file",
        action="append",
        default=[],
        help="Specific .ucas filename(s) to scan; can be repeated. Default: pakchunk0_s3-Windows.ucas if present.",
    )
    p_search.add_argument(
        "--contains",
        action="append",
        default=[],
        required=True,
        help="Substring filter; can be repeated",
    )
    p_search.add_argument("--output", required=True, help="Output JSON path")
    p_search.set_defaults(func=cmd_search_paths)

    p_manifest = sub.add_parser("loot-manifest", help="Generate loot table candidates for a mob keyword")
    p_manifest.add_argument("--paks-dir", required=True, help="Path containing .ucas files")
    p_manifest.add_argument(
        "--ucas-file",
        action="append",
        default=[],
        help="Specific .ucas filename(s) to scan; can be repeated. Default: pakchunk0_s3-Windows.ucas if present.",
    )
    p_manifest.add_argument("--mob-keyword", required=True, help="Example: Boar, Wolf, Goat")
    p_manifest.add_argument("--output", required=True, help="Output JSON path")
    p_manifest.set_defaults(func=cmd_loot_manifest)

    p_tools = sub.add_parser("tools-info", help="Show installed toolkit executable paths")
    p_tools.set_defaults(func=cmd_tools_info)

    p_pack = sub.add_parser("pack-pak", help="Pack a staged folder into a .pak mod with repak")
    p_pack.add_argument("--input-dir", required=True, help="Folder containing staged mod files")
    p_pack.add_argument("--output-pak", required=True, help="Output .pak path")
    p_pack.add_argument("--mount-point", default="../../../", help="Pak mount point")
    p_pack.add_argument(
        "--version",
        default="V11",
        help="Pak version for repak. Common modern choices are V9-V11.",
    )
    p_pack.add_argument(
        "--compression",
        default="",
        help="Optional compression: Zlib, Gzip, Oodle, Zstd, LZ4",
    )
    p_pack.add_argument(
        "--install-to-mods",
        default="",
        help="Optional target folder to copy built pak into (ex: Windrose ...\\Paks\\~mods)",
    )
    p_pack.add_argument("--repak-path", default="", help="Optional explicit repak.exe path")
    p_pack.set_defaults(func=cmd_pack_pak)

    p_unpack_io = sub.add_parser("unpack-iostore", help="Unpack .utoc/.ucas with retoc")
    p_unpack_io.add_argument("--utoc", required=True, help="Path to input .utoc file")
    p_unpack_io.add_argument("--output-dir", required=True, help="Directory for extracted output")
    p_unpack_io.add_argument("--retoc-path", default="", help="Optional explicit retoc.exe path")
    p_unpack_io.set_defaults(func=cmd_unpack_iostore)

    p_boar_template = sub.add_parser(
        "setup-boar-template",
        help="Create boar project template + build config",
    )
    p_boar_template.add_argument("--project-dir", required=True, help="Boar project root folder")
    p_boar_template.set_defaults(func=cmd_setup_boar_template)

    p_backup = sub.add_parser("backup-mods", help="Backup all files from mods directory")
    p_backup.add_argument(
        "--mods-dir",
        default=str(DEFAULT_GAME_MODS_DIR),
        help="Mods folder to back up",
    )
    p_backup.add_argument("--backup-dir", required=True, help="Backup destination root")
    p_backup.set_defaults(func=cmd_backup_mods)

    p_restore = sub.add_parser("restore-mods", help="Restore mods from a backup folder")
    p_restore.add_argument(
        "--mods-dir",
        default=str(DEFAULT_GAME_MODS_DIR),
        help="Mods folder to restore into",
    )
    p_restore.add_argument("--backup-dir", required=True, help="Specific backup folder to restore")
    p_restore.add_argument(
        "--clear-existing",
        action="store_true",
        help="Delete existing mods dir contents before restoring",
    )
    p_restore.set_defaults(func=cmd_restore_mods)

    p_build_install = sub.add_parser(
        "build-install",
        help="Build pak from config and install to mods folder",
    )
    p_build_install.add_argument(
        "--config",
        required=True,
        help="Path to build_config.json",
    )
    p_build_install.add_argument(
        "--backup-first",
        action="store_true",
        help="Backup current mods folder before installing",
    )
    p_build_install.add_argument("--repak-path", default="", help="Optional explicit repak.exe path")
    p_build_install.set_defaults(func=cmd_build_install)

    p_build_variants = sub.add_parser(
        "build-variants",
        help="Build multiple multiplier variants from one build config",
    )
    p_build_variants.add_argument("--config", required=True, help="Path to build_config.json")
    p_build_variants.add_argument(
        "--multipliers",
        required=True,
        help="Comma-separated multipliers to build, example: 2,3,5,10",
    )
    p_build_variants.add_argument(
        "--prepare-command-template",
        default="",
        help=(
            "Optional shell command run before each variant build. Supports {multiplier}, "
            "{multiplier_label}, {project_dir}, {variant_staged_dir}, {variant_output_pak}, plus *_quoted variants."
        ),
    )
    p_build_variants.add_argument(
        "--project-dir",
        default="",
        help="Optional project directory for prepare template. Defaults to input_dir/../..",
    )
    p_build_variants.add_argument(
        "--install-multipliers",
        default="",
        help="Optional comma-separated multipliers to copy into mods_dir after build",
    )
    p_build_variants.add_argument(
        "--backup-first",
        action="store_true",
        help="Backup mods folder once before first installed variant",
    )
    p_build_variants.add_argument(
        "--report-path",
        default="",
        help="Optional output path for variant build report JSON",
    )
    p_build_variants.add_argument(
        "--generated-root",
        default="",
        help="Optional directory for generated per-variant staged folders (default: <output>/generated)",
    )
    p_build_variants.add_argument(
        "--allow-unsafe-prepare-template",
        action="store_true",
        help="Allow prepare template without {variant_staged_dir}; not recommended.",
    )
    p_build_variants.add_argument("--repak-path", default="", help="Optional explicit repak.exe path")
    p_build_variants.set_defaults(func=cmd_build_variants)

    p_prepare_json = sub.add_parser(
        "prepare-boar-hide-json-mod",
        help="Extract boar leather JSON loot tables from pak and scale Min/Max values",
    )
    p_prepare_json.add_argument(
        "--aes-key",
        default="",
        help="AES key (hex or base64). Optional if WINDROSE_AES_KEY is set.",
    )
    p_prepare_json.add_argument(
        "--pak-path",
        default="pakchunk0-Windows.pak",
        help="Pak file containing boar loot JSON entries. If relative, resolves via WINDROSE_PAKS_DIR.",
    )
    p_prepare_json.add_argument(
        "--project-dir",
        default=str(workspace_root() / "mods" / "boar-loot"),
        help="Mod project directory root",
    )
    p_prepare_json.add_argument(
        "--staged-root",
        default="",
        help="Optional explicit staged output root. Defaults to <project_dir>/input/staged",
    )
    p_prepare_json.add_argument(
        "--multiplier",
        type=float,
        default=2.0,
        help="Scale factor for Min/Max hide quantities (default: 2.0)",
    )
    p_prepare_json.add_argument(
        "--resource-types",
        default="leather",
        help="Comma-separated boar resources to scale: leather, meat, fat, tusk, boarhead",
    )
    p_prepare_json.add_argument("--repak-path", default="", help="Optional explicit repak.exe path")
    p_prepare_json.set_defaults(func=cmd_prepare_boar_hide_json_mod)

    return parser


def main() -> int:
    load_local_env()
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
