"""Tests for input validation."""

from __future__ import annotations

from zerionis_log.validator import (
    is_valid_ip,
    is_valid_request_id,
    is_valid_trace_id,
    sanitize_message,
    sanitize_path,
    validate_extra_key,
)


class TestTraceId:
    def test_valid_uuid4(self) -> None:
        assert is_valid_trace_id("550e8400-e29b-41d4-a716-446655440000")

    def test_uppercase_valid(self) -> None:
        assert is_valid_trace_id("550E8400-E29B-41D4-A716-446655440000")

    def test_invalid_version(self) -> None:
        # Version 1 UUID
        assert not is_valid_trace_id("550e8400-e29b-11d4-a716-446655440000")

    def test_invalid_format(self) -> None:
        assert not is_valid_trace_id("not-a-uuid")

    def test_empty(self) -> None:
        assert not is_valid_trace_id("")

    def test_otel_32hex_format(self) -> None:
        assert is_valid_trace_id("0af7651916cd43dd8448eb211c80319c")

    def test_otel_uppercase(self) -> None:
        assert is_valid_trace_id("0AF7651916CD43DD8448EB211C80319C")

    def test_otel_wrong_length(self) -> None:
        assert not is_valid_trace_id("0af7651916cd43dd8448eb211c8031")  # 30 chars


class TestRequestId:
    def test_valid(self) -> None:
        assert is_valid_request_id("req-abc123def")

    def test_missing_prefix(self) -> None:
        assert not is_valid_request_id("abc123")

    def test_special_chars(self) -> None:
        assert not is_valid_request_id("req-abc_123")

    def test_empty(self) -> None:
        assert not is_valid_request_id("")


class TestSanitizePath:
    def test_control_chars_stripped(self) -> None:
        assert sanitize_path("/api/\x00test") == "/api/test"

    def test_truncation(self) -> None:
        long_path = "/" + "a" * 3000
        assert len(sanitize_path(long_path)) == 2048

    def test_normal_path(self) -> None:
        assert sanitize_path("/api/v1/users") == "/api/v1/users"


class TestSanitizeMessage:
    def test_control_chars(self) -> None:
        assert sanitize_message("hello\x00world") == "helloworld"

    def test_truncation(self) -> None:
        long_msg = "a" * 20000
        assert len(sanitize_message(long_msg)) == 10000

    def test_newline_preserved(self) -> None:
        # Newlines and tabs are NOT control chars in our regex
        assert sanitize_message("line1\nline2\ttab") == "line1\nline2\ttab"


class TestIP:
    def test_valid_ipv4(self) -> None:
        assert is_valid_ip("192.168.1.1")

    def test_valid_ipv6(self) -> None:
        assert is_valid_ip("::1")

    def test_valid_ipv6_full(self) -> None:
        assert is_valid_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")

    def test_invalid(self) -> None:
        assert not is_valid_ip("999.999.999.999")

    def test_not_ip(self) -> None:
        assert not is_valid_ip("hello")


class TestExtraKey:
    def test_truncation(self) -> None:
        long_key = "k" * 200
        assert len(validate_extra_key(long_key)) == 128

    def test_control_chars(self) -> None:
        assert validate_extra_key("key\x00name") == "keyname"
