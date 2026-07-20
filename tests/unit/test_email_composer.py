"""Unit tests for the email composer module."""

from unittest.mock import patch, MagicMock
from src.pulse_agent.email_composer import compose_html, send_digest_email

SAMPLE_POSTS = [
    {"title": "AWS Lambda Guide", "url": "https://example.com/lambda", "source": "Hacker News", "summary": "A comprehensive guide to Lambda."},
    {"title": "Python Tips", "url": "https://example.com/python", "source": "Dev.to", "summary": "Useful Python tips for developers."},
    {"title": "Cloud Architecture", "url": "https://example.com/cloud", "source": "Hacker News", "summary": "Modern cloud architecture patterns."},
]


def test_compose_html_contains_source_headings():
    """Test HTML output contains all source section headings as <h2> elements."""
    html = compose_html(SAMPLE_POSTS)

    assert "<h2>Hacker News</h2>" in html
    assert "<h2>Dev.to</h2>" in html


def test_compose_html_contains_post_details():
    """Test each post has title, summary, and link in HTML."""
    html = compose_html(SAMPLE_POSTS)

    for post in SAMPLE_POSTS:
        assert post["title"] in html
        assert post["summary"] in html
        assert post["url"] in html


@patch("src.pulse_agent.email_composer.boto3.client")
def test_send_digest_email_subject_contains_date(mock_boto_client):
    """Test email subject contains current date."""
    mock_ses = MagicMock()
    mock_boto_client.return_value = mock_ses

    config = {"sender_email": "sender@example.com", "recipient_email": "recipient@example.com"}
    send_digest_email(SAMPLE_POSTS, config)

    call_args = mock_ses.send_email.call_args
    subject = call_args[1]["Message"]["Subject"]["Data"]

    # Subject should start with "Dev Community Pulse - " followed by a date in YYYY-MM-DD format
    assert subject.startswith("Dev Community Pulse - ")
    date_part = subject.replace("Dev Community Pulse - ", "")
    # Validate date format
    from datetime import datetime
    datetime.strptime(date_part, "%Y-%m-%d")


@patch("src.pulse_agent.email_composer.boto3.client")
@patch("src.pulse_agent.email_composer.logger")
def test_send_digest_email_ses_error_logging(mock_logger, mock_boto_client):
    """Test SES error logging on delivery failure."""
    mock_ses = MagicMock()
    mock_boto_client.return_value = mock_ses
    mock_ses.send_email.side_effect = Exception("SES unavailable")

    config = {"sender_email": "sender@example.com", "recipient_email": "recipient@example.com"}
    send_digest_email(SAMPLE_POSTS, config)

    mock_logger.error.assert_called_once()
    error_message = mock_logger.error.call_args[0][0]
    assert "SES" in error_message or "failed" in error_message.lower()
