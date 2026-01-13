"""Enhanced file tree widget with icons, recent files, and file operations."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, DirectoryTree, Label, Static
from textual.widgets._tree import TreeNode

if TYPE_CHECKING:
    pass


# File type icons mapping
FILE_ICONS: dict[str, str] = {
    # Programming languages
    ".py": "",
    ".pyi": "",
    ".pyw": "",
    ".js": "",
    ".mjs": "",
    ".cjs": "",
    ".ts": "",
    ".tsx": "",
    ".jsx": "",
    ".go": "",
    ".rs": "",
    ".rb": "",
    ".php": "",
    ".java": "",
    ".kt": "",
    ".kts": "",
    ".scala": "",
    ".c": "",
    ".h": "",
    ".cpp": "",
    ".hpp": "",
    ".cs": "",
    ".swift": "",
    ".lua": "",
    ".r": "",
    ".R": "",
    ".pl": "",
    ".pm": "",
    ".sh": "",
    ".bash": "",
    ".zsh": "",
    ".fish": "",
    ".ps1": "",
    ".vim": "",
    ".ex": "",
    ".exs": "",
    ".erl": "",
    ".hs": "",
    ".clj": "",
    ".lisp": "",
    ".el": "",
    # Web
    ".html": "",
    ".htm": "",
    ".css": "",
    ".scss": "",
    ".sass": "",
    ".less": "",
    ".vue": "",
    ".svelte": "",
    # Data/Config
    ".json": "",
    ".yaml": "",
    ".yml": "",
    ".toml": "",
    ".xml": "",
    ".csv": "",
    ".ini": "",
    ".cfg": "",
    ".conf": "",
    ".env": "",
    # Documentation
    ".md": "",
    ".markdown": "",
    ".rst": "",
    ".txt": "",
    ".doc": "",
    ".docx": "",
    ".pdf": "",
    # Images
    ".png": "",
    ".jpg": "",
    ".jpeg": "",
    ".gif": "",
    ".svg": "",
    ".ico": "",
    ".webp": "",
    ".bmp": "",
    # Media
    ".mp3": "",
    ".wav": "",
    ".flac": "",
    ".mp4": "",
    ".avi": "",
    ".mkv": "",
    ".mov": "",
    # Archives
    ".zip": "",
    ".tar": "",
    ".gz": "",
    ".rar": "",
    ".7z": "",
    ".bz2": "",
    # Database
    ".sql": "",
    ".db": "",
    ".sqlite": "",
    ".sqlite3": "",
    # Docker/Container
    "Dockerfile": "",
    ".dockerfile": "",
    "docker-compose.yml": "",
    "docker-compose.yaml": "",
    # Git
    ".gitignore": "",
    ".gitattributes": "",
    ".gitmodules": "",
    # Build/Package
    "Makefile": "",
    "CMakeLists.txt": "",
    "requirements.txt": "",
    "pyproject.toml": "",
    "package.json": "",
    "cargo.toml": "",
    "go.mod": "",
    "Gemfile": "",
    # Lock files
    ".lock": "",
    "package-lock.json": "",
    "yarn.lock": "",
    "poetry.lock": "",
    "Cargo.lock": "",
    # Logs
    ".log": "",
    # Binaries/Executables
    ".exe": "",
    ".bin": "",
    ".so": "",
    ".dll": "",
    # Keys/Certs
    ".pem": "",
    ".key": "",
    ".crt": "",
    ".pub": "",
    # Misc
    "LICENSE": "",
    "README": "",
    "CHANGELOG": "",
}

# Default icons
DEFAULT_FILE_ICON = ""
FOLDER_ICON = ""
FOLDER_OPEN_ICON = ""


def get_file_icon(path: Path) -> str:
    """Get icon for a file based on its extension or name."""
    name = path.name

    if name in FILE_ICONS:
        return FILE_ICONS[name]

    suffix = path.suffix.lower()
    if suffix in FILE_ICONS:
        return FILE_ICONS[suffix]

    if name.startswith(".") and suffix == "":
        return ""

    return DEFAULT_FILE_ICON


class RecentFileEntry:
    """Represents a recently accessed file."""

    def __init__(self, path: Path, accessed_at: datetime | None = None):
        self.path = path
        self.accessed_at = accessed_at or datetime.now()

    @property
    def display_name(self) -> str:
        """Get display name with icon."""
        icon = get_file_icon(self.path)
        return f"{icon} {self.path.name}"

    @property
    def relative_path(self) -> str:
        """Get path relative to cwd if possible."""
        try:
            return str(self.path.relative_to(Path.cwd()))
        except ValueError:
            return str(self.path)


class EnhancedDirectoryTree(DirectoryTree):
    """DirectoryTree with file type icons."""

    def render_label(self, node: TreeNode[Path], base_style, style) -> str:
        """Render node label with appropriate icon."""
        path = node.data
        if path is None:
            return ""

        if path.is_dir():
            icon = FOLDER_OPEN_ICON if node.is_expanded else FOLDER_ICON
            return f"{icon} {path.name}"
        else:
            icon = get_file_icon(path)
            return f"{icon} {path.name}"


class FileTreeWidget(Static):
    """Enhanced file tree widget with navigation and operations."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("enter", "open_file", "Open"),
        Binding("delete", "delete_file", "Delete"),
        Binding("f2", "rename_file", "Rename"),
        Binding("n", "new_file", "New File"),
        Binding("N", "new_directory", "New Dir"),
        Binding("r", "refresh", "Refresh"),
        Binding(".", "toggle_hidden", "Toggle Hidden"),
        Binding("backspace", "go_up", "Parent Dir"),
        Binding("~", "go_home", "Home"),
    ]

    show_hidden = reactive(False)
    current_path = reactive(Path.cwd())

    class FileSelected(Message):
        """Posted when a file is selected."""

        def __init__(self, path: Path):
            super().__init__()
            self.path = path

    class FileOpened(Message):
        """Posted when a file is opened (double-click/enter)."""

        def __init__(self, path: Path):
            super().__init__()
            self.path = path

    class FileDeleteRequested(Message):
        """Posted when file deletion is requested."""

        def __init__(self, path: Path):
            super().__init__()
            self.path = path

    class FileRenameRequested(Message):
        """Posted when file rename is requested."""

        def __init__(self, path: Path, new_name: str):
            super().__init__()
            self.path = path
            self.new_name = new_name

    class NewFileRequested(Message):
        """Posted when new file creation is requested."""

        def __init__(self, parent_dir: Path, name: str):
            super().__init__()
            self.parent_dir = parent_dir
            self.name = name

    class NewDirectoryRequested(Message):
        """Posted when new directory creation is requested."""

        def __init__(self, parent_dir: Path, name: str):
            super().__init__()
            self.parent_dir = parent_dir
            self.name = name

    class DirectoryChanged(Message):
        """Posted when current directory changes."""

        def __init__(self, path: Path):
            super().__init__()
            self.path = path

    def __init__(self, path: str | Path = "."):
        super().__init__(id="file-tree-widget")
        self._initial_path = Path(path).resolve()
        self.current_path = self._initial_path

    def compose(self) -> ComposeResult:
        with Vertical(id="file-tree-container"):
            with Horizontal(id="file-tree-toolbar"):
                yield Button("", id="btn-go-up", classes="file-tree-btn")
                yield Button("", id="btn-go-home", classes="file-tree-btn")
                yield Button("", id="btn-refresh", classes="file-tree-btn")
                yield Button("", id="btn-toggle-hidden", classes="file-tree-btn")
            yield Label(str(self.current_path), id="current-path-label")
            yield EnhancedDirectoryTree(str(self.current_path), id="dir-tree")

    def on_mount(self) -> None:
        """Initialize the tree."""
        self._update_path_label()

    def _update_path_label(self) -> None:
        """Update the current path label."""
        try:
            label = self.query_one("#current-path-label", Label)
            path_str = str(self.current_path)
            if len(path_str) > 28:
                path_str = "..." + path_str[-25:]
            label.update(path_str)
        except Exception:
            pass

    def watch_current_path(self, path: Path) -> None:
        """React to path changes."""
        self._update_path_label()
        try:
            tree = self.query_one("#dir-tree", EnhancedDirectoryTree)
            tree.path = path
        except Exception:
            pass

    def watch_show_hidden(self, show: bool) -> None:
        """Toggle hidden files visibility."""
        try:
            tree = self.query_one("#dir-tree", EnhancedDirectoryTree)
            tree.show_root = show
            tree.reload()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle toolbar button presses."""
        button_id = event.button.id or ""

        if button_id == "btn-go-up":
            self.action_go_up()
        elif button_id == "btn-go-home":
            self.action_go_home()
        elif button_id == "btn-refresh":
            self.action_refresh()
        elif button_id == "btn-toggle-hidden":
            self.action_toggle_hidden()

        event.stop()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection in tree."""
        self.post_message(self.FileSelected(event.path))
        self.post_message(self.FileOpened(event.path))
        event.stop()

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Handle directory selection (navigate into it on double-click behavior)."""
        event.stop()

    def action_open_file(self) -> None:
        """Open the currently selected file."""
        try:
            tree = self.query_one("#dir-tree", EnhancedDirectoryTree)
            node = tree.cursor_node
            if node and node.data:
                path = node.data
                if path.is_file():
                    self.post_message(self.FileOpened(path))
                elif path.is_dir():
                    self.current_path = path
                    self.post_message(self.DirectoryChanged(path))
        except Exception:
            pass

    def action_delete_file(self) -> None:
        """Request deletion of selected file."""
        try:
            tree = self.query_one("#dir-tree", EnhancedDirectoryTree)
            node = tree.cursor_node
            if node and node.data and node.data.exists():
                self.post_message(self.FileDeleteRequested(node.data))
        except Exception:
            pass

    def action_rename_file(self) -> None:
        """Request rename of selected file."""
        try:
            tree = self.query_one("#dir-tree", EnhancedDirectoryTree)
            node = tree.cursor_node
            if node and node.data:
                self.app.notify("Press F2 on a file to rename (dialog not shown)")
        except Exception:
            pass

    def action_new_file(self) -> None:
        """Request creation of new file."""
        self.app.notify("Use 'touch <filename>' to create a new file")

    def action_new_directory(self) -> None:
        """Request creation of new directory."""
        self.app.notify("Use 'mkdir <dirname>' to create a new directory")

    def action_refresh(self) -> None:
        """Refresh the tree."""
        try:
            tree = self.query_one("#dir-tree", EnhancedDirectoryTree)
            tree.reload()
            self.app.notify("File tree refreshed")
        except Exception:
            pass

    def action_toggle_hidden(self) -> None:
        """Toggle display of hidden files."""
        self.show_hidden = not self.show_hidden
        state = "shown" if self.show_hidden else "hidden"
        self.app.notify(f"Hidden files {state}")

    def action_go_up(self) -> None:
        """Navigate to parent directory."""
        parent = self.current_path.parent
        if parent != self.current_path:
            self.current_path = parent
            self.post_message(self.DirectoryChanged(parent))

    def action_go_home(self) -> None:
        """Navigate to home directory."""
        home = Path.home()
        self.current_path = home
        self.post_message(self.DirectoryChanged(home))

    def navigate_to(self, path: Path) -> None:
        """Navigate to a specific path."""
        if path.is_dir():
            self.current_path = path.resolve()
            self.post_message(self.DirectoryChanged(self.current_path))
        elif path.is_file():
            self.current_path = path.parent.resolve()
            self.post_message(self.DirectoryChanged(self.current_path))


class RecentFilesWidget(Static):
    """Widget displaying recently accessed files."""

    MAX_RECENT: ClassVar[int] = 10

    class FileSelected(Message):
        """Posted when a recent file is selected."""

        def __init__(self, path: Path):
            super().__init__()
            self.path = path

    def __init__(self):
        super().__init__(id="recent-files-widget")
        self._recent_files: deque[RecentFileEntry] = deque(maxlen=self.MAX_RECENT)

    def compose(self) -> ComposeResult:
        with Vertical(id="recent-files-container"):
            yield Label("Recent Files", id="recent-files-header")
            with ScrollableContainer(id="recent-files-list"):
                yield Static("No recent files", id="recent-files-placeholder")

    def add_file(self, path: Path) -> None:
        """Add a file to the recent list."""
        if not path.exists() or not path.is_file():
            return

        resolved = path.resolve()

        self._recent_files = deque(
            (f for f in self._recent_files if f.path != resolved),
            maxlen=self.MAX_RECENT,
        )
        self._recent_files.appendleft(RecentFileEntry(resolved))
        self._refresh_list()

    def _refresh_list(self) -> None:
        """Refresh the displayed list."""
        try:
            container = self.query_one("#recent-files-list", ScrollableContainer)
            container.remove_children()

            if not self._recent_files:
                container.mount(
                    Static("No recent files", id="recent-files-placeholder")
                )
                return

            for entry in self._recent_files:
                item = RecentFileItem(entry)
                container.mount(item)

        except Exception:
            pass

    def clear(self) -> None:
        """Clear all recent files."""
        self._recent_files.clear()
        self._refresh_list()


class RecentFileItem(Static):
    """Individual item in the recent files list."""

    def __init__(self, entry: RecentFileEntry):
        super().__init__(classes="recent-file-item")
        self.entry = entry

    def compose(self) -> ComposeResult:
        icon = get_file_icon(self.entry.path)
        yield Label(f"{icon} {self.entry.path.name}", classes="recent-file-name")
        yield Label(self.entry.relative_path, classes="recent-file-path")

    def on_click(self) -> None:
        """Handle click on recent file."""
        self.post_message(RecentFilesWidget.FileSelected(self.entry.path))


class FileBrowserWidget(Static):
    """Combined file browser with tree and recent files."""

    class FileOpened(Message):
        """Posted when a file should be opened."""

        def __init__(self, path: Path):
            super().__init__()
            self.path = path

    def __init__(self, path: str | Path = "."):
        super().__init__(id="file-browser-widget")
        self._initial_path = Path(path).resolve()

    def compose(self) -> ComposeResult:
        with Vertical(id="file-browser-container"):
            yield RecentFilesWidget()
            yield FileTreeWidget(self._initial_path)

    def on_file_tree_widget_file_opened(self, event: FileTreeWidget.FileOpened) -> None:
        """Forward file opened events and track in recent."""
        try:
            recent = self.query_one(RecentFilesWidget)
            recent.add_file(event.path)
        except Exception:
            pass
        self.post_message(self.FileOpened(event.path))

    def on_recent_files_widget_file_selected(
        self, event: RecentFilesWidget.FileSelected
    ) -> None:
        """Handle selection from recent files."""
        self.post_message(self.FileOpened(event.path))

    def add_to_recent(self, path: Path) -> None:
        """Add a file to recent files from external source."""
        try:
            recent = self.query_one(RecentFilesWidget)
            recent.add_file(path)
        except Exception:
            pass

    def navigate_to(self, path: Path) -> None:
        """Navigate the tree to a path."""
        try:
            tree = self.query_one(FileTreeWidget)
            tree.navigate_to(path)
        except Exception:
            pass

    def refresh(self) -> None:
        """Refresh the file tree."""
        try:
            tree = self.query_one(FileTreeWidget)
            tree.action_refresh()
        except Exception:
            pass
