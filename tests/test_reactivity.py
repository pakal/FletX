import pytest
from fletx.core.state import (
    ReactiveDependencyTracker, Observer, Reactive, Computed,
    RxInt, RxStr, RxBool, RxList, RxDict
)

# --- ReactiveDependencyTracker ---
def test_dependency_tracker_tracks_dependencies():
    rx = Reactive(1)
    def computation():
        return rx.value + 1
    result, deps = ReactiveDependencyTracker.track(computation)
    assert result == 2
    assert rx in deps

# --- Observer ---
def test_observer_notifies_on_change():
    rx = Reactive(0)
    called = []
    def callback():
        called.append(True)
    obs = rx.listen(callback)
    rx.value = 1
    assert called
    obs.dispose()
    called.clear()
    rx.value = 2
    assert not called

def test_observer_auto_dispose():
    rx = Reactive(0)
    called = []
    def callback():
        called.append(True)
    obs = rx.listen(callback, auto_dispose=True)
    obs.dispose()
    rx.value = 1
    assert not called

# --- Reactive ---
def test_reactive_value_and_observers():
    rx = Reactive(10)
    assert rx.value == 10
    rx.value = 20
    assert rx.value == 20
    called = []
    rx.listen(lambda: called.append(rx.value))
    rx.value = 30
    assert called[-1] == 30

# --- Computed ---
def test_computed_tracks_and_updates():
    rx1 = Reactive(2)
    rx2 = Reactive(3)
    comp = Computed(lambda: rx1.value + rx2.value)
    assert comp.value == 5
    rx1.value = 5
    assert comp.value == 8
    rx2.value = 10
    assert comp.value == 15

# --- RxInt ---
def test_rxint_increment_decrement():
    rx = RxInt(5)
    rx.increment()
    assert rx.value == 6
    rx.decrement(2)
    assert rx.value == 4

# --- RxStr ---
def test_rxstr_append_and_clear():
    rx = RxStr("hi")
    rx.append(" there")
    assert rx.value == "hi there"
    rx.clear()
    assert rx.value == ""

# --- RxBool ---
def test_rxbool_toggle():
    rx = RxBool(True)
    rx.toggle()
    assert rx.value is False
    rx.toggle()
    assert rx.value is True

# --- RxList ---
def test_rxlist_append_remove_clear():
    rx = RxList([1, 2])
    rx.append(3)
    assert rx.value == [1, 2, 3]
    rx.remove(2)
    assert rx.value == [1, 3]
    rx.clear()
    assert rx.value == []
    rx.append(5)
    assert rx[0] == 5
    rx[0] = 10
    assert rx[0] == 10
    assert len(rx) == 1

# --- RxDict ---
def test_rxdict_set_get_del_update_clear():
    rx = RxDict({"a": 1})
    rx["b"] = 2
    assert rx["b"] == 2
    del rx["a"]
    assert "a" not in rx.value
    assert rx.get("b") == 2
    rx.update({"c": 3})
    assert rx["c"] == 3
    rx.clear()
    assert rx.value == {}


# --- RxList extended ---
def test_rxlist_pop():
    """pop() removes and returns the last element by default."""
    rx = RxList([10, 20, 30])
    popped = rx.pop()
    assert popped == 30
    assert rx.value == [10, 20]


def test_rxlist_pop_index():
    """pop(idx) removes and returns the element at index."""
    rx = RxList([10, 20, 30])
    popped = rx.pop(0)
    assert popped == 10
    assert rx.value == [20, 30]


def test_rxlist_extend():
    """extend() appends all items from another list."""
    rx = RxList([1])
    rx.extend([2, 3, 4])
    assert rx.value == [1, 2, 3, 4]


def test_rxlist_setitem_notifies():
    """__setitem__ triggers observer notification."""
    rx = RxList([1, 2, 3])
    notified = []
    rx.listen(lambda: notified.append(True))
    rx[1] = 99
    assert rx[1] == 99
    assert len(notified) >= 1


def test_rxlist_remove_nonexistent():
    """remove() on a non-existent item does nothing."""
    rx = RxList([1, 2])
    rx.remove(99)  # should not raise
    assert rx.value == [1, 2]


# --- Reactive extended ---
def test_reactive_set_alias():
    """set() is an alias for setting .value."""
    rx = Reactive(0)
    rx.set(42)
    assert rx.value == 42


def test_reactive_str():
    """__str__ returns string representation of the value."""
    rx = Reactive(123)
    assert str(rx) == "123"


def test_reactive_repr():
    """__repr__ includes class name and value."""
    rx = Reactive(7)
    r = repr(rx)
    assert "Reactive" in r
    assert "7" in r


def test_reactive_no_notify_same_value():
    """Setting the same value does not trigger observers."""
    rx = Reactive(10)
    calls = []
    rx.listen(lambda: calls.append(1))
    rx.value = 10  # same value
    assert calls == []


# --- Observer extended ---
def test_observer_notify_error_handling():
    """Observer.notify catches callback errors without crashing."""
    rx = Reactive(0)
    def bad_callback():
        raise ValueError("boom")
    obs = rx.listen(bad_callback)
    # Trigger observer — should not raise
    rx.value = 1
    obs.dispose()


def test_observer_dispose_clears_dependencies():
    """After dispose, observer has no dependencies."""
    rx = Reactive(0)
    obs = rx.listen(lambda: None)
    obs.dispose()
    assert obs._dependencies == set()
    assert obs.active is False


# --- RxBool extended ---
def test_rxbool_default():
    """RxBool defaults to False."""
    rx = RxBool()
    assert rx.value is False


# --- RxInt extended ---
def test_rxint_default():
    """RxInt defaults to 0."""
    rx = RxInt()
    assert rx.value == 0


def test_rxint_increment_custom_step():
    """increment with custom step."""
    rx = RxInt(0)
    rx.increment(5)
    assert rx.value == 5


# --- RxStr extended ---
def test_rxstr_default():
    """RxStr defaults to empty string."""
    rx = RxStr()
    assert rx.value == ""


# --- RxDict extended ---
def test_rxdict_default():
    """RxDict defaults to empty dict."""
    rx = RxDict()
    assert rx.value == {}


def test_rxdict_get_default():
    """get() returns default for missing key."""
    rx = RxDict({"a": 1})
    assert rx.get("missing", 42) == 42


def test_rxdict_del_nonexistent():
    """__delitem__ on missing key does nothing."""
    rx = RxDict({"a": 1})
    del rx["nonexistent"]  # should not raise
    assert rx.value == {"a": 1}


# --- Computed extended ---
def test_computed_with_explicit_dependencies():
    """Computed with explicit dependencies list."""
    rx = Reactive(3)
    comp = Computed(lambda: rx.value * 3, dependencies=[rx])
    assert comp.value == 9
    rx.value = 4
    assert comp.value == 12
