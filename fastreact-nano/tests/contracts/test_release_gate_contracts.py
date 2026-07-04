import importlib.util
import sys
from pathlib import Path


def load_release_gate_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "release_llm_gate.py"
    spec = importlib.util.spec_from_file_location("release_llm_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_pska_gate_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "pska_e2e_gate.py"
    spec = importlib.util.spec_from_file_location("pska_e2e_gate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_judge_response_accepts_lightly_wrapped_json():
    gate = load_release_gate_module()

    assert gate.parse_judge_response('{"pass": true, "reason": "ok"}')["pass"] is True
    assert gate.parse_judge_response('```json\n{"pass": false, "reason": "no"}\n```')["reason"] == "no"
    assert gate.parse_judge_response('Result:\n{"pass": true, "reason": "ok"}')["pass"] is True
    assert gate.parse_judge_response("not json") is None


def test_load_api_env_accepts_json_key_file(tmp_path, monkeypatch):
    gate = load_release_gate_module()
    key_file = tmp_path / "api_key.txt"
    key_file.write_text(
        '{"api_key":"test-key","model":"test-model","base_url":"https://example.test"}',
        encoding="utf-8",
    )

    monkeypatch.delenv("FASTRACT_API_KEY", raising=False)
    monkeypatch.delenv("FASTRACT_MODEL", raising=False)
    monkeypatch.delenv("FASTRACT_API_BASE", raising=False)

    gate.load_api_env(key_file)

    assert gate.os.environ["FASTRACT_API_KEY"] == "test-key"
    assert gate.os.environ["FASTRACT_MODEL"] == "test-model"
    assert gate.os.environ["FASTRACT_API_BASE"] == "https://example.test"


def test_pska_e2e_gate_targets_live_smoke_script(tmp_path):
    gate = load_pska_gate_module()
    pska_root = tmp_path / "PSKA"
    pska_core = pska_root / "core"
    smoke = pska_root / "scripts" / "pska-fastreact-kb-scope-smoke"
    smoke.parent.mkdir(parents=True)
    smoke.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    smoke.chmod(0o755)

    assert gate.resolve_pska_root(pska_root, None) == pska_root
    assert gate.resolve_pska_root(tmp_path / "ignored", pska_core) == pska_root.resolve()
    assert gate.build_smoke_command(smoke, timeout_seconds=45) == [
        str(smoke),
        "--timeout-seconds",
        "45",
    ]
