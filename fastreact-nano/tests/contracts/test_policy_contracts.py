from fastreact import Agent
from fastreact.adapters.http import create_app, set_agent_for_testing
from fastreact.core.config import Config, LLMConfig, PolicyConfig
from fastreact.core.safety import SafetyLevel, SafetyPolicy


def test_safety_policy_supports_tool_user_and_tenant_rules():
    policy = SafetyPolicy(
        policy_config={
            "tool_rules": {
                "exec": "require_approval",
                "write_file": "deny",
            },
            "tenant_rules": {
                "pska": {
                    "tools": {
                        "pska_search": "allow",
                        "exec": "deny",
                    }
                }
            },
            "user_rules": {
                "pska:operator": {
                    "tools": {
                        "exec": "require_approval",
                    }
                }
            },
        }
    )

    assert policy.check("write_file", {}).level == SafetyLevel.FORBIDDEN
    assert policy.check("pska_search", {}, user_key="pska:user").level == SafetyLevel.SAFE
    assert policy.check("exec", {"command": "ls"}, user_key="pska:user").level == SafetyLevel.FORBIDDEN
    operator_decision = policy.check("exec", {"command": "ls"}, user_key="pska:operator")
    assert operator_decision.level == SafetyLevel.DANGER
    assert operator_decision.requires_confirmation is True


def test_config_loads_policy_block(tmp_path):
    config_file = tmp_path / "fastreact.json"
    config_file.write_text(
        """
{
  "policy": {
    "tool_rules": {
      "exec": "require_approval",
      "write_file": "deny"
    },
    "tenant_rules": {
      "pska": {
        "tools": {
          "pska_search": "allow"
        }
      }
    }
  }
}
""",
        encoding="utf-8",
    )

    config = Config.load(config_file)

    assert config.policy.tool_rules["exec"] == "require_approval"
    assert config.policy.tool_rules["write_file"] == "deny"
    assert config.policy.tenant_rules["pska"]["tools"]["pska_search"] == "allow"
    assert config.policy.to_safety_policy()["tool_rules"]["exec"] == "require_approval"


def test_config_loads_run_retry_and_concurrency_settings(tmp_path):
    config_file = tmp_path / "fastreact.json"
    config_file.write_text(
        """
{
  "service": {
    "run_max_attempts": 5,
    "run_retry_base_seconds": 2,
    "run_retry_max_seconds": 30,
    "run_concurrency": 2
  }
}
""",
        encoding="utf-8",
    )

    config = Config.load(config_file)

    assert config.service.run_max_attempts == 5
    assert config.service.run_retry_base_seconds == 2
    assert config.service.run_retry_max_seconds == 30
    assert config.service.run_concurrency == 2


def test_policy_config_rejects_invalid_action():
    pytest = __import__("pytest")

    with pytest.raises(ValueError, match="invalid action"):
        PolicyConfig.from_dict({"tool_rules": {"exec": "approve_maybe"}})

    with pytest.raises(ValueError, match="invalid action"):
        PolicyConfig.from_dict({"tool_rules": {"exec": "require-approval"}})


def test_policy_config_rejects_invalid_structure():
    pytest = __import__("pytest")

    with pytest.raises(ValueError, match="policy.tenant_rules.pska.tools must be an object"):
        PolicyConfig.from_dict({"tenant_rules": {"pska": {"tools": "exec"}}})


def test_policy_allow_does_not_override_builtin_forbidden_exec_patterns():
    policy = SafetyPolicy(policy_config={"tool_rules": {"exec": "allow"}})

    decision = policy.check("exec", {"command": "rm -rf /"})

    assert decision.level == SafetyLevel.FORBIDDEN
    assert "forbidden pattern" in decision.reason


def test_safety_policy_decision_includes_policy_metadata():
    policy = SafetyPolicy(policy_config={"tool_rules": {"exec": "require_approval"}})

    decision = policy.check("exec", {"command": "ls"})

    assert decision.level == SafetyLevel.DANGER
    assert decision.policy_matched is True
    assert decision.policy_scope == "tool:exec"
    assert decision.policy_action == "require_approval"


def test_headless_policy_inspection_and_dry_run_endpoints(monkeypatch):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")
    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    config = Config(
        llm=LLMConfig(api_key="test-key", api_base="http://localhost:8000"),
        policy=PolicyConfig(
            tool_rules={"exec": "require_approval"},
            tenant_rules={"pska": {"tools": {"exec": "deny", "pska_search": "allow"}}},
            user_rules={"pska:operator": {"tools": {"exec": "require_approval"}}},
        ),
    )
    set_agent_for_testing(Agent(config=config))
    headers = {"X-FastReAct-Service-Token": "service-secret"}
    try:
        client = testclient.TestClient(create_app())
        assert client.get("/v1/policy").status_code == 401

        policy_response = client.get("/v1/policy", headers=headers)
        assert policy_response.status_code == 200
        policy_payload = policy_response.json()
        assert policy_payload["schema"] == "fastreact.policy.v1"
        assert policy_payload["policy"]["tool_rules"]["exec"] == "require_approval"
        assert policy_payload["policy_snapshot_hash"]
        assert policy_payload["policy_version"] == policy_payload["policy_snapshot_hash"]
        assert policy_payload["reload_supported"] is False
        assert "require_approval" in policy_payload["actions"]

        denied = client.post(
            "/v1/policy/check",
            headers=headers,
            json={"tool_name": "exec", "tool_args": {"command": "ls"}, "user_key": "pska:user"},
        )
        assert denied.status_code == 200
        assert denied.json()["level"] == "forbidden"
        assert denied.json()["should_allow"] is False
        assert denied.json()["policy_matched"] is True
        assert denied.json()["policy_scope"] == "tenant:pska"
        assert denied.json()["policy_action"] == "deny"

        operator = client.post(
            "/v1/policy/check",
            headers=headers,
            json={"tool_name": "exec", "tool_args": {"command": "ls"}, "user_key": "pska:operator"},
        )
        assert operator.status_code == 200
        assert operator.json()["level"] == "danger"
        assert operator.json()["requires_confirmation"] is True
        assert operator.json()["policy_scope"] == "user:pska:operator"
        assert operator.json()["policy_action"] == "require_approval"
    finally:
        set_agent_for_testing(None)
