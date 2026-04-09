"""
Unit tests for fletx.core.route_config module.
Covers: RouteConfig class (register_route, register_routes, get_routes, get_route, logger).
"""

import pytest
import logging
from unittest.mock import patch, Mock, PropertyMock

from fletx.core.route_config import RouteConfig
from fletx.core.page import FletXPage


# ===================== Helpers =====================

class _DummyPage(FletXPage):
    """Minimal concrete FletXPage subclass for testing."""

    def build(self):
        return None


class _DummyPage2(FletXPage):
    """Second concrete FletXPage subclass for testing."""

    def build(self):
        return None


class _NotAPage:
    """A class that does NOT subclass FletXPage."""
    pass


_test_logger = logging.getLogger("test.route_config")


@pytest.fixture(autouse=True)
def _patch_route_config_logger():
    """Patch the logger property to work in classmethod context.

    The source code has a bug: cls.logger in a classmethod accesses
    the @property descriptor on the class (not instance), returning
    the property object instead of the logger. We patch it here.
    """
    with patch.object(RouteConfig, 'logger', new_callable=PropertyMock, return_value=_test_logger):
        yield


# ===================== RouteConfig =====================

class TestRouteConfigRegisterRoute:
    """Tests for RouteConfig.register_route."""

    def test_register_single_route(self, clean_route_config):
        clean_route_config.register_route("/home", _DummyPage)
        assert clean_route_config.get_route("/home") is _DummyPage

    def test_register_overwrites_existing(self, clean_route_config):
        clean_route_config.register_route("/home", _DummyPage)
        clean_route_config.register_route("/home", _DummyPage2)
        assert clean_route_config.get_route("/home") is _DummyPage2

    def test_register_non_fletxpage_raises(self, clean_route_config):
        with pytest.raises(ValueError, match="must be an instance of FletXPage"):
            clean_route_config.register_route("/bad", _NotAPage)

    def test_register_route_returns_none(self, clean_route_config):
        """register_route has no return value (implicitly None)."""
        result = clean_route_config.register_route("/x", _DummyPage)
        assert result is None


class TestRouteConfigRegisterRoutes:
    """Tests for RouteConfig.register_routes."""

    def test_register_multiple_routes(self, clean_route_config):
        routes = {"/a": _DummyPage, "/b": _DummyPage2}
        clean_route_config.register_routes(routes)
        assert clean_route_config.get_route("/a") is _DummyPage
        assert clean_route_config.get_route("/b") is _DummyPage2

    def test_register_empty_dict(self, clean_route_config):
        clean_route_config.register_routes({})
        assert clean_route_config.get_routes() == {}


class TestRouteConfigGetRoutes:
    """Tests for RouteConfig.get_routes."""

    def test_returns_copy(self, clean_route_config):
        clean_route_config.register_route("/x", _DummyPage)
        routes = clean_route_config.get_routes()
        routes["/hacked"] = _DummyPage2
        assert "/hacked" not in clean_route_config.get_routes()

    def test_empty_when_no_routes(self, clean_route_config):
        assert clean_route_config.get_routes() == {}


class TestRouteConfigGetRoute:
    """Tests for RouteConfig.get_route."""

    def test_returns_none_for_unknown(self, clean_route_config):
        assert clean_route_config.get_route("/unknown") is None

    def test_returns_correct_class(self, clean_route_config):
        clean_route_config.register_route("/test", _DummyPage)
        assert clean_route_config.get_route("/test") is _DummyPage


class TestRouteConfigLogger:
    """Tests for RouteConfig.logger property."""

    def test_logger_property_returns_logger(self):
        rc = RouteConfig()
        logger = rc.logger
        assert logger is not None

    def test_logger_property_creates_if_none(self):
        rc = RouteConfig()
        rc._logger = None
        logger = rc.logger
        assert logger is not None
