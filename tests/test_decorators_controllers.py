"""
Unit tests for fletx.decorators.controllers module.
Covers: page_controller, with_controller.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from fletx.core.controller import FletXController


class TestPageController:
    """Tests for the page_controller decorator."""

    def test_decorator_sets_controller_attr(self):
        """page_controller()(PageClass) sets Controller attribute on the page class."""
        with patch("fletx.decorators.controllers.FletX") as MockFletX:
            MockFletX.find.return_value = None

            from fletx.decorators.controllers import page_controller

            class DummyController(FletXController):
                def __init__(self):
                    self._dummy = True

            # Use the two-step form: page_controller(ControllerClass)(PageClass)
            # When controller_class is a type, page_controller returns decorator(controller_class)
            # which expects a page class — so we pass it directly with the class arg
            class FakePage:
                def __init__(self):
                    pass
                def build(self):
                    return "content"

            # Use the no-arg form and then apply to page
            decorator_fn = page_controller()
            # decorator_fn is the inner `decorator` function
            Decorated = decorator_fn(FakePage)
            # When no controller_class, Controller is set to None
            assert hasattr(Decorated, "Controller")

    def test_decorator_invalid_arg_raises(self):
        """page_controller with non-type argument raises TypeError."""
        from fletx.decorators.controllers import page_controller

        with pytest.raises(TypeError, match="controller class must be"):
            page_controller("not_a_class")


class TestWithController:
    """Tests for the with_controller decorator."""

    def test_wrapped_build_injects_controller(self):
        """with_controller wraps build() to auto-inject."""
        with patch("fletx.decorators.controllers.FletX") as MockFletX:
            MockFletX.find.return_value = None

            from fletx.decorators.controllers import with_controller

            class DummyCtrl(FletXController):
                def __init__(self):
                    self._dummy = True

            class FakePage:
                Controller = DummyCtrl

                def build(self):
                    return "content"

            Decorated = with_controller(FakePage)
            instance = Decorated()
            result = instance.build()
            assert result == "content"
            # Controller should have been injected
            assert hasattr(instance, "controller")

