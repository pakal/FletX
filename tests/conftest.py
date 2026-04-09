"""
Shared pytest fixtures for FletX tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import flet as ft

from fletx.utils.context import AppContext
from fletx.core.controller import FletXController


@pytest.fixture
def mock_flet_page():
    """A reusable Mock(spec=ft.Page) with common attributes pre-configured."""
    page = Mock(spec=ft.Page)
    page.width = 800
    page.height = 600
    page.title = "Test App"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.theme = None
    page.dark_theme = None
    page.views = [Mock()]
    page.update = Mock()
    page.window = Mock()
    page.on_close = None
    return page


@pytest.fixture
def app_context(mock_flet_page):
    """Initialize AppContext with a mock page, clean up after test."""
    AppContext.initialize(mock_flet_page, debug=False)
    try:
        yield AppContext
    finally:
        AppContext.clear_data()
        AppContext._is_initialized = False
        AppContext._page = None
        AppContext._debug = False


@pytest.fixture
def app_context_debug(mock_flet_page):
    """Initialize AppContext in debug mode."""
    AppContext.initialize(mock_flet_page, debug=True)
    try:
        yield AppContext
    finally:
        AppContext.clear_data()
        AppContext._is_initialized = False
        AppContext._page = None
        AppContext._debug = False


@pytest.fixture
def fresh_controller():
    """Yield a non-initialized FletXController, dispose after test."""
    ctrl = FletXController(auto_initialize=False)
    try:
        yield ctrl
    finally:
        if not ctrl.is_disposed:
            ctrl.dispose()


@pytest.fixture
def ready_controller():
    """Yield a fully initialized (READY) FletXController, dispose after test."""
    ctrl = FletXController(auto_initialize=True)
    try:
        yield ctrl
    finally:
        if not ctrl.is_disposed:
            ctrl.dispose()


@pytest.fixture
def mock_page_dependencies():
    """Patch external dependencies of FletXPage for isolated testing."""
    with patch('fletx.core.page.get_page') as mock_get_page, \
         patch('fletx.core.page.get_logger') as mock_get_logger, \
         patch('fletx.core.page.DI') as mock_di, \
         patch('fletx.core.page.EffectManager') as mock_effect_manager:

        mock_page = Mock()
        mock_page.width = 800
        mock_page.views = [Mock()]
        mock_page.update = Mock()
        mock_get_page.return_value = mock_page

        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_di.put = Mock()
        mock_di.find = Mock(return_value=None)
        mock_di.delete = Mock()

        mock_effects = Mock()
        mock_effects.runEffects = Mock()
        mock_effects.dispose = Mock()
        mock_effect_manager.return_value = mock_effects

        yield {
            'page': mock_page,
            'logger': mock_logger,
            'di': mock_di,
            'effects': mock_effects,
        }


@pytest.fixture
def clean_route_config():
    """Provide a clean RouteConfig, reset after test."""
    from fletx.core.route_config import RouteConfig
    original_routes = RouteConfig._routes.copy()
    RouteConfig._routes = {}
    try:
        yield RouteConfig
    finally:
        RouteConfig._routes = original_routes


@pytest.fixture
def worker_pool():
    """Provide a fresh WorkerPool, shut down after test."""
    from fletx.core.concurency.worker import WorkerPool
    from fletx.core.concurency.config import WorkerPoolConfig
    pool = WorkerPool(WorkerPoolConfig(max_workers=2, enable_priority=True, auto_shutdown=False))
    try:
        yield pool
    finally:
        pool.shutdown(wait=True)


@pytest.fixture
def worker_pool_no_priority():
    """Provide a WorkerPool with priority disabled."""
    from fletx.core.concurency.worker import WorkerPool
    from fletx.core.concurency.config import WorkerPoolConfig
    pool = WorkerPool(WorkerPoolConfig(max_workers=2, enable_priority=False, auto_shutdown=False))
    try:
        yield pool
    finally:
        pool.shutdown(wait=True)


@pytest.fixture
def event_loop_manager():
    """Provide a fresh EventLoopManager, clean up after test."""
    from fletx.core.concurency.event_loop import EventLoopManager
    # Reset singleton
    original_instance = EventLoopManager._instance
    original_loop = EventLoopManager._loop
    original_owner = EventLoopManager._loop_owner
    EventLoopManager._instance = None
    EventLoopManager._loop = None
    EventLoopManager._loop_owner = False
    mgr = EventLoopManager()
    try:
        yield mgr
    finally:
        # Clean up: close loop if created
        if mgr._loop is not None and not mgr._loop.is_closed():
            mgr._loop.close()
        # Restore singleton state
        EventLoopManager._instance = original_instance
        EventLoopManager._loop = original_loop
        EventLoopManager._loop_owner = original_owner

