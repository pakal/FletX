"""
Unit tests for fletx.core.concurency.worker module.
Covers: BaseWorker, FunctionWorker, RunnableWorker, WorkerPool,
        WorkerTaskWrapper, BoundWorkerMethod, worker_task, parallel_task,
        get_global_pool, set_global_pool.
"""

import time
import pytest
from unittest.mock import Mock, patch
from concurrent.futures import Future

from fletx.core.concurency.config import (
    WorkerState, Priority, WorkerResult, WorkerPoolConfig,
)
from fletx.core.concurency.worker import (
    BaseWorker,
    FunctionWorker,
    RunnableWorker,
    WorkerPool,
    WorkerTaskWrapper,
    BoundWorkerMethod,
    worker_task,
    parallel_task,
    get_global_pool,
    set_global_pool,
    Runnable,
)


# ===================== FunctionWorker =====================

class TestFunctionWorker:
    """Tests for FunctionWorker."""

    def test_execute_returns_result(self):
        def add(a, b):
            return a + b

        w = FunctionWorker(add, 2, 3, worker_id="add_worker")
        result = w.run()
        assert result.state == WorkerState.COMPLETED
        assert result.result == 5
        assert result.worker_id == "add_worker"

    def test_execute_with_kwargs(self):
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        w = FunctionWorker(greet, "World", greeting="Hi")
        result = w.run()
        assert result.result == "Hi, World!"

    def test_execute_failure(self):
        def fail():
            raise ValueError("boom")

        w = FunctionWorker(fail, worker_id="fail_worker")
        result = w.run()
        assert result.state == WorkerState.FAILED
        assert result.error is not None
        assert "boom" in str(result.error)

    def test_execution_time_recorded(self):
        def slow():
            time.sleep(0.05)
            return 42

        w = FunctionWorker(slow)
        result = w.run()
        assert result.execution_time >= 0.04

    def test_default_priority(self):
        w = FunctionWorker(lambda: None)
        assert w.priority == Priority.NORMAL

    def test_custom_priority(self):
        w = FunctionWorker(lambda: None, priority=Priority.HIGH)
        assert w.priority == Priority.HIGH

    def test_default_worker_id_generated(self):
        w = FunctionWorker(lambda: None)
        assert w.worker_id.startswith("worker_")


# ===================== BaseWorker lifecycle =====================

class TestBaseWorkerLifecycle:
    """Tests for BaseWorker cancel/state management."""

    def test_cancel_pending_worker(self):
        w = FunctionWorker(lambda: 42)
        assert w.state == WorkerState.PENDING
        assert w.cancel() is True
        assert w.state == WorkerState.CANCELLED
        assert w.is_cancelled() is True

    def test_cancel_running_worker_returns_false(self):
        w = FunctionWorker(lambda: 42)
        w.state = WorkerState.RUNNING
        assert w.cancel() is False

    def test_run_cancelled_worker(self):
        w = FunctionWorker(lambda: 42)
        w.cancel()
        result = w.run()
        assert result.state == WorkerState.CANCELLED
        assert result.result is None

    def test_create_result_metadata_copy(self):
        w = FunctionWorker(lambda: 1)
        w._metadata["key"] = "value"
        result = w._create_result()
        assert result.metadata == {"key": "value"}
        # Mutation of result metadata should not affect worker
        result.metadata["key2"] = "value2"
        assert "key2" not in w._metadata


# ===================== RunnableWorker =====================

class TestRunnableWorker:
    """Tests for RunnableWorker."""

    def test_runnable_protocol(self):
        class MyRunnable:
            def run(self):
                return "done"

        assert isinstance(MyRunnable(), Runnable)

    def test_runnable_worker_executes(self):
        class MyRunnable:
            def run(self):
                return 99

        w = RunnableWorker(MyRunnable(), worker_id="runnable_1")
        result = w.run()
        assert result.state == WorkerState.COMPLETED
        assert result.result == 99

    def test_runnable_worker_failure(self):
        class FailRunnable:
            def run(self):
                raise RuntimeError("runnable failed")

        w = RunnableWorker(FailRunnable())
        result = w.run()
        assert result.state == WorkerState.FAILED


# ===================== WorkerPool =====================

class TestWorkerPool:
    """Tests for WorkerPool."""

    def test_submit_worker(self, worker_pool):
        w = FunctionWorker(lambda: 42, worker_id="w1")
        wid = worker_pool.submit_worker(w)
        assert wid == "w1"
        result = worker_pool.get_result("w1", timeout=5)
        assert result.result == 42

    def test_submit_function(self, worker_pool):
        wid = worker_pool.submit_function(
            lambda x: x * 2, 5, worker_id="fn1"
        )
        result = worker_pool.get_result(wid, timeout=5)
        assert result.result == 10

    def test_submit_runnable(self, worker_pool):
        class MyRunnable:
            def run(self):
                return "hello"

        wid = worker_pool.submit_runnable(MyRunnable(), worker_id="rn1")
        result = worker_pool.get_result(wid, timeout=5)
        assert result.result == "hello"

    def test_get_result_unknown_raises(self, worker_pool):
        with pytest.raises(ValueError, match="not found"):
            worker_pool.get_result("nonexistent", timeout=1)

    def test_wait_all(self, worker_pool):
        worker_pool.submit_function(lambda: 1, worker_id="a")
        worker_pool.submit_function(lambda: 2, worker_id="b")
        results = worker_pool.wait_all(timeout=5)
        values = {wid: r.result for wid, r in results.items()}
        assert values.get("a") == 1 or values.get("b") == 2

    def test_cancel_pending_worker(self, worker_pool):
        """Cancel a worker before it starts (requires blocking the pool)."""
        import threading
        barrier = threading.Event()

        def blocking():
            barrier.wait(timeout=5)
            return "done"

        # Fill up the pool
        worker_pool.submit_function(blocking, worker_id="blocker1")
        worker_pool.submit_function(blocking, worker_id="blocker2")
        # Third should be pending
        time.sleep(0.1)
        w3 = FunctionWorker(lambda: 3, worker_id="pending_w")
        worker_pool.submit_worker(w3)
        cancelled = worker_pool.cancel_worker("pending_w")
        barrier.set()
        assert cancelled is True

    def test_cancel_nonexistent_worker(self, worker_pool):
        assert worker_pool.cancel_worker("ghost") is False

    def test_get_stats(self, worker_pool):
        stats = worker_pool.get_stats()
        assert "pending" in stats
        assert "running" in stats
        assert "completed" in stats

    def test_submit_after_shutdown_raises(self, worker_pool):
        worker_pool.shutdown()
        with pytest.raises(RuntimeError, match="shutdown"):
            worker_pool.submit_function(lambda: 1)

    def test_context_manager(self):
        config = WorkerPoolConfig(max_workers=1, auto_shutdown=True)
        with WorkerPool(config) as pool:
            wid = pool.submit_function(lambda: 42, worker_id="ctx_w")
            result = pool.get_result(wid, timeout=5)
            assert result.result == 42

    def test_context_manager_no_auto_shutdown(self):
        config = WorkerPoolConfig(max_workers=1, auto_shutdown=False)
        with WorkerPool(config) as pool:
            pool.submit_function(lambda: 1, worker_id="ns")
        # Should not raise — pool is not shut down
        # We clean up manually
        pool.shutdown()

    def test_priority_ordering(self, worker_pool):
        """Higher-priority workers should be inserted before lower ones."""
        import threading
        barrier = threading.Event()

        def blocking():
            barrier.wait(timeout=5)

        # Fill pool slots
        worker_pool.submit_function(blocking, worker_id="b1")
        worker_pool.submit_function(blocking, worker_id="b2")
        time.sleep(0.05)

        execution_order = []

        def track(label):
            execution_order.append(label)

        # Submit low then high priority while pool is full
        worker_pool.submit_function(
            lambda: track("low"), worker_id="low", priority=Priority.LOW
        )
        worker_pool.submit_function(
            lambda: track("high"), worker_id="high", priority=Priority.HIGH
        )
        barrier.set()
        worker_pool.wait_all(timeout=5)
        # High should execute before low
        if len(execution_order) == 2:
            assert execution_order.index("high") < execution_order.index("low")

    def test_no_priority_ordering(self, worker_pool_no_priority):
        """When priority is disabled, workers are FIFO."""
        wid1 = worker_pool_no_priority.submit_function(lambda: 1, worker_id="f1")
        wid2 = worker_pool_no_priority.submit_function(lambda: 2, worker_id="f2")
        r1 = worker_pool_no_priority.get_result(wid1, timeout=5)
        r2 = worker_pool_no_priority.get_result(wid2, timeout=5)
        assert r1.result == 1
        assert r2.result == 2


# ===================== WorkerTaskWrapper =====================

class TestWorkerTaskWrapper:
    """Tests for WorkerTaskWrapper."""

    def test_sync_call(self):
        wrapper = WorkerTaskWrapper(lambda x: x * 2)
        assert wrapper(5) == 10

    def test_async_call_returns_worker_id(self):
        wrapper = WorkerTaskWrapper(lambda: 42)
        wid = wrapper.async_call()
        assert isinstance(wid, str)
        wrapper.shutdown_default_pool()

    def test_submit_alias(self):
        wrapper = WorkerTaskWrapper(lambda: 42)
        wid = wrapper.submit()
        assert isinstance(wid, str)
        wrapper.shutdown_default_pool()

    def test_run_and_wait(self):
        wrapper = WorkerTaskWrapper(lambda x: x + 1)
        result = wrapper.run_and_wait(10)
        assert result == 11
        wrapper.shutdown_default_pool()

    def test_run_and_wait_failure(self):
        def bad():
            raise ValueError("fail")

        wrapper = WorkerTaskWrapper(bad)
        with pytest.raises(ValueError, match="fail"):
            wrapper.run_and_wait()
        wrapper.shutdown_default_pool()

    def test_set_pool(self, worker_pool):
        wrapper = WorkerTaskWrapper(lambda: 99)
        wrapper.set_pool(worker_pool)
        result = wrapper.run_and_wait()
        assert result == 99

    def test_uses_global_pool_if_set(self):
        from fletx.core.concurency import worker as worker_module
        config = WorkerPoolConfig(max_workers=1, auto_shutdown=False)
        pool = WorkerPool(config)
        original = worker_module._global_pool
        try:
            set_global_pool(pool)
            wrapper = WorkerTaskWrapper(lambda: 77)
            result = wrapper.run_and_wait()
            assert result == 77
        finally:
            set_global_pool(original)
            pool.shutdown()

    def test_metadata_preserved(self):
        def my_fn():
            """docstring"""
            return 1

        wrapper = WorkerTaskWrapper(my_fn)
        assert wrapper.__name__ == "my_fn"
        assert wrapper.__doc__ == "docstring"

    def test_descriptor_unbound(self):
        wrapper = WorkerTaskWrapper(lambda: 1)
        assert wrapper.__get__(None, type) is wrapper

    def test_descriptor_bound_returns_proxy(self):
        wrapper = WorkerTaskWrapper(lambda self: 1)

        class Dummy:
            method = wrapper

        d = Dummy()
        bound = d.method
        assert isinstance(bound, BoundWorkerMethod)

    def test_shutdown_default_pool_noop_when_none(self):
        wrapper = WorkerTaskWrapper(lambda: 1)
        wrapper._default_pool = None
        wrapper.shutdown_default_pool()  # should not raise


# ===================== BoundWorkerMethod =====================

class TestBoundWorkerMethod:
    """Tests for BoundWorkerMethod."""

    def test_call(self):
        wrapper = WorkerTaskWrapper(lambda self, x: x * 3)
        bound = BoundWorkerMethod(wrapper, "instance")
        assert bound(5) == 15

    def test_async_call(self):
        wrapper = WorkerTaskWrapper(lambda self: 42)
        bound = BoundWorkerMethod(wrapper, "instance")
        wid = bound.async_call()
        assert isinstance(wid, str)
        wrapper.shutdown_default_pool()

    def test_submit(self):
        wrapper = WorkerTaskWrapper(lambda self: 42)
        bound = BoundWorkerMethod(wrapper, "instance")
        wid = bound.submit()
        assert isinstance(wid, str)
        wrapper.shutdown_default_pool()

    def test_run_and_wait(self):
        wrapper = WorkerTaskWrapper(lambda self, x: x + 10)
        bound = BoundWorkerMethod(wrapper, "instance")
        result = bound.run_and_wait(5)
        assert result == 15
        wrapper.shutdown_default_pool()

    def test_set_pool(self, worker_pool):
        wrapper = WorkerTaskWrapper(lambda self: 1)
        bound = BoundWorkerMethod(wrapper, "instance")
        bound.set_pool(worker_pool)
        assert wrapper._pool is worker_pool

    def test_shutdown_default_pool(self):
        wrapper = WorkerTaskWrapper(lambda self: 1)
        bound = BoundWorkerMethod(wrapper, "instance")
        bound.shutdown_default_pool()  # should not raise

    def test_getattr_fallback(self):
        wrapper = WorkerTaskWrapper(lambda self: 1)
        wrapper.custom_attr = "hello"
        bound = BoundWorkerMethod(wrapper, "instance")
        assert bound.custom_attr == "hello"


# ===================== worker_task decorator =====================

class TestWorkerTaskDecorator:
    """Tests for the worker_task decorator."""

    def test_sync_call(self):
        @worker_task()
        def double(x):
            return x * 2

        assert double(5) == 10

    def test_async_call(self):
        @worker_task()
        def add(a, b):
            return a + b

        wid = add.async_call(3, 4)
        assert isinstance(wid, str)
        add.shutdown_default_pool()

    def test_run_and_wait(self):
        @worker_task()
        def compute(x):
            return x ** 2

        result = compute.run_and_wait(4)
        assert result == 16
        compute.shutdown_default_pool()

    def test_custom_priority(self):
        @worker_task(priority=Priority.CRITICAL)
        def important():
            return "done"

        assert important.priority == Priority.CRITICAL
        important.shutdown_default_pool()

    def test_instance_method(self):
        """worker_task works as instance method via descriptor protocol."""

        class MyService:
            @worker_task()
            def compute(self, x):
                return x * 10

        svc = MyService()
        result = svc.compute(3)
        assert result == 30


# ===================== parallel_task decorator =====================

class TestParallelTaskDecorator:
    """Tests for the parallel_task decorator."""

    def test_always_returns_worker_id(self):
        @parallel_task()
        def add(a, b):
            return a + b

        wid = add(1, 2)
        assert isinstance(wid, str)
        add.shutdown_default_pool()

    def test_sync_call_available(self):
        @parallel_task()
        def mul(a, b):
            return a * b

        result = mul.sync_call(3, 4)
        assert result == 12
        mul.shutdown_default_pool()

    def test_run_and_wait(self):
        @parallel_task()
        def compute(x):
            return x + 100

        result = compute.run_and_wait(5)
        assert result == 105
        compute.shutdown_default_pool()

    def test_set_pool(self, worker_pool):
        @parallel_task()
        def fn():
            return 1

        fn.set_pool(worker_pool)
        wid = fn()
        assert isinstance(wid, str)


# ===================== Global pool =====================

class TestGlobalPool:
    """Tests for get_global_pool and set_global_pool."""

    def test_get_global_pool_creates_default(self):
        from fletx.core.concurency import worker as worker_module
        original = worker_module._global_pool
        try:
            worker_module._global_pool = None
            pool = get_global_pool()
            assert isinstance(pool, WorkerPool)
            assert pool.config.max_workers == 6
            assert pool.config.enable_priority is True
        finally:
            if worker_module._global_pool is not None:
                worker_module._global_pool.shutdown(wait=False)
            worker_module._global_pool = original

    def test_set_global_pool(self):
        from fletx.core.concurency import worker as worker_module
        original = worker_module._global_pool
        custom = WorkerPool(WorkerPoolConfig(max_workers=1, auto_shutdown=False))
        try:
            set_global_pool(custom)
            assert get_global_pool() is custom
        finally:
            custom.shutdown(wait=False)
            worker_module._global_pool = original

