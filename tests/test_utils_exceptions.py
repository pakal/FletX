"""
Unit tests for fletx.utils.exceptions module.
Covers exception hierarchy and CommandError returncode.
"""

import pytest
from fletx.utils.exceptions import (
    FletXError,
    RouteNotFoundError,
    NavigationError,
    NavigationAborted,
    DependencyNotFoundError,
    ControllerError,
    StateError,
    ValidationError,
    ConfigurationError,
    FletXCLIError,
    CommandError,
    CommandNotFoundError,
    CommandExecutionError,
    TemplateError,
    ProjectError,
    NetworkError,
    RateLimitError,
    APIError,
)


class TestExceptionHierarchy:
    """Verify all exceptions inherit correctly."""

    @pytest.mark.parametrize("exc_class", [
        RouteNotFoundError,
        NavigationError,
        NavigationAborted,
        DependencyNotFoundError,
        ControllerError,
        StateError,
        ValidationError,
        ConfigurationError,
        FletXCLIError,
        NetworkError,
        RateLimitError,
        APIError,
    ])
    def test_inherits_from_fletx_error(self, exc_class):
        assert issubclass(exc_class, FletXError)

    @pytest.mark.parametrize("exc_class", [
        CommandError,
        CommandNotFoundError,
        CommandExecutionError,
    ])
    def test_cli_errors_inherit_from_cli_error(self, exc_class):
        assert issubclass(exc_class, FletXCLIError)

    @pytest.mark.parametrize("exc_class", [
        TemplateError,
        ProjectError,
    ])
    def test_project_errors_inherit_from_cli_error(self, exc_class):
        assert issubclass(exc_class, FletXCLIError)


class TestCommandError:
    """Tests for CommandError custom returncode."""

    def test_default_returncode(self):
        err = CommandError("fail")
        assert err.returncode == 1

    def test_custom_returncode(self):
        err = CommandError("fail", returncode=2)
        assert err.returncode == 2

    def test_message(self):
        err = CommandError("something broke")
        assert str(err) == "something broke"


class TestExceptionInstantiation:
    """Verify all exceptions can be instantiated and raised."""

    @pytest.mark.parametrize("exc_class,msg", [
        (FletXError, "base error"),
        (RouteNotFoundError, "/unknown"),
        (NavigationError, "nav failed"),
        (NavigationAborted, "cancelled"),
        (DependencyNotFoundError, "not found"),
        (ControllerError, "ctrl error"),
        (StateError, "state error"),
        (ValidationError, "invalid input"),
        (ConfigurationError, "bad config"),
        (NetworkError, "timeout"),
        (RateLimitError, "429"),
        (APIError, "500"),
        (TemplateError, "template broken"),
        (ProjectError, "project missing"),
    ])
    def test_can_raise_and_catch(self, exc_class, msg):
        with pytest.raises(exc_class, match=msg):
            raise exc_class(msg)

