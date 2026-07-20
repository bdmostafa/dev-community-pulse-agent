"""Unit tests for the config loader."""

import json
import tempfile

import pytest

from src.pulse_agent.config import ConfigValidationError, load_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_valid(self):
        """Test successful load with valid config file containing all fields."""
        config_data = {
            "interests": ["python", "rust"],
            "recipient_email": "recipient@example.com",
            "sender_email": "sender@example.com",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(config_data, tmp)
            tmp_path = tmp.name

        result = load_config(tmp_path)

        assert result == config_data

    def test_load_config_missing_fields(self):
        """Test that missing fields raise ConfigValidationError with field names in message."""
        config_data = {"interests": ["python"]}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(config_data, tmp)
            tmp_path = tmp.name

        with pytest.raises(ConfigValidationError, match="Missing required fields"):
            load_config(tmp_path)

    def test_load_config_empty_interests(self):
        """Test that empty interests list raises ConfigValidationError."""
        config_data = {
            "interests": [],
            "recipient_email": "recipient@example.com",
            "sender_email": "sender@example.com",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(config_data, tmp)
            tmp_path = tmp.name

        with pytest.raises(ConfigValidationError, match="non-empty list"):
            load_config(tmp_path)

    def test_load_config_non_list_interests(self):
        """Test that non-list interests value raises ConfigValidationError."""
        config_data = {
            "interests": "python",
            "recipient_email": "recipient@example.com",
            "sender_email": "sender@example.com",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(config_data, tmp)
            tmp_path = tmp.name

        with pytest.raises(ConfigValidationError, match="non-empty list"):
            load_config(tmp_path)
