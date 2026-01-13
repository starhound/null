"""Command sanitization for AI-generated shell commands.

This module provides security hardening for shell command execution by detecting
dangerous patterns, preventing path traversal attacks, and properly escaping
shell arguments.
"""

from __future__ import annotations

import logging
import re
import shlex
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


@dataclass
class SanitizationResult:
    """Result of command sanitization check.

    Attributes:
        is_safe: Whether the command passed all security checks.
        command: The (potentially sanitized) command string.
        warnings: List of security warnings or reasons for blocking.
        blocked_patterns: List of dangerous patterns that were detected.
    """

    is_safe: bool
    command: str
    warnings: list[str] = field(default_factory=list)
    blocked_patterns: list[str] = field(default_factory=list)


class CommandSanitizer:
    """Sanitizes and validates shell commands for safe execution.

    This class detects dangerous shell command patterns that could cause
    system damage, privilege escalation, or data exfiltration. It can
    operate in allowlist mode for restrictive environments.

    Attributes:
        DANGEROUS_PATTERNS: Compiled regex patterns for dangerous commands.
        allowlist_mode: If True, only commands matching ALLOWED_COMMANDS pass.
        allowed_commands: Set of allowed command prefixes in allowlist mode.
        custom_blocked_patterns: User-defined patterns to block.
    """

    # Dangerous command patterns with descriptions
    DANGEROUS_PATTERN_DEFS: list[tuple[str, str]] = [
        # Recursive delete patterns
        (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+/\s*$", "rm -rf /"),
        (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+/\*", "rm -rf /*"),
        (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+~/?(\s|$)", "rm -rf ~"),
        (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+\*\s*$", "rm -rf *"),
        (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+\.\s*$", "rm -rf ."),
        (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+\.\./", "rm -rf ../"),
        # Privilege escalation
        (r"\bsudo\b", "sudo command"),
        (r"\bsu\s+-", "su - (switch user)"),
        (r"\bsu\s+root\b", "su root"),
        (r"\bdoas\b", "doas command"),
        (r"\bpkexec\b", "pkexec command"),
        # System modification
        (r"\bchmod\s+777\b", "chmod 777"),
        (r"\bchmod\s+-R\s+777\b", "chmod -R 777"),
        (r"\bchmod\s+[0-7]*777\b", "chmod with 777"),
        (r"\bchown\s+(-R\s+)?root\b", "chown to root"),
        (r"\bdd\s+if=", "dd command (disk destroyer)"),
        (r"\bmkfs\.", "mkfs (filesystem creation)"),
        (r"\bfdisk\b", "fdisk (disk partitioning)"),
        (r"\bparted\b", "parted (disk partitioning)"),
        # Network exfiltration
        (r"\bcurl\s+.*\|\s*(ba)?sh", "curl | sh (remote code execution)"),
        (r"\bwget\s+.*\|\s*(ba)?sh", "wget | sh (remote code execution)"),
        (r"\bcurl\s+.*\|\s*python", "curl | python"),
        (r"\bwget\s+.*\|\s*python", "wget | python"),
        (r"\bnc\s+(-[a-zA-Z]*e|-e)", "nc -e (netcat reverse shell)"),
        (r"\bncat\s+(-[a-zA-Z]*e|-e)", "ncat -e (reverse shell)"),
        (r"\bnetcat\s+(-[a-zA-Z]*e|-e)", "netcat -e (reverse shell)"),
        (r"/dev/tcp/", "/dev/tcp (bash network)"),
        (r"\bsocat\b.*EXEC", "socat EXEC (remote execution)"),
        # History and credential access
        (r"\bcat\s+.*\.ssh/", "cat ~/.ssh (SSH key access)"),
        (r"\bcat\s+.*/etc/passwd\b", "cat /etc/passwd"),
        (r"\bcat\s+.*/etc/shadow\b", "cat /etc/shadow"),
        (r"\bcat\s+.*\.bash_history\b", "cat .bash_history"),
        (r"\bcat\s+.*\.zsh_history\b", "cat .zsh_history"),
        (r"\bhistory\b", "history command"),
        (r"\bcat\s+.*\.env\b", "cat .env (environment secrets)"),
        (r"\bcat\s+.*\.netrc\b", "cat .netrc (credentials)"),
        (r"\bcat\s+.*\.aws/credentials\b", "cat AWS credentials"),
        (r"\bcat\s+.*\.config/gcloud\b", "cat GCloud credentials"),
        # Fork bomb and resource exhaustion
        (r":\(\)\s*\{\s*:\|:&\s*\}\s*;", "fork bomb"),
        (r"\bfork\s*\(\s*\)\s*while", "fork bomb variant"),
        (r"\bwhile\s+true\s*;\s*do\s*:\s*;\s*done", "infinite loop"),
        # Dangerous shell features
        (r"\beval\s+", "eval (arbitrary code execution)"),
        (r"`.*`", "command substitution (backticks)"),
        (r"\$\(.*\)", "command substitution $()"),
        # System destruction
        (r"\b>\s*/dev/sd[a-z]", "overwrite disk device"),
        (r"\bcat\s+.*>\s*/dev/sd[a-z]", "overwrite disk via cat"),
        (r"\bshred\s+", "shred (secure delete)"),
        (r"\bwipe\b", "wipe command"),
        # Kernel/boot manipulation
        (r"\binsmod\b", "insmod (kernel module)"),
        (r"\brmmod\b", "rmmod (kernel module)"),
        (r"\bmodprobe\b", "modprobe (kernel module)"),
        (r"\bsysctl\s+-w", "sysctl -w (kernel params)"),
        # Service manipulation
        (r"\bsystemctl\s+(stop|disable|mask)\s+", "systemctl stop/disable"),
        (r"\bservice\s+\S+\s+stop", "service stop"),
        (r"\bkillall\b", "killall"),
        (r"\bpkill\s+-9", "pkill -9"),
    ]

    # Compile patterns once at class level
    DANGEROUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(pattern, re.IGNORECASE), desc)
        for pattern, desc in DANGEROUS_PATTERN_DEFS
    ]

    # Default allowed commands for restrictive mode
    DEFAULT_ALLOWED_COMMANDS: frozenset[str] = frozenset(
        {
            "ls",
            "cat",
            "head",
            "tail",
            "grep",
            "find",
            "echo",
            "pwd",
            "cd",
            "mkdir",
            "touch",
            "cp",
            "mv",
            "python",
            "python3",
            "pip",
            "pip3",
            "node",
            "npm",
            "npx",
            "git",
            "uv",
            "ruff",
            "pytest",
            "mypy",
            "black",
            "isort",
            "which",
            "whereis",
            "file",
            "wc",
            "sort",
            "uniq",
            "diff",
            "tree",
            "less",
            "more",
            "date",
            "whoami",
            "hostname",
            "env",
            "printenv",
        }
    )

    def __init__(
        self,
        allowlist_mode: bool = False,
        allowed_commands: set[str] | None = None,
        custom_blocked_patterns: list[str] | None = None,
    ) -> None:
        """Initialize the command sanitizer.

        Args:
            allowlist_mode: If True, only explicitly allowed commands pass.
            allowed_commands: Custom set of allowed command prefixes.
            custom_blocked_patterns: Additional regex patterns to block.
        """
        self.allowlist_mode = allowlist_mode
        self.allowed_commands: set[str] = (
            set(allowed_commands)
            if allowed_commands
            else set(self.DEFAULT_ALLOWED_COMMANDS)
        )
        self.custom_blocked_patterns: list[re.Pattern[str]] = []

        if custom_blocked_patterns:
            for pattern in custom_blocked_patterns:
                try:
                    self.custom_blocked_patterns.append(
                        re.compile(pattern, re.IGNORECASE)
                    )
                except re.error as e:
                    logger.warning(f"Invalid custom pattern '{pattern}': {e}")

    def sanitize_command(self, cmd: str) -> tuple[bool, str, list[str]]:
        """Sanitize a shell command and check for dangerous patterns.

        Args:
            cmd: The shell command to sanitize.

        Returns:
            A tuple of (is_safe, sanitized_command, warnings).
            - is_safe: True if the command passed all security checks.
            - sanitized_command: The command (unchanged if safe, empty if blocked).
            - warnings: List of security warnings or blocked pattern descriptions.
        """
        if not cmd or not cmd.strip():
            return True, "", []

        cmd = cmd.strip()
        warnings: list[str] = []
        blocked_patterns: list[str] = []

        # Check allowlist mode first
        if self.allowlist_mode:
            first_word = cmd.split()[0] if cmd.split() else ""
            # Handle command with path (e.g., /usr/bin/python)
            base_cmd = first_word.rsplit("/", 1)[-1]

            if base_cmd not in self.allowed_commands:
                warnings.append(
                    f"Command '{base_cmd}' not in allowlist (allowlist mode enabled)"
                )
                logger.warning(f"Blocked command (allowlist): {cmd[:100]}")
                return False, "", warnings

        # Check for dangerous patterns
        for pattern, description in self.DANGEROUS_PATTERNS:
            if pattern.search(cmd):
                blocked_patterns.append(description)

        # Check custom blocked patterns
        for pattern in self.custom_blocked_patterns:
            if pattern.search(cmd):
                blocked_patterns.append(f"Custom pattern: {pattern.pattern}")

        if blocked_patterns:
            warnings.extend([f"Blocked: {pattern}" for pattern in blocked_patterns])
            logger.warning(
                f"Blocked dangerous command: {cmd[:100]} "
                f"(patterns: {', '.join(blocked_patterns)})"
            )
            return False, "", warnings

        return True, cmd, warnings

    def check_path_traversal(self, path: str) -> bool:
        """Check if a path contains traversal attacks.

        Detects attempts to escape the current directory using '../' sequences
        or absolute paths that might access sensitive locations.

        Args:
            path: The path string to check.

        Returns:
            True if path traversal is detected (unsafe), False if safe.
        """
        if not path:
            return False

        # Normalize the path for analysis
        normalized = path.replace("\\", "/")

        # Check for explicit traversal
        if "../" in normalized or "/.." in normalized:
            return True

        # Check for attempts to access root
        if normalized.startswith("/"):
            # Allow common safe paths
            safe_prefixes = ("/tmp/", "/var/tmp/", "/home/")
            if not any(normalized.startswith(prefix) for prefix in safe_prefixes):
                # Check for sensitive system paths
                sensitive_paths = (
                    "/etc/",
                    "/root/",
                    "/boot/",
                    "/sys/",
                    "/proc/",
                    "/dev/",
                    "/var/log/",
                    "/usr/",
                    "/bin/",
                    "/sbin/",
                )
                if any(normalized.startswith(p) for p in sensitive_paths):
                    return True

        # Check for home directory escape attempts
        if normalized.startswith("~") and ".." in normalized:
            return True

        return False

    def escape_shell_args(self, args: Sequence[str]) -> list[str]:
        """Properly escape shell arguments using shlex.

        Args:
            args: List of argument strings to escape.

        Returns:
            List of properly escaped argument strings.
        """
        return [shlex.quote(arg) for arg in args]

    def get_result(self, cmd: str) -> SanitizationResult:
        """Get a full sanitization result object.

        Args:
            cmd: The command to sanitize.

        Returns:
            SanitizationResult with full details about the sanitization.
        """
        is_safe, sanitized_cmd, warnings = self.sanitize_command(cmd)

        # Extract blocked patterns from warnings
        blocked_patterns = [
            w.replace("Blocked: ", "") for w in warnings if w.startswith("Blocked: ")
        ]

        return SanitizationResult(
            is_safe=is_safe,
            command=sanitized_cmd,
            warnings=warnings,
            blocked_patterns=blocked_patterns,
        )


# Module-level singleton for convenience
_default_sanitizer: CommandSanitizer | None = None


def get_sanitizer() -> CommandSanitizer:
    """Get the default command sanitizer instance.

    Returns:
        The default CommandSanitizer instance.
    """
    global _default_sanitizer
    if _default_sanitizer is None:
        _default_sanitizer = CommandSanitizer()
    return _default_sanitizer


def configure_sanitizer(
    allowlist_mode: bool = False,
    allowed_commands: set[str] | None = None,
    custom_blocked_patterns: list[str] | None = None,
) -> CommandSanitizer:
    """Configure and return a new default sanitizer.

    Args:
        allowlist_mode: If True, only explicitly allowed commands pass.
        allowed_commands: Custom set of allowed command prefixes.
        custom_blocked_patterns: Additional regex patterns to block.

    Returns:
        The newly configured CommandSanitizer instance.
    """
    global _default_sanitizer
    _default_sanitizer = CommandSanitizer(
        allowlist_mode=allowlist_mode,
        allowed_commands=allowed_commands,
        custom_blocked_patterns=custom_blocked_patterns,
    )
    return _default_sanitizer
