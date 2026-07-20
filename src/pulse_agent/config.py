"""Configuration loader and validator for the Pulse Agent."""

import json
import logging

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["interests", "recipient_email", "sender_email"]


class ConfigValidationError(Exception):
    """Raised when the configuration file is missing or has invalid fields."""

    pass


def load_config(config_path: str = "interest_config.json") -> dict:
    """Load and validate the interest configuration file.

    Args:
        config_path: Path to the JSON configuration file.

    Returns:
        Validated configuration dictionary.

    Raises:
        ConfigValidationError: If required fields are missing or invalid.
    """
    with open(config_path, "r") as f:
        config = json.load(f)

    missing = [field for field in REQUIRED_FIELDS if field not in config]
    if missing:
        logger.error(f"Config validation failed - missing fields: {missing}")
        raise ConfigValidationError(f"Missing required fields: {missing}")

    if not isinstance(config["interests"], list) or len(config["interests"]) == 0:
        logger.error("Config validation failed - interests must be a non-empty list")
        raise ConfigValidationError("interests must be a non-empty list")

    return config
