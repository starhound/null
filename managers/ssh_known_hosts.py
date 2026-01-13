"""SSH known_hosts verification manager for host key validation."""

import base64
import hashlib
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class HostKeyStatus(Enum):
    """Result of host key verification."""

    VERIFIED = "verified"  # Host key matches known_hosts
    UNKNOWN = "unknown"  # Host not in known_hosts
    MISMATCH = "mismatch"  # Host key differs from known_hosts (MITM warning)
    ERROR = "error"  # Could not verify (file error, etc.)


@dataclass
class HostKeyInfo:
    """Information about a host key."""

    hostname: str
    port: int
    key_type: str  # ssh-rsa, ssh-ed25519, ecdsa-sha2-nistp256, etc.
    key_data: bytes
    status: HostKeyStatus
    fingerprint: str = ""
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Calculate fingerprint if not provided."""
        if not self.fingerprint and self.key_data:
            self.fingerprint = self._calculate_fingerprint()

    def _calculate_fingerprint(self) -> str:
        """Calculate SHA256 fingerprint of the key."""
        digest = hashlib.sha256(self.key_data).digest()
        return f"SHA256:{base64.b64encode(digest).decode().rstrip('=')}"


class KnownHostsManager:
    """Manages SSH known_hosts verification and updates.

    Handles host key verification against ~/.ssh/known_hosts,
    with support for adding new hosts and detecting key changes.
    """

    def __init__(
        self,
        known_hosts_path: str | Path | None = None,
        strict_mode: bool = True,
    ):
        """Initialize the known hosts manager.

        Args:
            known_hosts_path: Path to known_hosts file. Defaults to ~/.ssh/known_hosts
            strict_mode: If True, reject connections to unknown hosts by default
        """
        if known_hosts_path is None:
            self._known_hosts_path = Path.home() / ".ssh" / "known_hosts"
        else:
            self._known_hosts_path = Path(known_hosts_path)

        self._strict_mode = strict_mode
        self._entries: dict[
            str, list[tuple[str, bytes]]
        ] = {}  # host -> [(key_type, key_data)]
        self._loaded = False

        # Callback for user confirmation on unknown hosts
        self._confirm_callback: Callable[[HostKeyInfo], bool] | None = None

    @property
    def known_hosts_path(self) -> Path:
        """Get the known_hosts file path."""
        return self._known_hosts_path

    @property
    def strict_mode(self) -> bool:
        """Get strict mode setting."""
        return self._strict_mode

    def set_confirm_callback(
        self, callback: Callable[[HostKeyInfo], bool] | None
    ) -> None:
        """Set callback for user confirmation on unknown hosts.

        Args:
            callback: Function that receives HostKeyInfo and returns True to accept
        """
        self._confirm_callback = callback

    def load(self) -> bool:
        """Load and parse the known_hosts file.

        Returns:
            True if file was loaded successfully (or doesn't exist), False on error
        """
        self._entries.clear()
        self._loaded = False

        if not self._known_hosts_path.exists():
            logger.info(f"known_hosts file not found: {self._known_hosts_path}")
            self._loaded = True  # Not an error, just empty
            return True

        try:
            with open(self._known_hosts_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    try:
                        self._parse_line(line)
                    except ValueError as e:
                        logger.warning(
                            f"Skipping invalid known_hosts line {line_num}: {e}"
                        )

            self._loaded = True
            logger.info(
                f"Loaded {len(self._entries)} hosts from {self._known_hosts_path}"
            )
            return True

        except PermissionError:
            logger.error(f"Permission denied reading {self._known_hosts_path}")
            return False
        except OSError as e:
            logger.error(f"Error reading known_hosts: {e}")
            return False

    def _parse_line(self, line: str) -> None:
        """Parse a single known_hosts line.

        Format: hostname[,hostname2] key_type base64_key [comment]
        Hashed format: |1|salt|hash key_type base64_key
        """
        parts = line.split()
        if len(parts) < 3:
            raise ValueError("Not enough fields")

        hostnames_str = parts[0]
        key_type = parts[1]
        key_b64 = parts[2]

        try:
            key_data = base64.b64decode(key_b64)
        except Exception as e:
            raise ValueError(f"Invalid base64 key data: {e}")

        # Handle hashed hostnames (starts with |1|)
        if hostnames_str.startswith("|1|"):
            # Hashed entries are stored with their hash as the key
            self._add_entry(hostnames_str, key_type, key_data)
        else:
            # Plain hostnames (may include port in [host]:port format)
            for hostname in hostnames_str.split(","):
                hostname = hostname.strip()
                if hostname:
                    self._add_entry(hostname, key_type, key_data)

    def _add_entry(self, hostname: str, key_type: str, key_data: bytes) -> None:
        """Add an entry to the internal cache."""
        if hostname not in self._entries:
            self._entries[hostname] = []
        self._entries[hostname].append((key_type, key_data))

    def _get_host_key(self, hostname: str, port: int = 22) -> str:
        """Get the lookup key for a host.

        Standard ports use just hostname, non-standard use [host]:port format.
        """
        if port == 22:
            return hostname
        return f"[{hostname}]:{port}"

    def verify_host_key(
        self,
        hostname: str,
        port: int,
        key_type: str,
        key_data: bytes,
    ) -> HostKeyInfo:
        """Verify a host key against known_hosts.

        Args:
            hostname: The host being connected to
            port: SSH port
            key_type: Key algorithm (ssh-rsa, ssh-ed25519, etc.)
            key_data: Raw public key bytes

        Returns:
            HostKeyInfo with verification status
        """
        if not self._loaded:
            self.load()

        host_key = self._get_host_key(hostname, port)
        info = HostKeyInfo(
            hostname=hostname,
            port=port,
            key_type=key_type,
            key_data=key_data,
            status=HostKeyStatus.UNKNOWN,
        )

        # Check direct hostname match
        entries = self._entries.get(host_key, [])

        # Also check hashed entries
        for stored_host, stored_keys in self._entries.items():
            if stored_host.startswith("|1|"):
                if self._check_hashed_host(stored_host, host_key):
                    entries.extend(stored_keys)

        if not entries:
            info.status = HostKeyStatus.UNKNOWN
            logger.warning(
                f"Unknown host: {hostname}:{port} (fingerprint: {info.fingerprint})"
            )
            return info

        # Check if any stored key matches
        for stored_type, stored_data in entries:
            if stored_type == key_type and stored_data == key_data:
                info.status = HostKeyStatus.VERIFIED
                logger.debug(f"Host key verified for {hostname}:{port}")
                return info

        # Key exists but doesn't match - potential MITM
        info.status = HostKeyStatus.MISMATCH
        info.error_message = (
            f"HOST KEY MISMATCH for {hostname}:{port}! "
            "The host key has changed. This could indicate a MITM attack."
        )
        logger.error(info.error_message)
        return info

    def _check_hashed_host(self, hashed_entry: str, hostname: str) -> bool:
        """Check if a hostname matches a hashed known_hosts entry.

        Hashed format: |1|base64_salt|base64_hash
        """
        try:
            parts = hashed_entry.split("|")
            if len(parts) != 4 or parts[1] != "1":
                return False

            salt = base64.b64decode(parts[2])
            stored_hash = base64.b64decode(parts[3])

            # Compute HMAC-SHA1 of hostname with salt
            import hmac

            computed = hmac.new(salt, hostname.encode(), "sha1").digest()
            return hmac.compare_digest(computed, stored_hash)

        except Exception:
            return False

    def add_host_key(
        self,
        hostname: str,
        port: int,
        key_type: str,
        key_data: bytes,
        confirm: bool = True,
    ) -> bool:
        """Add a new host key to known_hosts.

        Args:
            hostname: The host to add
            port: SSH port
            key_type: Key algorithm
            key_data: Raw public key bytes
            confirm: If True, require user confirmation via callback

        Returns:
            True if key was added successfully
        """
        info = HostKeyInfo(
            hostname=hostname,
            port=port,
            key_type=key_type,
            key_data=key_data,
            status=HostKeyStatus.UNKNOWN,
        )

        # Request user confirmation if enabled
        if confirm and self._confirm_callback:
            if not self._confirm_callback(info):
                logger.info(f"User rejected host key for {hostname}:{port}")
                return False

        # Ensure .ssh directory exists
        ssh_dir = self._known_hosts_path.parent
        try:
            ssh_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(ssh_dir, 0o700)
        except OSError as e:
            logger.error(f"Failed to create .ssh directory: {e}")
            return False

        # Format the entry
        host_key = self._get_host_key(hostname, port)
        key_b64 = base64.b64encode(key_data).decode()
        entry = f"{host_key} {key_type} {key_b64}\n"

        try:
            with open(self._known_hosts_path, "a") as f:
                f.write(entry)

            # Set proper permissions
            os.chmod(self._known_hosts_path, 0o644)

            # Update cache
            self._add_entry(host_key, key_type, key_data)

            logger.info(
                f"Added host key for {hostname}:{port} "
                f"(fingerprint: {info.fingerprint})"
            )
            return True

        except PermissionError:
            logger.error(f"Permission denied writing to {self._known_hosts_path}")
            return False
        except OSError as e:
            logger.error(f"Error writing to known_hosts: {e}")
            return False

    def remove_host_key(self, hostname: str, port: int = 22) -> bool:
        """Remove all entries for a host from known_hosts.

        Args:
            hostname: The host to remove
            port: SSH port

        Returns:
            True if entries were removed
        """
        if not self._known_hosts_path.exists():
            return False

        host_key = self._get_host_key(hostname, port)
        removed = False

        try:
            with open(self._known_hosts_path, "r") as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith("#"):
                    new_lines.append(line)
                    continue

                parts = line_stripped.split()
                if parts:
                    hostnames = parts[0].split(",")
                    if host_key not in hostnames:
                        new_lines.append(line)
                    else:
                        removed = True

            if removed:
                with open(self._known_hosts_path, "w") as f:
                    f.writelines(new_lines)

                # Update cache
                if host_key in self._entries:
                    del self._entries[host_key]

                logger.info(f"Removed host key entries for {hostname}:{port}")

            return removed

        except OSError as e:
            logger.error(f"Error removing host key: {e}")
            return False

    def get_host_fingerprint(self, hostname: str, port: int = 22) -> str | None:
        """Get the stored fingerprint for a host.

        Args:
            hostname: The host to look up
            port: SSH port

        Returns:
            SHA256 fingerprint string or None if not found
        """
        if not self._loaded:
            self.load()

        host_key = self._get_host_key(hostname, port)
        entries = self._entries.get(host_key, [])

        if entries:
            key_type, key_data = entries[0]
            digest = hashlib.sha256(key_data).digest()
            return f"SHA256:{base64.b64encode(digest).decode().rstrip('=')}"

        return None

    def list_known_hosts(self) -> list[str]:
        """List all known hostnames.

        Returns:
            List of hostname strings (may include [host]:port format)
        """
        if not self._loaded:
            self.load()

        return [
            h
            for h in self._entries.keys()
            if not h.startswith("|1|")  # Exclude hashed entries
        ]
