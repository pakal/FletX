import pytest
from unittest.mock import Mock, patch
from fletx.core.controller import (
    FletXController, ControllerState,
    EventBus, ControllerEvent, ControllerContext,
)
from fletx.core.state import Reactive, RxInt, RxStr, RxBool, RxList, RxDict, Computed


# ===================== Existing tests =====================

def test_default_initialization_registers_instance():
    controller = FletXController()
    
    # State should auto-initialize and then transition to READY
    assert controller.state.value == ControllerState.READY

    # It should be in the global instances list
    assert controller in FletXController.get_all_instances()
    
    # Should have an event bus and context
    assert controller.event_bus is not None
    assert controller.context is not None
    assert controller.effects is not None


def test_initialization_with_auto_initialize_false():
    controller = FletXController(auto_initialize=False)
    
    # Should remain CREATED
    assert controller.state.value == ControllerState.CREATED
    
    # After explicit initialize, it transitions to INITIALIZED then READY
    controller.initialize()
    assert controller.state.value == ControllerState.READY


def test_repr_contains_state_and_id():
    controller = FletXController()
    text = repr(controller)
    assert "FletXController" in text
    assert "initialized" in text or "ready" in text


# ===================== EventBus tests =====================

class TestEventBus:
    """Tests for the EventBus class."""

    def test_on_and_emit(self):
        """on() registers a listener that emit() invokes."""
        bus = EventBus()
        received = []
        bus.on("test_event", lambda e: received.append(e.data))
        bus.emit("test_event", "payload")
        assert received == ["payload"]

    def test_emit_controller_event(self):
        """emit() accepts a ControllerEvent directly."""
        bus = EventBus()
        received = []
        bus.on("custom", lambda e: received.append(e.data))
        event = ControllerEvent("custom", data=42)
        bus.emit(event)
        assert received == [42]

    def test_once_fires_only_once(self):
        """once() listener fires only on the first emit."""
        bus = EventBus()
        received = []
        bus.once("evt", lambda e: received.append(e.data))
        bus.emit("evt", "first")
        bus.emit("evt", "second")
        assert received == ["first"]

    def test_off_removes_specific_callback(self):
        """off() with a callback removes only that callback."""
        bus = EventBus()
        calls_a, calls_b = [], []
        cb_a = lambda e: calls_a.append(1)
        cb_b = lambda e: calls_b.append(1)
        bus.on("evt", cb_a)
        bus.on("evt", cb_b)
        bus.off("evt", cb_a)
        bus.emit("evt")
        assert calls_a == []
        assert calls_b == [1]

    def test_off_removes_all_listeners(self):
        """off() without callback removes all listeners for the event type."""
        bus = EventBus()
        calls = []
        bus.on("evt", lambda e: calls.append(1))
        bus.once("evt", lambda e: calls.append(2))
        bus.off("evt")
        bus.emit("evt")
        assert calls == []

    def test_last_event_property(self):
        """last_event is a Reactive updated on each emit."""
        bus = EventBus()
        bus.emit("a", "data_a")
        assert bus.last_event.value.type == "a"
        assert bus.last_event.value.data == "data_a"

    def test_event_history(self):
        """event_history tracks all emitted events."""
        bus = EventBus()
        bus.emit("e1", 1)
        bus.emit("e2", 2)
        assert len(bus.event_history) == 2
        assert bus.event_history[0].type == "e1"
        assert bus.event_history[1].type == "e2"

    def test_listen_reactive(self):
        """listen_reactive returns a Computed filtering events by type."""
        bus = EventBus()
        bus.emit("a", 1)
        bus.emit("b", 2)
        bus.emit("a", 3)
        comp = bus.listen_reactive("a")
        assert len(comp.value) == 2
        assert all(e.type == "a" for e in comp.value)

    def test_emit_callback_error_does_not_crash(self):
        """Errors in a callback are caught; other listeners still fire."""
        bus = EventBus()
        good_calls = []

        def bad_cb(e):
            raise RuntimeError("oops")

        bus.on("evt", bad_cb)
        bus.on("evt", lambda e: good_calls.append(1))
        bus.emit("evt")  # should not raise
        assert good_calls == [1]

    def test_dispose_clears_all(self):
        """dispose clears listeners and reactive state."""
        bus = EventBus()
        bus.on("x", lambda e: None)
        bus.once("y", lambda e: None)
        bus.emit("x")
        bus.dispose()
        assert bus._listeners == {}
        assert bus._once_listeners == {}


# ===================== ControllerContext tests =====================

class TestControllerContext:
    """Tests for the ControllerContext class."""

    def test_set_and_get(self):
        ctx = ControllerContext()
        ctx.set("name", "Alice")
        assert ctx.get("name") == "Alice"

    def test_get_default(self):
        ctx = ControllerContext()
        assert ctx.get("missing", "default") == "default"

    def test_has(self):
        ctx = ControllerContext()
        ctx.set("key", 1)
        assert ctx.has("key") is True
        assert ctx.has("nope") is False

    def test_has_reactive(self):
        ctx = ControllerContext()
        ctx.set("k", True)
        comp = ctx.has_reactive("k")
        assert comp.value is True
        comp_no = ctx.has_reactive("missing")
        assert comp_no.value is False

    def test_get_reactive(self):
        ctx = ControllerContext()
        ctx.set("x", 10)
        comp = ctx.get_reactive("x")
        assert comp.value == 10

    def test_remove(self):
        ctx = ControllerContext()
        ctx.set("k", "v")
        ctx.remove("k")
        assert ctx.has("k") is False

    def test_remove_nonexistent(self):
        """remove on a missing key does nothing."""
        ctx = ControllerContext()
        ctx.remove("nope")  # should not raise

    def test_update(self):
        ctx = ControllerContext()
        ctx.update(a=1, b=2)
        assert ctx.get("a") == 1
        assert ctx.get("b") == 2

    def test_clear(self):
        ctx = ControllerContext()
        ctx.set("a", 1)
        ctx.clear()
        assert ctx.has("a") is False

    def test_data_property(self):
        ctx = ControllerContext()
        assert isinstance(ctx.data, RxDict)

    def test_listen(self):
        ctx = ControllerContext()
        calls = []
        observer = ctx.listen(lambda: calls.append(1))
        ctx.set("x", 1)
        assert len(calls) >= 1
        observer.dispose()

    def test_dispose(self):
        ctx = ControllerContext()
        ctx.set("k", "v")
        ctx.dispose()
        # After dispose, internal dict is cleaned up


# ===================== ControllerEvent tests =====================

class TestControllerEvent:
    """Tests for the ControllerEvent dataclass."""

    def test_creation(self):
        evt = ControllerEvent("click", data={"x": 1}, source="btn")
        assert evt.type == "click"
        assert evt.data == {"x": 1}
        assert evt.source == "btn"

    def test_defaults(self):
        evt = ControllerEvent("test")
        assert evt.data is None
        assert evt.source is None


# ===================== FletXController lifecycle =====================

class TestControllerLifecycle:

    def test_initialize_idempotent(self, fresh_controller):
        """Calling initialize twice has no effect once past CREATED."""
        fresh_controller.initialize()
        assert fresh_controller.state.value == ControllerState.READY
        result = fresh_controller.initialize()
        assert result is fresh_controller  # returns self
        assert fresh_controller.state.value == ControllerState.READY

    def test_dispose_transitions_state(self):
        ctrl = FletXController()
        ctrl.dispose()
        assert ctrl.state.value == ControllerState.DISPOSED

    def test_dispose_idempotent(self):
        ctrl = FletXController()
        ctrl.dispose()
        ctrl.dispose()  # should not raise
        assert ctrl.is_disposed

    def test_is_disposed_property(self):
        ctrl = FletXController()
        assert ctrl.is_disposed is False
        ctrl.dispose()
        assert ctrl.is_disposed is True

    def test_check_not_disposed_raises(self):
        ctrl = FletXController()
        ctrl.dispose()
        with pytest.raises(RuntimeError, match="is disposed"):
            ctrl.emit_local("test")

    def test_context_manager(self):
        """FletXController supports the 'with' statement."""
        with FletXController() as ctrl:
            assert ctrl.state.value == ControllerState.READY
        assert ctrl.is_disposed


# ===================== FletXController child management =====================

class TestControllerChildren:

    def test_add_child(self):
        parent = FletXController()
        child = FletXController()
        parent.add_child(child)
        assert child in parent._children.value
        assert child._parent.value is parent
        parent.dispose()

    def test_remove_child(self):
        parent = FletXController()
        child = FletXController()
        parent.add_child(child)
        parent.remove_child(child)
        assert child not in parent._children.value
        assert child._parent.value is None
        parent.dispose()
        child.dispose()

    def test_dispose_cascades_to_children(self):
        parent = FletXController()
        child = FletXController()
        parent.add_child(child)
        parent.dispose()
        assert child.is_disposed

    def test_add_child_after_dispose_raises(self):
        parent = FletXController()
        parent.dispose()
        with pytest.raises(RuntimeError):
            parent.add_child(FletXController())


# ===================== FletXController event methods =====================

class TestControllerEvents:

    def test_emit_and_on_local(self, ready_controller):
        received = []
        ready_controller.on_local("my_event", lambda e: received.append(e.data))
        ready_controller.emit_local("my_event", "hello")
        assert received == ["hello"]

    def test_off_local(self, ready_controller):
        calls = []
        cb = lambda e: calls.append(1)
        ready_controller.on_local("evt", cb)
        ready_controller.off_local("evt", cb)
        ready_controller.emit_local("evt")
        assert calls == []

    def test_once_local(self, ready_controller):
        calls = []
        ready_controller.once_local("evt", lambda e: calls.append(1))
        ready_controller.emit_local("evt")
        ready_controller.emit_local("evt")
        assert calls == [1]

    def test_emit_and_on_global(self):
        ctrl1 = FletXController()
        ctrl2 = FletXController()
        received = []
        ctrl2.on_global("global_evt", lambda e: received.append(e.data))
        ctrl1.emit_global("global_evt", "shared")
        assert received == ["shared"]
        ctrl1.dispose()
        ctrl2.dispose()

    def test_off_global(self):
        ctrl = FletXController()
        calls = []
        cb = lambda e: calls.append(1)
        ctrl.on_global("g", cb)
        ctrl.off_global("g", cb)
        ctrl.emit_global("g")
        assert calls == []
        ctrl.dispose()

    def test_once_global(self):
        ctrl = FletXController()
        calls = []
        ctrl.once_global("g", lambda e: calls.append(1))
        ctrl.emit_global("g")
        ctrl.emit_global("g")
        assert calls == [1]
        ctrl.dispose()

    def test_listen_reactive_local(self, ready_controller):
        ready_controller.emit_local("typed", 1)
        ready_controller.emit_local("other", 2)
        ready_controller.emit_local("typed", 3)
        comp = ready_controller.listen_reactive_local("typed")
        assert len(comp.value) == 2

    def test_listen_reactive_global(self):
        ctrl = FletXController()
        ctrl.emit_global("g_typed", 1)
        comp = ctrl.listen_reactive_global("g_typed")
        assert len(comp.value) >= 1
        ctrl.dispose()


# ===================== FletXController context methods =====================

class TestControllerContextMethods:

    def test_set_get_context(self, ready_controller):
        ready_controller.set_context("k", "v")
        assert ready_controller.get_context("k") == "v"
        assert ready_controller.get_context("missing", "def") == "def"

    def test_has_context(self, ready_controller):
        ready_controller.set_context("k", 1)
        assert ready_controller.has_context("k") is True
        assert ready_controller.has_context("nope") is False

    def test_has_context_reactive(self, ready_controller):
        ready_controller.set_context("k", 1)
        comp = ready_controller.has_context_reactive("k")
        assert comp.value is True

    def test_remove_context(self, ready_controller):
        ready_controller.set_context("k", 1)
        ready_controller.remove_context("k")
        assert ready_controller.has_context("k") is False

    def test_update_context(self, ready_controller):
        ready_controller.update_context(a=1, b=2)
        assert ready_controller.get_context("a") == 1
        assert ready_controller.get_context("b") == 2

    def test_listen_context(self, ready_controller):
        calls = []
        obs = ready_controller.listen_context(lambda: calls.append(1))
        ready_controller.set_context("x", 10)
        assert len(calls) >= 1
        obs.dispose()

    def test_get_context_reactive(self, ready_controller):
        ready_controller.set_context("x", 42)
        comp = ready_controller.get_context_reactive("x")
        assert comp.value == 42

    def test_set_global_context(self):
        ctrl = FletXController()
        ctrl.set_global_context("gk", "gv")
        assert ctrl.get_global_context("gk") == "gv"
        ctrl.dispose()

    def test_get_global_context_reactive(self):
        ctrl = FletXController()
        ctrl.set_global_context("grk", 99)
        comp = ctrl.get_global_context_reactive("grk")
        assert comp.value == 99
        ctrl.dispose()


# ===================== FletXController reactive factories =====================

class TestControllerReactiveFactories:

    def test_create_reactive(self, ready_controller):
        rx = ready_controller.create_reactive(10)
        assert isinstance(rx, Reactive)
        assert rx.value == 10

    def test_create_rx_int(self, ready_controller):
        rx = ready_controller.create_rx_int(5)
        assert isinstance(rx, RxInt)
        assert rx.value == 5

    def test_create_rx_str(self, ready_controller):
        rx = ready_controller.create_rx_str("hello")
        assert isinstance(rx, RxStr)
        assert rx.value == "hello"

    def test_create_rx_bool(self, ready_controller):
        rx = ready_controller.create_rx_bool(True)
        assert isinstance(rx, RxBool)
        assert rx.value is True

    def test_create_rx_list(self, ready_controller):
        rx = ready_controller.create_rx_list([1, 2])
        assert isinstance(rx, RxList)
        assert rx.value == [1, 2]

    def test_create_rx_dict(self, ready_controller):
        rx = ready_controller.create_rx_dict({"a": 1})
        assert isinstance(rx, RxDict)
        assert rx["a"] == 1

    def test_create_computed(self, ready_controller):
        rx = ready_controller.create_reactive(5)
        comp = ready_controller.create_computed(lambda: rx.value * 2)
        assert isinstance(comp, Computed)
        assert comp.value == 10

    def test_factory_after_dispose_raises(self):
        ctrl = FletXController()
        ctrl.dispose()
        with pytest.raises(RuntimeError):
            ctrl.create_reactive(0)


# ===================== FletXController utility methods =====================

class TestControllerUtilities:

    def test_set_loading(self, ready_controller):
        ready_controller.set_loading(True)
        assert ready_controller._is_loading.value is True
        ready_controller.set_loading(False)
        assert ready_controller._is_loading.value is False

    def test_set_error(self, ready_controller):
        ready_controller.set_error("something went wrong")
        assert ready_controller._error_message.value == "something went wrong"

    def test_clear_error(self, ready_controller):
        ready_controller.set_error("err")
        ready_controller.clear_error()
        assert ready_controller._error_message.value == ""

    def test_chain(self, ready_controller):
        calls = []
        result = ready_controller.chain(
            lambda c: calls.append("a"),
            lambda c: calls.append("b"),
        )
        assert calls == ["a", "b"]
        assert result is ready_controller

    def test_add_cleanup(self, ready_controller):
        cleanup_called = []
        ready_controller.add_cleanup(lambda: cleanup_called.append(1))
        ready_controller.dispose()
        assert cleanup_called == [1]

    def test_find_by_type(self):
        class CustomCtrl(FletXController):
            pass

        ctrl = CustomCtrl()
        found = FletXController.find_by_type(CustomCtrl)
        assert ctrl in found
        ctrl.dispose()

    def test_get_all_instances(self):
        ctrl = FletXController()
        assert ctrl in FletXController.get_all_instances()
        ctrl.dispose()

