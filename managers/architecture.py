"""Architecture mapping system for project structure visualization."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Literal


@dataclass
class Component:
    """Represents a code component (module, class, function, etc.)."""

    name: str
    path: str
    type: Literal["module", "class", "function", "file", "directory"]
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def __hash__(self):
        """Make component hashable for set operations."""
        return hash((self.name, self.path))

    def __eq__(self, other):
        """Compare components by name and path."""
        if not isinstance(other, Component):
            return False
        return self.name == other.name and self.path == other.path


@dataclass
class ArchitectureMap:
    """Represents the complete architecture of a project."""

    components: list[Component] = field(default_factory=list)
    relationships: list[tuple[str, str, str]] = field(
        default_factory=list
    )  # (from, to, type)
    layers: dict[str, list[str]] = field(default_factory=dict)  # Logical groupings


class ArchitectureMapper:
    """Generates project architecture diagrams and analysis."""

    DEFAULT_IGNORE: ClassVar[list[str]] = [
        "__pycache__",
        "node_modules",
        ".git",
        ".venv",
        "venv",
        "*.pyc",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".vscode",
        ".claude",
        "coverage_html",
        "__pycache__",
    ]

    def __init__(self, root_path: Path | None = None):
        """Initialize the architecture mapper.

        Args:
            root_path: Root directory to scan. Defaults to current working directory.
        """
        self.root = root_path or Path.cwd()
        self.ignore_patterns = list(self.DEFAULT_IGNORE)

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern.startswith("*"):
                # Handle wildcard patterns like *.pyc
                if path.name.endswith(pattern[1:]):
                    return True
            elif path.name == pattern or path.name.startswith(pattern):
                return True
        return False

    def _extract_python_info(self, file_path: Path) -> tuple[list[str], list[str]]:
        """Extract imports and exports from a Python file using AST.

        Args:
            file_path: Path to the Python file.

        Returns:
            Tuple of (imports, exports) lists.
        """
        imports = []
        exports = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Extract imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                    for alias in node.names:
                        if alias.name != "*":
                            imports.append(f"{node.module}.{alias.name}")

                # Extract exports (top-level classes and functions)
                elif isinstance(
                    node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    if isinstance(node, ast.ClassDef):
                        exports.append(f"{node.name}:class")
                    else:
                        exports.append(f"{node.name}:function")

            # Remove duplicates while preserving order
            imports = list(dict.fromkeys(imports))
            exports = list(dict.fromkeys(exports))

        except (SyntaxError, UnicodeDecodeError):
            # Skip files that can't be parsed
            pass

        return imports, exports

    async def scan(
        self, path: Path | None = None, max_depth: int = 3
    ) -> ArchitectureMap:
        """Scan directory and build architecture map.

        Args:
            path: Path to scan. Defaults to root.
            max_depth: Maximum directory depth to scan.

        Returns:
            ArchitectureMap with components and relationships.
        """
        scan_path = path or self.root
        arch_map = ArchitectureMap()
        components_by_path: dict[str, Component] = {}

        def _scan_recursive(current_path: Path, depth: int = 0):
            """Recursively scan directories."""
            if depth > max_depth or self._should_ignore(current_path):
                return

            try:
                items = sorted(current_path.iterdir())
            except (PermissionError, OSError):
                return

            for item in items:
                if self._should_ignore(item):
                    continue

                if item.is_dir():
                    # Create directory component
                    rel_path = str(item.relative_to(self.root))
                    component = Component(
                        name=item.name,
                        path=rel_path,
                        type="directory",
                    )
                    arch_map.components.append(component)
                    components_by_path[rel_path] = component

                    # Recurse into subdirectory
                    _scan_recursive(item, depth + 1)

                elif item.suffix == ".py":
                    # Create module component
                    rel_path = str(item.relative_to(self.root))
                    imports, exports = self._extract_python_info(item)

                    component = Component(
                        name=item.stem,
                        path=rel_path,
                        type="module",
                        imports=imports,
                        exports=exports,
                    )
                    arch_map.components.append(component)
                    components_by_path[rel_path] = component

        _scan_recursive(scan_path)

        # Build relationships
        arch_map.relationships = self._build_relationships(arch_map.components)

        # Organize into layers
        arch_map.layers = self._organize_layers(arch_map.components)

        return arch_map

    def _build_relationships(
        self, components: list[Component]
    ) -> list[tuple[str, str, str]]:
        """Build import/dependency relationships between components.

        Args:
            components: List of components to analyze.

        Returns:
            List of (from, to, type) tuples representing relationships.
        """
        relationships = []

        for component in components:
            if component.type != "module":
                continue

            for import_name in component.imports:
                # Try to find matching component
                for other in components:
                    if other.type != "module" or other.path == component.path:
                        continue

                    # Check if import matches this component
                    if import_name in other.exports or import_name.startswith(
                        other.name
                    ):
                        relationships.append((component.path, other.path, "imports"))
                        break

        return relationships

    def _organize_layers(self, components: list[Component]) -> dict[str, list[str]]:
        """Organize components into logical layers.

        Args:
            components: List of components.

        Returns:
            Dictionary mapping layer names to component paths.
        """
        layers: dict[str, list[str]] = {
            "core": [],
            "managers": [],
            "commands": [],
            "handlers": [],
            "widgets": [],
            "screens": [],
            "ai": [],
            "config": [],
            "utils": [],
            "other": [],
        }

        for component in components:
            path = component.path
            if "managers" in path:
                layers["managers"].append(path)
            elif "commands" in path:
                layers["commands"].append(path)
            elif "handlers" in path:
                layers["handlers"].append(path)
            elif "widgets" in path:
                layers["widgets"].append(path)
            elif "screens" in path:
                layers["screens"].append(path)
            elif "ai" in path:
                layers["ai"].append(path)
            elif "config" in path:
                layers["config"].append(path)
            elif "utils" in path:
                layers["utils"].append(path)
            elif path in ["app.py", "main.py", "executor.py", "context.py"]:
                layers["core"].append(path)
            else:
                layers["other"].append(path)

        # Remove empty layers
        return {k: v for k, v in layers.items() if v}

    def to_ascii(self, arch_map: ArchitectureMap, max_width: int = 80) -> str:
        """Generate ASCII box diagram of architecture.

        Args:
            arch_map: Architecture map to visualize.
            max_width: Maximum width of output.

        Returns:
            ASCII diagram as string.
        """
        lines = []

        # Header
        title = "📊 Project Architecture: null-terminal"
        lines.append("┌" + "─" * (max_width - 2) + "┐")
        lines.append(f"│ {title:<{max_width - 3}}│")
        lines.append("├" + "─" * (max_width - 2) + "┤")

        # Layers section
        if arch_map.layers:
            lines.append(
                "│ Layers:                                                              │"
            )
            for layer_name, components in arch_map.layers.items():
                count = len(components)
                layer_line = f"│   • {layer_name:<20} ({count:2d} components)"
                lines.append(f"{layer_line:<{max_width - 1}}│")

        lines.append(
            "│                                                                      │"
        )

        # Components summary
        lines.append(f"│ Total Components: {len(arch_map.components):<45}│")
        lines.append(f"│ Total Relationships: {len(arch_map.relationships):<40}│")

        lines.append(
            "│                                                                      │"
        )

        # Top-level structure
        lines.append(
            "│ Structure:                                                           │"
        )
        root_dirs = set()
        for component in arch_map.components:
            if component.type == "directory":
                parts = component.path.split("/")
                if len(parts) == 1:
                    root_dirs.add(component.name)

        for dir_name in sorted(root_dirs):
            lines.append(f"│   📁 {dir_name:<60}│")

        lines.append("└" + "─" * (max_width - 2) + "┘")

        return "\n".join(lines)

    def to_mermaid(self, arch_map: ArchitectureMap) -> str:
        """Generate Mermaid diagram syntax.

        Args:
            arch_map: Architecture map to visualize.

        Returns:
            Mermaid diagram syntax as string.
        """
        lines = ["graph TD"]

        # Add components as nodes
        for component in arch_map.components:
            if component.type == "directory":
                safe_id = component.path.replace("/", "_").replace(".", "_")
                lines.append(f'    {safe_id}["📁 {component.name}"]')
            elif component.type == "module":
                safe_id = component.path.replace("/", "_").replace(".", "_")
                lines.append(f'    {safe_id}["📄 {component.name}"]')

        # Add relationships
        for from_path, to_path, rel_type in arch_map.relationships:
            from_id = from_path.replace("/", "_").replace(".", "_")
            to_id = to_path.replace("/", "_").replace(".", "_")
            lines.append(f"    {from_id} -->|{rel_type}| {to_id}")

        return "\n".join(lines)

    def get_component_detail(
        self, arch_map: ArchitectureMap, component_name: str
    ) -> str:
        """Get detailed view of a single component.

        Args:
            arch_map: Architecture map.
            component_name: Name or path of component to detail.

        Returns:
            Detailed component information as string.
        """
        # Find component by name or path
        component = None
        for comp in arch_map.components:
            if comp.name == component_name or comp.path == component_name:
                component = comp
                break

        if not component:
            return f"Component '{component_name}' not found"

        lines = [
            f"Component: {component.name}",
            f"Path: {component.path}",
            f"Type: {component.type}",
        ]

        if component.imports:
            lines.append(f"\nImports ({len(component.imports)}):")
            for imp in sorted(component.imports)[:10]:
                lines.append(f"  • {imp}")
            if len(component.imports) > 10:
                lines.append(f"  ... and {len(component.imports) - 10} more")

        if component.exports:
            lines.append(f"\nExports ({len(component.exports)}):")
            for exp in sorted(component.exports)[:10]:
                lines.append(f"  • {exp}")
            if len(component.exports) > 10:
                lines.append(f"  ... and {len(component.exports) - 10} more")

        # Find relationships
        incoming = [r for r in arch_map.relationships if r[1] == component.path]
        outgoing = [r for r in arch_map.relationships if r[0] == component.path]

        if incoming:
            lines.append(f"\nIncoming Dependencies ({len(incoming)}):")
            for from_path, _, rel_type in incoming[:5]:
                lines.append(f"  • {from_path} ({rel_type})")
            if len(incoming) > 5:
                lines.append(f"  ... and {len(incoming) - 5} more")

        if outgoing:
            lines.append(f"\nOutgoing Dependencies ({len(outgoing)}):")
            for _, to_path, rel_type in outgoing[:5]:
                lines.append(f"  • {to_path} ({rel_type})")
            if len(outgoing) > 5:
                lines.append(f"  ... and {len(outgoing) - 5} more")

        return "\n".join(lines)
