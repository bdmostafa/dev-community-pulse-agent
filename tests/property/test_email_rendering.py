"""Property-based tests for email rendering completeness.

Property 3: Email rendering completeness
- For any non-empty list of summarized posts, the HTML contains a section
  heading per source, and each post has its title, summary, and anchor link.

Validates: Requirements 4.1, 4.2
"""

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from src.pulse_agent.email_composer import compose_html

# --- Strategies ---

source_names = st.text(min_size=1, max_size=30, alphabet=st.characters(
    whitelist_categories=("L", "N", "Z"),
    whitelist_characters=" -_",
))

post_titles = st.text(min_size=1, max_size=100, alphabet=st.characters(
    whitelist_categories=("L", "N", "Z", "P"),
    whitelist_characters=" -_!?",
))

post_urls = st.from_regex(r"https://[a-z]{1,10}\.[a-z]{2,4}/[a-z0-9]{1,20}", fullmatch=True)

summaries = st.text(min_size=1, max_size=200, alphabet=st.characters(
    whitelist_categories=("L", "N", "Z", "P"),
    whitelist_characters=" -_.,!?",
))

summarized_post = st.fixed_dictionaries({
    "title": post_titles,
    "url": post_urls,
    "source": source_names,
    "summary": summaries,
})

non_empty_posts = st.lists(summarized_post, min_size=1, max_size=20)


# --- Tests ---


@given(posts=non_empty_posts)
@settings(max_examples=100)
def test_html_contains_section_heading_per_source(posts: list[dict]) -> None:
    """For any generated posts with various sources, the HTML output contains
    an <h2> for each unique source."""
    html = compose_html(posts)
    unique_sources = {p["source"] for p in posts}

    for source in unique_sources:
        assert f"<h2>{source}</h2>" in html, (
            f"Missing <h2> heading for source: {source!r}"
        )


@given(posts=non_empty_posts)
@settings(max_examples=100)
def test_html_contains_post_title_and_summary(posts: list[dict]) -> None:
    """Each post's title text and summary text appear in the HTML."""
    html = compose_html(posts)

    for post in posts:
        assert post["title"] in html, (
            f"Post title missing from HTML: {post['title']!r}"
        )
        assert post["summary"] in html, (
            f"Post summary missing from HTML: {post['summary']!r}"
        )


@given(posts=non_empty_posts)
@settings(max_examples=100)
def test_html_contains_anchor_link_per_post(posts: list[dict]) -> None:
    """Each post has an <a href="..."> element with its URL."""
    html = compose_html(posts)

    for post in posts:
        expected_anchor = f'<a href="{post["url"]}">'
        assert expected_anchor in html, (
            f"Missing anchor link for URL: {post['url']!r}"
        )


@given(posts=non_empty_posts)
@settings(max_examples=100)
def test_html_contains_all_posts(posts: list[dict]) -> None:
    """Number of <li> elements equals number of posts."""
    html = compose_html(posts)
    li_count = len(re.findall(r"<li>", html))

    assert li_count == len(posts), (
        f"Expected {len(posts)} <li> elements, found {li_count}"
    )
