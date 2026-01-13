import pytest
from security.sandbox import MCPSandbox, SandboxConfig, get_sandbox


class TestMCPSandbox:
    @pytest.fixture
    def sandbox(self):
        return MCPSandbox(
            SandboxConfig(
                enabled=True,
                blocked_paths=["~/.ssh", "~/.aws"],
                block_private_ips=True,
            )
        )

    def test_blocks_sensitive_paths(self, sandbox):
        allowed = sandbox.validate_file_access("~/.ssh/id_rsa")
        assert not allowed

    def test_allows_safe_paths(self, sandbox):
        allowed = sandbox.validate_file_access("./myproject/file.py")
        assert allowed

    def test_blocks_internal_ips(self, sandbox):
        allowed = sandbox.validate_network_access("192.168.1.1", 80)
        assert not allowed

        allowed = sandbox.validate_network_access("10.0.0.1", 443)
        assert not allowed

        allowed = sandbox.validate_network_access("localhost", 80)
        assert not allowed

    def test_allows_external_hosts(self, sandbox):
        allowed = sandbox.validate_network_access("api.openai.com", 443)
        assert allowed

    def test_redacts_blocked_file_content(self, sandbox):
        content = "some secret data"
        redacted = sandbox.redact_file_content("~/.ssh/id_rsa", content)
        assert "REDACTED" in redacted
        assert "secret" not in redacted

    def test_allows_safe_file_content(self, sandbox):
        content = "normal file data"
        result = sandbox.redact_file_content("./safe/file.txt", content)
        assert result == content

    def test_disabled_sandbox(self):
        sandbox = MCPSandbox(SandboxConfig(enabled=False))
        assert sandbox.validate_file_access("~/.ssh/id_rsa")
        assert sandbox.validate_network_access("192.168.1.1", 80)

    def test_records_violations(self, sandbox):
        sandbox.validate_file_access("~/.ssh/id_rsa")
        sandbox.validate_network_access("10.0.0.1", 22)
        violations = sandbox.get_violations()
        assert len(violations) == 2
        assert violations[0].violation_type == "file"
        assert violations[1].violation_type == "network"

    def test_clear_violations(self, sandbox):
        sandbox.validate_file_access("~/.ssh/id_rsa")
        assert len(sandbox.get_violations()) == 1
        sandbox.clear_violations()
        assert len(sandbox.get_violations()) == 0

    def test_filter_tool_result_dict(self, sandbox):
        result = {"path": "~/.ssh/id_rsa", "content": "-----BEGIN RSA PRIVATE KEY-----"}
        filtered = sandbox.filter_tool_result(result)
        assert "REDACTED" in filtered["content"]

    def test_filter_tool_result_list(self, sandbox):
        result = [{"path": "~/.ssh/id_rsa", "content": "secret"}]
        filtered = sandbox.filter_tool_result(result)
        assert "REDACTED" in filtered[0]["content"]

    def test_with_overrides(self, sandbox):
        new_sandbox = sandbox.with_overrides(
            {
                "allowed_paths": ["/extra/path"],
                "block_private_ips": False,
            }
        )
        assert "/extra/path" in [str(p) for p in new_sandbox._allowed_paths] or any(
            "/extra/path" in str(p) for p in new_sandbox._allowed_paths
        )
        assert not new_sandbox.config.block_private_ips

    def test_get_sandbox_singleton(self):
        s1 = get_sandbox()
        s2 = get_sandbox()
        assert s1 is s2


class TestSandboxConfig:
    def test_default_config(self):
        config = SandboxConfig()
        assert config.enabled
        assert config.allow_network
        assert config.block_private_ips

    def test_custom_config(self):
        config = SandboxConfig(
            enabled=False,
            allowed_paths=["/custom/path"],
            block_private_ips=False,
        )
        assert not config.enabled
        assert "/custom/path" in config.allowed_paths
        assert not config.block_private_ips

    def test_from_dict(self):
        data = {"enabled": False, "allow_network": False}
        config = SandboxConfig.from_dict(data)
        assert not config.enabled
        assert not config.allow_network

    def test_to_dict(self):
        config = SandboxConfig(enabled=True, blocked_paths=["~/.ssh"])
        data = config.to_dict()
        assert data["enabled"] is True
        assert "~/.ssh" in data["blocked_paths"]
