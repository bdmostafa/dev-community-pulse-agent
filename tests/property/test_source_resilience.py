"""Property-based tests for partial source failure resilience (Property 1).

Validates: Requirements 2.5

Tests that:
- For any subset of sources that raise exceptions, posts from non-failing sources
  are all returned without data loss
- No posts from failing sources appear in the result
- When all sources fail, result is an empty list
"""

from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.pulse_agent.fetchers import fetch_all_sources, Post


# --- Constants ---

SOURCES = [
    ("Hacker News", "src.pulse_agent.fetchers.fetch_hackernews"),
    ("Dev.to", "src.pulse_agent.fetchers.fetch_devto"),
    ("Reddit r/aws", "src.pulse_agent.fetchers.fetch_reddit_aws"),
    ("Reddit r/programming", "src.pulse_agent.fetchers.fetch_reddit_programming"),
]

# --- Strategies ---

# Generate a non-empty subset of source indices that will fail
failing_source_indices = st.lists(
    st.integers(min_value=0, max_value=len(SOURCES) - 1),
    min_size=1,
    max_size=len(SOURCES) - 1,
    unique=True,
)

# Generate mock posts for a given source name
def mock_posts_strategy(source_name: str) -> st.SearchStrategy[list[Post]]:
    """Generate a list of mock posts for a specific source."""
    return st.lists(
        st.fixed_dictionaries(
            {
                "title": st.text(min_size=1, max_size=50),
                "url": st.from_regex(r"https://example\.com/[a-z0-9]{1,20}", fullmatch=True),
                "source": st.just(source_name),
            }
        ),
        min_size=1,
        max_size=5,
    )


# Generate posts for all sources (used to provide return values for working sources)
all_source_posts = st.fixed_dictionaries(
    {name: mock_posts_strategy(name) for name, _ in SOURCES}
)


class TestPartialSourceFailure:
    """Property: For any subset of failing sources, posts from non-failing
    sources are all returned without data loss."""

    @given(
        failing_indices=failing_source_indices,
        source_posts=all_source_posts,
    )
    @settings(max_examples=50)
    def test_non_failing_sources_return_all_posts(
        self, failing_indices, source_posts
    ):
        """For any subset of sources that raise exceptions, all posts from
        non-failing sources appear in the result."""
        failing_set = set(failing_indices)

        patches = {}
        for i, (source_name, patch_path) in enumerate(SOURCES):
            if i in failing_set:
                patches[patch_path] = Exception(f"Simulated failure for {source_name}")
            else:
                patches[patch_path] = source_posts[source_name]

        with _apply_patches(patches):
            result = fetch_all_sources()

        # Collect expected posts from non-failing sources
        expected_posts = []
        for i, (source_name, _) in enumerate(SOURCES):
            if i not in failing_set:
                expected_posts.extend(source_posts[source_name])

        # All posts from non-failing sources must be present
        assert len(result) == len(expected_posts)
        for post in expected_posts:
            assert post in result, (
                f"Post {post!r} from a non-failing source is missing from result"
            )

    @given(
        failing_indices=failing_source_indices,
        source_posts=all_source_posts,
    )
    @settings(max_examples=50)
    def test_no_posts_from_failing_sources(self, failing_indices, source_posts):
        """No posts from failing sources appear in the result."""
        failing_set = set(failing_indices)

        patches = {}
        for i, (source_name, patch_path) in enumerate(SOURCES):
            if i in failing_set:
                patches[patch_path] = Exception(f"Simulated failure for {source_name}")
            else:
                patches[patch_path] = source_posts[source_name]

        with _apply_patches(patches):
            result = fetch_all_sources()

        # Identify source names that failed
        failing_source_names = {
            SOURCES[i][0] for i in failing_indices
        }

        # No post in the result should be from a failing source
        for post in result:
            assert post["source"] not in failing_source_names, (
                f"Post from failing source '{post['source']}' found in result"
            )


class TestAllSourcesFail:
    """Property: When all sources fail, the result is an empty list."""

    @given(
        source_posts=all_source_posts,
    )
    @settings(max_examples=20)
    def test_all_sources_fail_returns_empty(self, source_posts):
        """When every source raises an exception, fetch_all_sources returns []."""
        patches = {}
        for source_name, patch_path in SOURCES:
            patches[patch_path] = Exception(f"Simulated failure for {source_name}")

        with _apply_patches(patches):
            result = fetch_all_sources()

        assert result == []


class TestNoSourcesFail:
    """Property: When no sources fail, all posts from all sources are returned."""

    @given(source_posts=all_source_posts)
    @settings(max_examples=50)
    def test_all_sources_succeed_returns_all_posts(self, source_posts):
        """When all sources succeed, every post from every source is in the result."""
        patches = {}
        for source_name, patch_path in SOURCES:
            patches[patch_path] = source_posts[source_name]

        with _apply_patches(patches):
            result = fetch_all_sources()

        expected_posts = []
        for source_name, _ in SOURCES:
            expected_posts.extend(source_posts[source_name])

        assert len(result) == len(expected_posts)
        for post in expected_posts:
            assert post in result


# --- Helpers ---

class _apply_patches:
    """Context manager that patches multiple fetcher functions.

    Args:
        patch_map: Dict mapping dotted patch paths to either:
            - An Exception instance (the mock will raise it)
            - A list of Posts (the mock will return it)
    """

    def __init__(self, patch_map: dict):
        self._patch_map = patch_map
        self._patchers = []

    def __enter__(self):
        for target, value in self._patch_map.items():
            patcher = patch(target)
            mock_obj = patcher.start()
            if isinstance(value, Exception):
                mock_obj.side_effect = value
            else:
                mock_obj.return_value = value
            self._patchers.append(patcher)
        return self

    def __exit__(self, *args):
        for patcher in self._patchers:
            patcher.stop()
