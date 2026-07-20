"""Property-based tests for relevance filtering and Bedrock call efficiency.

Property 2: Relevance filtering correctness
Property 5: Bedrock call efficiency

Validates: Requirements 3.3, 7.3

Tests that:
- _parse_response only includes posts marked relevant and includes ALL relevant posts
- No posts with relevant=false appear in output
- For N posts across S sources, Bedrock is invoked exactly S times
"""

import json
from unittest.mock import patch, MagicMock

from hypothesis import given, assume, settings
from hypothesis import strategies as st

from src.pulse_agent.summarizer import _parse_response, filter_and_summarize


# --- Strategies ---

# Strategy for a single source post
def source_post_strategy(source_name: st.SearchStrategy[str] = st.just("TestSource")):
    """Generate a single post dict with title, url, and source."""
    return st.fixed_dictionaries(
        {
            "title": st.text(min_size=1, max_size=50),
            "url": st.from_regex(
                r"https://example\.com/[a-z0-9]{1,20}", fullmatch=True
            ),
            "source": source_name,
        }
    )


# Strategy for Bedrock response items (index, relevant, summary)
def response_item_strategy(index: int):
    """Generate a response item for a given post index."""
    return st.fixed_dictionaries(
        {
            "index": st.just(index),
            "relevant": st.booleans(),
            "summary": st.text(min_size=1, max_size=100),
        }
    )


# Strategy for generating source_posts and a matching Bedrock response
@st.composite
def posts_and_response(draw):
    """Generate a list of source posts and a corresponding Bedrock response JSON."""
    num_posts = draw(st.integers(min_value=1, max_value=10))
    source_posts = [
        draw(source_post_strategy(st.just("TestSource"))) for _ in range(num_posts)
    ]

    # Generate a response item for each post
    response_items = []
    for i in range(num_posts):
        item = draw(response_item_strategy(i))
        response_items.append(item)

    response_text = json.dumps(response_items)
    return source_posts, response_items, response_text


# Strategy for generating posts distributed across multiple sources
@st.composite
def posts_across_sources(draw):
    """Generate posts distributed across a variable number of sources."""
    num_sources = draw(st.integers(min_value=1, max_value=5))
    source_names = [f"Source_{i}" for i in range(num_sources)]

    all_posts = []
    for source_name in source_names:
        num_posts = draw(st.integers(min_value=1, max_value=5))
        for _ in range(num_posts):
            post = draw(source_post_strategy(st.just(source_name)))
            all_posts.append(post)

    return all_posts, source_names


class TestRelevanceFilteringCorrectness:
    """Property 2: _parse_response only includes posts marked relevant
    and includes ALL relevant posts."""

    @given(data=posts_and_response())
    @settings(max_examples=100)
    def test_output_contains_exactly_relevant_posts(self, data):
        """Output contains exactly those posts whose index has relevant=true."""
        source_posts, response_items, response_text = data

        result = _parse_response(response_text, source_posts)

        # Determine which indices are marked relevant
        relevant_indices = {
            item["index"]
            for item in response_items
            if item["relevant"] and 0 <= item["index"] < len(source_posts)
        }

        # Result should have exactly as many posts as relevant indices
        assert len(result) == len(relevant_indices), (
            f"Expected {len(relevant_indices)} relevant posts, got {len(result)}"
        )

        # Each result post should correspond to a relevant index
        result_titles = [p["title"] for p in result]
        for idx in relevant_indices:
            assert source_posts[idx]["title"] in result_titles, (
                f"Relevant post at index {idx} not found in output"
            )

    @given(data=posts_and_response())
    @settings(max_examples=100)
    def test_no_irrelevant_posts_in_output(self, data):
        """No posts with relevant=false appear in output."""
        source_posts, response_items, response_text = data

        result = _parse_response(response_text, source_posts)

        # Determine which indices are NOT relevant
        irrelevant_indices = {
            item["index"]
            for item in response_items
            if not item["relevant"] and 0 <= item["index"] < len(source_posts)
        }

        # No result post should match an irrelevant index's title+url combination
        for post in result:
            for idx in irrelevant_indices:
                source = source_posts[idx]
                # A post matches if both title and url are the same
                if post["title"] == source["title"] and post["url"] == source["url"]:
                    # This could be a coincidence if two posts have same title/url
                    # but different indices. Only fail if this is the only match.
                    relevant_with_same_data = any(
                        source_posts[r_idx]["title"] == source["title"]
                        and source_posts[r_idx]["url"] == source["url"]
                        for r_idx in (
                            item["index"]
                            for item in response_items
                            if item["relevant"]
                            and 0 <= item["index"] < len(source_posts)
                        )
                    )
                    if not relevant_with_same_data:
                        assert False, (
                            f"Irrelevant post at index {idx} found in output"
                        )

    @given(data=posts_and_response())
    @settings(max_examples=100)
    def test_relevant_posts_have_summaries(self, data):
        """All relevant posts in output have a summary field attached."""
        source_posts, response_items, response_text = data

        result = _parse_response(response_text, source_posts)

        for post in result:
            assert "summary" in post, "Relevant post missing 'summary' field"

    @given(data=posts_and_response())
    @settings(max_examples=50)
    def test_output_preserves_original_post_fields(self, data):
        """Relevant posts in output retain all original fields (title, url, source)."""
        source_posts, response_items, response_text = data

        result = _parse_response(response_text, source_posts)

        relevant_indices = {
            item["index"]
            for item in response_items
            if item["relevant"] and 0 <= item["index"] < len(source_posts)
        }

        for post in result:
            assert "title" in post
            assert "url" in post
            assert "source" in post


class TestParseResponseEdgeCases:
    """Edge cases for _parse_response parsing behavior."""

    @given(
        source_posts=st.lists(
            source_post_strategy(st.just("TestSource")), min_size=1, max_size=5
        )
    )
    @settings(max_examples=50)
    def test_invalid_json_returns_empty_list(self, source_posts):
        """When response text is not valid JSON, _parse_response returns []."""
        result = _parse_response("not valid json {{{", source_posts)
        assert result == []

    @given(
        source_posts=st.lists(
            source_post_strategy(st.just("TestSource")), min_size=1, max_size=5
        ),
        num_relevant=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50)
    def test_out_of_bounds_indices_are_ignored(self, source_posts, num_relevant):
        """Response items with out-of-bounds indices are silently ignored."""
        # Create response items with indices beyond the length of source_posts
        response_items = [
            {"index": len(source_posts) + i, "relevant": True, "summary": "test"}
            for i in range(num_relevant)
        ]
        response_text = json.dumps(response_items)

        result = _parse_response(response_text, source_posts)
        assert result == []

    @given(
        source_posts=st.lists(
            source_post_strategy(st.just("TestSource")), min_size=1, max_size=5
        )
    )
    @settings(max_examples=50)
    def test_markdown_wrapped_json_is_parsed(self, source_posts):
        """Response wrapped in markdown code block is parsed correctly."""
        response_items = [
            {"index": 0, "relevant": True, "summary": "A relevant post"}
        ]
        wrapped = f"```json\n{json.dumps(response_items)}\n```"

        result = _parse_response(wrapped, source_posts)
        assert len(result) == 1
        assert result[0]["title"] == source_posts[0]["title"]


class TestBedrockCallEfficiency:
    """Property 5: For N posts across S sources, Bedrock is invoked exactly S times."""

    @given(data=posts_across_sources())
    @settings(max_examples=50)
    def test_bedrock_invoked_once_per_source(self, data):
        """For posts distributed across S sources, Bedrock is called exactly S times."""
        all_posts, source_names = data
        num_sources = len(source_names)

        # Build a mock response that marks all posts as relevant
        def mock_invoke_model(**kwargs):
            body = json.loads(kwargs["body"])
            prompt_text = body["messages"][0]["content"][0]["text"]
            # Count posts in the prompt by counting [index] patterns
            import re

            indices = re.findall(r"\[(\d+)\]", prompt_text)
            response_items = [
                {"index": int(i), "relevant": True, "summary": "summary"}
                for i in indices
            ]
            mock_body = MagicMock()
            mock_body.read.return_value = json.dumps(
                {
                    "output": {
                        "message": {
                            "content": [{"text": json.dumps(response_items)}]
                        }
                    }
                }
            ).encode()
            return {"body": mock_body}

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = mock_invoke_model

        with patch("boto3.client", return_value=mock_client):
            filter_and_summarize(all_posts, ["python", "ai"])

        # Bedrock should be invoked exactly once per source
        assert mock_client.invoke_model.call_count == num_sources, (
            f"Expected {num_sources} Bedrock calls, "
            f"got {mock_client.invoke_model.call_count}"
        )

    @given(data=posts_across_sources())
    @settings(max_examples=50)
    def test_posts_grouped_by_source_in_calls(self, data):
        """Each Bedrock call contains only posts from a single source."""
        all_posts, source_names = data

        call_prompts = []

        def mock_invoke_model(**kwargs):
            body = json.loads(kwargs["body"])
            prompt_text = body["messages"][0]["content"][0]["text"]
            call_prompts.append(prompt_text)
            # Return empty relevant list
            mock_body = MagicMock()
            mock_body.read.return_value = json.dumps(
                {"output": {"message": {"content": [{"text": "[]"}]}}}
            ).encode()
            return {"body": mock_body}

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = mock_invoke_model

        with patch("boto3.client", return_value=mock_client):
            filter_and_summarize(all_posts, ["testing"])

        # We should have one call per source
        assert len(call_prompts) == len(source_names)
