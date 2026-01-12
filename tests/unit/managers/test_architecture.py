import pytest

from managers.architecture import ArchitectureMap, ArchitectureMapper, Component


class TestComponent:
    def test_basic_component(self):
        comp = Component(name="main", path="main.py", type="module")
        assert comp.name == "main"
        assert comp.path == "main.py"
        assert comp.type == "module"
        assert comp.imports == []
        assert comp.exports == []
        assert comp.dependencies == []

    def test_component_with_all_fields(self):
        comp = Component(
            name="MyClass",
            path="src/myclass.py",
            type="class",
            imports=["os", "sys"],
            exports=["MyClass"],
            dependencies=["utils.py"],
        )
        assert comp.imports == ["os", "sys"]
        assert comp.exports == ["MyClass"]
        assert comp.dependencies == ["utils.py"]

    def test_component_hash(self):
        comp1 = Component(name="test", path="test.py", type="module")
        comp2 = Component(name="test", path="test.py", type="module")
        comp3 = Component(name="other", path="test.py", type="module")
        assert hash(comp1) == hash(comp2)
        assert hash(comp1) != hash(comp3)
        test_set = {comp1, comp2}
        assert len(test_set) == 1

    def test_component_equality(self):
        comp1 = Component(name="test", path="test.py", type="module")
        comp2 = Component(name="test", path="test.py", type="class")
        comp3 = Component(name="other", path="test.py", type="module")
        assert comp1 == comp2
        assert comp1 != comp3
        assert comp1 != "not a component"


class TestArchitectureMap:
    def test_empty_map(self):
        arch_map = ArchitectureMap()
        assert arch_map.components == []
        assert arch_map.relationships == []
        assert arch_map.layers == {}

    def test_map_with_data(self):
        components = [
            Component(name="main", path="main.py", type="module"),
            Component(name="utils", path="utils.py", type="module"),
        ]
        relationships = [("main", "utils", "imports")]
        layers = {"core": ["main"], "utilities": ["utils"]}
        arch_map = ArchitectureMap(
            components=components, relationships=relationships, layers=layers
        )
        assert len(arch_map.components) == 2
        assert len(arch_map.relationships) == 1
        assert "core" in arch_map.layers


class TestArchitectureMapper:
    def test_init_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mapper = ArchitectureMapper()
        assert mapper.root == tmp_path

    def test_init_with_path(self, tmp_path):
        mapper = ArchitectureMapper(tmp_path)
        assert mapper.root == tmp_path

    def test_default_ignore_patterns(self):
        mapper = ArchitectureMapper()
        assert "__pycache__" in mapper.ignore_patterns
        assert "node_modules" in mapper.ignore_patterns
        assert ".git" in mapper.ignore_patterns
        assert "*.pyc" in mapper.ignore_patterns

    def test_should_ignore_exact_match(self, tmp_path):
        mapper = ArchitectureMapper(tmp_path)
        assert mapper._should_ignore(tmp_path / "__pycache__") is True
        assert mapper._should_ignore(tmp_path / ".git") is True

    def test_should_ignore_wildcard(self, tmp_path):
        mapper = ArchitectureMapper(tmp_path)
        assert mapper._should_ignore(tmp_path / "test.pyc") is True
        assert mapper._should_ignore(tmp_path / "module.pyc") is True

    def test_should_not_ignore_regular_files(self, tmp_path):
        mapper = ArchitectureMapper(tmp_path)
        assert mapper._should_ignore(tmp_path / "main.py") is False
        assert mapper._should_ignore(tmp_path / "utils.py") is False
        assert mapper._should_ignore(tmp_path / "README.md") is False

    def test_extract_python_info(self, tmp_path):
        py_file = tmp_path / "test_module.py"
        py_file.write_text(
            """
import os
from sys import path

class MyClass:
    pass

def my_function():
    pass
"""
        )
        mapper = ArchitectureMapper(tmp_path)
        imports, exports = mapper._extract_python_info(py_file)
        assert "os" in imports
        assert "sys" in imports
        assert "MyClass:class" in exports
        assert "my_function:function" in exports

    def test_extract_python_info_with_from_imports(self, tmp_path):
        py_file = tmp_path / "module.py"
        py_file.write_text(
            """
from typing import List, Dict
from dataclasses import dataclass
"""
        )
        mapper = ArchitectureMapper(tmp_path)
        imports, _exports = mapper._extract_python_info(py_file)
        assert "typing" in imports
        assert "dataclasses" in imports

    def test_extract_python_info_handles_syntax_error(self, tmp_path):
        py_file = tmp_path / "bad.py"
        py_file.write_text("def broken(:\n    pass")
        mapper = ArchitectureMapper(tmp_path)
        imports, exports = mapper._extract_python_info(py_file)
        assert imports == []
        assert exports == []

    @pytest.mark.asyncio
    async def test_scan_full_project(self, tmp_path):
        (tmp_path / "app.py").write_text(
            """
from utils import helper

def main():
    helper()
"""
        )
        (tmp_path / "utils.py").write_text(
            """
def helper():
    pass
"""
        )
        mapper = ArchitectureMapper(tmp_path)
        arch_map = await mapper.scan()
        assert len(arch_map.components) >= 2
        component_names = [c.name for c in arch_map.components]
        assert "app" in component_names
        assert "utils" in component_names

    @pytest.mark.asyncio
    async def test_scan_with_directories(self, tmp_path):
        (tmp_path / "main.py").write_text("pass")
        sub_dir = tmp_path / "submodule"
        sub_dir.mkdir()
        (sub_dir / "helper.py").write_text("pass")
        mapper = ArchitectureMapper(tmp_path)
        arch_map = await mapper.scan()
        component_names = [c.name for c in arch_map.components]
        assert "main" in component_names
        assert "helper" in component_names
        assert "submodule" in component_names

    @pytest.mark.asyncio
    async def test_scan_ignores_pycache(self, tmp_path):
        (tmp_path / "main.py").write_text("pass")
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "main.cpython-312.pyc").write_bytes(b"")
        mapper = ArchitectureMapper(tmp_path)
        arch_map = await mapper.scan()
        component_names = [c.name for c in arch_map.components]
        assert "__pycache__" not in component_names

    def test_build_relationships(self, tmp_path):
        components = [
            Component(
                name="main",
                path="main.py",
                type="module",
                imports=["utils"],
                exports=["main:function"],
            ),
            Component(
                name="utils",
                path="utils.py",
                type="module",
                imports=[],
                exports=["helper:function"],
            ),
        ]
        mapper = ArchitectureMapper(tmp_path)
        relationships = mapper._build_relationships(components)
        assert len(relationships) >= 1
        assert any(r[2] == "imports" for r in relationships)

    def test_organize_layers(self, tmp_path):
        components = [
            Component(name="main", path="main.py", type="module"),
            Component(name="process", path="managers/process.py", type="module"),
            Component(name="ai_cmd", path="commands/ai.py", type="module"),
            Component(name="config", path="config/settings.py", type="module"),
        ]
        mapper = ArchitectureMapper(tmp_path)
        layers = mapper._organize_layers(components)
        assert "managers" in layers
        assert "commands" in layers
        assert "config" in layers

    def test_to_ascii(self, tmp_path):
        mapper = ArchitectureMapper(tmp_path)
        arch_map = ArchitectureMap(
            components=[
                Component(name="main", path="main.py", type="module"),
                Component(name="utils", path="utils", type="directory"),
            ],
            layers={"core": ["main.py"]},
        )
        ascii_output = mapper.to_ascii(arch_map)
        assert isinstance(ascii_output, str)
        assert "Project Architecture" in ascii_output
        assert "core" in ascii_output

    def test_to_mermaid(self, tmp_path):
        mapper = ArchitectureMapper(tmp_path)
        arch_map = ArchitectureMap(
            components=[
                Component(name="main", path="main.py", type="module"),
                Component(name="utils", path="utils.py", type="module"),
            ],
            relationships=[("main.py", "utils.py", "imports")],
        )
        mermaid_output = mapper.to_mermaid(arch_map)
        assert "graph TD" in mermaid_output
        assert "imports" in mermaid_output

    def test_get_component_detail_found(self, tmp_path):
        mapper = ArchitectureMapper(tmp_path)
        arch_map = ArchitectureMap(
            components=[
                Component(
                    name="main",
                    path="main.py",
                    type="module",
                    imports=["os", "sys"],
                    exports=["main:function"],
                ),
            ],
            relationships=[],
        )
        detail = mapper.get_component_detail(arch_map, "main")
        assert "Component: main" in detail
        assert "Path: main.py" in detail
        assert "Imports" in detail

    def test_get_component_detail_not_found(self, tmp_path):
        mapper = ArchitectureMapper(tmp_path)
        arch_map = ArchitectureMap()
        detail = mapper.get_component_detail(arch_map, "nonexistent")
        assert "not found" in detail
