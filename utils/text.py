"""Text processing utilities."""

import re

# Regex to match URLs that are NOT already in markdown link format
# Matches http://, https://, ftp:// URLs
URL_PATTERN = re.compile(
    r"(?<!\]\()(?<!\[)"  # Not preceded by ]( or [
    r"(https?://|ftp://)"  # Protocol
    r"[^\s<>\[\]\"\'`\)]+",  # URL characters (exclude markdown/quote chars)
    re.IGNORECASE,
)

# Pattern to detect if URL is already a markdown link
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def make_links_clickable(text: str) -> str:
    """Convert plain URLs in text to Rich/Markdown clickable links.

    URLs that are already in markdown link format [text](url) are preserved.
    Plain URLs like https://example.com become [https://example.com](https://example.com)

    Args:
        text: The input text potentially containing URLs

    Returns:
        Text with plain URLs converted to markdown link format
    """
    if not text:
        return text

    # Find all existing markdown links to avoid double-processing
    existing_links = set()
    for match in MARKDOWN_LINK_PATTERN.finditer(text):
        existing_links.add(match.group(2))  # The URL part

    def replace_url(match: re.Match) -> str:
        url = match.group(0)
        # Skip if this URL is already part of a markdown link
        if url in existing_links:
            return url
        # Convert to markdown link format
        # Truncate display text if URL is very long
        display = url if len(url) <= 60 else url[:57] + "..."
        return f"[{display}]({url})"

    return URL_PATTERN.sub(replace_url, text)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length, adding suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
