from fastreact.core.config import Config
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


def test_policy_allow_does_not_override_builtin_forbidden_exec_patterns():
    policy = SafetyPolicy(policy_config={"tool_rules": {"exec": "allow"}})

    decision = policy.check("exec", {"command": "rm -rf /"})

    assert decision.level == SafetyLevel.FORBIDDEN
    assert "forbidden pattern" in decision.reason
