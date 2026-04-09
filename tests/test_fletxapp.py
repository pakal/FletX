import pytest

from unittest.mock import Mock
from fletx.app import FletXApp
import flet as ft


def test_fletxapp_initialization_defaults():
    """Test FletXApp initialization with default values."""
    app = FletXApp()
    assert app.initial_route == "/"
    assert app.theme_mode == ft.ThemeMode.SYSTEM
    assert not app.debug
    assert app.title == "FletX App"
    assert app.theme is None
    assert app.dark_theme is None
    assert app.window_config == {}
    assert app.on_startup == []
    assert app.on_shutdown == []
    assert not app.is_initialized

def test_fletxapp_initialization_custom():
    """Test FletXApp initialization with custom values."""
    theme = ft.Theme()
    dark_theme = ft.Theme()
    window_config = {"width": 800, "height": 600}
    startup_hook = Mock()
    shutdown_hook = Mock()

    app = FletXApp(
        initial_route="/home",
        theme_mode=ft.ThemeMode.DARK,
        debug=True,
        title="My Test App",
        theme=theme,
        dark_theme=dark_theme,
        window_config=window_config,
        on_startup=[startup_hook],
        on_shutdown=shutdown_hook,
    )

    assert app.initial_route == "/home"
    assert app.theme_mode == ft.ThemeMode.DARK
    assert app.debug
    assert app.title == "My Test App"
    assert app.theme is theme
    assert app.dark_theme is dark_theme
    assert app.window_config == window_config
    assert app.on_startup == [startup_hook]
    assert app.on_shutdown == [shutdown_hook]

def test_add_hooks():
    """Test adding startup and shutdown hooks."""
    app = FletXApp()
    startup_hook1 = Mock()
    startup_hook2 = Mock()
    shutdown_hook1 = Mock()
    shutdown_hook2 = Mock()

    app.add_startup_hook(startup_hook1).add_startup_hook(startup_hook2)
    app.add_shutdown_hook(shutdown_hook1).add_shutdown_hook(shutdown_hook2)

    assert app.on_startup == [startup_hook1, startup_hook2]
    assert app.on_shutdown == [shutdown_hook1, shutdown_hook2]

def test_fluent_configuration():
    """Test fluent interface for configuration."""
    app = FletXApp()
    theme = ft.Theme()
    dark_theme = ft.Theme()

    app.with_title("Fluent Title") \
       .with_theme(theme) \
       .with_dark_theme(dark_theme) \
       .with_window_size(1024, 768) \
       .with_debug(True)

    assert app.title == "Fluent Title"
    assert app.theme is theme
    assert app.dark_theme is dark_theme
    assert app.window_config == {"width": 1024, "height": 768}
    assert app.debug



def test_configure_window():
    """Test configuring window properties after initialization."""
    app = FletXApp()
    app.configure_window(width=1200, height=900, fullscreen=True)
    assert app.window_config == {"width": 1200, "height": 900, "fullscreen": True}
    app.configure_window(width=1000)
    assert app.window_config == {"width": 1000, "height": 900, "fullscreen": True}


# ---------- _normalize_hooks ----------

def test_normalize_hooks_none():
    """_normalize_hooks with None returns empty list."""
    app = FletXApp()
    assert app._normalize_hooks(None) == []


def test_normalize_hooks_single_callable():
    """_normalize_hooks wraps a single callable in a list."""
    fn = Mock()
    app = FletXApp()
    assert app._normalize_hooks(fn) == [fn]


def test_normalize_hooks_list():
    """_normalize_hooks passes through a list."""
    fn1, fn2 = Mock(), Mock()
    app = FletXApp()
    assert app._normalize_hooks([fn1, fn2]) == [fn1, fn2]


def test_normalize_hooks_invalid():
    """_normalize_hooks raises ValueError for non-callable, non-list input."""
    app = FletXApp()
    with pytest.raises(ValueError, match="Hooks must be callable"):
        app._normalize_hooks(42)


# ---------- configure_theme ----------

def test_configure_theme_both():
    """configure_theme sets both light and dark themes."""
    app = FletXApp()
    light = ft.Theme()
    dark = ft.Theme()
    result = app.configure_theme(theme=light, dark_theme=dark)
    assert app.theme is light
    assert app.dark_theme is dark
    assert result is app  # fluent


def test_configure_theme_partial():
    """configure_theme updates only the provided theme."""
    app = FletXApp()
    dark = ft.Theme()
    app.configure_theme(dark_theme=dark)
    assert app.theme is None
    assert app.dark_theme is dark


# ---------- _execute_hooks ----------

@pytest.mark.asyncio
async def test_execute_hooks_sync():
    """_execute_hooks calls synchronous hooks with page."""
    app = FletXApp()
    app._page = Mock()
    hook = Mock(__name__="sync_hook")
    await app._execute_hooks([hook], "test")
    hook.assert_called_once_with(app._page)


@pytest.mark.asyncio
async def test_execute_hooks_async():
    """_execute_hooks awaits async hooks."""
    app = FletXApp()
    app._page = Mock()
    called = []

    async def async_hook(page):
        called.append(page)

    await app._execute_hooks([async_hook], "test")
    assert len(called) == 1
    assert called[0] is app._page


@pytest.mark.asyncio
async def test_execute_hooks_mixed():
    """_execute_hooks handles a mix of sync and async hooks."""
    app = FletXApp()
    app._page = Mock()
    sync_hook = Mock(__name__="sync_hook")
    async_calls = []

    async def async_hook(page):
        async_calls.append(page)

    await app._execute_hooks([sync_hook, async_hook], "mixed")
    sync_hook.assert_called_once()
    assert len(async_calls) == 1


@pytest.mark.asyncio
async def test_execute_hooks_error_handling():
    """_execute_hooks logs errors but does not crash on hook failure."""
    app = FletXApp()
    app._page = Mock()
    bad_hook = Mock(side_effect=RuntimeError("boom"), __name__="bad_hook")
    good_hook = Mock(__name__="good_hook")

    # Should not raise
    await app._execute_hooks([bad_hook, good_hook], "err")
    bad_hook.assert_called_once()
    good_hook.assert_called_once()


# ---------- _configure_page ----------

def test_configure_page_basic(mock_flet_page):
    """_configure_page sets title and theme_mode on the page."""
    app = FletXApp(title="Cfg Test", theme_mode=ft.ThemeMode.DARK)
    app._configure_page(mock_flet_page)
    assert mock_flet_page.title == "Cfg Test"
    assert mock_flet_page.theme_mode == ft.ThemeMode.DARK


def test_configure_page_with_themes(mock_flet_page):
    """_configure_page applies light and dark themes."""
    light = ft.Theme()
    dark = ft.Theme()
    app = FletXApp(theme=light, dark_theme=dark)
    app._configure_page(mock_flet_page)
    assert mock_flet_page.theme is light
    assert mock_flet_page.dark_theme is dark


def test_configure_page_window_config(mock_flet_page):
    """_configure_page sets known window properties."""
    mock_flet_page.window.width = 0
    mock_flet_page.window.height = 0
    app = FletXApp(window_config={"width": 1024, "height": 768})
    app._configure_page(mock_flet_page)
    assert mock_flet_page.window.width == 1024
    assert mock_flet_page.window.height == 768


def test_configure_page_unknown_window_prop(mock_flet_page):
    """_configure_page warns on unknown window property."""
    # Make sure window does NOT have 'nonexistent'
    mock_flet_page.window = Mock(spec=[])
    app = FletXApp(window_config={"nonexistent": True})
    app._configure_page(mock_flet_page)
    # Should have logged a warning (not raise)


# ---------- context data ----------

def test_get_set_context_data(app_context):
    """get_context_data / set_context_data work via AppContext."""
    app = FletXApp()
    app.set_context_data("foo", "bar")
    assert app.get_context_data("foo") == "bar"
    assert app.get_context_data("missing", "default") == "default"


# ---------- create handlers ----------

def test_create_main_handler():
    """create_main_handler returns _sync_main."""
    app = FletXApp()
    handler = app.create_main_handler()
    assert handler == app._sync_main


def test_create_async_main_handler():
    """create_async_main_handler returns _async_main."""
    app = FletXApp()
    handler = app.create_async_main_handler()
    assert handler == app._async_main


# ---------- page property ----------

def test_page_property_none_initially():
    """page property is None before initialization."""
    app = FletXApp()
    assert app.page is None


# ---------- on_system_exit hooks ----------

def test_on_system_exit_hooks_normalized():
    """on_system_exit hooks are normalized to a list."""
    fn = Mock()
    app = FletXApp(on_system_exit=fn)
    assert app.on_system_exit == [fn]
