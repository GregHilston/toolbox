#!/usr/bin/env python3
"""Shared utilities for converting web threads (HN, Reddit) to markdown.

This module provides common functionality for various thread-to-markdown
converters.
"""

from __future__ import annotations

import html
import re


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text, preserving content and unescaping entities.

    Args:
        text: Text potentially containing HTML tags and entities.

    Returns:
        Text with tags removed and entities unescaped.
    """
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities
    text = html.unescape(text)
    return text


def detect_thread_type(url: str) -> str:
    """Detect whether a URL is from Hacker News, Reddit, or unknown.

    Args:
        url: URL string to analyze.

    Returns:
        One of: 'hn', 'reddit', or 'unknown'.
    """
    url_lower = url.lower()

    if "news.ycombinator.com" in url_lower or "ycombinator.com" in url_lower:
        return "hn"

    if "reddit.com" in url_lower:
        return "reddit"

    return "unknown"
