"""Content fetchers for developer community sources.

Each fetcher is a standalone function that returns a normalized list of posts.
Failures in individual fetchers are caught and logged without stopping the pipeline.
"""

import urllib.request
import json
import logging
import xml.etree.ElementTree as ET
from typing import TypedDict

logger = logging.getLogger(__name__)


class Post(TypedDict):
    title: str
    url: str
    source: str


def _http_get_json(url: str, headers: dict | None = None) -> any:
    """Make an HTTP GET request and parse JSON response.

    Args:
        url: The URL to fetch.
        headers: Optional dictionary of HTTP headers to include.

    Returns:
        Parsed JSON response.

    Raises:
        urllib.error.URLError: If the request fails.
        json.JSONDecodeError: If the response is not valid JSON.
    """
    req = urllib.request.Request(url)
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def fetch_hackernews() -> list[Post]:
    """Fetch top 30 stories from Hacker News API.

    Retrieves the top story IDs, then fetches each story's details.
    Stories without a title or URL are skipped.

    Returns:
        List of Post dicts with title, url, and source fields.
    """
    top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    story_ids = _http_get_json(top_url)[:30]

    posts: list[Post] = []
    for story_id in story_ids:
        item = _http_get_json(
            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        )
        if item and item.get("title") and item.get("url"):
            posts.append(
                Post(title=item["title"], url=item["url"], source="Hacker News")
            )
    return posts


def _http_get(url: str, headers: dict | None = None) -> str:
    """Make an HTTP GET request and return raw response text."""
    req = urllib.request.Request(url)
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode()


def _parse_rss(xml_text: str, source: str, limit: int = 25) -> list[Post]:
    """Parse RSS/Atom XML and return a list of Posts."""
    root = ET.fromstring(xml_text)
    posts = []

    # RSS 2.0 format
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item")
    for item in items[:limit]:
        title_el = item.find("title")
        link_el = item.find("link")
        title = title_el.text if title_el is not None else None
        url = link_el.text if link_el is not None else None
        if title and url:
            posts.append(Post(title=title.strip(), url=url.strip(), source=source))

    # Atom format fallback
    if not posts:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for entry in entries[:limit]:
            title_el = entry.find("{http://www.w3.org/2005/Atom}title")
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            title = title_el.text if title_el is not None else None
            url = link_el.get("href") if link_el is not None else None
            if title and url:
                posts.append(Post(title=title.strip(), url=url.strip(), source=source))

    return posts


def fetch_devto() -> list[Post]:
    """Fetch recent articles from Dev.to via RSS feed."""
    xml = _http_get("https://dev.to/feed")
    return _parse_rss(xml, source="Dev.to")


def fetch_reddit_aws() -> list[Post]:
    """Fetch recent posts from Reddit r/aws via RSS."""
    return _fetch_reddit_rss("aws")


def fetch_reddit_programming() -> list[Post]:
    """Fetch recent posts from Reddit r/programming via RSS."""
    return _fetch_reddit_rss("programming")


def _fetch_reddit_rss(subreddit: str) -> list[Post]:
    """Fetch posts from a subreddit via its RSS feed."""
    xml = _http_get(
        f"https://www.reddit.com/r/{subreddit}/hot.rss?limit=25",
        headers={"User-Agent": "DevCommunityPulseAgent/1.0"}
    )
    return _parse_rss(xml, source=f"Reddit r/{subreddit}")


def fetch_all_sources() -> list[Post]:
    """Fetch posts from all sources, skipping failed ones.
    
    Iterates over all fetcher functions, catches exceptions per source,
    logs errors for failed sources, and continues.
    Returns combined post list from successful sources.
    Returns empty list only when all sources fail.
    """
    fetchers = [
        ("Hacker News", fetch_hackernews),
        ("Dev.to", fetch_devto),
        ("Reddit r/aws", fetch_reddit_aws),
        ("Reddit r/programming", fetch_reddit_programming),
    ]
    
    all_posts: list[Post] = []
    for source_name, fetcher in fetchers:
        try:
            posts = fetcher()
            all_posts.extend(posts)
        except Exception as e:
            logger.error(f"Failed to fetch from {source_name}: {e}")
    
    return all_posts
