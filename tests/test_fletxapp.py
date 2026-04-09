import pytest

import fletx
print(">>>>>>>>>>>>", fletx)
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