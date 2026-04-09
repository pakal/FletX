"""
Unit tests for fletx.utils.__init__ module.
Covers: get_logger, get_page, get_event_loop, import_module_from, ui_friendly_sleep.
"""

import pytest
import logging
from unittest.mock import Mock, patch

from fletx.utils.context import AppContext


class TestGetLogger:
    """Tests for fletx.utils.get_logger."""

    def test_returns_child_when_context_has_logger(self, app_context):
        """get_logger returns a child of the base logger from context."""
        base_logger = logging.getLogger("TestBase")
        app_context.set_data("logger", base_logger)

        from fletx.utils import get_logger
        child = get_logger("MyModule")
        assert child.name == "TestBase.MyModule"

    def test_fallback_when_no_context_logger(self):
        """get_logger falls back to SharedLogger when context has no logger."""
        # Ensure no logger in context
        old_page = AppContext._page
        old_data = AppContext._data.copy()
        AppContext._page = None
        AppContext._data = {}
        try:
            from fletx.utils import get_logger
            logger = get_logger("FallbackTest")
            assert logger is not None
        finally:
            AppContext._page = old_page
            AppContext._data = old_data


class TestGetPage:
    """Tests for fletx.utils.get_page."""

    def test_returns_page_from_context(self, app_context, mock_flet_page):
        """get_page returns the initialized page."""
        from fletx.utils import get_page
        page = get_page()
        assert page is mock_flet_page

    def test_raises_when_not_initialized(self):
        """get_page raises RuntimeError when AppContext has no page."""
        old_page = AppContext._page
        AppContext._page = None
        try:
            from fletx.utils import get_page
            with pytest.raises(RuntimeError, match="not initialized"):
                get_page()
        finally:
            AppContext._page = old_page


class TestGetEventLoop:
    """Tests for fletx.utils.get_event_loop."""

    def test_returns_event_loop_from_context(self, app_context):
        """get_event_loop returns the loop stored in AppContext."""
        mock_loop = Mock()
        app_context.set_data("event_loop", mock_loop)

        from fletx.utils import get_event_loop
        loop = get_event_loop()
        assert loop is mock_loop


class TestImportModuleFrom:
    """Tests for fletx.utils.import_module_from."""

    def test_imports_known_module(self):
        """import_module_from imports a standard library module by path."""
        from fletx.utils import import_module_from
        mod = import_module_from("json")
        assert hasattr(mod, "dumps")

    def test_import_nonexistent_raises(self):
        """import_module_from raises for non-existent module."""
        from fletx.utils import import_module_from
        with pytest.raises(ModuleNotFoundError):
            import_module_from("nonexistent_module_12345")


class TestRunAsync:
    """Tests for fletx.utils.run_async."""

    def test_run_async_with_non_running_loop(self, app_context):
        """run_async runs coroutine to completion on non-running loop."""
        import asyncio

        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete = Mock()
        app_context.set_data("event_loop", mock_loop)

        from fletx.utils import run_async

        called = []

        async def my_coro():
            called.append(True)
            return 42

        run_async(my_coro)
        mock_loop.run_until_complete.assert_called_once()
        # Close the coroutine passed to run_until_complete to avoid warning
        coro = mock_loop.run_until_complete.call_args[0][0]
        coro.close()

    def test_run_async_with_running_loop(self, app_context):
        """run_async schedules a task when loop is already running."""
        import asyncio

        mock_task = Mock()
        mock_task.add_done_callback = Mock()
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_loop.create_task.return_value = mock_task
        app_context.set_data("event_loop", mock_loop)

        from fletx.utils import run_async

        async def my_coro():
            return 42

        run_async(my_coro)
        mock_loop.create_task.assert_called_once()
        mock_task.add_done_callback.assert_called_once()
        # Close the coroutine passed to create_task to avoid warning
        coro = mock_loop.create_task.call_args[0][0]
        coro.close()


class TestUiFriendlySleep:
    """Tests for fletx.utils.ui_friendly_sleep."""

    @pytest.mark.asyncio
    async def test_zero_duration_returns_immediately(self):
        """ui_friendly_sleep with duration <= 0 returns immediately."""
        from fletx.utils import ui_friendly_sleep
        mock_page = Mock()
        await ui_friendly_sleep(0, mock_page)
        mock_page.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_negative_duration_returns_immediately(self):
        """ui_friendly_sleep with negative duration returns immediately."""
        from fletx.utils import ui_friendly_sleep
        mock_page = Mock()
        await ui_friendly_sleep(-5, mock_page)
        mock_page.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_page_update(self):
        """ui_friendly_sleep calls page.update between chunks."""
        from fletx.utils import ui_friendly_sleep
        mock_page = Mock()
        await ui_friendly_sleep(20, mock_page)
        assert mock_page.update.call_count >= 1

