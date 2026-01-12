from __future__ import annotations

import difflib
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class HunkStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class DiffHunk:
    id: str
    start_line: int
    end_line: int
    original_lines: list[str]
    proposed_lines: list[str]
    status: HunkStatus = HunkStatus.PENDING
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        start_line: int,
        end_line: int,
        original: list[str],
        proposed: list[str],
        context_before: list[str] | None = None,
        context_after: list[str] | None = None,
    ) -> DiffHunk:
        return cls(
            id=str(uuid.uuid4())[:8],
            start_line=start_line,
            end_line=end_line,
            original_lines=original,
            proposed_lines=proposed,
            context_before=context_before or [],
            context_after=context_after or [],
        )

    @property
    def diff_text(self) -> str:
        lines = []
        for line in self.original_lines:
            lines.append(f"- {line}")
        for line in self.proposed_lines:
            lines.append(f"+ {line}")
        return "\n".join(lines)

    @property
    def additions(self) -> int:
        return len(self.proposed_lines)

    @property
    def deletions(self) -> int:
        return len(self.original_lines)


@dataclass
class ProposedChange:
    file: str
    original: str | None
    proposed: str
    hunks: list[DiffHunk] = field(default_factory=list)
    rationale: str = ""
    is_new_file: bool = False
    is_deletion: bool = False

    @classmethod
    def from_content(
        cls,
        file: str,
        original: str | None,
        proposed: str,
        rationale: str = "",
    ) -> ProposedChange:
        change = cls(
            file=file,
            original=original,
            proposed=proposed,
            rationale=rationale,
            is_new_file=original is None,
            is_deletion=proposed == "",
        )

        if original is not None:
            change.hunks = change._compute_hunks(original, proposed)

        return change

    def _compute_hunks(self, original: str, proposed: str) -> list[DiffHunk]:
        original_lines = original.splitlines(keepends=True)
        proposed_lines = proposed.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, original_lines, proposed_lines)
        hunks: list[DiffHunk] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue

            context_before = original_lines[max(0, i1 - 3) : i1]
            context_after = original_lines[i2 : min(len(original_lines), i2 + 3)]

            hunk = DiffHunk.create(
                start_line=i1 + 1,
                end_line=i2,
                original=[line.rstrip("\n\r") for line in original_lines[i1:i2]],
                proposed=[line.rstrip("\n\r") for line in proposed_lines[j1:j2]],
                context_before=[line.rstrip("\n\r") for line in context_before],
                context_after=[line.rstrip("\n\r") for line in context_after],
            )
            hunks.append(hunk)

        return hunks

    @property
    def total_additions(self) -> int:
        if self.is_new_file:
            return len(self.proposed.splitlines())
        return sum(h.additions for h in self.hunks)

    @property
    def total_deletions(self) -> int:
        if self.is_deletion:
            return len(self.original.splitlines()) if self.original else 0
        return sum(h.deletions for h in self.hunks)

    @property
    def all_accepted(self) -> bool:
        return all(h.status == HunkStatus.ACCEPTED for h in self.hunks)

    @property
    def all_rejected(self) -> bool:
        return all(h.status == HunkStatus.REJECTED for h in self.hunks)

    def apply_accepted(self) -> str:
        if not self.original:
            return self.proposed if self.all_accepted else ""

        original_lines = self.original.splitlines(keepends=True)
        result_lines = list(original_lines)

        offset = 0
        for hunk in sorted(self.hunks, key=lambda h: h.start_line):
            if hunk.status != HunkStatus.ACCEPTED:
                continue

            start = hunk.start_line - 1 + offset
            end = hunk.end_line + offset

            new_lines = [line + "\n" for line in hunk.proposed_lines]
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] = new_lines[-1].rstrip("\n") + "\n"

            result_lines[start:end] = new_lines
            offset += len(hunk.proposed_lines) - len(hunk.original_lines)

        return "".join(result_lines).rstrip("\n")


class ReviewManager:
    def __init__(self):
        self.pending_changes: dict[str, ProposedChange] = {}
        self.review_enabled = True

    def propose(
        self,
        file: str,
        original: str | None,
        proposed: str,
        rationale: str = "",
    ) -> ProposedChange:
        change = ProposedChange.from_content(file, original, proposed, rationale)
        self.pending_changes[file] = change
        return change

    def get_change(self, file: str) -> ProposedChange | None:
        return self.pending_changes.get(file)

    def accept_hunk(self, file: str, hunk_id: str) -> bool:
        change = self.pending_changes.get(file)
        if not change:
            return False

        for hunk in change.hunks:
            if hunk.id == hunk_id:
                hunk.status = HunkStatus.ACCEPTED
                return True
        return False

    def reject_hunk(self, file: str, hunk_id: str) -> bool:
        change = self.pending_changes.get(file)
        if not change:
            return False

        for hunk in change.hunks:
            if hunk.id == hunk_id:
                hunk.status = HunkStatus.REJECTED
                return True
        return False

    def accept_file(self, file: str) -> bool:
        change = self.pending_changes.get(file)
        if not change:
            return False

        for hunk in change.hunks:
            hunk.status = HunkStatus.ACCEPTED
        return True

    def reject_file(self, file: str) -> bool:
        change = self.pending_changes.get(file)
        if not change:
            return False

        for hunk in change.hunks:
            hunk.status = HunkStatus.REJECTED
        return True

    def accept_all(self) -> int:
        count = 0
        for change in self.pending_changes.values():
            for hunk in change.hunks:
                if hunk.status == HunkStatus.PENDING:
                    hunk.status = HunkStatus.ACCEPTED
                    count += 1
        return count

    def reject_all(self) -> int:
        count = 0
        for change in self.pending_changes.values():
            for hunk in change.hunks:
                if hunk.status == HunkStatus.PENDING:
                    hunk.status = HunkStatus.REJECTED
                    count += 1
        return count

    async def apply_accepted(self) -> list[str]:
        applied: list[str] = []

        for file, change in list(self.pending_changes.items()):
            has_accepted = any(h.status == HunkStatus.ACCEPTED for h in change.hunks)
            if not has_accepted and not change.is_new_file:
                continue

            if change.is_new_file and change.all_accepted:
                content = change.proposed
            elif change.is_deletion and change.all_accepted:
                import os

                if os.path.exists(file):
                    os.remove(file)
                applied.append(file)
                del self.pending_changes[file]
                continue
            else:
                content = change.apply_accepted()
                if not content:
                    continue

            try:
                import asyncio
                import os

                os.makedirs(os.path.dirname(file) or ".", exist_ok=True)

                def _write(file=file, content=content):
                    with open(file, "w", encoding="utf-8") as f:
                        f.write(content)

                await asyncio.to_thread(_write)
                applied.append(file)
            except Exception:
                continue

            del self.pending_changes[file]

        return applied

    def clear(self):
        self.pending_changes.clear()

    def get_summary(self) -> str:
        if not self.pending_changes:
            return "No pending changes"

        lines = [f"Pending changes: {len(self.pending_changes)} file(s)"]
        for file, change in self.pending_changes.items():
            accepted = sum(1 for h in change.hunks if h.status == HunkStatus.ACCEPTED)
            rejected = sum(1 for h in change.hunks if h.status == HunkStatus.REJECTED)
            pending = sum(1 for h in change.hunks if h.status == HunkStatus.PENDING)

            status_parts = []
            if accepted:
                status_parts.append(f"{accepted} accepted")
            if rejected:
                status_parts.append(f"{rejected} rejected")
            if pending:
                status_parts.append(f"{pending} pending")

            lines.append(
                f"  {file}: +{change.total_additions}/-{change.total_deletions} ({', '.join(status_parts)})"
            )

        return "\n".join(lines)
