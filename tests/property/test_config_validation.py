"""Property-based tests for config validation correctness (Property 4).

Validates: Requirements 5.2, 5.3, 5.4, 5.5

Tests that:
- Any JSON with all required fields (non-empty interests list, recipient_email, sender_email) is accepted
- Any JSON missing required fields is rejected with an error identifying the missing fields
- Any JSON with an empty interests list is rejected
"""

import json
import tempfile
import os

import pytest
from hypothesis import given, assume, settings
from hypothesis import strategies as st

from src.pulse_agent.config import load_config, ConfigValidationError


# --- Strategies ---

non_empty_interests = st.lists(st.text(min_size=1), min_size=1, max_size=10)

valid_config_strategy = st.fixed_dictionaries(
    {
        "interests": non_empty_interests,
        "recipient_email": st.text(min_size=1),
        "sender_email": st.text(min_size=1),
    },
    optional=st.just({}).flatmap(
        lambda _: st.dictionaries(
            keys=st.text(min_size=1).filter(
                lambda k: k not in ("interests", "recipient_email", "sender_email")
            ),
            values=st.text(),
            max_size=3,
        )
    ),
)


def _write_config_to_temp(config_data: dict) -> str:
    """Write config dict to a temporary JSON file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="test_config_"
    )
    json.dump(config_data, tmp)
    tmp.close()
    return tmp.name


class TestValidConfigAccepted:
    """Property: Any config with all required fields and non-empty interests is accepted."""

    @given(
        interests=non_empty_interests,
        recipient_email=st.text(min_size=1),
        sender_email=st.text(min_size=1),
        extra_fields=st.dictionaries(
            keys=st.text(min_size=1).filter(
                lambda k: k not in ("interests", "recipient_email", "sender_email")
            ),
            values=st.text(),
            max_size=3,
        ),
    )
    @settings(max_examples=50)
    def test_valid_config_is_accepted(
        self, interests, recipient_email, sender_email, extra_fields
    ):
        """Any JSON with all required fields (non-empty interests list,
        recipient_email string, sender_email string) is accepted by load_config."""
        config_data = {
            "interests": interests,
            "recipient_email": recipient_email,
            "sender_email": sender_email,
            **extra_fields,
        }
        path = _write_config_to_temp(config_data)
        try:
            result = load_config(path)
            assert result["interests"] == interests
            assert result["recipient_email"] == recipient_email
            assert result["sender_email"] == sender_email
        finally:
            os.unlink(path)


class TestMissingFieldsRejected:
    """Property: Any config missing at least one required field is rejected
    with an error identifying the missing fields."""

    @given(
        fields_to_remove=st.lists(
            st.sampled_from(["interests", "recipient_email", "sender_email"]),
            min_size=1,
            max_size=3,
            unique=True,
        ),
        interests=non_empty_interests,
        recipient_email=st.text(min_size=1),
        sender_email=st.text(min_size=1),
    )
    @settings(max_examples=50)
    def test_missing_required_fields_raises_error(
        self, fields_to_remove, interests, recipient_email, sender_email
    ):
        """Any JSON missing required fields is rejected with ConfigValidationError
        that identifies the missing field names in the error message."""
        config_data = {
            "interests": interests,
            "recipient_email": recipient_email,
            "sender_email": sender_email,
        }

        for field in fields_to_remove:
            del config_data[field]

        path = _write_config_to_temp(config_data)
        try:
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config(path)

            error_message = str(exc_info.value)
            for field in fields_to_remove:
                assert field in error_message, (
                    f"Missing field '{field}' not mentioned in error: {error_message}"
                )
        finally:
            os.unlink(path)


class TestEmptyInterestsRejected:
    """Property: Any config with an empty interests list is rejected."""

    @given(
        recipient_email=st.text(min_size=1),
        sender_email=st.text(min_size=1),
    )
    @settings(max_examples=50)
    def test_empty_interests_raises_error(self, recipient_email, sender_email):
        """A config with an empty interests list raises ConfigValidationError."""
        config_data = {
            "interests": [],
            "recipient_email": recipient_email,
            "sender_email": sender_email,
        }
        path = _write_config_to_temp(config_data)
        try:
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config(path)

            error_message = str(exc_info.value)
            assert "interests" in error_message.lower(), (
                f"Error should mention 'interests': {error_message}"
            )
        finally:
            os.unlink(path)
