import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GitStatus:
    branch: str = ""
    is_dirty: bool = False
    is_repo: bool = False


async def get_git_status(path: Path | None = None) -> GitStatus:
    if not shutil.which("git"):
        return GitStatus()

    cwd = str(path or Path.cwd())

    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "rev-parse",
            "--is-inside-work-tree",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode != 0:
            return GitStatus()

        proc = await asyncio.create_subprocess_exec(
            "git",
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        branch = stdout.decode().strip()

        proc = await asyncio.create_subprocess_exec(
            "git",
            "status",
            "--porcelain",
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        is_dirty = bool(stdout.strip())

        return GitStatus(branch=branch, is_dirty=is_dirty, is_repo=True)
    except Exception:
        return GitStatus()
