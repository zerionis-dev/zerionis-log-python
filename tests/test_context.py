"""Tests for async-safe context management."""

from __future__ import annotations

from zerionis_log.context import ZerionisContext


class TestContextBasic:
    def test_set_and_get(self) -> None:
        ZerionisContext.set(trace_id="abc", request_id="req-123")
        ctx = ZerionisContext.get()
        assert ctx["trace_id"] == "abc"
        assert ctx["request_id"] == "req-123"
        ZerionisContext.clear()

    def test_clear(self) -> None:
        ZerionisContext.set(trace_id="abc")
        ZerionisContext.clear()
        assert ZerionisContext.get() == {}

    def test_user_id(self) -> None:
        ZerionisContext.set(user_id="user-42")
        assert ZerionisContext.get()["user_id"] == "user-42"
        ZerionisContext.clear()

    def test_empty_by_default(self) -> None:
        ZerionisContext.clear()
        assert ZerionisContext.get() == {}


class TestContextExtra:
    def test_put_extra(self) -> None:
        ZerionisContext.set(trace_id="t")
        ZerionisContext.put("tenant", "acme")
        ctx = ZerionisContext.get()
        assert ctx["extra"]["tenant"] == "acme"
        ZerionisContext.clear()

    def test_max_extra_fields(self) -> None:
        ZerionisContext.configure(20)
        ZerionisContext.set(trace_id="t")
        for i in range(25):
            ZerionisContext.put(f"key_{i}", f"val_{i}")
        ctx = ZerionisContext.get()
        assert len(ctx.get("extra", {})) == 20  # Max is 20
        ZerionisContext.clear()

    def test_put_without_context(self) -> None:
        ZerionisContext.clear()
        # Should not raise, but logs a warning
        ZerionisContext.put("key", "value")
        assert ZerionisContext.get() == {}

    def test_overwrite_extra(self) -> None:
        ZerionisContext.set(trace_id="t")
        ZerionisContext.put("key", "v1")
        ZerionisContext.put("key", "v2")
        ctx = ZerionisContext.get()
        assert ctx["extra"]["key"] == "v2"
        ZerionisContext.clear()

    def test_configure_max_extra(self) -> None:
        ZerionisContext.configure(5)
        ZerionisContext.set(trace_id="t")
        for i in range(10):
            ZerionisContext.put(f"key_{i}", f"val_{i}")
        ctx = ZerionisContext.get()
        assert len(ctx.get("extra", {})) == 5
        ZerionisContext.clear()
        # Reset to default
        ZerionisContext.configure(20)
