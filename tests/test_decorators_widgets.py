"""
Unit tests for fletx.decorators.widgets module.
Covers: obx decorator, reactive_form decorator, reactive_state_machine decorator,
        simple_reactive, two_way_reactive, computed_reactive.

NOTE: The reactive_control decorator deeply integrates with Flet controls
and FletXWidget, so we test it indirectly through its convenience wrappers.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from enum import Enum

from fletx.core.state import Reactive, RxStr, RxInt, RxBool, RxList
from fletx.core.types import (
    BindingConfig, BindingType, ComputedBindingConfig, FormFieldValidationRule,
)


# ===================== Helper to patch FletXWidget for decorator tests =====================

@pytest.fixture(autouse=True)
def patch_fletx_widget_for_decorators():
    """Patch FletXWidget.__init_subclass__ and get_page to avoid Flet dependencies."""
    import warnings
    with patch("fletx.core.widget.get_page") as mock_get_page, \
         patch("fletx.core.widget.FletXWidgetRegistry") as mock_registry, \
         patch("fletx.decorators.reactive.asyncio.create_task"), \
         warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="coroutine.*was never awaited")
        mock_page = Mock()
        mock_page.controls = []
        mock_page.update = Mock()
        mock_get_page.return_value = mock_page
        yield


# ===================== obx decorator =====================

class TestObxDecorator:
    """Tests for the @obx decorator."""

    def test_obx_returns_callable(self):
        from fletx.decorators.widgets import obx

        @obx
        def my_builder():
            import flet as ft
            return ft.Text("hello")

        assert callable(my_builder)

    def test_obx_preserves_function_name(self):
        from fletx.decorators.widgets import obx

        @obx
        def my_widget_builder():
            import flet as ft
            return ft.Text("test")

        assert my_widget_builder.__name__ == "my_widget_builder"

    def test_obx_creates_obx_wrapper(self):
        """obx decorator should return an Obx wrapper when called."""
        from fletx.decorators.widgets import obx
        from fletx.widgets.obx import Obx

        @obx
        def builder():
            import flet as ft
            return ft.Text("test")

        result = builder()
        assert isinstance(result, Obx)


# ===================== reactive_form decorator =====================

class TestReactiveFormDecorator:
    """Tests for the @reactive_form decorator."""

    def _make_form_class(self, **decorator_kwargs):
        """Helper to create a decorated form class with a Flet-compatible base."""
        import flet as ft
        from fletx.decorators.widgets import reactive_form

        @reactive_form(**decorator_kwargs)
        class TestForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("")
                self.rx_email = RxStr("")
                self.rx_is_valid = RxBool(False)
                super().__init__()

            def build(self):
                return None

        return TestForm

    def test_form_has_get_values(self):
        FormClass = self._make_form_class(
            form_fields={"name": "rx_name", "email": "rx_email"}
        )
        form = FormClass()
        values = form.get_values()
        assert values == {"name": "", "email": ""}

    def test_form_has_get_errors(self):
        FormClass = self._make_form_class(
            form_fields={"name": "rx_name"}
        )
        form = FormClass()
        errors = form.get_errors()
        assert errors == {}

    def test_form_is_valid_initially(self):
        FormClass = self._make_form_class(
            form_fields={"name": "rx_name"}
        )
        form = FormClass()
        assert form.is_valid() is True

    def test_form_validation_callable(self):
        FormClass = self._make_form_class(
            form_fields={"name": "rx_name"},
            validation_rules={"name": lambda x: len(x) >= 3},
            auto_validate=False,
        )
        form = FormClass()
        form.rx_name.value = "ab"
        assert form.validate_field("name") is False
        assert "name" in form.get_errors()

        form.rx_name.value = "abc"
        assert form.validate_field("name") is True
        assert "name" not in form.get_errors()

    def test_form_validation_method_name(self):
        """Validation rule can reference a method name on the form class."""
        import flet as ft
        from fletx.decorators.widgets import reactive_form

        @reactive_form(
            form_fields={"name": "rx_name"},
            validation_rules={"name": "check_name"},
            auto_validate=False,
        )
        class MyForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("")
                super().__init__()

            def check_name(self, value):
                return value == "valid"

            def build(self):
                return None

        form = MyForm()
        form.rx_name.value = "invalid"
        assert form.validate_field("name") is False
        form.rx_name.value = "valid"
        assert form.validate_field("name") is True

    def test_form_validation_missing_method_name(self):
        """Validation rule referencing missing method should log warning."""
        import flet as ft
        from fletx.decorators.widgets import reactive_form

        @reactive_form(
            form_fields={"name": "rx_name"},
            validation_rules={"name": "nonexistent_method"},
            auto_validate=False,
        )
        class MyForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("")
                super().__init__()

            def build(self):
                return None

        form = MyForm()
        form.rx_name.value = "test"
        # Should not raise, just log warning
        form.validate_field("name")

    def test_form_validation_rules_list(self):
        """Multiple FormFieldValidationRule rules for a single field."""
        import flet as ft
        from fletx.decorators.widgets import reactive_form

        @reactive_form(
            form_fields={"name": "rx_name"},
            validation_rules={
                "name": [
                    FormFieldValidationRule(
                        validate_fn=lambda v: len(v) >= 3,
                        err_message="{field} must be at least 3 chars"
                    ),
                    FormFieldValidationRule(
                        validate_fn=lambda v: v != "bad",
                        err_message="{field} cannot be 'bad'"
                    ),
                ]
            },
            auto_validate=False,
        )
        class MyForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("")
                super().__init__()

            def build(self):
                return None

        form = MyForm()
        form.rx_name.value = "ab"
        assert form.validate_field("name") is False
        errors = form.get_errors()
        assert "name" in errors
        # Error list should contain the message
        assert any("at least 3" in e for e in errors["name"])

    def test_form_validation_rules_list_method_name(self):
        """FormFieldValidationRule with validate_fn as method name."""
        import flet as ft
        from fletx.decorators.widgets import reactive_form

        @reactive_form(
            form_fields={"name": "rx_name"},
            validation_rules={
                "name": [
                    FormFieldValidationRule(
                        validate_fn="check_valid",
                        err_message="{field} check failed"
                    ),
                ]
            },
            auto_validate=False,
        )
        class MyForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("")
                super().__init__()

            def check_valid(self, value):
                return value == "ok"

            def build(self):
                return None

        form = MyForm()
        form.rx_name.value = "ok"
        assert form.validate_field("name") is True

    def test_form_validation_rules_list_missing_method(self):
        """FormFieldValidationRule with validate_fn referencing missing method."""
        import flet as ft
        from fletx.decorators.widgets import reactive_form

        @reactive_form(
            form_fields={"name": "rx_name"},
            validation_rules={
                "name": [
                    FormFieldValidationRule(
                        validate_fn="missing_method",
                        err_message="{field} check failed"
                    ),
                ]
            },
            auto_validate=False,
        )
        class MyForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("")
                super().__init__()

            def build(self):
                return None

        form = MyForm()
        form.rx_name.value = "test"
        # Should not raise, just log warning
        result = form.validate_field("name")
        assert result is True  # missing rule is ignored

    def test_form_validate_all(self):
        FormClass = self._make_form_class(
            form_fields={"name": "rx_name", "email": "rx_email"},
            validation_rules={
                "name": lambda x: len(x) >= 1,
                "email": lambda x: "@" in x,
            },
            auto_validate=False,
        )
        form = FormClass()
        form.rx_name.value = "John"
        form.rx_email.value = "invalid"
        assert form.validate_all() is False

        form.rx_email.value = "john@example.com"
        assert form.validate_all() is True

    def test_form_validate_no_rule_for_field(self):
        """validate_field returns True for fields without rules."""
        FormClass = self._make_form_class(
            form_fields={"name": "rx_name"},
            validation_rules={},
            auto_validate=False,
        )
        form = FormClass()
        assert form.validate_field("name") is True

    def test_form_submit_calls_on_submit(self):
        calls = []

        FormClass = self._make_form_class(
            form_fields={"name": "rx_name"},
            on_submit=lambda form: calls.append("submitted"),
            auto_validate=False,
        )
        form = FormClass()
        form.rx_name.value = "test"
        form.submit()
        assert "submitted" in calls

    def test_form_submit_calls_on_submit_success(self):
        calls = []

        FormClass = self._make_form_class(
            form_fields={"name": "rx_name"},
            on_submit_success=lambda values: calls.append(values),
            auto_validate=False,
        )
        form = FormClass()
        form.rx_name.value = "test"
        form.submit()
        assert len(calls) == 1
        assert calls[0]["name"] == "test"

    def test_form_submit_fails_validation(self):
        calls = []

        FormClass = self._make_form_class(
            form_fields={"name": "rx_name"},
            validation_rules={"name": lambda x: len(x) >= 5},
            on_submit_failed=lambda errors: calls.append(errors),
            auto_validate=False,
        )
        form = FormClass()
        form.rx_name.value = "ab"
        form.submit()
        assert len(calls) >= 1

    def test_form_submit_exception_handler(self):
        calls = []

        def bad_submit(form):
            raise RuntimeError("boom")

        FormClass = self._make_form_class(
            form_fields={"name": "rx_name"},
            on_submit=bad_submit,
            on_submit_exception=lambda e: calls.append(str(e)),
            auto_validate=False,
        )
        form = FormClass()
        form.rx_name.value = "test"
        form.submit()
        assert len(calls) == 1
        assert "boom" in calls[0]

    def test_form_call_handler_string(self):
        """_call_handler with a string method name."""
        import flet as ft
        from fletx.decorators.widgets import reactive_form

        @reactive_form(
            form_fields={"name": "rx_name"},
            on_submit="my_handler",
            auto_validate=False,
        )
        class MyForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("test")
                self.handled = False
                super().__init__()

            def my_handler(self, form):
                self.handled = True

            def build(self):
                return None

        form = MyForm()
        form.submit()
        assert form.handled is True

    def test_form_call_handler_invalid_string(self):
        """_call_handler with string referencing non-existent method raises inside submit.

        _handle_submit catches the exception, so without on_submit_exception
        it gets logged silently. With on_submit_exception, it's captured.
        """
        import flet as ft
        from fletx.decorators.widgets import reactive_form
        errors_caught = []

        @reactive_form(
            form_fields={"name": "rx_name"},
            on_submit="nonexistent_handler",
            on_submit_exception=lambda e: errors_caught.append(e),
            auto_validate=False,
        )
        class MyForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("test")
                super().__init__()

            def build(self):
                return None

        form = MyForm()
        form.submit()
        assert len(errors_caught) == 1
        assert isinstance(errors_caught[0], AttributeError)

    def test_form_call_handler_invalid_type(self):
        """_call_handler with invalid type raises TypeError, caught by _handle_submit."""
        import flet as ft
        from fletx.decorators.widgets import reactive_form
        errors_caught = []

        @reactive_form(
            form_fields={"name": "rx_name"},
            on_submit=12345,  # invalid type
            on_submit_exception=lambda e: errors_caught.append(e),
            auto_validate=False,
        )
        class MyForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("test")
                super().__init__()

            def build(self):
                return None

        form = MyForm()
        form.submit()
        assert len(errors_caught) == 1
        assert isinstance(errors_caught[0], TypeError)

    def test_form_rx_is_valid_updated(self):
        """rx_is_valid is updated when validation runs."""
        FormClass = self._make_form_class(
            form_fields={"name": "rx_name"},
            validation_rules={"name": lambda x: len(x) >= 1},
            auto_validate=False,
        )
        form = FormClass()
        form.rx_name.value = ""
        form.validate_field("name")
        assert form.rx_is_valid.value is False

        form.rx_name.value = "ok"
        form.validate_field("name")
        assert form.rx_is_valid.value is True

    def test_form_auto_validate(self):
        """When auto_validate=True, fields validate on change."""
        import flet as ft
        from fletx.decorators.widgets import reactive_form
        validation_errors = []

        @reactive_form(
            form_fields={"name": "rx_name"},
            validation_rules={"name": lambda x: len(x) >= 3},
            on_submit_failed=lambda errors: validation_errors.append(errors),
            auto_validate=True,
        )
        class MyForm(ft.Column):
            def __init__(self):
                self.rx_name = RxStr("")
                self.rx_is_valid = RxBool(True)
                super().__init__()

            def build(self):
                return None

        form = MyForm()
        form.rx_name.value = "ab"  # triggers auto-validation
        # After auto-validation, rx_is_valid should be False
        assert form.rx_is_valid.value is False
        assert len(validation_errors) >= 1


# ===================== reactive_state_machine decorator =====================

class TestReactiveStateMachineDecorator:
    """Tests for the @reactive_state_machine decorator."""

    def _make_state_machine(self, on_state_change=None):
        import flet as ft
        from fletx.decorators.widgets import reactive_state_machine

        class MyState(Enum):
            IDLE = "idle"
            LOADING = "loading"
            DONE = "done"

        @reactive_state_machine(
            states=MyState,
            initial_state=MyState.IDLE,
            transitions={
                (MyState.IDLE, "start"): MyState.LOADING,
                (MyState.LOADING, "finish"): MyState.DONE,
                (MyState.DONE, "reset"): MyState.IDLE,
            },
            on_state_change=on_state_change,
        )
        class MyWidget(ft.Container):
            def __init__(self):
                super().__init__()

            def build(self):
                return None

        return MyWidget, MyState

    def test_initial_state(self):
        WidgetClass, MyState = self._make_state_machine()
        w = WidgetClass()
        assert w.get_current_state() == MyState.IDLE

    def test_valid_transition(self):
        WidgetClass, MyState = self._make_state_machine()
        w = WidgetClass()
        result = w.transition("start")
        assert result is True
        assert w.get_current_state() == MyState.LOADING

    def test_invalid_transition(self):
        WidgetClass, MyState = self._make_state_machine()
        w = WidgetClass()
        result = w.transition("finish")  # can't finish from IDLE
        assert result is False
        assert w.get_current_state() == MyState.IDLE

    def test_can_transition(self):
        WidgetClass, MyState = self._make_state_machine()
        w = WidgetClass()
        assert w.can_transition("start") is True
        assert w.can_transition("finish") is False

    def test_full_cycle(self):
        WidgetClass, MyState = self._make_state_machine()
        w = WidgetClass()
        w.transition("start")
        assert w.get_current_state() == MyState.LOADING
        w.transition("finish")
        assert w.get_current_state() == MyState.DONE
        w.transition("reset")
        assert w.get_current_state() == MyState.IDLE

    def test_on_state_change_callback(self):
        changes = []

        def on_change(old, new):
            changes.append((old, new))

        WidgetClass, MyState = self._make_state_machine(on_state_change=on_change)
        w = WidgetClass()
        w.transition("start")
        # Should have recorded the change
        assert len(changes) >= 1

    def test_rx_state_attribute(self):
        WidgetClass, MyState = self._make_state_machine()
        w = WidgetClass()
        assert hasattr(w, "rx_state")
        assert w.rx_state.value == "idle"


# ===================== simple_reactive =====================

class TestSimpleReactive:
    """Tests for simple_reactive convenience wrapper."""

    def test_simple_reactive_calls_reactive_control(self):
        from fletx.decorators.widgets import simple_reactive
        dec = simple_reactive({"value": "rx_value"})
        assert callable(dec)


# ===================== two_way_reactive =====================

class TestTwoWayReactive:
    """Tests for two_way_reactive convenience wrapper."""

    def test_two_way_reactive_returns_decorator(self):
        from fletx.decorators.widgets import two_way_reactive
        dec = two_way_reactive({"value": "rx_value"})
        assert callable(dec)


# ===================== computed_reactive =====================

class TestComputedReactive:
    """Tests for computed_reactive convenience wrapper."""

    def test_computed_reactive_returns_decorator(self):
        from fletx.decorators.widgets import computed_reactive
        dec = computed_reactive(text=lambda self: "hello")
        assert callable(dec)

