from utils.text import make_links_clickable, strip_ansi, truncate_text


class TestMakeLinksClickable:
    def test_empty_string(self):
        assert make_links_clickable("") == ""

    def test_none_returns_none(self):
        assert make_links_clickable(None) is None

    def test_no_urls(self):
        text = "This is plain text without any links"
        assert make_links_clickable(text) == text

    def test_simple_https_url(self):
        text = "Check out https://example.com for more"
        result = make_links_clickable(text)
        assert "[https://example.com](https://example.com)" in result

    def test_http_url(self):
        text = "Visit http://example.com"
        result = make_links_clickable(text)
        assert "[http://example.com](http://example.com)" in result

    def test_ftp_url(self):
        text = "Download from ftp://files.example.com/file.txt"
        result = make_links_clickable(text)
        assert "ftp://files.example.com/file.txt" in result

    def test_url_with_path(self):
        text = "See https://example.com/path/to/page"
        result = make_links_clickable(text)
        assert (
            "[https://example.com/path/to/page](https://example.com/path/to/page)"
            in result
        )

    def test_url_with_query_params(self):
        text = "Link: https://example.com/search?q=test&page=1"
        result = make_links_clickable(text)
        assert "https://example.com/search?q=test&page=1" in result

    def test_multiple_urls(self):
        text = "Check https://one.com and https://two.com"
        result = make_links_clickable(text)
        assert "[https://one.com](https://one.com)" in result
        assert "[https://two.com](https://two.com)" in result

    def test_existing_markdown_link_preserved(self):
        text = "Click [here](https://example.com) for more"
        result = make_links_clickable(text)
        assert "[here](https://example.com)" in result

    def test_long_url_truncated_in_display(self):
        long_url = "https://example.com/" + "a" * 100
        text = f"See {long_url}"
        result = make_links_clickable(text)
        assert "..." in result
        assert f"]({long_url})" in result


class TestStripAnsi:
    def test_no_ansi_codes(self):
        text = "Plain text"
        assert strip_ansi(text) == "Plain text"

    def test_single_color_code(self):
        text = "\x1b[31mRed text\x1b[0m"
        assert strip_ansi(text) == "Red text"

    def test_multiple_codes(self):
        text = "\x1b[1;32mBold green\x1b[0m normal \x1b[34mblue\x1b[0m"
        assert strip_ansi(text) == "Bold green normal blue"

    def test_empty_string(self):
        assert strip_ansi("") == ""

    def test_only_ansi_codes(self):
        text = "\x1b[31m\x1b[0m"
        assert strip_ansi(text) == ""


class TestTruncateText:
    def test_short_text_not_truncated(self):
        text = "Short"
        assert truncate_text(text, 10) == "Short"

    def test_exact_length_not_truncated(self):
        text = "Exactly10c"
        assert truncate_text(text, 10) == "Exactly10c"

    def test_long_text_truncated(self):
        text = "This is a very long text that needs truncation"
        result = truncate_text(text, 20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_custom_suffix(self):
        text = "Long text to truncate"
        result = truncate_text(text, 10, suffix=">>")
        assert result.endswith(">>")
        assert len(result) == 10

    def test_empty_suffix(self):
        text = "Long text here"
        result = truncate_text(text, 5, suffix="")
        assert result == "Long "
        assert len(result) == 5

    def test_empty_text(self):
        assert truncate_text("", 10) == ""
