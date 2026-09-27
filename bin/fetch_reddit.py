#!/usr/bin/env python3
"""Search Reddit and read threads without a login, cookie or API key.

old.reddit.com redirects to a login page and the .json endpoints answer 403. The HTML partials
Reddit's own web UI lazy-loads (/svc/shreddit/) are not, given a browser
User-Agent. Parsing them breaks when Reddit changes its markup;
tests/test_fetch_reddit_live.py is the check that notices.

A module, imported by fetch-thread.py, reddit-search.py and notes-triage-fetch.py.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

BASE = "https://www.reddit.com"
# Reddit answers 403 to a non-browser User-Agent, curl's included.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
ATOM = "{http://www.w3.org/2005/Atom}"


class RedditError(RuntimeError):
    """Reddit refused, walled or reshaped a request; the message says which."""


@dataclass
class Post:
    id: str
    subreddit: str
    title: str
    url: str
    author: str = ""
    created: str = ""
    score: int | None = None
    comments: int | None = None
    body: str = ""
    snippet: str = ""


@dataclass
class Comment:
    id: str
    parent_id: str
    author: str
    score: int | None
    depth: int
    created: str
    body: str


# ============================================================================
# HTTP
# ============================================================================


def get(path: str, form: dict | None = None) -> str:
    """GET, or POST when `form` is given, a reddit.com path; the body as text."""
    data = urlencode(form).encode() if form is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            final, body = resp.geturl(), resp.read().decode("utf-8", "replace")
    except HTTPError as e:
        if e.code == 403:
            raise RedditError(
                f"HTTP 403 on {path}: Reddit blocked the request. The User-Agent in "
                "fetch_reddit.py may look too old, or this IP is flagged."
            ) from e
        if e.code == 429:
            raise RedditError(f"HTTP 429 on {path}: rate-limited. Wait a minute and slow down.") from e
        raise RedditError(f"HTTP {e.code} on {path}") from e
    except URLError as e:
        raise RedditError(f"could not reach reddit.com: {e.reason}") from e
    except TimeoutError as e:
        raise RedditError(f"{path} timed out after 20s") from e
    if "/login" in final:
        raise RedditError(
            f"{path} redirected to the login page: Reddit has login-walled it, "
            "as it did old.reddit.com."
        )
    return body


# ============================================================================
# Parsing
# ============================================================================


def _int(value: str | None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text(fragment: str) -> str:
    """Rendered HTML to plain text, one blank line between paragraphs."""
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"<li\b[^>]*>", "\n- ", fragment)
    fragment = re.sub(r"</(p|ol|ul|pre|blockquote|h\d)>", "\n\n", fragment)
    text = html.unescape(re.sub(r"<[^>]+>", "", fragment))
    lines = [ln.strip() for ln in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def parse_search(page: str) -> tuple[list[Post], str | None]:
    """Search results, and the path of the next page if there is one."""
    posts = []
    for unit in page.split('data-testid="sdui-post-unit"')[1:]:
        title = re.search(
            r'data-testid="post-title-text"[^>]*href="(/r/([^/]+)/comments/(\w+)/[^"]*)"[^>]*>(.*?)</a>',
            unit,
            re.S,
        )
        if not title:
            continue
        path, sub, post_id, text = title.groups()
        context = re.search(r'data-faceplate-tracking-context="([^"]*)"', unit)
        tracking = json.loads(html.unescape(context.group(1))) if context else {}
        created = re.search(r'<faceplate-timeago[^>]*ts="([^"]+)"', unit)
        counts = re.search(r'data-testid="search-counter-row".*?</div>', unit, re.S)
        numbers = re.findall(r'number="(\d+)"', counts.group(0)) if counts else []
        posts.append(
            Post(
                id=post_id,
                subreddit=sub,
                title=_text(text),
                url=BASE + path,
                author=tracking.get("profile", {}).get("name", ""),
                created=created.group(1) if created else "",
                score=_int(numbers[0]) if numbers else None,
                comments=_int(numbers[1]) if len(numbers) > 1 else None,
                snippet=tracking.get("search", {}).get("snippet", ""),
            )
        )
    cursor = re.search(r'<faceplate-partial[^>]*src="(/svc/shreddit/[^"]*search/[^"]*cursor=[^"]*)"', page)
    return posts, html.unescape(cursor.group(1)) if cursor else None


class _CommentParser(HTMLParser):
    """Collects <shreddit-comment> attributes and the text of each comment body."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.comments: list[Comment] = []
        self._body: list[str] | None = None
        self._divs = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "shreddit-comment":
            self.comments.append(
                Comment(
                    id=(a.get("thingid") or "").removeprefix("t1_"),
                    parent_id=(a.get("parentid") or "").removeprefix("t1_"),
                    author=a.get("author") or "[deleted]",
                    score=_int(a.get("score")),
                    depth=_int(a.get("depth")) or 0,
                    created=a.get("created") or "",
                    body="",
                )
            )
        elif self._body is not None:
            if tag == "div":
                self._divs += 1
            self._body.append(self.get_starttag_text() or "")
        elif tag == "div" and (a.get("id") or "").endswith("-comment-rtjson-content"):
            self._body, self._divs = [], 0

    def handle_endtag(self, tag: str) -> None:
        if self._body is None:
            return
        if tag == "div":
            if self._divs == 0:
                if self.comments:
                    self.comments[-1].body = _text("".join(self._body))
                self._body = None
                return
            self._divs -= 1
        self._body.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._body is not None:
            self._body.append(data)

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")


def parse_comments(page: str) -> tuple[list[Comment], tuple[str, str] | None]:
    """Comments in page order, and (path, cursor) for the next top-level batch."""
    parser = _CommentParser()
    parser.feed(page)
    more = re.search(
        r'<faceplate-partial[^>]*src="(/svc/shreddit/more-comments/[^"]*top-level=1[^"]*)"[^>]*>'
        r'\s*<input[^>]*name="cursor"[^>]*value="([^"]+)"',
        page,
    )
    return parser.comments, (html.unescape(more.group(1)), more.group(2)) if more else None


def parse_post_rss(feed: str, subreddit: str, post_id: str) -> Post:
    """The post itself: the first entry of the thread's Atom feed."""
    entry = ET.fromstring(feed).find(f"{ATOM}entry")
    if entry is None:
        raise RedditError(f"the feed for r/{subreddit} post {post_id} has no entries")
    return Post(
        id=post_id,
        subreddit=subreddit,
        title=(entry.findtext(f"{ATOM}title") or "").strip(),
        url=f"{BASE}/r/{subreddit}/comments/{post_id}/",
        author=(entry.findtext(f"{ATOM}author/{ATOM}name") or "").removeprefix("/u/"),
        created=entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated") or "",
        body=_text(entry.findtext(f"{ATOM}content") or ""),
    )


# ============================================================================
# High level
# ============================================================================


def search(query: str, subreddit: str = "", sort: str = "relevance", period: str = "all", limit: int = 25) -> list[Post]:
    """Up to `limit` posts matching `query`, optionally within one subreddit."""
    scope = f"/r/{subreddit}" if subreddit else ""
    path: str | None = f"/svc/shreddit{scope}/search/?" + urlencode(
        {"q": query, "type": "posts", "sort": sort, "t": period}
    )
    posts: list[Post] = []
    while path and len(posts) < limit:
        if posts:
            time.sleep(1)
        page, path = parse_search(get(path))
        if not page:
            break
        posts.extend(page)
    return posts[:limit]


def fetch_thread(post_id: str, subreddit: str, limit: int = 50) -> tuple[Post, list[Comment]]:
    """The post and up to `limit` comments, top-voted first.

    Branches Reddit folds behind "more replies" are not expanded.
    """
    # No shreddit partial serves a post by id, and RSS is tightly
    # rate-limited, so the comments must not depend on it.
    try:
        post = parse_post_rss(get(f"/r/{subreddit}/comments/{post_id}/.rss?limit=1"), subreddit, post_id)
    except RedditError as e:
        post = Post(post_id, subreddit, "", f"{BASE}/r/{subreddit}/comments/{post_id}/", body=f"(post text unavailable: {e})")
    comments, more = parse_comments(get(f"/svc/shreddit/comments/r/{subreddit}/t3_{post_id}?sort=top"))
    while more and len(comments) < limit:
        time.sleep(1)
        batch, more = parse_comments(get(more[0], {"cursor": more[1]}))
        if not batch:
            break
        comments.extend(batch)
    return post, comments[:limit]


def extract_reddit_info(source: str) -> tuple[str, str]:
    """(post_id, subreddit) from a thread URL, 'r/sub/comments/id', or 'id sub'."""
    parts = source.split()
    if len(parts) == 2:
        return parts[0], parts[1]
    match = re.search(r"r/(\w+)/comments/(\w+)", source)
    if match:
        return match.group(2), match.group(1)
    raise ValueError(
        "Could not parse Reddit source. Expected:\n"
        "  - URL: https://reddit.com/r/python/comments/abc123/title\n"
        "  - Shorthand: r/python/comments/abc123\n"
        "  - Post ID + sub: abc123 python"
    )


def format_thread(post: Post, comments: list[Comment], mark: str = "") -> str:
    """Markdown, replies indented under their parents; `mark` flags one comment id."""
    byline = " | ".join(x for x in (f"**r/{post.subreddit}**", post.author and f"u/{post.author}", post.created[:10]) if x)
    lines = [f"# {post.title or post.url}", byline, ""]
    if post.body:
        lines += [post.body, ""]
    for c in comments:
        indent = "  " * c.depth
        score = c.score if c.score is not None else "?"
        flag = "  <-- SAVED COMMENT" if c.id == mark else ""
        lines.append(f"{indent}**u/{c.author}** ({score} points){flag}:")
        lines += [f"{indent}> {ln}" for ln in c.body.splitlines()]
        lines.append("")
    return "\n".join(lines)


def convert_reddit(source: str, output_format: str = "markdown") -> str:
    """fetch-thread.py's entry point."""
    post_id, subreddit = extract_reddit_info(source)
    post, comments = fetch_thread(post_id, subreddit)
    if output_format == "json":
        return json.dumps({"post": asdict(post), "comments": [asdict(c) for c in comments]}, indent=2)
    return format_thread(post, comments)
