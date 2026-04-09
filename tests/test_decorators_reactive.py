"""
Unit tests for fletx.decorators.reactive module.
Covers: reactive_throttle, reactive_when, reactive_select,
        reactive_computed, reactive_memo, reactive_effect,
        ReactiveMemoryCache, BatchManager.
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock

from fletx.core.state import Reactive, RxInt, RxStr, RxBool, Computed
from fletx.decorators.reactive import (
    reactive_throttle,
    reactive_when,
    reactive_select,
    reactive_computed,
    reactive_memo,
    reactive_effect,
    reactive_batch,
    ReactiveMemoryCache,
    BatchManager,
)


# ===================== ReactiveMemoryCache =====================

class TestReactiveMemoryCache:
    """Tests for the LRU cache used by reactive_memo."""

    def test_set_and_get(self):
        cache = ReactiveMemoryCache(maxsize=10)
        cache.set("k1", 42, set())
        result = cache.get("k1")
        assert result is not None
        assert result[0] == 42

    def test_get_missing_returns_none(self):
        cache = ReactiveMemoryCache(maxsize=10)
        assert cache.get("missing") is None

    def test_lru_eviction(self):
        cache = ReactiveMemoryCache(maxsize=2)
        cache.set("a", 1, set())
        cache.set("b", 2, set())
        # Access "a" to make it recently used
        cache.get("a")
        # Add "c" — should evict "b" (least recently used)
        cache.set("c", 3, set())
        assert cache.get("b") is None
        assert cache.get("a") is not None
        assert cache.get("c") is not None

    def test_invalidate_existing_key(self):
        cache = ReactiveMemoryCache(maxsize=10)
        cache.set("x", 99, set())
        cache.invalidate("x")
        assert cache.get("x") is None

    def test_invalidate_missing_key(self):
        cache = ReactiveMemoryCache(maxsize=10)
        cache.invalidate("nope")  # should not raise

    def test_overwrite_existing_key(self):
        cache = ReactiveMemoryCache(maxsize=10)
        cache.set("k", 1, set())
        cache.set("k", 2, set())
        assert cache.get("k")[0] == 2
        # access_order should not have duplicates
        assert cache.access_order.count("k") == 1


# ===================== reactive_throttle =====================

class TestReactiveThrottle:
    """Tests for the reactive_throttle decorator."""

    def test_first_call_executes(self):
        calls = []

        @reactive_throttle(1.0)
        def fn():
            calls.append(1)

        fn()
        assert calls == [1]

    def test_rapid_second_call_blocked(self):
        calls = []

        @reactive_throttle(10.0)  # large interval
        def fn():
            calls.append(1)

        fn()
        fn()  # should be throttled
        assert calls == [1]

    def test_call_allowed_after_interval(self):
        calls = []

        @reactive_throttle(0.01)
        def fn():
            calls.append(1)

        fn()
        time.sleep(0.02)
        fn()
        assert calls == [1, 1]

    def test_return_value_passed_through(self):
        @reactive_throttle(0.01)
        def fn():
            return 42

        assert fn() == 42

    def test_throttled_call_returns_none(self):
        @reactive_throttle(10.0)
        def fn():
            return 42

        fn()  # first call
        assert fn() is None  # throttled


# ===================== reactive_when =====================

class TestReactiveWhen:
    """Tests for the reactive_when decorator."""

    def test_callable_condition_true(self):
        calls = []

        @reactive_when(lambda: True)
        def fn():
            calls.append(1)
            return "ok"

        result = fn()
        assert calls == [1]
        assert result == "ok"

    def test_callable_condition_false(self):
        calls = []

        @reactive_when(lambda: False)
        def fn():
            calls.append(1)

        result = fn()
        assert calls == []
        assert result is None

    def test_reactive_bool_condition_true(self):
        flag = RxBool(True)
        calls = []

        @reactive_when(flag)
        def fn():
            calls.append(1)

        fn()
        assert calls == [1]

    def test_reactive_bool_condition_false(self):
        flag = RxBool(False)
        calls = []

        @reactive_when(flag)
        def fn():
            calls.append(1)

        fn()
        assert calls == []

    def test_reactive_condition_dynamic(self):
        """Condition can change between calls."""
        flag = RxBool(False)
        calls = []

        @reactive_when(flag)
        def fn():
            calls.append(1)

        fn()
        assert calls == []
        flag.value = True
        fn()
        assert calls == [1]


# ===================== reactive_select =====================

class TestReactiveSelect:
    """Tests for the reactive_select decorator."""

    def test_auto_triggers_on_change(self):
        rx = RxInt(0)
        calls = []

        @reactive_select(rx)
        def fn():
            calls.append(rx.value)

        rx.value = 5
        assert 5 in calls

    def test_dispose_stops_listening(self):
        rx = RxInt(0)
        calls = []

        @reactive_select(rx)
        def fn():
            calls.append(rx.value)

        fn.dispose()
        calls.clear()
        rx.value = 10
        assert calls == []

    def test_manual_call_works(self):
        rx = RxStr("hello")

        @reactive_select(rx)
        def fn():
            return rx.value

        assert fn() == "hello"


# ===================== reactive_computed =====================

class TestReactiveComputed:
    """Tests for the reactive_computed decorator."""

    def test_creates_computed_with_deps(self):
        rx_a = RxInt(2)
        rx_b = RxInt(3)

        @reactive_computed([rx_a, rx_b])
        def total():
            return rx_a.value + rx_b.value

        assert isinstance(total, Computed)
        assert total.value == 5

    def test_computed_auto_updates(self):
        rx_a = RxInt(2)
        rx_b = RxInt(3)

        @reactive_computed([rx_a, rx_b])
        def total():
            return rx_a.value + rx_b.value

        rx_a.value = 10
        assert total.value == 13

    def test_computed_auto_detect_deps(self):
        rx = RxInt(7)

        @reactive_computed()
        def doubled():
            return rx.value * 2

        assert isinstance(doubled, Computed)
        assert doubled.value == 14
        rx.value = 5
        assert doubled.value == 10


# ===================== reactive_memo =====================

class TestReactiveMemo:
    """Tests for the reactive_memo decorator."""

    def test_cache_hit(self):
        call_count = []

        @reactive_memo()
        def expensive():
            call_count.append(1)
            return 42

        r1 = expensive()
        r2 = expensive()
        assert r1 == 42
        assert r2 == 42
        assert len(call_count) == 1  # only computed once

    def test_cache_invalidation_on_dep_change(self):
        rx = RxInt(5)
        call_count = []

        @reactive_memo()
        def compute():
            call_count.append(1)
            return rx.value * 2

        r1 = compute()
        assert r1 == 10
        assert len(call_count) == 1

        # Invalidate by changing dependency
        rx.value = 10
        r2 = compute()
        assert r2 == 20
        assert len(call_count) == 2

    def test_clear_cache(self):
        call_count = []

        @reactive_memo()
        def compute():
            call_count.append(1)
            return 99

        compute()
        compute.clear_cache()
        compute()
        assert len(call_count) == 2

    def test_custom_key_fn(self):
        call_count = []

        @reactive_memo(key_fn=lambda x: f"key_{x}")
        def compute(x):
            call_count.append(1)
            return x * 2

        assert compute(5) == 10
        assert compute(5) == 10  # cached
        assert compute(3) == 6  # different key
        assert len(call_count) == 2

    def test_cache_attribute_exposed(self):
        @reactive_memo()
        def compute():
            return 1

        assert hasattr(compute, "cache")
        assert isinstance(compute.cache, ReactiveMemoryCache)


# ===================== reactive_effect =====================

class TestReactiveEffect:
    """Tests for the reactive_effect decorator."""

    def test_effect_with_deps_auto_runs(self):
        rx = RxInt(0)
        calls = []

        # auto_run passes _self=None as positional, so effect must accept *args
        @reactive_effect(dependencies=[rx], auto_run=True)
        def effect(*args, **kwargs):
            calls.append(rx.value)

        assert 0 in calls

    def test_effect_listens_to_deps(self):
        rx = RxInt(0)
        calls = []

        @reactive_effect(dependencies=[rx], auto_run=True)
        def effect(*args, **kwargs):
            calls.append(rx.value)

        calls.clear()
        rx.value = 5
        assert 5 in calls

    def test_effect_dispose(self):
        rx = RxInt(0)
        calls = []

        @reactive_effect(dependencies=[rx], auto_run=True)
        def effect(*args, **kwargs):
            calls.append(rx.value)

        effect.dispose()
        calls.clear()
        rx.value = 10
        assert calls == []

    def test_effect_no_auto_run(self):
        rx = RxInt(0)
        calls = []

        @reactive_effect(dependencies=[rx], auto_run=False)
        def effect(*args, **kwargs):
            calls.append(rx.value)

        # Should NOT have been called
        assert calls == []

        # But calling manually should work and set up listeners
        effect()
        assert 0 in calls
        calls.clear()
        rx.value = 3
        assert 3 in calls


# ===================== reactive_batch =====================

class TestReactiveBatch:
    """Tests for reactive_batch and BatchManager (sync parts only)."""

    def test_batch_manager_add_update(self):
        """BatchManager.add_update adds fn to pending_updates."""
        bm = BatchManager()
        fn = Mock()
        with patch("fletx.decorators.reactive.asyncio.create_task"):
            bm.add_update(fn)
        assert fn in bm.pending_updates

    def test_batch_manager_schedules_once(self):
        """Multiple add_update calls schedule flush only once."""
        bm = BatchManager()
        with patch("fletx.decorators.reactive.asyncio.create_task") as mock_ct:
            bm.add_update(Mock())
            bm.add_update(Mock())
        assert mock_ct.call_count == 1
        assert bm.batch_scheduled is True
        # Close the coroutine to avoid "was never awaited" warning
        coro = mock_ct.call_args[0][0]
        coro.close()

    @pytest.mark.asyncio
    async def test_flush_batch_executes_all(self):
        """_flush_batch runs all pending updates."""
        bm = BatchManager()
        fn1 = Mock()
        fn2 = Mock()
        bm.pending_updates = {fn1, fn2}
        bm.batch_scheduled = True
        await bm._flush_batch()
        fn1.assert_called_once()
        fn2.assert_called_once()
        assert bm.batch_scheduled is False
        assert len(bm.pending_updates) == 0

    @pytest.mark.asyncio
    async def test_flush_batch_handles_errors(self):
        """_flush_batch catches errors in individual updates."""
        bm = BatchManager()
        bad = Mock(side_effect=RuntimeError("boom"))
        good = Mock()
        bm.pending_updates = {bad, good}
        bm.batch_scheduled = True
        await bm._flush_batch()
        # Both should have been called despite error in bad
        bad.assert_called_once()
        good.assert_called_once()

