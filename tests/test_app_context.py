"""
Unit tests for fletx.utils.context.AppContext
"""


from fletx.utils.context import AppContext


class TestAppContextInitialize:
    """Tests for AppContext.initialize and basic accessors."""

    def test_initialize_sets_page_and_debug(self, mock_flet_page):
        """initialize stores page and debug flag."""
        AppContext.initialize(mock_flet_page, debug=True)
        assert AppContext.get_page() is mock_flet_page
        assert AppContext.is_debug() is True
        assert AppContext._is_initialized is True
        # cleanup
        AppContext._is_initialized = False
        AppContext._page = None
        AppContext._debug = False
        AppContext._data = {}

    def test_initialize_defaults_debug_false(self, mock_flet_page):
        """initialize defaults debug to False."""
        AppContext.initialize(mock_flet_page)
        assert AppContext.is_debug() is False
        # cleanup
        AppContext._is_initialized = False
        AppContext._page = None
        AppContext._data = {}

    def test_initialize_resets_data(self, mock_flet_page):
        """initialize clears any previously stored data."""
        AppContext._data = {"leftover": True}
        AppContext.initialize(mock_flet_page)
        assert AppContext._data == {}
        # cleanup
        AppContext._is_initialized = False
        AppContext._page = None
        AppContext._data = {}


class TestAppContextData:
    """Tests for set_data / get_data / remove_data / clear_data."""

    def test_set_and_get_data(self, app_context):
        """set_data stores a value retrievable by get_data."""
        app_context.set_data("key1", "value1")
        assert app_context.get_data("key1") == "value1"

    def test_get_data_default(self, app_context):
        """get_data returns default for missing key."""
        assert app_context.get_data("nope") is None
        assert app_context.get_data("nope", "fallback") == "fallback"

    def test_remove_data_existing(self, app_context):
        """remove_data returns True and removes key when it exists."""
        app_context.set_data("rm_key", 42)
        assert app_context.remove_data("rm_key") is True
        assert app_context.get_data("rm_key") is None

    def test_remove_data_missing(self, app_context):
        """remove_data returns False for a missing key."""
        assert app_context.remove_data("no_such_key") is False

    def test_clear_data(self, app_context):
        """clear_data removes all stored data."""
        app_context.set_data("a", 1)
        app_context.set_data("b", 2)
        app_context.clear_data()
        assert app_context.get_data("a") is None
        assert app_context.get_data("b") is None


class TestAppContextDebug:
    """Tests for is_debug."""

    def test_is_debug_true(self, app_context_debug):
        """is_debug returns True when initialized in debug mode."""
        assert app_context_debug.is_debug() is True

    def test_is_debug_false(self, app_context):
        """is_debug returns False when initialized without debug."""
        assert app_context.is_debug() is False


class TestAppContextGetPage:
    """Tests for get_page."""

    def test_get_page_returns_page(self, app_context, mock_flet_page):
        """get_page returns the page passed to initialize."""
        assert app_context.get_page() is mock_flet_page

    def test_get_page_none_before_init(self):
        """get_page returns None before initialization."""
        # Ensure clean state
        old_page = AppContext._page
        AppContext._page = None
        try:
            assert AppContext.get_page() is None
        finally:
            AppContext._page = old_page

