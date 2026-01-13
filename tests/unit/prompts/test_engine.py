"""Tests for prompts/engine.py template engine."""

import pytest

from prompts.engine import TemplateEngine, TemplateVariable, BUILTIN_VARIABLES


class TestTemplateVariable:
    """Tests for TemplateVariable."""

    def test_resolve_from_context(self):
        var = TemplateVariable(name="test", description="Test var", example="example")
        result = var.resolve({"test": "context_value"})
        assert result == "context_value"

    def test_resolve_from_resolver(self):
        var = TemplateVariable(
            name="test",
            description="Test var",
            example="example",
            resolver=lambda: "resolved_value",
        )
        result = var.resolve({})
        assert result == "resolved_value"

    def test_context_overrides_resolver(self):
        var = TemplateVariable(
            name="test",
            description="Test var",
            example="example",
            resolver=lambda: "from_resolver",
        )
        result = var.resolve({"test": "from_context"})
        assert result == "from_context"

    def test_empty_for_missing(self):
        var = TemplateVariable(name="test", description="Test var", example="ex")
        result = var.resolve({})
        assert result == ""


class TestBuiltinVariables:
    """Tests for built-in variable definitions."""

    def test_builtin_variables_exist(self):
        expected = {
            "model",
            "provider",
            "agent_mode",
            "prompt_name",
            "date",
            "time",
            "datetime",
            "cwd",
            "home",
            "user",
            "hostname",
            "os",
            "shell",
        }
        assert expected.issubset(set(BUILTIN_VARIABLES.keys()))

    def test_date_resolver_format(self):
        var = BUILTIN_VARIABLES["date"]
        result = var.resolve({})
        assert len(result) == 10
        assert result[4] == "-"
        assert result[7] == "-"

    def test_time_resolver_format(self):
        var = BUILTIN_VARIABLES["time"]
        result = var.resolve({})
        assert len(result) == 8
        assert result[2] == ":"
        assert result[5] == ":"


class TestTemplateEngine:
    """Tests for TemplateEngine."""

    @pytest.fixture
    def engine(self):
        return TemplateEngine()

    def test_simple_variable_substitution(self, engine):
        result = engine.render("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_variables(self, engine):
        template = "{{greeting}} {{name}}, today is {{day}}."
        context = {"greeting": "Hello", "name": "User", "day": "Monday"}
        result = engine.render(template, context)
        assert result == "Hello User, today is Monday."

    def test_undefined_variable_returns_empty(self, engine):
        result = engine.render("Hello {{unknown}}!", {})
        assert result == "Hello !"

    def test_whitespace_in_variable_syntax(self, engine):
        result = engine.render("{{ name }}", {"name": "Test"})
        assert result == "Test"

    def test_builtin_variable_resolution(self, engine):
        result = engine.render("Date: {{date}}", {})
        assert len(result) > 6
        assert "-" in result


class TestConditionals:
    """Tests for conditional blocks."""

    @pytest.fixture
    def engine(self):
        return TemplateEngine()

    def test_if_true_shows_content(self, engine):
        template = "{{#if enabled}}Enabled{{/if}}"
        result = engine.render(template, {"enabled": True})
        assert result == "Enabled"

    def test_if_false_hides_content(self, engine):
        template = "{{#if enabled}}Enabled{{/if}}"
        result = engine.render(template, {"enabled": False})
        assert result == ""

    def test_if_else_true_branch(self, engine):
        template = "{{#if active}}ON{{else}}OFF{{/if}}"
        result = engine.render(template, {"active": True})
        assert result == "ON"

    def test_if_else_false_branch(self, engine):
        template = "{{#if active}}ON{{else}}OFF{{/if}}"
        result = engine.render(template, {"active": False})
        assert result == "OFF"

    def test_unless_false_shows_content(self, engine):
        template = "{{#unless disabled}}Active{{/unless}}"
        result = engine.render(template, {"disabled": False})
        assert result == "Active"

    def test_unless_true_hides_content(self, engine):
        template = "{{#unless disabled}}Active{{/unless}}"
        result = engine.render(template, {"disabled": True})
        assert result == ""

    def test_nested_conditionals(self, engine):
        template = "{{#if outer}}{{#if inner}}Both{{/if}}{{/if}}"
        result = engine.render(template, {"outer": True, "inner": True})
        assert result == "Both"

    def test_nested_with_else(self, engine):
        template = "{{#if outer}}{{#if inner}}A{{else}}B{{/if}}{{else}}C{{/if}}"
        result = engine.render(template, {"outer": True, "inner": False})
        assert result == "B"

    def test_variables_inside_conditionals(self, engine):
        template = "{{#if show}}Hello {{name}}!{{/if}}"
        result = engine.render(template, {"show": True, "name": "World"})
        assert result == "Hello World!"


class TestTruthiness:
    """Tests for truthy/falsy value handling."""

    @pytest.fixture
    def engine(self):
        return TemplateEngine()

    def test_empty_string_is_falsy(self, engine):
        template = "{{#if value}}Yes{{else}}No{{/if}}"
        result = engine.render(template, {"value": ""})
        assert result == "No"

    def test_zero_is_falsy(self, engine):
        template = "{{#if value}}Yes{{else}}No{{/if}}"
        result = engine.render(template, {"value": 0})
        assert result == "No"

    def test_none_is_falsy(self, engine):
        template = "{{#if value}}Yes{{else}}No{{/if}}"
        result = engine.render(template, {"value": None})
        assert result == "No"

    def test_string_false_is_falsy(self, engine):
        template = "{{#if value}}Yes{{else}}No{{/if}}"
        result = engine.render(template, {"value": "false"})
        assert result == "No"

    def test_string_no_is_falsy(self, engine):
        template = "{{#if value}}Yes{{else}}No{{/if}}"
        result = engine.render(template, {"value": "no"})
        assert result == "No"

    def test_nonzero_is_truthy(self, engine):
        template = "{{#if value}}Yes{{else}}No{{/if}}"
        result = engine.render(template, {"value": 1})
        assert result == "Yes"

    def test_nonempty_string_is_truthy(self, engine):
        template = "{{#if value}}Yes{{else}}No{{/if}}"
        result = engine.render(template, {"value": "hello"})
        assert result == "Yes"


class TestCustomVariables:
    """Tests for custom variable management."""

    def test_add_custom_variable(self):
        engine = TemplateEngine()
        engine.add_custom_variable("project", "Project name", "my-project", "custom")

        all_vars = engine.get_all_variables()
        assert "project" in all_vars
        assert all_vars["project"].description == "Project name"

    def test_custom_variable_with_resolver(self):
        engine = TemplateEngine()
        engine.add_custom_variable(
            "computed", "Computed value", "ex", "custom", resolver=lambda: "dynamic"
        )

        result = engine.render("{{computed}}", {})
        assert result == "dynamic"

    def test_remove_custom_variable(self):
        engine = TemplateEngine()
        engine.add_custom_variable("temp", "Temp", "t", "custom")
        assert "temp" in engine.get_all_variables()

        result = engine.remove_custom_variable("temp")
        assert result is True
        assert "temp" not in engine.get_all_variables()

    def test_remove_nonexistent_returns_false(self):
        engine = TemplateEngine()
        result = engine.remove_custom_variable("nonexistent")
        assert result is False


class TestPreview:
    """Tests for template preview functionality."""

    @pytest.fixture
    def engine(self):
        return TemplateEngine()

    def test_preview_uses_examples(self, engine):
        template = "Model: {{model}}, Provider: {{provider}}"
        result = engine.preview(template, {})
        assert "gpt-4o" in result
        assert "openai" in result

    def test_preview_respects_context(self, engine):
        template = "Model: {{model}}"
        result = engine.preview(template, {"model": "claude-3"})
        assert result == "Model: claude-3"


class TestExtractVariables:
    """Tests for variable extraction."""

    @pytest.fixture
    def engine(self):
        return TemplateEngine()

    def test_extract_simple_variables(self, engine):
        template = "{{foo}} and {{bar}}"
        vars = engine.extract_variables(template)
        assert vars == {"foo", "bar"}

    def test_extract_from_conditionals(self, engine):
        template = "{{#if enabled}}{{name}}{{/if}}"
        vars = engine.extract_variables(template)
        assert "enabled" in vars
        assert "name" in vars


class TestValidation:
    """Tests for template validation."""

    @pytest.fixture
    def engine(self):
        return TemplateEngine()

    def test_valid_template_no_errors(self, engine):
        template = "{{#if agent_mode}}Agent{{/if}} - {{model}}"
        errors = engine.validate_template(template)
        assert errors == []

    def test_unclosed_if_block(self, engine):
        template = "{{#if enabled}}Content"
        errors = engine.validate_template(template)
        assert len(errors) > 0
        assert "if" in errors[0].lower()

    def test_unclosed_unless_block(self, engine):
        template = "{{#unless disabled}}Content"
        errors = engine.validate_template(template)
        assert len(errors) > 0
        assert "unless" in errors[0].lower()

    def test_unknown_variable_warning(self, engine):
        template = "{{unknown_xyz_123}}"
        errors = engine.validate_template(template)
        assert len(errors) > 0
        assert "unknown" in errors[0].lower()


class TestVariableReference:
    """Tests for variable reference generation."""

    def test_reference_includes_categories(self):
        engine = TemplateEngine()
        ref = engine.get_variable_reference()

        assert "AI Context" in ref
        assert "Date & Time" in ref
        assert "Environment" in ref

    def test_reference_includes_conditionals_docs(self):
        engine = TemplateEngine()
        ref = engine.get_variable_reference()

        assert "{{#if" in ref
        assert "{{#unless" in ref
        assert "{{else}}" in ref


class TestComplexTemplates:
    """Tests for complex real-world templates."""

    @pytest.fixture
    def engine(self):
        return TemplateEngine()

    def test_system_prompt_style_template(self, engine):
        template = """You are an AI assistant.
{{#if agent_mode}}
## Agent Mode
You can execute commands and read/write files.
{{else}}
## Chat Mode
You are in conversation mode.
{{/if}}

Current model: {{model}}
Working directory: {{cwd}}"""

        result = engine.render(
            template, {"agent_mode": True, "model": "gpt-4o", "cwd": "/home/user"}
        )

        assert "Agent Mode" in result
        assert "Chat Mode" not in result
        assert "gpt-4o" in result
        assert "/home/user" in result

    def test_multiline_conditionals(self, engine):
        template = """Header
{{#if show_section}}
Line 1
Line 2
Line 3
{{/if}}
Footer"""
        result = engine.render(template, {"show_section": True})
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
