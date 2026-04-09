"""
Extended unit tests for fletx.core.page (FletXPage).
Covers lifecycle, controller management, effects, watch, events,
gestures, navigation widgets, performance monitoring.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fletx.core.page import FletXPage, PageState
from fletx.core.controller import FletXController
import flet as ft


class SamplePage(FletXPage):
    """Concrete implementation of FletXPage for testing."""

    def build(self):
        return ft.Text("Test Page Content")


class SampleController(FletXController):
    """Test controller."""
    pass


# ===================== Lifecycle =====================

class TestPageLifecycle:

    def test_did_mount_sets_state(self, mock_page_dependencies):
        page = SamplePage()
        page.did_mount()
        assert page.state == PageState.ACTIVE  # did_mount -> before_on_init -> ACTIVE
        assert page._mount_time is not None
        assert page._is_mounted is True

    def test_will_unmount_sets_state(self, mock_page_dependencies):
        page = SamplePage()
        page.did_mount()
        page.will_unmount()
        assert page.state == PageState.DISPOSED

    def test_did_unmount_disposes_effects(self, mock_page_dependencies):
        page = SamplePage()
        page.did_mount()
        page.did_unmount()
        assert page.state == PageState.DISPOSED
        mock_page_dependencies['effects'].dispose.assert_called()

    def test_before_on_init_calls_on_init(self, mock_page_dependencies):
        on_init_called = []

        class CustomPage(FletXPage):
            def build(self):
                return ft.Text("custom")

            def on_init(self):
                on_init_called.append(True)

        page = CustomPage()
        page.before_on_init()
        assert on_init_called == [True]
        assert page.state == PageState.ACTIVE

    def test_on_destroy_hook_called(self, mock_page_dependencies):
        destroy_called = []

        class CustomPage(FletXPage):
            def build(self):
                return ft.Text("x")

            def on_destroy(self):
                destroy_called.append(True)

        page = CustomPage()
        page.did_mount()
        page.will_unmount()
        # on_destroy is called both in will_unmount and did_unmount
        assert len(destroy_called) >= 1


# ===================== Controller management =====================

class TestPageControllerManagement:

    def test_get_controller_creates_new(self, mock_page_dependencies):
        mock_page_dependencies['di'].find.return_value = None
        page = SamplePage()

        ctrl = page.get_controller(SampleController, lazy=False)
        assert isinstance(ctrl, SampleController)
        # Should be cached
        ctrl2 = page.get_controller(SampleController, lazy=False)
        assert ctrl2 is ctrl

    def test_get_controller_with_tag(self, mock_page_dependencies):
        mock_page_dependencies['di'].find.return_value = None
        page = SamplePage()

        ctrl = page.get_controller(SampleController, tag="my_tag", lazy=False)
        assert isinstance(ctrl, SampleController)

    def test_inject_controller(self, mock_page_dependencies):
        page = SamplePage()
        ctrl = SampleController()
        page.inject_controller(ctrl, tag="test")
        key = "SampleController_test"
        assert page._controllers[key] is ctrl

    def test_remove_controller(self, mock_page_dependencies):
        page = SamplePage()
        ctrl = SampleController()
        page.inject_controller(ctrl)
        removed = page.remove_controller(SampleController)
        assert removed is True
        assert "SampleController" not in page._controllers

    def test_remove_controller_missing(self, mock_page_dependencies):
        page = SamplePage()
        removed = page.remove_controller(SampleController)
        assert removed is False


# ===================== Watch / reactive =====================

class TestPageWatch:

    def test_watch_reactive(self, mock_page_dependencies):
        from fletx.core.state import RxInt
        page = SamplePage()
        page.did_mount()  # must be mounted for _safe_callback
        rx = RxInt(0)
        calls = []
        observer = page.watch(rx, lambda: calls.append(rx.value))
        assert observer is not None
        rx.value = 5
        assert 5 in calls

    def test_watch_non_reactive_returns_none(self, mock_page_dependencies):
        page = SamplePage()
        result = page.watch("not_reactive", lambda: None)
        assert result is None

    def test_watch_immediate(self, mock_page_dependencies):
        from fletx.core.state import RxInt
        page = SamplePage()
        page.did_mount()  # must be mounted for _safe_callback
        rx = RxInt(10)
        calls = []
        page.watch(rx, lambda: calls.append(True), immediate=True)
        assert len(calls) >= 1

    def test_watch_multiple(self, mock_page_dependencies):
        from fletx.core.state import RxInt
        page = SamplePage()
        page.did_mount()  # must be mounted for _safe_callback
        rx1 = RxInt(0)
        rx2 = RxInt(0)
        calls = []
        observers = page.watch_multiple([rx1, rx2], lambda: calls.append(1))
        assert len(observers) == 2
        rx1.value = 1
        assert len(calls) >= 1


# ===================== Event handlers =====================

class TestPageEventHandlers:

    def test_on_resize_registers(self, mock_page_dependencies):
        page = SamplePage()
        cb = Mock()
        page.on_resize(cb)
        assert "resized" in page._event_handlers
        assert cb in page._event_handlers["resized"]

    def test_on_keyboard_registers(self, mock_page_dependencies):
        page = SamplePage()
        cb = Mock()
        page.on_keyboard(cb)
        assert "keyboard_event" in page._event_handlers
        assert cb in page._event_handlers["keyboard_event"]

    def test_on_error_registers(self, mock_page_dependencies):
        page = SamplePage()
        cb = Mock()
        page.on_error(cb)
        assert "error" in page._event_handlers

    def test_on_media_change_registers(self, mock_page_dependencies):
        page = SamplePage()
        cb = Mock()
        page.on_media_change(cb)
        assert "media_change" in page._event_handlers


# ===================== Gesture handlers =====================

class TestPageGestures:

    def test_on_tap_when_enabled(self, mock_page_dependencies):
        page = SamplePage(enable_gestures=True)
        cb = Mock()
        page.on_tap(cb)
        assert page._gesture_handlers.get("tap") is cb

    def test_on_tap_when_disabled(self, mock_page_dependencies):
        page = SamplePage(enable_gestures=False)
        cb = Mock()
        page.on_tap(cb)
        assert "tap" not in page._gesture_handlers

    def test_on_long_press(self, mock_page_dependencies):
        page = SamplePage(enable_gestures=True)
        cb = Mock()
        # ft.Container.on_long_press property shadows the FletXPage method,
        # so we call the unbound class method directly
        FletXPage.on_long_press(page, cb)
        assert page._gesture_handlers.get("long_press") is cb

    def test_on_scale(self, mock_page_dependencies):
        page = SamplePage(enable_gestures=True)
        cb = Mock()
        FletXPage.on_scale(page, cb)
        assert page._gesture_handlers.get("scale") is cb


# ===================== Properties & performance =====================

class TestPageProperties:

    def test_mount_time_none_before_mount(self, mock_page_dependencies):
        page = SamplePage()
        assert page.mount_time is None

    def test_mount_time_set_after_mount(self, mock_page_dependencies):
        page = SamplePage()
        page.did_mount()
        assert page.mount_time is not None

    def test_average_render_time_empty(self, mock_page_dependencies):
        page = SamplePage()
        assert page.average_render_time == 0.0

    def test_average_render_time_with_data(self, mock_page_dependencies):
        page = SamplePage()
        page._render_times = [10.0, 20.0, 30.0]
        assert page.average_render_time == 20.0

    def test_get_performance_stats(self, mock_page_dependencies):
        page = SamplePage()
        # Mock effects needs a _effects dict for len()
        mock_page_dependencies['effects']._effects = {}
        stats = page.get_performance_stats()
        assert "mount_time" in stats
        assert "update_count" in stats
        assert "average_render_time" in stats
        assert "controller_count" in stats
        assert stats["controller_count"] == 0

    def test_measure_render_time(self, mock_page_dependencies):
        page = SamplePage()

        @page.measure_render_time
        def build_content():
            return "content"

        build_content()
        assert len(page._render_times) == 1


# ===================== Keyboard shortcuts =====================

class TestPageKeyboardShortcuts:

    def test_get_key_combination(self, mock_page_dependencies):
        page = SamplePage()
        event = Mock()
        event.ctrl = True
        event.alt = False
        event.shift = True
        event.meta = False
        event.key = "S"
        combo = page._get_key_combination(event)
        assert combo == "ctrl+shift+s"

    def test_get_key_combination_no_modifiers(self, mock_page_dependencies):
        page = SamplePage()
        event = Mock()
        event.ctrl = False
        event.alt = False
        event.shift = False
        event.meta = False
        event.key = "Escape"
        combo = page._get_key_combination(event)
        assert combo == "escape"

    def test_handle_keyboard_shortcuts(self, mock_page_dependencies):
        page = SamplePage()
        cb = Mock()
        page._keyboard_shortcuts["ctrl+s"] = {"callback": cb}
        event = Mock()
        event.ctrl = True
        event.alt = False
        event.shift = False
        event.meta = False
        event.key = "S"
        page._handle_keyboard_shortcuts(event)
        cb.assert_called_once()

    def test_handle_keyboard_shortcuts_error(self, mock_page_dependencies):
        page = SamplePage()
        cb = Mock(side_effect=RuntimeError("boom"))
        page._keyboard_shortcuts["ctrl+x"] = {"callback": cb}
        event = Mock()
        event.ctrl = True
        event.alt = False
        event.shift = False
        event.meta = False
        event.key = "X"
        # Should not raise
        page._handle_keyboard_shortcuts(event)

