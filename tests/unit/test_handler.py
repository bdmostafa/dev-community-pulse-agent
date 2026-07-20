"""Unit tests for the Lambda handler orchestration logic."""

from unittest.mock import patch, MagicMock

from src.pulse_agent.handler import lambda_handler


@patch("src.pulse_agent.handler.send_digest_email")
@patch("src.pulse_agent.handler.filter_and_summarize")
@patch("src.pulse_agent.handler.fetch_all_sources")
@patch("src.pulse_agent.handler.load_config")
def test_handler_full_pipeline(
    mock_load_config,
    mock_fetch_all_sources,
    mock_filter_and_summarize,
    mock_send_digest_email,
):
    """Test full pipeline execution with mocked dependencies.

    Verify all steps are called in order and response includes post count.
    """
    mock_load_config.return_value = {"interests": ["python", "ai"]}
    mock_fetch_all_sources.return_value = [
        {"title": "Post 1", "source": "reddit"},
        {"title": "Post 2", "source": "hackernews"},
    ]
    mock_filter_and_summarize.return_value = [
        {"title": "Post 1", "source": "reddit", "summary": "A Python post"},
    ]

    response = lambda_handler({}, None)

    mock_load_config.assert_called_once()
    mock_fetch_all_sources.assert_called_once()
    mock_filter_and_summarize.assert_called_once_with(
        mock_fetch_all_sources.return_value, ["python", "ai"]
    )
    mock_send_digest_email.assert_called_once_with(
        mock_filter_and_summarize.return_value, mock_load_config.return_value
    )
    assert response["statusCode"] == 200
    assert "1 posts" in response["body"]


@patch("src.pulse_agent.handler.send_digest_email")
@patch("src.pulse_agent.handler.filter_and_summarize")
@patch("src.pulse_agent.handler.fetch_all_sources")
@patch("src.pulse_agent.handler.load_config")
def test_handler_exits_early_when_no_posts(
    mock_load_config,
    mock_fetch_all_sources,
    mock_filter_and_summarize,
    mock_send_digest_email,
):
    """Mock fetch_all_sources to return empty list.

    Verify filter_and_summarize and send_digest_email are NOT called.
    Verify response body mentions no posts.
    """
    mock_load_config.return_value = {"interests": ["python"]}
    mock_fetch_all_sources.return_value = []

    response = lambda_handler({}, None)

    mock_load_config.assert_called_once()
    mock_fetch_all_sources.assert_called_once()
    mock_filter_and_summarize.assert_not_called()
    mock_send_digest_email.assert_not_called()
    assert response["statusCode"] == 200
    assert "No posts" in response["body"]


@patch("src.pulse_agent.handler.send_digest_email")
@patch("src.pulse_agent.handler.filter_and_summarize")
@patch("src.pulse_agent.handler.fetch_all_sources")
@patch("src.pulse_agent.handler.load_config")
def test_handler_skips_email_when_no_relevant(
    mock_load_config,
    mock_fetch_all_sources,
    mock_filter_and_summarize,
    mock_send_digest_email,
):
    """Mock fetch_all_sources to return posts but filter_and_summarize returns empty.

    Verify send_digest_email is NOT called.
    Verify response mentions no relevant posts.
    """
    mock_load_config.return_value = {"interests": ["python"]}
    mock_fetch_all_sources.return_value = [
        {"title": "Post 1", "source": "reddit"},
    ]
    mock_filter_and_summarize.return_value = []

    response = lambda_handler({}, None)

    mock_load_config.assert_called_once()
    mock_fetch_all_sources.assert_called_once()
    mock_filter_and_summarize.assert_called_once_with(
        mock_fetch_all_sources.return_value, ["python"]
    )
    mock_send_digest_email.assert_not_called()
    assert response["statusCode"] == 200
    assert "No relevant posts" in response["body"]
