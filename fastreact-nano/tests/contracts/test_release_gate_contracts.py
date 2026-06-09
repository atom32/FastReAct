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


def test_parse_judge_response_accepts_lightly_wrapped_json():
    gate = load_release_gate_module()

    assert gate.parse_judge_response('{"pass": true, "reason": "ok"}')["pass"] is True
    assert gate.parse_judge_response('```json\n{"pass": false, "reason": "no"}\n```')["reason"] == "no"
    assert gate.parse_judge_response('Result:\n{"pass": true, "reason": "ok"}')["pass"] is True
    assert gate.parse_judge_response("not json") is None
