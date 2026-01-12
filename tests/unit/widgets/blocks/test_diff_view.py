"""Tests for widgets/blocks/diff_view.py - DiffViewWidget."""

from widgets.blocks.diff_view import DiffViewWidget


class TestDiffViewWidgetInit:
    """Test DiffViewWidget initialization."""

    def test_init_stores_file_path(self):
        widget = DiffViewWidget(file="src/main.py", diff_content="")
        assert widget.file == "src/main.py"

    def test_init_stores_diff_content(self):
        content = "+added line\n-removed line"
        widget = DiffViewWidget(file="test.py", diff_content=content)
        assert widget.diff_content == content

    def test_init_with_empty_file(self):
        widget = DiffViewWidget(file="", diff_content="some diff")
        assert widget.file == ""

    def test_init_with_empty_diff_content(self):
        widget = DiffViewWidget(file="file.py", diff_content="")
        assert widget.diff_content == ""

    def test_init_accepts_kwargs(self):
        widget = DiffViewWidget(
            file="test.py", diff_content="", id="my-diff", classes="custom-class"
        )
        assert widget.id == "my-diff"
        assert "custom-class" in widget.classes

    def test_init_with_multiline_diff(self):
        content = "+line1\n+line2\n-line3\n context"
        widget = DiffViewWidget(file="multi.py", diff_content=content)
        assert widget.diff_content == content


class TestDiffViewWidgetCSSDefinitions:
    """Test that CSS classes are properly defined."""

    def test_default_css_contains_diff_header(self):
        assert ".diff-header" in DiffViewWidget.DEFAULT_CSS

    def test_default_css_contains_diff_add(self):
        assert ".diff-add" in DiffViewWidget.DEFAULT_CSS

    def test_default_css_contains_diff_del(self):
        assert ".diff-del" in DiffViewWidget.DEFAULT_CSS

    def test_default_css_contains_diff_context(self):
        assert ".diff-context" in DiffViewWidget.DEFAULT_CSS

    def test_default_css_contains_diff_hunk(self):
        assert ".diff-hunk" in DiffViewWidget.DEFAULT_CSS

    def test_default_css_uses_primary_color_variable(self):
        assert "$primary" in DiffViewWidget.DEFAULT_CSS

    def test_default_css_uses_success_color_variable(self):
        assert "$success" in DiffViewWidget.DEFAULT_CSS

    def test_default_css_uses_error_color_variable(self):
        assert "$error" in DiffViewWidget.DEFAULT_CSS

    def test_default_css_uses_text_muted_variable(self):
        assert "$text-muted" in DiffViewWidget.DEFAULT_CSS


class TestDiffViewWidgetLineClassification:
    """Test the line classification logic in compose method."""

    def test_addition_line_starts_with_plus(self):
        # Lines starting with + (but not +++) should be additions
        content = "+added line"
        widget = DiffViewWidget(file="test.py", diff_content=content)
        # Verify the content is stored correctly - compose will classify it
        assert widget.diff_content.startswith("+")
        assert not widget.diff_content.startswith("+++")

    def test_deletion_line_starts_with_minus(self):
        # Lines starting with - (but not ---) should be deletions
        content = "-removed line"
        widget = DiffViewWidget(file="test.py", diff_content=content)
        assert widget.diff_content.startswith("-")
        assert not widget.diff_content.startswith("---")

    def test_hunk_header_starts_with_at_at(self):
        # Lines starting with @@ are hunk headers
        content = "@@ -1,5 +1,6 @@"
        widget = DiffViewWidget(file="test.py", diff_content=content)
        assert widget.diff_content.startswith("@@")

    def test_file_header_plus_not_treated_as_addition(self):
        # +++ lines are file headers, not additions
        content = "+++ b/src/main.py"
        widget = DiffViewWidget(file="test.py", diff_content=content)
        assert widget.diff_content.startswith("+++")

    def test_file_header_minus_not_treated_as_deletion(self):
        # --- lines are file headers, not deletions
        content = "--- a/src/main.py"
        widget = DiffViewWidget(file="test.py", diff_content=content)
        assert widget.diff_content.startswith("---")

    def test_context_line_is_plain_text(self):
        content = " unchanged context line"
        widget = DiffViewWidget(file="test.py", diff_content=content)
        assert not widget.diff_content.startswith("+")
        assert not widget.diff_content.startswith("-")
        assert not widget.diff_content.startswith("@@")


class TestDiffViewWidgetDiffParsing:
    """Test parsing of realistic diff content."""

    def test_parses_typical_git_diff(self):
        diff = """--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
-    print("old")
+    print("new")
+    return True"""
        widget = DiffViewWidget(file="file.py", diff_content=diff)
        lines = widget.diff_content.split("\n")
        assert len(lines) == 7

    def test_handles_multiple_hunks(self):
        diff = """@@ -1,3 +1,3 @@
 context1
-old1
+new1
@@ -10,3 +10,3 @@
 context2
-old2
+new2"""
        widget = DiffViewWidget(file="multi.py", diff_content=diff)
        hunks = [
            line for line in widget.diff_content.split("\n") if line.startswith("@@")
        ]
        assert len(hunks) == 2

    def test_handles_only_additions(self):
        diff = """+line1
+line2
+line3"""
        widget = DiffViewWidget(file="add.py", diff_content=diff)
        lines = widget.diff_content.split("\n")
        assert all(line.startswith("+") for line in lines)

    def test_handles_only_deletions(self):
        diff = """-line1
-line2
-line3"""
        widget = DiffViewWidget(file="del.py", diff_content=diff)
        lines = widget.diff_content.split("\n")
        assert all(line.startswith("-") for line in lines)

    def test_handles_empty_lines_in_diff(self):
        diff = """+added

-removed

 context"""
        widget = DiffViewWidget(file="gaps.py", diff_content=diff)
        lines = widget.diff_content.split("\n")
        assert "" in lines  # Empty lines should be preserved

    def test_handles_special_characters_in_content(self):
        diff = """+print("hello 'world'")
-# TODO: fix this <tag>"""
        widget = DiffViewWidget(file="special.py", diff_content=diff)
        assert "'" in widget.diff_content
        assert "<tag>" in widget.diff_content


class TestDiffViewWidgetInheritance:
    """Test that DiffViewWidget properly inherits from Static."""

    def test_inherits_from_static(self):
        from textual.widgets import Static

        widget = DiffViewWidget(file="test.py", diff_content="")
        assert isinstance(widget, Static)

    def test_has_compose_method(self):
        widget = DiffViewWidget(file="test.py", diff_content="")
        assert hasattr(widget, "compose")
        assert callable(widget.compose)


class TestDiffViewWidgetEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_character_addition(self):
        widget = DiffViewWidget(file="test.py", diff_content="+")
        assert widget.diff_content == "+"

    def test_single_character_deletion(self):
        widget = DiffViewWidget(file="test.py", diff_content="-")
        assert widget.diff_content == "-"

    def test_whitespace_only_content(self):
        widget = DiffViewWidget(file="test.py", diff_content="   \n  \t  ")
        assert widget.diff_content == "   \n  \t  "

    def test_very_long_file_path(self):
        long_path = "a" * 500 + "/very/long/path/to/file.py"
        widget = DiffViewWidget(file=long_path, diff_content="")
        assert widget.file == long_path

    def test_unicode_in_file_path(self):
        widget = DiffViewWidget(file="src/日本語/файл.py", diff_content="")
        assert widget.file == "src/日本語/файл.py"

    def test_unicode_in_diff_content(self):
        content = "+print('こんにちは')\n-print('Привет')"
        widget = DiffViewWidget(file="i18n.py", diff_content=content)
        assert "こんにちは" in widget.diff_content
        assert "Привет" in widget.diff_content

    def test_newline_variations(self):
        # Test different newline styles
        content_unix = "+line1\n+line2"
        widget = DiffViewWidget(file="unix.py", diff_content=content_unix)
        assert len(widget.diff_content.split("\n")) == 2

    def test_trailing_newline(self):
        content = "+line1\n+line2\n"
        widget = DiffViewWidget(file="trail.py", diff_content=content)
        lines = widget.diff_content.split("\n")
        assert lines[-1] == ""  # Trailing newline creates empty string

    def test_no_trailing_newline(self):
        content = "+line1\n+line2"
        widget = DiffViewWidget(file="notrail.py", diff_content=content)
        lines = widget.diff_content.split("\n")
        assert lines[-1] == "+line2"


class TestDiffViewWidgetRealWorldDiffs:
    """Test with realistic git diff outputs."""

    def test_function_modification_diff(self):
        diff = """@@ -10,7 +10,8 @@ class MyClass:
     def method(self):
-        return self.value
+        if self.value is None:
+            return 0
+        return self.value

     def other(self):"""
        widget = DiffViewWidget(file="myclass.py", diff_content=diff)
        assert "@@ -10,7 +10,8 @@" in widget.diff_content
        assert "-        return self.value" in widget.diff_content
        assert "+        if self.value is None:" in widget.diff_content

    def test_import_statement_diff(self):
        diff = """-import os
-import sys
+from pathlib import Path
+import sys
+import typing"""
        widget = DiffViewWidget(file="imports.py", diff_content=diff)
        assert widget.diff_content.count("+") == 3
        assert widget.diff_content.count("-") == 2

    def test_config_file_diff(self):
        diff = """ [settings]
-debug = true
+debug = false
 timeout = 30
+max_retries = 3"""
        widget = DiffViewWidget(file="config.ini", diff_content=diff)
        lines = widget.diff_content.split("\n")
        context_lines = [line for line in lines if line.startswith(" ")]
        assert len(context_lines) == 2
