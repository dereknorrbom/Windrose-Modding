from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import pytest


def _load_cli_module():
    cli_path = Path(__file__).resolve().parents[1] / "windrose_mod_cli.py"
    spec = importlib.util.spec_from_file_location("windrose_mod_cli_test_module", cli_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cli = _load_cli_module()


def test_scale_value_rounding_and_floor():
    assert cli.scale_value(0, 3.0) == 0
    assert cli.scale_value(1, 0.1) == 1
    assert cli.scale_value(2, 1.5) == 3
    assert cli.scale_value(5, 3.0) == 15


def test_parse_resource_types_accepts_csv_and_rejects_invalid():
    assert cli.parse_resource_types("leather, meat") == {"leather", "meat"}
    with pytest.raises(ValueError):
        cli.parse_resource_types("leather,unknown")


def test_parse_multipliers_and_labels():
    assert cli.parse_multipliers("2,3,5,10") == [2.0, 3.0, 5.0, 10.0]
    assert cli.multiplier_label(2.0) == "2"
    assert cli.multiplier_label(2.5) == "2p5"
    with pytest.raises(ValueError):
        cli.parse_multipliers("0")


def test_clear_matching_paks_removes_only_matching_files(tmp_path: Path):
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir()
    (mods_dir / "BoarLoot_P.pak").write_bytes(b"x")
    (mods_dir / "BoarLoot_P_x3.pak").write_bytes(b"x")
    (mods_dir / "OtherMod.pak").write_bytes(b"x")
    removed = cli.clear_matching_paks(mods_dir, "BoarLoot_P")
    assert removed == 2
    assert not (mods_dir / "BoarLoot_P.pak").exists()
    assert not (mods_dir / "BoarLoot_P_x3.pak").exists()
    assert (mods_dir / "OtherMod.pak").exists()


def test_cmd_pack_pak_filters_scaffold_placeholders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    input_dir = tmp_path / "staged"
    asset_dir = input_dir / "R5" / "Plugins" / "R5BusinessRules" / "Content"
    asset_dir.mkdir(parents=True)
    (input_dir / ".gitkeep").write_text("", encoding="utf-8")
    (asset_dir / "DA_LT_Test.json").write_text("{}", encoding="utf-8")
    output_pak = tmp_path / "out" / "Test_P.pak"

    def fake_run_cmd(cmd):
        pack_input_dir = Path(cmd[-2])
        assert pack_input_dir != input_dir
        assert not (pack_input_dir / ".gitkeep").exists()
        assert (pack_input_dir / "R5" / "Plugins" / "R5BusinessRules" / "Content" / "DA_LT_Test.json").exists()
        output_pak.parent.mkdir(parents=True, exist_ok=True)
        output_pak.write_bytes(b"pak")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("repak.exe"))
    monkeypatch.setattr(cli, "run_cmd", fake_run_cmd)

    args = argparse.Namespace(
        input_dir=str(input_dir),
        output_pak=str(output_pak),
        mount_point="../../../",
        version="V11",
        compression="",
        install_to_mods="",
        repak_path="",
    )
    assert cli.cmd_pack_pak(args) == 0


def test_cue4parse_package_patterns_include_wildcard():
    patterns = cli.cue4parse_package_patterns("/Game/Gameplay/ItemsLogic/Consumables/CT_Alchemy_GE_Values")
    assert "/Game/Gameplay/ItemsLogic/Consumables/CT_Alchemy_GE_Values" in patterns
    assert "Game/Gameplay/ItemsLogic/Consumables/CT_Alchemy_GE_Values.uasset" in patterns
    assert "*CT_Alchemy_GE_Values*" in patterns


def test_cmd_inspect_cooked_asset_exports_json_with_mappings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from windrose_cli.tools import cue4parse
    from windrose_cli.tools.process import ProcessResult

    paks_dir = tmp_path / "Paks"
    paks_dir.mkdir()
    mappings = tmp_path / "Windrose.usmap"
    mappings.write_bytes(b"usmap")
    output = tmp_path / "inspection.json"
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, cwd=None, check=True, redacted_cmd=None):
        captured["cmd"] = cmd
        captured["redacted_cmd"] = redacted_cmd
        export_dir = Path(cmd[cmd.index("--output") + 1])
        asset_json = export_dir / "R5" / "Content" / "Gameplay" / "ItemsLogic" / "Consumables" / "CT_Alchemy_GE_Values.json"
        asset_json.parent.mkdir(parents=True, exist_ok=True)
        asset_json.write_text(
            json.dumps(
                [
                    {
                        "Type": "CurveTable",
                        "Rows": {
                            "Alchemy_Bandages_T01_Duration": {"Keys": [{"Time": 1.0, "Value": 30.0}]}
                        },
                    }
                ]
            ),
            encoding="utf-8-sig",
        )
        return ProcessResult(0, "", "Processed 1 packages")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("cue4parse.exe"))
    monkeypatch.setattr(cue4parse, "run", fake_run)
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))
    monkeypatch.setenv("WINDROSE_AES_KEY", "0xsecret")
    monkeypatch.setenv("WINDROSE_USMAP_PATH", str(mappings))

    args = argparse.Namespace(
        asset_path="/Game/Gameplay/ItemsLogic/Consumables/CT_Alchemy_GE_Values",
        package_pattern=[],
        paks_dir="",
        aes_key="",
        mappings="",
        output=str(output),
        export_dir="",
        game_version="GAME_UE5_LATEST",
        format="json",
        raw_fallback=True,
        scan_text=[],
        no_include_data=False,
        verbose=False,
        cue4parse_path="",
    )
    assert cli.cmd_inspect_cooked_asset(args) == 0
    assert "--mappings" in captured["cmd"]
    assert "0xsecret" not in captured["redacted_cmd"]
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["mappings"] == str(mappings)
    assert report["exported_json_count"] == 1
    assert report["exports"][0]["data"][0]["Rows"]["Alchemy_Bandages_T01_Duration"]["Keys"][0]["Value"] == 30.0


def test_cmd_inspect_cooked_asset_raw_fallback_scans_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from windrose_cli.tools import cue4parse
    from windrose_cli.tools.process import ProcessResult

    paks_dir = tmp_path / "Paks"
    paks_dir.mkdir()
    output = tmp_path / "inspection.json"
    calls: list[str] = []

    def fake_run(cmd, cwd=None, check=True, redacted_cmd=None):
        export_format = cmd[cmd.index("--format") + 1]
        calls.append(export_format)
        if export_format == "json":
            return ProcessResult(1, "", "Could not load standard asset")
        export_dir = Path(cmd[cmd.index("--output") + 1])
        raw_asset = export_dir / "R5" / "Content" / "Gameplay" / "ItemsLogic" / "Consumables" / "CT_Alchemy_GE_Values.uasset"
        raw_asset.parent.mkdir(parents=True, exist_ok=True)
        raw_asset.write_bytes(b"\x00Alchemy_Bandages_T01_Duration\x00")
        return ProcessResult(0, "", "Processed 1 packages")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("cue4parse.exe"))
    monkeypatch.setattr(cue4parse, "run", fake_run)
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))
    monkeypatch.setenv("WINDROSE_AES_KEY", "0xsecret")

    args = argparse.Namespace(
        asset_path="/Game/Gameplay/ItemsLogic/Consumables/CT_Alchemy_GE_Values",
        package_pattern=[],
        paks_dir="",
        aes_key="",
        mappings="",
        output=str(output),
        export_dir="",
        game_version="GAME_UE5_LATEST",
        format="json",
        raw_fallback=True,
        scan_text=["Alchemy_Bandages_T01_Duration"],
        no_include_data=True,
        verbose=False,
        cue4parse_path="",
    )
    assert cli.cmd_inspect_cooked_asset(args) == 0
    assert calls == ["json", "raw"]
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["raw_fallback_used"] is True
    assert report["exports"][0]["string_hits"][0]["term"] == "Alchemy_Bandages_T01_Duration"


def test_patch_bandage_curve_asset_preserves_total_healing(tmp_path: Path):
    import struct

    source = tmp_path / "CT_Alchemy_GE_Values.uasset"
    output = tmp_path / "staged" / "CT_Alchemy_GE_Values.uasset"
    source.write_bytes(b"prefix" + struct.pack("<f", 15.0) + b"middle" + struct.pack("<f", 30.0) + b"suffix")

    edits = cli.patch_bandage_curve_asset(
        source,
        output,
        vanilla_duration=30.0,
        target_duration=15.0,
        vanilla_health_per_tick=15.0,
        target_health_per_tick=30.0,
    )

    patched = output.read_bytes()
    assert edits == [
        {"label": "Alchemy_Bandages_T01_Duration", "offset": 16, "old_value": 30.0, "new_value": 15.0},
        {"label": "Alchemy_Bandages_T01_HealthPerTick", "offset": 6, "old_value": 15.0, "new_value": 30.0},
    ]
    assert patched == b"prefix" + struct.pack("<f", 30.0) + b"middle" + struct.pack("<f", 15.0) + b"suffix"


def test_patch_bandage_curve_asset_rejects_ambiguous_values(tmp_path: Path):
    import struct

    source = tmp_path / "CT_Alchemy_GE_Values.uasset"
    output = tmp_path / "staged" / "CT_Alchemy_GE_Values.uasset"
    source.write_bytes(struct.pack("<f", 15.0) + struct.pack("<f", 15.0) + struct.pack("<f", 30.0))

    with pytest.raises(ValueError, match="Alchemy_Bandages_T01_HealthPerTick"):
        cli.patch_bandage_curve_asset(
            source,
            output,
            vanilla_duration=30.0,
            target_duration=15.0,
            vanilla_health_per_tick=15.0,
            target_health_per_tick=30.0,
        )


def test_cmd_prepare_bandage_speed_mod_extracts_split_asset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import struct

    project = tmp_path / "mods" / "fast-bandages"
    (project / "docs").mkdir(parents=True)
    paks_dir = tmp_path / "Paks"
    paks_dir.mkdir()

    def fake_extract(retoc_path, paks_dir_arg, output_dir, asset_filter, unreal_version):
        assert asset_filter == "CT_Alchemy_GE_Values"
        assert unreal_version == "UE5_6"
        asset_dir = output_dir / "R5" / "Content" / "Gameplay" / "ItemsLogic" / "Consumables"
        asset_dir.mkdir(parents=True)
        (asset_dir / "CT_Alchemy_GE_Values.uasset").write_bytes(b"asset")
        (asset_dir / "CT_Alchemy_GE_Values.uexp").write_bytes(
            b"prefix" + struct.pack("<f", 15.0) + b"middle" + struct.pack("<f", 30.0) + b"suffix"
        )

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("retoc.exe"))
    monkeypatch.setattr(cli, "extract_legacy_asset_with_retoc", fake_extract)
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))

    args = argparse.Namespace(
        project_dir=str(project),
        staged_root="",
        target_duration=15.0,
        vanilla_duration=30.0,
        vanilla_health_per_tick=15.0,
        target_health_per_tick=0.0,
        report_name="bandage_speed_edit_report",
        paks_dir="",
        unreal_version="UE5_6",
        retoc_path="",
    )
    assert cli.cmd_prepare_bandage_speed_mod(args) == 0

    staged = project / "input" / "staged" / "R5" / "Content" / "Gameplay" / "ItemsLogic" / "Consumables"
    assert (staged / "CT_Alchemy_GE_Values.uasset").read_bytes() == b"asset"
    patched = (staged / "CT_Alchemy_GE_Values.uexp").read_bytes()
    assert struct.pack("<f", 30.0) in patched
    assert struct.pack("<f", 15.0) in patched
    report = json.loads((project / "docs" / "bandage_speed_edit_report.json").read_text(encoding="utf-8"))
    assert report["target_duration"] == 15.0
    assert report["target_health_per_tick"] == 30.0
    assert report["output_uexp"].endswith("CT_Alchemy_GE_Values.uexp")


def test_cmd_pack_iostore_mod_packs_converts_and_installs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    input_dir = tmp_path / "staged"
    input_dir.mkdir()
    output_pak = tmp_path / "output" / "FastBandages_P.pak"
    install_dir = tmp_path / "install"
    pack_calls = []
    run_calls = []

    def fake_pack(ns):
        pack_calls.append(ns)
        out = Path(ns.output_pak)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"pak")
        return 0

    def fake_run(cmd, cwd=None):
        run_calls.append(cmd)
        Path(cmd[3]).write_bytes(b"utoc")
        Path(cmd[3]).with_suffix(".ucas").write_bytes(b"ucas")

    monkeypatch.setattr(cli, "cmd_pack_pak", fake_pack)
    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("retoc.exe"))
    monkeypatch.setattr(cli, "run_cmd", fake_run)

    args = argparse.Namespace(
        input_dir=str(input_dir),
        output_pak=str(output_pak),
        mount_point="../../../",
        pak_version="V11",
        iostore_version="UE5_6",
        compression="",
        install_to_mods=str(install_dir),
        repak_path="",
        retoc_path="",
    )
    assert cli.cmd_pack_iostore_mod(args) == 0
    assert len(pack_calls) == 1
    assert run_calls[0][1] == "to-zen"
    assert (install_dir / "FastBandages_P.pak").read_bytes() == b"pak"
    assert (install_dir / "FastBandages_P.ucas").read_bytes() == b"ucas"
    assert (install_dir / "FastBandages_P.utoc").read_bytes() == b"utoc"


def test_slug_and_pak_name_helpers():
    assert cli.slugify_mod_name("Better Boar Loot!!") == "better-boar-loot"
    assert cli.pak_name_from_mod_name("better boar loot") == "BetterBoarLoot"


def test_iter_ucas_files_prefers_s3_default(tmp_path: Path):
    paks = tmp_path / "paks"
    paks.mkdir()
    (paks / "pakchunk0_s3-Windows.ucas").write_text("x", encoding="utf-8")
    (paks / "pakchunk0-Windows.ucas").write_text("x", encoding="utf-8")
    result = cli.iter_ucas_files(paks)
    assert result == [paks / "pakchunk0_s3-Windows.ucas"]


def test_iter_ucas_files_include_filter(tmp_path: Path):
    paks = tmp_path / "paks"
    paks.mkdir()
    (paks / "a.ucas").write_text("x", encoding="utf-8")
    (paks / "b.ucas").write_text("x", encoding="utf-8")
    result = cli.iter_ucas_files(paks, include_files=["b.ucas", "missing.ucas"])
    assert result == [paks / "b.ucas"]


def test_load_local_env_from_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    local_dir = tmp_path / ".local"
    local_dir.mkdir()
    (local_dir / ".env").write_text(
        "\n".join(
            [
                "# comment",
                "TEST_KEY=hello",
                "QUOTED='abc def'",
                "EXISTING=from_file",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "workspace_root", lambda: tmp_path)
    monkeypatch.setenv("EXISTING", "from_env")

    cli.load_local_env()

    assert cli.os.environ["TEST_KEY"] == "hello"
    assert cli.os.environ["QUOTED"] == "abc def"
    # setdefault keeps existing env value
    assert cli.os.environ["EXISTING"] == "from_env"


def test_resolve_config_string_token_expansion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(cli, "workspace_root", lambda: tmp_path)
    monkeypatch.setattr(cli, "repo_root", lambda: tmp_path / "modding_tools")
    monkeypatch.setenv("WINDROSE_MODS_DIR", r"C:\Mods")
    monkeypatch.setenv("CUSTOM_NAME", "abc")

    raw = r"<REPO_ROOT>\mods\${CUSTOM_NAME}\out"
    resolved = cli.resolve_config_string(raw, tmp_path / "cfg.json", "output_pak")
    assert resolved.endswith(r"mods\abc\out")
    assert str(tmp_path) in resolved


def test_resolve_config_string_missing_required_env_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("WINDROSE_PAKS_DIR", raising=False)
    with pytest.raises(ValueError):
        cli.resolve_config_string("<WINDROSE_PAKS_DIR>\\x", tmp_path / "cfg.json", "paks")


def test_resolve_config_path_relative_to_config_file(tmp_path: Path):
    cfg = tmp_path / "cfg" / "build.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("{}", encoding="utf-8")
    resolved = cli.resolve_config_path(r".\output\file.pak", cfg, "output_pak")
    assert resolved == (cfg.parent / r".\output\file.pak").resolve()


def test_cmd_setup_boar_template_creates_structure(tmp_path: Path):
    project = tmp_path / "boar-loot"
    args = argparse.Namespace(project_dir=str(project))
    exit_code = cli.cmd_setup_boar_template(args)
    assert exit_code == 0
    assert (project / "input" / "staged" / "R5" / "Plugins" / "R5BusinessRules" / "Content").exists()
    assert (project / "docs" / "build_config.json").exists()
    assert (project / "docs" / "boar_required_assets.json").exists()


def test_cmd_init_mod_scaffolds_template_and_replaces_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = tmp_path / "repo"
    template = workspace / "mods" / "new-mod-template"
    (template / "docs").mkdir(parents=True)
    (template / "scripts").mkdir(parents=True)
    (template / "__MOD_SLUG___notes").mkdir(parents=True)
    (template / "README.md").write_text("name=__MOD_NAME__", encoding="utf-8")
    (template / "scripts" / "build_install.ps1").write_text("slug=__MOD_SLUG__", encoding="utf-8")
    (template / "__MOD_SLUG___notes" / "info.txt").write_text("pak=__MOD_PAK_NAME__", encoding="utf-8")

    monkeypatch.setattr(cli, "workspace_root", lambda: workspace)

    args = argparse.Namespace(
        name="Starter Mod",
        slug="",
        mods_root=str(workspace / "mods"),
        force=False,
    )
    assert cli.cmd_init_mod(args) == 0

    mod_dir = workspace / "mods" / "starter-mod"
    assert (mod_dir / "README.md").read_text(encoding="utf-8") == "name=Starter Mod"
    assert (mod_dir / "scripts" / "build_install.ps1").read_text(encoding="utf-8") == "slug=starter-mod"
    assert (mod_dir / "starter-mod_notes" / "info.txt").read_text(encoding="utf-8") == "pak=StarterMod"

    cfg = json.loads((mod_dir / "docs" / "build_config.json").read_text(encoding="utf-8"))
    assert cfg["name"] == "StarterMod"
    assert "starter-mod" in cfg["input_dir"]


def test_cmd_init_mod_existing_dir_requires_force(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = tmp_path / "repo"
    template = workspace / "mods" / "new-mod-template"
    (template / "docs").mkdir(parents=True)
    (template / "README.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(cli, "workspace_root", lambda: workspace)

    existing = workspace / "mods" / "starter-mod"
    existing.mkdir(parents=True)
    (existing / "already.txt").write_text("x", encoding="utf-8")
    args = argparse.Namespace(name="Starter Mod", slug="", mods_root=str(workspace / "mods"), force=False)
    with pytest.raises(FileExistsError):
        cli.cmd_init_mod(args)


def test_cmd_build_install_resolves_config_and_dispatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(cli, "workspace_root", lambda: repo)
    monkeypatch.setattr(cli, "repo_root", lambda: repo / "modding_tools")
    monkeypatch.setenv("WINDROSE_MODS_DIR", str(repo / "mods_install"))

    config = {
        "input_dir": r"<REPO_ROOT>\mods\boar\input\staged",
        "output_pak": r"<REPO_ROOT>\mods\boar\output\Boar.pak",
        "mods_dir": "<WINDROSE_MODS_DIR>",
        "backup_dir": r"<REPO_ROOT>\mods\boar\output\mods_backups",
        "mount_point": "../../../",
        "version": "V11",
        "compression": "",
    }
    cfg_path = repo / "cfg.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")
    source_staged = repo / "mods" / "boar" / "input" / "staged"
    source_staged.mkdir(parents=True)
    (source_staged / "seed.txt").write_text("x", encoding="utf-8")

    calls = {"backup": None, "pack": None}

    def fake_backup(ns):
        calls["backup"] = ns
        return 0

    def fake_pack(ns):
        calls["pack"] = ns
        return 0

    monkeypatch.setattr(cli, "cmd_backup_mods", fake_backup)
    monkeypatch.setattr(cli, "cmd_pack_pak", fake_pack)

    args = argparse.Namespace(config=str(cfg_path), backup_first=True, repak_path="")
    assert cli.cmd_build_install(args) == 0
    assert calls["backup"] is not None
    assert calls["pack"] is not None
    assert "mods_install" in calls["pack"].install_to_mods
    assert calls["pack"].output_pak.endswith("Boar.pak")


def test_cmd_build_variants_runs_prepare_pack_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(cli, "workspace_root", lambda: repo)
    monkeypatch.setattr(cli, "repo_root", lambda: repo / "modding_tools")
    monkeypatch.setenv("WINDROSE_MODS_DIR", str(repo / "mods_install"))

    config = {
        "input_dir": r"<REPO_ROOT>\mods\boar\input\staged",
        "output_pak": r"<REPO_ROOT>\mods\boar\output\Boar.pak",
        "mods_dir": "<WINDROSE_MODS_DIR>",
        "backup_dir": r"<REPO_ROOT>\mods\boar\output\mods_backups",
        "mount_point": "../../../",
        "version": "V11",
        "compression": "",
    }
    cfg_path = repo / "cfg.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")
    source_staged = repo / "mods" / "boar" / "input" / "staged"
    source_staged.mkdir(parents=True)
    (source_staged / "seed.txt").write_text("x", encoding="utf-8")

    prep_calls = []
    backup_calls = []
    pack_calls = []

    def fake_prepare(template, multiplier, project_dir, variant_staged_dir, variant_output_pak):
        prep_calls.append((template, multiplier, project_dir, variant_staged_dir, variant_output_pak))

    def fake_backup(ns):
        backup_calls.append(ns)
        return 0

    def fake_pack(ns):
        pack_calls.append(ns)
        return 0

    monkeypatch.setattr(cli, "run_prepare_template", fake_prepare)
    monkeypatch.setattr(cli, "cmd_backup_mods", fake_backup)
    monkeypatch.setattr(cli, "cmd_pack_pak", fake_pack)

    args = argparse.Namespace(
        config=str(cfg_path),
        multipliers="2,3,5",
        prepare_command_template="prepare --mult {multiplier} --staged {variant_staged_dir}",
        project_dir=str(repo / "mods" / "boar"),
        install_multipliers="5",
        backup_first=True,
        report_path="",
        generated_root="",
        allow_unsafe_prepare_template=False,
        repak_path="",
    )
    assert cli.cmd_build_variants(args) == 0
    assert len(prep_calls) == 3
    assert len(pack_calls) == 3
    assert len(backup_calls) == 1
    assert len(prep_calls) == 3
    assert prep_calls[0][3].as_posix().endswith("/mods/boar/output/generated/x2/staged")
    assert pack_calls[0].input_dir.endswith(r"mods\boar\output\generated\x2\staged")
    assert pack_calls[0].output_pak.endswith("Boar_x2.pak")
    assert pack_calls[1].output_pak.endswith("Boar_x3.pak")
    assert pack_calls[2].output_pak.endswith("Boar_x5.pak")
    assert pack_calls[2].install_to_mods.endswith("mods_install")
    report = json.loads((repo / "mods" / "boar" / "output" / "variant_build_report.json").read_text(encoding="utf-8"))
    assert report["multipliers"] == [2.0, 3.0, 5.0]
    assert report["generated_root"].endswith(r"mods\boar\output\generated")


def test_cmd_prepare_boar_hide_json_mod_requires_aes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("WINDROSE_AES_KEY", raising=False)
    args = argparse.Namespace(
        aes_key="",
        pak_path="pakchunk0-Windows.pak",
        project_dir=str(tmp_path),
        staged_root="",
        multiplier=2.0,
        resource_types="leather",
        repak_path="",
    )
    with pytest.raises(ValueError):
        cli.cmd_prepare_boar_hide_json_mod(args)


def test_cmd_prepare_boar_hide_json_mod_writes_scaled_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    paks_dir = tmp_path / "paks"
    paks_dir.mkdir()
    pak_file = paks_dir / "pakchunk0-Windows.pak"
    pak_file.write_bytes(b"pak")
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))

    paths = [
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Boar_Leather.json",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Boar_Meat.json",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_BoarMega_Leather.json",
    ]
    sample_json = {
        "$type": "R5BLLootParams",
        "LootData": [{"Min": 1, "Max": 2, "Weight": 100, "LootItem": "X", "LootTable": "None"}],
    }

    def fake_run_capture(cmd, cwd=None):
        if "list" in cmd:
            return "\n".join(paths)
        if "get" in cmd:
            return json.dumps(sample_json)
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("repak.exe"))
    monkeypatch.setattr(cli, "run_cmd_capture", fake_run_capture)

    project_dir = tmp_path / "mods" / "boar-loot"
    args = argparse.Namespace(
        aes_key="0xabc",
        pak_path="pakchunk0-Windows.pak",
        project_dir=str(project_dir),
        staged_root="",
        multiplier=3.0,
        resource_types="leather,meat",
        repak_path="",
    )
    assert cli.cmd_prepare_boar_hide_json_mod(args) == 0

    out_file = project_dir / "input" / "staged" / Path(paths[0])
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["LootData"][0]["Min"] == 3
    assert data["LootData"][0]["Max"] == 6
    report = json.loads((project_dir / "docs" / "boar_hide_edit_report.json").read_text(encoding="utf-8"))
    assert report["edited_file_count"] == 3
    assert report["resource_types"] == ["leather", "meat"]


def test_cmd_prepare_cayenne_pepper_json_mod_scales_pepper_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    paks_dir = tmp_path / "paks"
    paks_dir.mkdir()
    (paks_dir / "pakchunk0-Windows.pak").write_bytes(b"pak")
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))

    payload_main = {
        "LootData": [
            {
                "Min": 1,
                "Max": 2,
                "LootItem": "/R5BusinessRules/InventoryItems/Consumables/Food/DA_CID_Food_Raw_Pepper_T01.DA_CID_Food_Raw_Pepper_T01",
                "LootTable": "None",
            },
            {"Min": 1, "Max": 1, "LootItem": "None", "LootTable": "/R5BusinessRules/LootTables/Foliage/Sub_tables/DA_LT_Foliage_Bush_Pepper_Seeds.DA_LT_Foliage_Bush_Pepper_Seeds"},
        ]
    }
    payload_sub = {
        "LootData": [
            {
                "Min": 1,
                "Max": 2,
                "LootItem": "/R5BusinessRules/InventoryItems/Consumables/Food/DA_CID_Food_Raw_Pepper_T01.DA_CID_Food_Raw_Pepper_T01",
                "LootTable": "None",
            }
        ]
    }

    def fake_run_capture(cmd, cwd=None):
        path = cmd[-1]
        if path.endswith("DA_LT_Foliage_Bush_Pepper.json"):
            return json.dumps(payload_main)
        if path.endswith("DA_LT_Foliage_Bush_Pepper_Pepper.json"):
            return json.dumps(payload_sub)
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("repak.exe"))
    monkeypatch.setattr(cli, "run_cmd_capture", fake_run_capture)

    project_dir = tmp_path / "mods" / "cayenne-pepper-yield"
    args = argparse.Namespace(
        aes_key="0xabc",
        pak_path="pakchunk0-Windows.pak",
        project_dir=str(project_dir),
        staged_root="",
        multiplier=3.0,
        repak_path="",
    )
    assert cli.cmd_prepare_cayenne_pepper_json_mod(args) == 0

    main_file = project_dir / "input" / "staged" / "R5/Plugins/R5BusinessRules/Content/LootTables/Foliage/DA_LT_Foliage_Bush_Pepper.json"
    data = json.loads(main_file.read_text(encoding="utf-8"))
    assert data["LootData"][0]["Min"] == 3
    assert data["LootData"][0]["Max"] == 6
    # Seed link row should remain unchanged.
    assert data["LootData"][1]["Min"] == 1
    assert data["LootData"][1]["Max"] == 1


def test_cmd_prepare_mob_rss_json_mod_filters_and_scales(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    paks_dir = tmp_path / "paks"
    paks_dir.mkdir()
    (paks_dir / "pakchunk0-Windows.pak").write_bytes(b"pak")
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))

    paths = [
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Crocodile_Leather.json",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_CorruptedCrocodile_Bones.json",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Boar_Leather.json",
    ]
    sample_json = {"LootData": [{"Min": 1, "Max": 2, "LootItem": "X", "LootTable": "None"}]}

    def fake_run_capture(cmd, cwd=None):
        if "list" in cmd:
            return "\n".join(paths)
        if "get" in cmd:
            return json.dumps(sample_json)
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("repak.exe"))
    monkeypatch.setattr(cli, "run_cmd_capture", fake_run_capture)

    project_dir = tmp_path / "mods" / "crocodile-bounty"
    args = argparse.Namespace(
        mob_keywords="crocodile",
        aes_key="0xabc",
        pak_path="pakchunk0-Windows.pak",
        project_dir=str(project_dir),
        staged_root="",
        report_name="crocodile_loot_edit_report",
        report_path="",
        multiplier=3.0,
        repak_path="",
    )
    assert cli.cmd_prepare_mob_rss_json_mod(args) == 0

    croc_file = project_dir / "input" / "staged" / "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Crocodile_Leather.json"
    data = json.loads(croc_file.read_text(encoding="utf-8"))
    assert data["LootData"][0]["Min"] == 3
    assert data["LootData"][0]["Max"] == 6
    boar_file = project_dir / "input" / "staged" / "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Boar_Leather.json"
    assert not boar_file.exists()


def test_cmd_prepare_mob_rss_json_mod_supports_rss_include_exclude_filters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paks_dir = tmp_path / "paks"
    paks_dir.mkdir()
    (paks_dir / "pakchunk0-Windows.pak").write_bytes(b"pak")
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))

    paths = [
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_BlackBeard_Sailor_Gunpowder.json",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_BlackBeard_Sailor_Gunpowder_low1.json",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_BlackBeard_Sailor_Rum.json",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_BlackBeard_Sergeant_BlackbeardSign.json",
    ]
    sample_json = {"LootData": [{"Min": 1, "Max": 2, "LootItem": "X", "LootTable": "None"}]}

    def fake_run_capture(cmd, cwd=None):
        if "list" in cmd:
            return "\n".join(paths)
        if "get" in cmd:
            return json.dumps(sample_json)
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("repak.exe"))
    monkeypatch.setattr(cli, "run_cmd_capture", fake_run_capture)

    project_dir = tmp_path / "mods" / "blackbeard-gunpowder"
    args = argparse.Namespace(
        mob_keywords="blackbeard",
        rss_include_keywords="gunpowder",
        rss_exclude_keywords="",
        aes_key="0xabc",
        pak_path="pakchunk0-Windows.pak",
        project_dir=str(project_dir),
        staged_root="",
        report_name="blackbeard_gunpowder_edit_report",
        report_path="",
        multiplier=2.0,
        repak_path="",
    )
    assert cli.cmd_prepare_mob_rss_json_mod(args) == 0

    staged_root = project_dir / "input" / "staged"
    assert (staged_root / paths[0]).exists()
    assert (staged_root / paths[1]).exists()
    assert not (staged_root / paths[2]).exists()
    assert not (staged_root / paths[3]).exists()
    report = json.loads((project_dir / "docs" / "blackbeard_gunpowder_edit_report.json").read_text(encoding="utf-8"))
    assert report["rss_include_keywords"] == ["gunpowder"]
    assert report["edited_file_count"] == 2


def test_cmd_prepare_sweet_potato_json_mod_scales_potato_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    paks_dir = tmp_path / "paks"
    paks_dir.mkdir()
    (paks_dir / "pakchunk0-Windows.pak").write_bytes(b"pak")
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))

    payload = {
        "LootData": [
            {
                "Min": 2,
                "Max": 3,
                "LootItem": "/R5BusinessRules/InventoryItems/DefaultItems/Resource/DA_DID_Resource_Potato_T01.DA_DID_Resource_Potato_T01",
                "LootTable": "None",
            },
            {
                "Min": 1,
                "Max": 1,
                "LootItem": "/R5BusinessRules/InventoryItems/DefaultItems/Resource/DA_DID_Resource_PotatoSeeds_T01.DA_DID_Resource_PotatoSeeds_T01",
                "LootTable": "None",
            },
        ]
    }

    def fake_run_capture(cmd, cwd=None):
        if "get" in cmd:
            return json.dumps(payload)
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("repak.exe"))
    monkeypatch.setattr(cli, "run_cmd_capture", fake_run_capture)

    project_dir = tmp_path / "mods" / "sweet-potato-bounty"
    args = argparse.Namespace(
        aes_key="0xabc",
        pak_path="pakchunk0-Windows.pak",
        project_dir=str(project_dir),
        staged_root="",
        multiplier=3.0,
        repak_path="",
    )
    assert cli.cmd_prepare_sweet_potato_json_mod(args) == 0

    out_file = project_dir / "input" / "staged" / "R5/Plugins/R5BusinessRules/Content/LootTables/Foliage/DA_LT_Foliage_Potato.json"
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["LootData"][0]["Min"] == 6
    assert data["LootData"][0]["Max"] == 9
    assert data["LootData"][1]["Min"] == 1
    assert data["LootData"][1]["Max"] == 1


def test_cmd_prepare_loot_table_items_json_mod_scales_matching_items_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paks_dir = tmp_path / "paks"
    paks_dir.mkdir()
    (paks_dir / "pakchunk0-Windows.pak").write_bytes(b"pak")
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))

    fish_path = "R5/Plugins/R5BusinessRules/Content/LootTables/Fishing/FishList/DA_LT_FishData_Coast_SmallFish.json"
    junk_path = "R5/Plugins/R5BusinessRules/Content/LootTables/Fishing/FishList/DA_LT_FishData_Coast_Items.json"
    payloads = {
        fish_path: {
            "LootData": [
                {"Min": 1, "Max": 1, "Weight": 5, "LootItem": "DA_CID_Misc_Fish_Small_ReefSnapper_T01"},
                {"Min": 1, "Max": 1, "Weight": 5, "LootItem": "DA_EID_MeleeWeapon_Club_Fish_Base"},
            ]
        },
        junk_path: {"LootData": [{"Min": 1, "Max": 1, "Weight": 2, "LootItem": "DA_DID_Resource_Nails_T01"}]},
    }

    def fake_run_capture(cmd, cwd=None):
        if "list" in cmd:
            return "\n".join(payloads)
        if "get" in cmd:
            return json.dumps(payloads[cmd[-1]])
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("repak.exe"))
    monkeypatch.setattr(cli, "run_cmd_capture", fake_run_capture)

    project_dir = tmp_path / "mods" / "fish-bounty"
    args = argparse.Namespace(
        loot_table_paths=f"{fish_path},{junk_path}",
        item_include_keywords="misc_fish",
        item_exclude_keywords="",
        aes_key="0xabc",
        pak_path="pakchunk0-Windows.pak",
        project_dir=str(project_dir),
        staged_root="",
        report_name="fish_bounty_edit_report",
        report_path="",
        multiplier=3.0,
        repak_path="",
    )
    assert cli.cmd_prepare_loot_table_items_json_mod(args) == 0

    out_file = project_dir / "input" / "staged" / fish_path
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["LootData"][0]["Min"] == 3
    assert data["LootData"][0]["Max"] == 3
    assert data["LootData"][1]["Min"] == 1
    assert data["LootData"][1]["Max"] == 1
    assert not (project_dir / "input" / "staged" / junk_path).exists()


def test_load_recipe_validates_mob_keywords(tmp_path: Path):
    project = tmp_path / "mods" / "goat-bounty"
    docs = project / "docs"
    docs.mkdir(parents=True)
    (docs / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Goat Bounty",
                "slug": "goat-bounty",
                "pak_name": "GoatBounty",
                "workflow": "mob_rss",
                "report_name": "goat_loot_edit_report",
                "variants": [2, 3],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        cli.load_recipe(project)


def test_load_recipe_accepts_mob_rss_filters(tmp_path: Path):
    project = tmp_path / "mods" / "blackbeard-gunpowder"
    docs = project / "docs"
    docs.mkdir(parents=True)
    (docs / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Blackbeard Gunpowder",
                "slug": "blackbeard-gunpowder",
                "pak_name": "BlackbeardGunpowder",
                "workflow": "mob_rss",
                "mob_keywords": ["blackbeard"],
                "rss_include_keywords": ["gunpowder"],
                "rss_exclude_keywords": ["blackbeardsign"],
                "report_name": "blackbeard_gunpowder_edit_report",
                "variants": [2, 3],
            }
        ),
        encoding="utf-8",
    )
    recipe = cli.load_recipe(project)
    assert recipe.rss_include_keywords == ["gunpowder"]
    assert recipe.rss_exclude_keywords == ["blackbeardsign"]


def test_load_recipe_accepts_loot_table_items_workflow(tmp_path: Path):
    project = tmp_path / "mods" / "fish-bounty"
    docs = project / "docs"
    docs.mkdir(parents=True)
    (docs / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Fish Bounty",
                "slug": "fish-bounty",
                "pak_name": "FishBounty",
                "workflow": "loot_table_items",
                "loot_table_paths": [
                    "R5/Plugins/R5BusinessRules/Content/LootTables/Fishing/FishList/DA_LT_FishData_Coast_SmallFish.json"
                ],
                "item_include_keywords": ["misc_fish"],
                "report_name": "fish_bounty_edit_report",
                "variants": [2, 3],
            }
        ),
        encoding="utf-8",
    )
    recipe = cli.load_recipe(project)
    assert recipe.workflow == "loot_table_items"
    assert recipe.item_include_keywords == ["misc_fish"]


def test_load_recipe_accepts_bundle_included_mods(tmp_path: Path):
    project = tmp_path / "mods" / "windrose-bounty"
    docs = project / "docs"
    docs.mkdir(parents=True)
    (docs / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Windrose Bounty",
                "slug": "windrose-bounty",
                "pak_name": "WindroseBounty",
                "workflow": "bundle",
                "included_mods": ["boar-loot", "goat-bounty"],
                "report_name": "windrose_bounty_bundle_report",
                "variants": [2, 3],
            }
        ),
        encoding="utf-8",
    )
    recipe = cli.load_recipe(project)
    assert recipe.workflow == "bundle"
    assert recipe.included_mods == ["boar-loot", "goat-bounty"]


def test_bundle_recipe_requires_included_mods(tmp_path: Path):
    project = tmp_path / "mods" / "windrose-bounty"
    docs = project / "docs"
    docs.mkdir(parents=True)
    (docs / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Windrose Bounty",
                "slug": "windrose-bounty",
                "pak_name": "WindroseBounty",
                "workflow": "bundle",
                "report_name": "windrose_bounty_bundle_report",
                "variants": [2, 3],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        cli.load_recipe(project)


def test_cmd_build_mod_uses_recipe_packages_and_variant_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    project = repo / "mods" / "goat-bounty"
    staged = project / "input" / "staged"
    staged.mkdir(parents=True)
    (staged / ".gitkeep").write_text("", encoding="utf-8")
    (project / "docs").mkdir(parents=True)
    monkeypatch.setattr(cli, "workspace_root", lambda: repo)
    monkeypatch.setattr(cli, "repo_root", lambda: repo / "modding_tools")
    monkeypatch.setenv("WINDROSE_MODS_DIR", str(repo / "mods_install"))

    (project / "docs" / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Goat Bounty",
                "slug": "goat-bounty",
                "pak_name": "GoatBounty",
                "workflow": "mob_rss",
                "mob_keywords": ["goat"],
                "report_name": "goat_loot_edit_report",
                "variants": [2, 3],
                "default_install_variant": 3,
                "install_target": "custom",
                "package_variants": True,
                "validate_outputs": True,
                "nexus": {"summary": "Goats", "resources": ["goat drops"]},
            }
        ),
        encoding="utf-8",
    )
    (project / "docs" / "build_config.example.json").write_text(
        json.dumps(
            {
                "input_dir": r"<REPO_ROOT>\mods\goat-bounty\input\staged",
                "output_pak": r"<REPO_ROOT>\mods\goat-bounty\output\GoatBounty_P.pak",
                "mods_dir": "<WINDROSE_MODS_DIR>",
                "backup_dir": r"<REPO_ROOT>\mods\goat-bounty\output\mods_backups",
                "mount_point": "../../../",
                "version": "V11",
                "compression": "",
            }
        ),
        encoding="utf-8",
    )

    pack_calls = []
    backup_calls = []

    def fake_prepare(recipe, project_dir, variant_staged_dir, multiplier, label, repak_path):
        out = variant_staged_dir / "R5" / "Plugins" / "R5BusinessRules" / "Content" / "LootTables" / "Mobs" / "Rss" / "DA_LT_Mob_GoatF_Meat.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"LootData": [{"Min": multiplier, "Max": multiplier}]}), encoding="utf-8")
        report = project_dir / "docs" / f"{recipe.report_name}_x{label}.json"
        report.write_text(json.dumps({"multiplier": multiplier}), encoding="utf-8")
        return report

    def fake_pack(ns):
        pack_calls.append(ns)
        output = Path(ns.output_pak)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"pak")
        if ns.install_to_mods:
            target = Path(ns.install_to_mods) / output.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"pak")
        return 0

    def fake_backup(ns):
        backup_calls.append(ns)
        return 0

    monkeypatch.setattr(cli, "prepare_recipe_variant", fake_prepare)
    monkeypatch.setattr(cli, "cmd_pack_pak", fake_pack)
    monkeypatch.setattr(cli, "cmd_backup_mods", fake_backup)

    args = argparse.Namespace(
        project_dir=str(project),
        config="",
        install_multipliers="",
        install_target="",
        backup_first=True,
        no_package=False,
        no_validate=False,
        repak_path="",
    )
    assert cli.cmd_build_mod(args) == 0
    assert len(pack_calls) == 2
    assert len(backup_calls) == 1
    assert (project / "output" / "GoatBounty_P_x2.zip").exists()
    assert (project / "output" / "GoatBounty_P_x3.zip").exists()
    assert (project / "docs" / "goat_loot_edit_report_x2.json").exists()
    report = json.loads((project / "output" / "variant_build_report.json").read_text(encoding="utf-8"))
    assert report["variants"][1]["installed"] is True
    assert report["variants"][0]["package"].endswith("GoatBounty_P_x2.zip")


def test_cmd_build_mod_bundle_combines_included_recipes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    monkeypatch.setattr(cli, "workspace_root", lambda: repo)
    monkeypatch.setattr(cli, "repo_root", lambda: repo / "modding_tools")
    monkeypatch.setenv("WINDROSE_MODS_DIR", str(repo / "mods_install"))

    bundle_project = repo / "mods" / "windrose-bounty"
    staged = bundle_project / "input" / "staged"
    staged.mkdir(parents=True)
    (staged / ".gitkeep").write_text("", encoding="utf-8")
    (bundle_project / "docs").mkdir(parents=True)
    (bundle_project / "docs" / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Windrose Bounty",
                "slug": "windrose-bounty",
                "pak_name": "WindroseBounty",
                "workflow": "bundle",
                "included_mods": ["goat-bounty", "wolf-bounty"],
                "report_name": "windrose_bounty_bundle_report",
                "variants": [2],
                "default_install_variant": 2,
                "install_target": "custom",
                "package_variants": True,
                "validate_outputs": True,
            }
        ),
        encoding="utf-8",
    )
    (bundle_project / "docs" / "build_config.example.json").write_text(
        json.dumps(
            {
                "input_dir": r"<REPO_ROOT>\mods\windrose-bounty\input\staged",
                "output_pak": r"<REPO_ROOT>\mods\windrose-bounty\output\WindroseBounty_P.pak",
                "mods_dir": "<WINDROSE_MODS_DIR>",
                "backup_dir": r"<REPO_ROOT>\mods\windrose-bounty\output\mods_backups",
                "mount_point": "../../../",
                "version": "V11",
                "compression": "",
            }
        ),
        encoding="utf-8",
    )
    for slug, keyword in [("goat-bounty", "goat"), ("wolf-bounty", "wolf")]:
        project = repo / "mods" / slug
        (project / "docs").mkdir(parents=True)
        (project / "docs" / "mod_recipe.json").write_text(
            json.dumps(
                {
                    "display_name": slug,
                    "slug": slug,
                        "pak_name": cli.pak_name_from_mod_name(slug),
                    "workflow": "mob_rss",
                    "mob_keywords": [keyword],
                    "report_name": f"{keyword}_loot_edit_report",
                    "variants": [2],
                }
            ),
            encoding="utf-8",
        )

    def fake_prepare_mob(args):
        keyword = args.mob_keywords.split(",")[0]
        out = Path(args.staged_root) / "R5" / "Plugins" / "R5BusinessRules" / "Content" / "LootTables" / "Mobs" / "Rss" / f"DA_LT_Mob_{keyword.title()}_Meat.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"LootData": [{"Min": args.multiplier, "Max": args.multiplier}]}), encoding="utf-8")
        Path(args.report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_path).write_text(json.dumps({"keyword": keyword}), encoding="utf-8")
        return 0

    def fake_pack(ns):
        output = Path(ns.output_pak)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"pak")
        return 0

    monkeypatch.setattr(cli, "cmd_prepare_mob_rss_json_mod", fake_prepare_mob)
    monkeypatch.setattr(cli, "cmd_pack_pak", fake_pack)
    monkeypatch.setattr(cli, "cmd_backup_mods", lambda ns: 0)
    removed_prefixes = []
    monkeypatch.setattr(
        cli,
        "clear_matching_paks",
        lambda mods_dir, stem_prefix: removed_prefixes.append(stem_prefix) or 0,
    )

    args = argparse.Namespace(
        project_dir=str(bundle_project),
        config="",
        install_multipliers="",
        install_target="",
        backup_first=False,
        no_package=False,
        no_validate=False,
        repak_path="",
    )
    assert cli.cmd_build_mod(args) == 0
    generated = bundle_project / "output" / "generated" / "x2" / "staged"
    assert (generated / "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Goat_Meat.json").exists()
    assert (generated / "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Wolf_Meat.json").exists()
    bundle_report = json.loads((bundle_project / "docs" / "windrose_bounty_bundle_report_x2.json").read_text(encoding="utf-8"))
    assert [item["slug"] for item in bundle_report["included_mods"]] == ["goat-bounty", "wolf-bounty"]
    assert (bundle_project / "output" / "WindroseBounty_P_x2.zip").exists()
    assert removed_prefixes == ["WindroseBounty_P", "GoatBounty_P", "WolfBounty_P"]


def test_bundle_recipe_detects_path_conflicts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    monkeypatch.setattr(cli, "workspace_root", lambda: repo)

    bundle_project = repo / "mods" / "windrose-bounty"
    (bundle_project / "docs").mkdir(parents=True)
    recipe = cli.ModRecipe(
        display_name="Windrose Bounty",
        slug="windrose-bounty",
        pak_name="WindroseBounty",
        workflow="bundle",
        variants=[2.0],
        default_install_variant=None,
        install_target="custom",
        report_name="bundle_report",
        included_mods=["first", "second"],
    )
    for slug in recipe.included_mods:
        project = repo / "mods" / slug
        (project / "docs").mkdir(parents=True)
        (project / "docs" / "mod_recipe.json").write_text(
            json.dumps(
                {
                    "display_name": slug,
                    "slug": slug,
                    "pak_name": slug.title(),
                    "workflow": "mob_rss",
                    "mob_keywords": [slug],
                    "report_name": f"{slug}_report",
                    "variants": [2],
                }
            ),
            encoding="utf-8",
        )

    def fake_prepare(recipe, project_dir, variant_staged_dir, multiplier, label, repak_path):
        if recipe.workflow == "bundle":
            return original_prepare(recipe, project_dir, variant_staged_dir, multiplier, label, repak_path)
        out = variant_staged_dir / "same.json"
        out.write_text(recipe.slug, encoding="utf-8")
        report = project_dir / "docs" / f"{recipe.report_name}_x{label}.json"
        report.write_text("{}", encoding="utf-8")
        return report

    original_prepare = cli.prepare_recipe_variant
    monkeypatch.setattr(cli, "prepare_recipe_variant", fake_prepare)
    staged = bundle_project / "output" / "generated" / "x2" / "staged"
    staged.mkdir(parents=True)
    with pytest.raises(ValueError, match="path conflicts"):
        cli.prepare_recipe_variant(recipe, bundle_project, staged, 2.0, "2", "")


def test_cmd_discover_mob_loot_reports_final_and_rss_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    paks_dir = tmp_path / "paks"
    paks_dir.mkdir()
    (paks_dir / "pakchunk0-Windows.pak").write_bytes(b"pak")
    monkeypatch.setenv("WINDROSE_PAKS_DIR", str(paks_dir))
    paths = [
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/DA_LT_Mob_GoatF_Final.json",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_GoatF_Meat.json",
        "R5/Plugins/R5BusinessRules/Content/LootTables/Mobs/Rss/DA_LT_Mob_Boar_Meat.json",
    ]

    def fake_run_capture(cmd, cwd=None):
        if "list" in cmd:
            return "\n".join(paths)
        if "get" in cmd:
            return json.dumps({"LootData": [{"Min": 1, "Max": 2, "Weight": 100, "LootItem": "X", "LootTable": "None"}]})
        raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("repak.exe"))
    monkeypatch.setattr(cli, "run_cmd_capture", fake_run_capture)
    output = tmp_path / "goat_discovery.json"
    args = argparse.Namespace(
        keyword="goat",
        aes_key="0xabc",
        pak_path="pakchunk0-Windows.pak",
        output=str(output),
        repak_path="",
    )
    assert cli.cmd_discover_mob_loot(args) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["final_tables"] == [paths[0]]
    assert payload["rss_tables"][0]["rows"][0]["min"] == 1


def test_generate_nexus_description_from_recipe(tmp_path: Path):
    project = tmp_path / "mods" / "goat-bounty"
    (project / "docs").mkdir(parents=True)
    (project / "docs" / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Goat Bounty",
                "slug": "goat-bounty",
                "pak_name": "GoatBounty",
                "workflow": "mob_rss",
                "mob_keywords": ["goat"],
                "report_name": "goat_loot_edit_report",
                "variants": [2, 3, 5, 10],
                "nexus": {"summary": "Increase goats.", "resources": ["goat meat"], "covered": ["goats"]},
            }
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(project_dir=str(project), output="")
    assert cli.cmd_generate_nexus_description(args) == 0
    text = (project / "docs" / "NEXUS_DESCRIPTION.txt").read_text(encoding="utf-8")
    assert "Goat Bounty - Loot Variants" in text
    assert "Single-player" in text


def test_cmd_init_mob_bounty_scaffolds_recipe_and_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    workspace = tmp_path / "repo"
    template = workspace / "mods" / "new-mod-template"
    (template / "docs").mkdir(parents=True)
    (template / "input" / "staged").mkdir(parents=True)
    (template / "output").mkdir(parents=True)
    (template / "README.md").write_text("# __MOD_NAME__", encoding="utf-8")
    (template / "docs" / "build_config.example.json").write_text(
        json.dumps(
            {
                "name": "__MOD_PAK_NAME__",
                "input_dir": "<REPO_ROOT>\\mods\\__MOD_SLUG__\\input\\staged",
                "output_pak": "<REPO_ROOT>\\mods\\__MOD_SLUG__\\output\\__MOD_PAK_NAME___P.pak",
                "mods_dir": "<WINDROSE_MODS_DIR>",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "workspace_root", lambda: workspace)
    args = argparse.Namespace(
        name="Goat Bounty",
        mob_keywords="goat",
        resources="goat meat, leather",
        slug="",
        mods_root=str(workspace / "mods"),
        force=False,
    )
    assert cli.cmd_init_mob_bounty(args) == 0
    project = workspace / "mods" / "goat-bounty"
    recipe = json.loads((project / "docs" / "mod_recipe.json").read_text(encoding="utf-8"))
    assert recipe["workflow"] == "mob_rss"
    assert recipe["mob_keywords"] == ["goat"]
    assert (project / "docs" / "NEXUS_DESCRIPTION.txt").exists()


@pytest.mark.parametrize(
    "argv,expected_func",
    [
        (["tools-info"], cli.cmd_tools_info),
        (["search-paths", "--paks-dir", "paks", "--contains", "boar", "--output", "out.json"], cli.cmd_search_paths),
        (["loot-manifest", "--paks-dir", "paks", "--mob-keyword", "boar", "--output", "out.json"], cli.cmd_loot_manifest),
        (["backup-mods", "--mods-dir", "mods", "--backup-dir", "backup"], cli.cmd_backup_mods),
        (["restore-mods", "--mods-dir", "mods", "--backup-dir", "backup"], cli.cmd_restore_mods),
        (["unpack-iostore", "--utoc", "pakchunk0.utoc", "--output-dir", "out"], cli.cmd_unpack_iostore),
        (["build-mod", "--project-dir", "mods/boar-loot"], cli.cmd_build_mod),
        (
            [
                "inspect-cooked-asset",
                "--asset-path",
                "/Game/R5/Content/Test",
                "--paks-dir",
                "paks",
                "--aes-key",
                "0xabc",
            ],
            cli.cmd_inspect_cooked_asset,
        ),
        (["prepare-bandage-speed-mod", "--project-dir", "mods/fast-bandages"], cli.cmd_prepare_bandage_speed_mod),
        (
            ["pack-iostore-mod", "--input-dir", "staged", "--output-pak", "out/Test_P.pak"],
            cli.cmd_pack_iostore_mod,
        ),
    ],
)
def test_parser_smoke_wires_uncovered_commands(argv, expected_func):
    args = cli.build_parser().parse_args(argv)
    assert args.func is expected_func


def test_cmd_tools_info_outputs_machine_readable_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    tools_dir = tmp_path / "bin"
    tools_dir.mkdir()
    (tools_dir / "repak.exe").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "bin_dir", lambda: tools_dir)

    assert cli.cmd_tools_info(argparse.Namespace()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repak.exe"] == str(tools_dir / "repak.exe")
    assert payload["retoc.exe"] == ""


def test_backup_restore_mods_roundtrip(tmp_path: Path):
    mods_dir = tmp_path / "mods"
    backup_root = tmp_path / "backups"
    mods_dir.mkdir()
    (mods_dir / "Example_P.pak").write_text("original", encoding="utf-8")

    assert cli.cmd_backup_mods(argparse.Namespace(mods_dir=str(mods_dir), backup_dir=str(backup_root))) == 0
    (mods_dir / "Example_P.pak").write_text("changed", encoding="utf-8")
    backup_dir = next(backup_root.iterdir())

    assert cli.cmd_restore_mods(argparse.Namespace(mods_dir=str(mods_dir), backup_dir=str(backup_dir))) == 0
    assert (mods_dir / "Example_P.pak").read_text(encoding="utf-8") == "original"


def test_cmd_unpack_iostore_uses_retoc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    utoc = tmp_path / "mod.utoc"
    utoc.write_bytes(b"utoc")
    output_dir = tmp_path / "unpacked"
    calls = []
    monkeypatch.setattr(cli, "resolve_tool", lambda *_args, **_kwargs: Path("retoc.exe"))
    monkeypatch.setattr(cli, "run_cmd", lambda cmd: calls.append(cmd))

    args = argparse.Namespace(utoc=str(utoc), output_dir=str(output_dir), retoc_path="")
    assert cli.cmd_unpack_iostore(args) == 0
    assert calls == [[str(Path("retoc.exe")), "unpack", str(utoc), str(output_dir)]]


def test_load_recipe_accepts_bandage_speed_iostore_workflow(tmp_path: Path):
    project = tmp_path / "mods" / "fast-bandages"
    (project / "docs").mkdir(parents=True)
    (project / "docs" / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Fast Bandages",
                "slug": "fast-bandages",
                "pak_name": "FastBandages",
                "workflow": "bandage_speed",
                "package_mode": "iostore",
                "variants": [15.0],
                "default_install_variant": 15.0,
                "install_target": "single-player",
                "report_name": "bandage_speed_edit_report",
            }
        ),
        encoding="utf-8",
    )
    recipe = cli.load_recipe(project)
    assert recipe.workflow == "bandage_speed"
    assert recipe.package_mode == "iostore"


def test_package_iostore_variant_zips_output_trio(tmp_path: Path):
    pak = tmp_path / "FastBandages_P_x15.pak"
    pak.write_bytes(b"pak")
    pak.with_suffix(".ucas").write_bytes(b"ucas")
    pak.with_suffix(".utoc").write_bytes(b"utoc")

    zip_path = cli.package_iostore_variant(pak)
    assert zip_path.exists()


def test_tool_clients_build_expected_external_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from windrose_cli.tools import cue4parse, repak, retoc
    from windrose_cli.tools.process import ProcessResult

    calls = []

    def fake_run(cmd, cwd=None, check=True, redacted_cmd=None):
        calls.append({"cmd": cmd, "redacted_cmd": redacted_cmd, "check": check})
        return ProcessResult(0, "entry.json\n", "")

    monkeypatch.setattr(repak, "run", fake_run)
    monkeypatch.setattr(retoc, "run", fake_run)
    monkeypatch.setattr(cue4parse, "run", fake_run)

    repak.RepakClient(Path("repak.exe")).list_entries(tmp_path / "pakchunk0-Windows.pak", "0xsecret")
    retoc.RetocClient(Path("retoc.exe")).to_zen(tmp_path / "Mod_P.pak", tmp_path / "Mod_P.utoc")
    cue4parse.Cue4ParseClient(Path("cue4parse.exe")).export_asset(
        paks_dir=tmp_path / "Paks",
        output_dir=tmp_path / "exported",
        package_patterns=["/Game/TestAsset.uasset"],
        aes_key="0xsecret",
        mappings=tmp_path / "Windrose.usmap",
        check=False,
    )

    assert calls[0]["cmd"] == [
        "repak.exe",
        "--aes-key",
        "0xsecret",
        "list",
        str(tmp_path / "pakchunk0-Windows.pak"),
    ]
    assert calls[1]["cmd"] == [
        "retoc.exe",
        "to-zen",
        str(tmp_path / "Mod_P.pak"),
        str(tmp_path / "Mod_P.utoc"),
        "--version",
        "UE5_6",
    ]
    assert "--mappings" in calls[2]["cmd"]
    assert "/Game/TestAsset.uasset" in calls[2]["cmd"]
    assert calls[2]["redacted_cmd"][calls[2]["redacted_cmd"].index("--key") + 1] == "<redacted>"


def test_validate_bundle_metadata_detects_missing_covered_mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from windrose_cli.recipes import NexusMetadata

    workspace = tmp_path / "repo"
    included = workspace / "mods" / "goat-bounty" / "docs"
    included.mkdir(parents=True)
    (included / "mod_recipe.json").write_text(
        json.dumps(
            {
                "display_name": "Goat Bounty",
                "slug": "goat-bounty",
                "pak_name": "GoatBounty",
                "workflow": "mob_rss",
                "mob_keywords": ["goat"],
                "report_name": "goat_loot_edit_report",
                "variants": [2],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "workspace_root", lambda: workspace)
    recipe = cli.ModRecipe(
        display_name="Windrose Bounty",
        slug="windrose-bounty",
        pak_name="WindroseBounty",
        workflow="bundle",
        variants=[2.0],
        default_install_variant=None,
        install_target="custom",
        report_name="bundle_report",
        included_mods=["goat-bounty"],
        nexus=NexusMetadata(summary="", covered=["Other Bounty"]),
    )
    with pytest.raises(ValueError, match="Goat Bounty"):
        cli.validate_bundle_metadata(recipe)
