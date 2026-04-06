"""Tests for the deep field sanitizer."""

from __future__ import annotations

from zerionis_log.sanitizer import REDACTED, Sanitizer


class TestSanitizerBasic:
    def test_password_redacted(self) -> None:
        s = Sanitizer()
        result = s.sanitize({"password": "secret123"})
        assert result["password"] == REDACTED

    def test_nested_redaction(self) -> None:
        s = Sanitizer()
        result = s.sanitize({"user": {"token": "abcdefghijklmnopqrst"}})
        assert result["user"]["token"] == "abcd...qrst"

    def test_deep_list_redaction(self) -> None:
        s = Sanitizer()
        result = s.sanitize({"items": [{"api_key": "1234567890abcdefghij"}]})
        assert result["items"][0]["api_key"] == "1234...ghij"

    def test_non_sensitive_passthrough(self) -> None:
        s = Sanitizer()
        result = s.sanitize({"name": "Alice", "age": 30})
        assert result == {"name": "Alice", "age": 30}


class TestPartialRedaction:
    def test_long_value_partial(self) -> None:
        s = Sanitizer(partial_redaction=True)
        result = s.sanitize({"token": "abcdefghijklmnopqrst"})
        assert result["token"] == "abcd...qrst"

    def test_short_value_full_redact(self) -> None:
        s = Sanitizer(partial_redaction=True)
        result = s.sanitize({"token": "shortvalue12345"})
        assert result["token"] == REDACTED

    def test_partial_disabled(self) -> None:
        s = Sanitizer(partial_redaction=False)
        result = s.sanitize({"token": "abcdefghijklmnopqrst"})
        assert result["token"] == REDACTED


class TestHeaders:
    def test_authorization_header(self) -> None:
        s = Sanitizer()
        result = s.sanitize_headers({"Authorization": "Bearer abcdefghijklmnop1234"})
        assert result["Authorization"] == "Bear...1234"

    def test_cookie_header(self) -> None:
        s = Sanitizer()
        result = s.sanitize_headers({"Cookie": "session=abc"})
        assert result["Cookie"] == REDACTED

    def test_safe_header_passthrough(self) -> None:
        s = Sanitizer()
        result = s.sanitize_headers({"Content-Type": "application/json"})
        assert result["Content-Type"] == "application/json"


class TestExtraFields:
    def test_custom_fields(self) -> None:
        s = Sanitizer(extra_fields=["my_secret"])
        result = s.sanitize({"my_secret": "hidden"})
        assert result["my_secret"] == REDACTED


class TestDisabled:
    def test_disabled_passthrough(self) -> None:
        s = Sanitizer(enabled=False)
        result = s.sanitize({"password": "visible"})
        assert result["password"] == "visible"


class TestEdgeCases:
    def test_none_value(self) -> None:
        s = Sanitizer()
        result = s.sanitize({"password": None})
        assert result["password"] == REDACTED

    def test_empty_dict(self) -> None:
        s = Sanitizer()
        assert s.sanitize({}) == {}

    def test_non_string_sensitive(self) -> None:
        s = Sanitizer()
        result = s.sanitize({"password": 12345})
        assert result["password"] == REDACTED

    def test_key_normalization(self) -> None:
        s = Sanitizer()
        result = s.sanitize({"API-KEY": "abcdefghijklmnopqrst"})
        assert result["API-KEY"] == "abcd...qrst"

    def test_nested_three_levels(self) -> None:
        s = Sanitizer()
        data = {"a": {"b": {"secret": "abcdefghijklmnopqrst"}}}
        result = s.sanitize(data)
        assert result["a"]["b"]["secret"] == "abcd...qrst"
