"""MCP sandbox for file system and network access restrictions."""

import ipaddress
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default blocked paths - sensitive directories that should never be accessible
DEFAULT_BLOCKED_PATHS = [
    "~/.ssh",
    "~/.gnupg",
    "~/.aws",
    "~/.config/gcloud",
    "~/.azure",
    "~/.kube",
    "~/.docker/config.json",
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "~/.netrc",
    "~/.git-credentials",
    "~/.npmrc",
    "~/.pypirc",
]

# Internal/private IP ranges that should be blocked by default
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


@dataclass
class SandboxConfig:
    """Configuration for sandbox restrictions."""

    enabled: bool = True
    allowed_paths: list[str] = field(default_factory=lambda: ["./"])
    blocked_paths: list[str] = field(default_factory=list)
    allowed_hosts: list[str] = field(default_factory=list)
    allow_network: bool = True
    block_private_ips: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SandboxConfig":
        """Create SandboxConfig from dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            allowed_paths=data.get("allowed_paths", ["./"]),
            blocked_paths=data.get("blocked_paths", []),
            allowed_hosts=data.get("allowed_hosts", []),
            allow_network=data.get("allow_network", True),
            block_private_ips=data.get("block_private_ips", True),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "enabled": self.enabled,
            "allowed_paths": self.allowed_paths,
            "blocked_paths": self.blocked_paths,
            "allowed_hosts": self.allowed_hosts,
            "allow_network": self.allow_network,
            "block_private_ips": self.block_private_ips,
        }


@dataclass
class SandboxViolation:
    """Represents a sandbox violation."""

    violation_type: str  # "file" or "network"
    resource: str  # path or host:port
    operation: str  # "read", "write", "connect", etc.
    reason: str  # Human-readable explanation
    server_name: str | None = None


class MCPSandbox:
    """Sandbox for validating MCP tool access to files and network."""

    def __init__(
        self,
        config: SandboxConfig | None = None,
        working_dir: Path | None = None,
    ):
        self.config = config or SandboxConfig()
        self.working_dir = working_dir or Path.cwd()
        self._violations: list[SandboxViolation] = []

        # Combine default blocked paths with config blocked paths
        self._blocked_paths = self._resolve_paths(
            DEFAULT_BLOCKED_PATHS + self.config.blocked_paths
        )
        self._allowed_paths = self._resolve_paths(self.config.allowed_paths)

    def _resolve_paths(self, paths: list[str]) -> list[Path]:
        """Resolve path patterns to absolute paths."""
        resolved = []
        for p in paths:
            # Expand ~ and environment variables
            expanded = os.path.expanduser(os.path.expandvars(p))

            # Handle relative paths
            if not os.path.isabs(expanded):
                if expanded == "./":
                    expanded = str(self.working_dir)
                else:
                    expanded = str(self.working_dir / expanded)

            try:
                resolved.append(Path(expanded).resolve())
            except (OSError, ValueError):
                # Skip invalid paths
                continue

        return resolved

    def _normalize_path(self, path: str) -> Path:
        """Normalize a path string to absolute Path."""
        expanded = os.path.expanduser(os.path.expandvars(path))
        if not os.path.isabs(expanded):
            expanded = str(self.working_dir / expanded)
        return Path(expanded).resolve()

    def _is_path_under(self, path: Path, parent: Path) -> bool:
        """Check if path is under parent directory."""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    def validate_file_access(
        self, path: str, operation: str = "read", server_name: str | None = None
    ) -> bool:
        """
        Validate if file access is allowed.

        Args:
            path: File path to validate
            operation: Type of operation ("read", "write", "delete", "list")
            server_name: Optional server name for logging

        Returns:
            True if access is allowed, False otherwise
        """
        if not self.config.enabled:
            return True

        try:
            normalized = self._normalize_path(path)
        except (OSError, ValueError) as e:
            self._log_violation(
                "file", path, operation, f"Invalid path: {e}", server_name
            )
            return False

        # Check blocked paths first (highest priority)
        for blocked in self._blocked_paths:
            if self._is_path_under(normalized, blocked) or normalized == blocked:
                self._log_violation(
                    "file",
                    path,
                    operation,
                    f"Path is in blocked list: {blocked}",
                    server_name,
                )
                return False

        # Check if path is within allowed paths
        is_allowed = False
        for allowed in self._allowed_paths:
            if self._is_path_under(normalized, allowed) or normalized == allowed:
                is_allowed = True
                break

        if not is_allowed and self._allowed_paths:
            self._log_violation(
                "file",
                path,
                operation,
                "Path is not within allowed directories",
                server_name,
            )
            return False

        return True

    def validate_network_access(
        self, host: str, port: int = 80, server_name: str | None = None
    ) -> bool:
        """
        Validate if network access is allowed.

        Args:
            host: Hostname or IP address
            port: Port number
            server_name: Optional server name for logging

        Returns:
            True if access is allowed, False otherwise
        """
        if not self.config.enabled:
            return True

        if not self.config.allow_network:
            self._log_violation(
                "network",
                f"{host}:{port}",
                "connect",
                "Network access is disabled",
                server_name,
            )
            return False

        # Check if host is in allowed hosts (bypass all other checks)
        if self.config.allowed_hosts:
            for allowed in self.config.allowed_hosts:
                if self._match_host(host, allowed):
                    return True

        # Check for private IP addresses
        if self.config.block_private_ips:
            if self._is_private_ip(host):
                self._log_violation(
                    "network",
                    f"{host}:{port}",
                    "connect",
                    "Access to private/internal IPs is blocked",
                    server_name,
                )
                return False

        return True

    def _match_host(self, host: str, pattern: str) -> bool:
        """Check if host matches a pattern (supports wildcards)."""
        # Convert wildcard pattern to regex
        regex_pattern = pattern.replace(".", r"\.").replace("*", r".*")
        return bool(re.match(f"^{regex_pattern}$", host, re.IGNORECASE))

    def _is_private_ip(self, host: str) -> bool:
        """Check if host resolves to a private IP address."""
        try:
            ip = ipaddress.ip_address(host)
            for network in PRIVATE_IP_RANGES:
                if ip in network:
                    return True
            return False
        except ValueError:
            # Not an IP address, it's a hostname
            # For hostnames like "localhost", we block them
            if host.lower() in ("localhost", "localhost.localdomain"):
                return True
            return False

    def _log_violation(
        self,
        violation_type: str,
        resource: str,
        operation: str,
        reason: str,
        server_name: str | None,
    ):
        """Log a sandbox violation."""
        violation = SandboxViolation(
            violation_type=violation_type,
            resource=resource,
            operation=operation,
            reason=reason,
            server_name=server_name,
        )
        self._violations.append(violation)

        server_info = f" [{server_name}]" if server_name else ""
        logger.warning(
            f"Sandbox violation{server_info}: {violation_type} access to "
            f"'{resource}' ({operation}) denied - {reason}"
        )

    def get_violations(self) -> list[SandboxViolation]:
        """Get list of recorded violations."""
        return self._violations.copy()

    def clear_violations(self):
        """Clear recorded violations."""
        self._violations.clear()

    def redact_file_content(
        self, path: str, content: str, server_name: str | None = None
    ) -> str:
        """
        Redact file content if path is blocked.

        Args:
            path: File path
            content: File content to potentially redact
            server_name: Optional server name for logging

        Returns:
            Original content if allowed, redacted message otherwise
        """
        if self.validate_file_access(path, "read", server_name):
            return content

        return f"[REDACTED: Access to '{path}' is blocked by sandbox policy]"

    def filter_tool_result(self, result: Any, server_name: str | None = None) -> Any:
        """
        Filter tool result for sensitive content.

        Scans result for file paths and redacts blocked content.

        Args:
            result: Tool result to filter
            server_name: Optional server name for logging

        Returns:
            Filtered result with blocked content redacted
        """
        if not self.config.enabled:
            return result

        if isinstance(result, dict):
            return self._filter_dict(result, server_name)
        elif isinstance(result, list):
            return [self.filter_tool_result(item, server_name) for item in result]
        elif isinstance(result, str):
            return self._filter_string(result, server_name)

        return result

    def _filter_dict(self, data: dict, server_name: str | None) -> dict:
        """Filter dictionary for sensitive content."""
        filtered = {}
        for key, value in data.items():
            # Check if this looks like file content
            if key in ("content", "text", "data") and isinstance(value, str):
                # Look for path indicators in the dict
                path = data.get("path") or data.get("uri") or data.get("file")
                if path and isinstance(path, str):
                    filtered[key] = self.redact_file_content(path, value, server_name)
                else:
                    filtered[key] = self.filter_tool_result(value, server_name)
            else:
                filtered[key] = self.filter_tool_result(value, server_name)
        return filtered

    def _filter_string(self, text: str, server_name: str | None) -> str:
        """Filter string content for obvious sensitive data patterns."""
        # Check for embedded file paths that might contain sensitive data
        # This is a basic heuristic - real implementation might need more
        for blocked in self._blocked_paths:
            blocked_str = str(blocked)
            if blocked_str in text:
                text = text.replace(
                    blocked_str,
                    f"[REDACTED: {blocked_str}]",
                )
        return text

    def with_overrides(self, overrides: dict[str, Any]) -> "MCPSandbox":
        """
        Create a new sandbox with configuration overrides.

        Used for per-server sandbox configuration.

        Args:
            overrides: Dictionary of configuration overrides

        Returns:
            New MCPSandbox instance with merged configuration
        """
        config_dict = self.config.to_dict()

        for key, value in overrides.items():
            if key in config_dict:
                if isinstance(value, list) and isinstance(config_dict[key], list):
                    config_dict[key] = config_dict[key] + value
                else:
                    config_dict[key] = value

        new_config = SandboxConfig.from_dict(config_dict)
        return MCPSandbox(config=new_config, working_dir=self.working_dir)


_sandbox: MCPSandbox | None = None


def get_sandbox() -> MCPSandbox:
    """Get the global sandbox instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = MCPSandbox()
    return _sandbox


def configure_sandbox(config: SandboxConfig) -> MCPSandbox:
    """Configure and return the global sandbox."""
    global _sandbox
    _sandbox = MCPSandbox(config=config)
    return _sandbox
