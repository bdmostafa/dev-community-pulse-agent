"""Unit tests for the summarizer module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.pulse_agent.summarizer import _build_prompt, _parse_response, filter_and_summarize


class TestBuildPrompt:
    """Tests for _build_prompt."""

    def test_build_prompt_includes_all_posts_and_interests(self):
        """Test _build_prompt includes all post titles and all interests in the output string."""
        posts = [
            {"title": "Intro to FastAPI", "url": "https://example.com/fastapi", "source": "dev.to"},
            {"title": "Rust vs Go", "url": "https://example.com/rust-go", "source": "dev.to"},
            {"title": "AWS Lambda Tips", "url": "https://example.com/lambda", "source": "dev.to"},
        ]
        interests = ["Python", "Cloud Computing", "Rust"]

        result = _build_prompt(posts, interests)

        # All post titles should appear in the prompt
        for post in posts:
            assert post["title"] in result

        # All interests should appear in the prompt
        for interest in interests:
            assert interest in result


class TestParseResponse:
    """Tests for _parse_response."""

    def test_parse_response_valid_json(self):
        """Test _parse_response with valid JSON response returns only relevant posts with summaries attached."""
        source_posts = [
            {"title": "Post A", "url": "https://a.com", "source": "dev.to"},
            {"title": "Post B", "url": "https://b.com", "source": "dev.to"},
            {"title": "Post C", "url": "https://c.com", "source": "dev.to"},
        ]
        response_text = json.dumps([
            {"index": 0, "relevant": True, "summary": "Summary of Post A"},
            {"index": 1, "relevant": False, "summary": ""},
            {"index": 2, "relevant": True, "summary": "Summary of Post C"},
        ])

        result = _parse_response(response_text, source_posts)

        assert len(result) == 2
        assert result[0]["title"] == "Post A"
        assert result[0]["summary"] == "Summary of Post A"
        assert result[1]["title"] == "Post C"
        assert result[1]["summary"] == "Summary of Post C"

    def test_parse_response_code_block_wrapped(self):
        """Test _parse_response handles JSON wrapped in ```json ... ``` markdown code blocks."""
        source_posts = [
            {"title": "Post X", "url": "https://x.com", "source": "reddit"},
        ]
        inner_json = json.dumps([
            {"index": 0, "relevant": True, "summary": "Relevant post about X"},
        ])
        response_text = f"```json\n{inner_json}\n```"

        result = _parse_response(response_text, source_posts)

        assert len(result) == 1
        assert result[0]["title"] == "Post X"
        assert result[0]["summary"] == "Relevant post about X"

    def test_parse_response_malformed_json(self):
        """Test _parse_response returns empty list for malformed JSON."""
        source_posts = [
            {"title": "Post Y", "url": "https://y.com", "source": "hn"},
        ]
        response_text = "this is not valid json {[}"

        result = _parse_response(response_text, source_posts)

        assert result == []

    def test_parse_response_invalid_index(self):
        """Test _parse_response handles out-of-range indices gracefully."""
        source_posts = [
            {"title": "Only Post", "url": "https://only.com", "source": "dev.to"},
        ]
        response_text = json.dumps([
            {"index": 5, "relevant": True, "summary": "Out of range"},
            {"index": -1, "relevant": True, "summary": "Negative index"},
            {"index": 0, "relevant": True, "summary": "Valid index"},
        ])

        result = _parse_response(response_text, source_posts)

        # Only index 0 is valid (index -1 fails the 0 <= idx check)
        assert len(result) == 1
        assert result[0]["title"] == "Only Post"
        assert result[0]["summary"] == "Valid index"


class TestFilterAndSummarize:
    """Tests for filter_and_summarize."""

    @patch("src.pulse_agent.summarizer.boto3.client")
    def test_filter_and_summarize_calls_bedrock_per_source(self, mock_boto_client):
        """Mock boto3 client, pass posts from 2 sources, verify invoke_model called exactly 2 times."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Set up mock response for invoke_model
        def make_response(posts):
            body_content = json.dumps({
                "output": {
                    "message": {
                        "content": [{"text": json.dumps([
                            {"index": 0, "relevant": True, "summary": "A summary"}
                        ])}]
                    }
                }
            })
            mock_body = MagicMock()
            mock_body.read.return_value = body_content.encode()
            return {"body": mock_body}

        mock_client.invoke_model.side_effect = [make_response(None), make_response(None)]

        posts = [
            {"title": "Post from Dev", "url": "https://dev.to/1", "source": "dev.to"},
            {"title": "Post from HN", "url": "https://hn.com/1", "source": "hackernews"},
        ]
        interests = ["Python", "AI"]

        result = filter_and_summarize(posts, interests)

        # Should call invoke_model exactly 2 times (once per source)
        assert mock_client.invoke_model.call_count == 2
        # Should return relevant posts from both sources
        assert len(result) == 2
