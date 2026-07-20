"""Unit tests for content fetchers."""

from unittest.mock import patch, MagicMock

from src.pulse_agent.fetchers import (
    fetch_hackernews,
    fetch_devto,
    fetch_reddit_aws,
    fetch_reddit_programming,
    fetch_all_sources,
)


@patch("src.pulse_agent.fetchers._http_get_json")
def test_fetch_hackernews(mock_get):
    """Mock _http_get_json to return fake story IDs and story data, verify correct Post list."""
    mock_get.side_effect = [
        [101, 102],  # top story IDs
        {"title": "Story A", "url": "https://a.com", "id": 101},
        {"title": "Story B", "url": "https://b.com", "id": 102},
    ]

    posts = fetch_hackernews()

    assert len(posts) == 2
    assert posts[0] == {"title": "Story A", "url": "https://a.com", "source": "Hacker News"}
    assert posts[1] == {"title": "Story B", "url": "https://b.com", "source": "Hacker News"}


@patch("src.pulse_agent.fetchers._http_get")
def test_fetch_devto(mock_get):
    """Mock _http_get to return fake RSS XML, verify correct Post list."""
    mock_get.return_value = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <item><title>Dev Article 1</title><link>https://dev.to/article1</link></item>
        <item><title>Dev Article 2</title><link>https://dev.to/article2</link></item>
      </channel>
    </rss>"""

    posts = fetch_devto()

    assert len(posts) == 2
    assert posts[0] == {"title": "Dev Article 1", "url": "https://dev.to/article1", "source": "Dev.to"}
    assert posts[1] == {"title": "Dev Article 2", "url": "https://dev.to/article2", "source": "Dev.to"}


@patch("src.pulse_agent.fetchers._http_get")
def test_fetch_reddit_aws(mock_get):
    """Mock _http_get to return fake Atom XML, verify 'Reddit r/aws' source."""
    mock_get.return_value = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>AWS Post 1</title><link href="https://reddit.com/r/aws/1"/></entry>
      <entry><title>AWS Post 2</title><link href="https://reddit.com/r/aws/2"/></entry>
    </feed>"""

    posts = fetch_reddit_aws()

    assert len(posts) == 2
    assert posts[0] == {"title": "AWS Post 1", "url": "https://reddit.com/r/aws/1", "source": "Reddit r/aws"}
    assert posts[1] == {"title": "AWS Post 2", "url": "https://reddit.com/r/aws/2", "source": "Reddit r/aws"}


@patch("src.pulse_agent.fetchers._http_get")
def test_fetch_reddit_programming(mock_get):
    """Mock _http_get to return fake Atom XML, verify 'Reddit r/programming' source."""
    mock_get.return_value = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Prog Post</title><link href="https://reddit.com/r/programming/1"/></entry>
    </feed>"""

    posts = fetch_reddit_programming()

    assert len(posts) == 1
    assert posts[0] == {
        "title": "Prog Post",
        "url": "https://reddit.com/r/programming/1",
        "source": "Reddit r/programming",
    }


@patch("src.pulse_agent.fetchers._http_get_json")
def test_fetch_hackernews_skips_items_without_url(mock_get):
    """Mock items missing url field, verify they're skipped."""
    mock_get.side_effect = [
        [201, 202, 203],  # story IDs
        {"title": "Has URL", "url": "https://valid.com", "id": 201},
        {"title": "No URL Item", "id": 202},  # missing url
        None,  # null item
    ]

    posts = fetch_hackernews()

    assert len(posts) == 1
    assert posts[0]["title"] == "Has URL"


@patch("src.pulse_agent.fetchers.fetch_reddit_programming")
@patch("src.pulse_agent.fetchers.fetch_reddit_aws")
@patch("src.pulse_agent.fetchers.fetch_devto")
@patch("src.pulse_agent.fetchers.fetch_hackernews")
def test_fetch_all_sources_skips_failed(mock_hn, mock_dev, mock_aws, mock_prog):
    """Mock one fetcher to raise exception, verify others still return data."""
    mock_hn.return_value = [{"title": "HN", "url": "https://hn.com", "source": "Hacker News"}]
    mock_dev.side_effect = Exception("Dev.to is down")
    mock_aws.return_value = [{"title": "AWS", "url": "https://aws.com", "source": "Reddit r/aws"}]
    mock_prog.return_value = [{"title": "Prog", "url": "https://prog.com", "source": "Reddit r/programming"}]

    posts = fetch_all_sources()

    assert len(posts) == 3
    sources = {p["source"] for p in posts}
    assert "Hacker News" in sources
    assert "Reddit r/aws" in sources
    assert "Reddit r/programming" in sources
    assert "Dev.to" not in sources


@patch("src.pulse_agent.fetchers.fetch_reddit_programming")
@patch("src.pulse_agent.fetchers.fetch_reddit_aws")
@patch("src.pulse_agent.fetchers.fetch_devto")
@patch("src.pulse_agent.fetchers.fetch_hackernews")
def test_fetch_all_sources_all_fail(mock_hn, mock_dev, mock_aws, mock_prog):
    """Mock all fetchers to raise, verify empty list returned."""
    mock_hn.side_effect = Exception("fail")
    mock_dev.side_effect = Exception("fail")
    mock_aws.side_effect = Exception("fail")
    mock_prog.side_effect = Exception("fail")

    posts = fetch_all_sources()

    assert posts == []
