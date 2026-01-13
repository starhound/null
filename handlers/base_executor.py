"""Base executor with common functionality for AI and CLI executors."""

from __future__ import annotations

import asyncio
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from app import NullApp
    from models import BlockState


@dataclass
class ExecutorContext:
    """Dependency injection container decoupling executors from NullApp."""

    notify: Callable[[str], None]
    log: Callable[[str], None]
    auto_save: Callable[[], None]
    set_interval: Callable[[float, Callable[[], None]], Any]
    query_one: Callable[..., Any] | None = None

    @classmethod
    def from_app(cls, app: NullApp) -> ExecutorContext:
        """Factory method to create context from NullApp instance."""
        return cls(
            notify=lambda msg, severity="information": app.notify(  # type: ignore[union-attr]
                msg, severity=severity
            ),
            log=app.log,  # type: ignore[union-attr]
            auto_save=app._auto_save,  # type: ignore[union-attr]
            set_interval=app.set_interval,  # type: ignore[union-attr]
            query_one=getattr(app, "query_one", None),
        )


class BaseExecutor(ABC):
    """Base class providing shared executor functionality."""

    _background_tasks: ClassVar[set[asyncio.Task[None]]] = set()

    def __init__(self, context: ExecutorContext) -> None:
        self._context = context

    def _trigger_auto_save(self) -> None:
        from config import get_settings

        if get_settings().terminal.auto_save_session:
            self._context.auto_save()

    def _index_interaction(self, block: BlockState) -> None:
        try:
            from managers.recall import RecallManager

            recall_manager = RecallManager()
            task = asyncio.create_task(recall_manager.index_interaction(block))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except Exception:
            pass

    def _finalize_block(self, block: BlockState) -> None:
        self._trigger_auto_save()
        self._index_interaction(block)
