import os
import sys
import types
import importlib.util

from conftest_utils import backup_sys_modules


@backup_sys_modules("fletx", "fletx.utils", "fletx.utils.exceptions", "fletx.core.state", "fletx.core.http")
def _load_services_and_deps():

    # Stub minimal 'fletx.utils' and 'fletx.utils.exceptions' and 'fletx.core.state' and 'fletx.core.http'
    if "fletx" not in sys.modules:
        sys.modules["fletx"] = types.ModuleType("fletx")

    utils_mod = types.ModuleType("fletx.utils")

    class _Logger:
        def debug(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

    def get_logger(name):
        return _Logger()

    utils_mod.get_logger = get_logger

    exceptions_mod = types.ModuleType("fletx.utils.exceptions")

    class NetworkError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    class APIError(Exception):
        pass

    exceptions_mod.NetworkError = NetworkError
    exceptions_mod.RateLimitError = RateLimitError
    exceptions_mod.APIError = APIError

    # Stub state
    state_mod = types.ModuleType("fletx.core.state")
    from enum import Enum
    from typing import Generic, TypeVar

    T = TypeVar("T")

    class ServiceState(Enum):
        IDLE = "idle"
        LOADING = "loading"
        READY = "ready"
        ERROR = "error"
        DISPOSED = "disposed"

    state_mod.ServiceState = ServiceState

    class Reactive(Generic[T]):
        def __init__(self, initial_value):
            self._value = initial_value

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, v):
            self._value = v

        def listen(self, callback, auto_dispose=True):
            # stub
            class Observer:
                def dispose(self):
                    pass

            return Observer()

        def dispose(self):
            pass

    state_mod.Reactive = Reactive
    state_mod.ServiceState = ServiceState

    # Stub http
    http_mod = types.ModuleType("fletx.core.http")

    class HTTPClient:
        def __init__(self, *args, **kwargs):
            pass

    http_mod.HTTPClient = HTTPClient

    sys.modules["fletx.utils"] = utils_mod
    sys.modules["fletx.utils.exceptions"] = exceptions_mod
    sys.modules["fletx.core.state"] = state_mod
    sys.modules["fletx.core.http"] = http_mod

    # Load fletx/core/services.py directly
    services_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "fletx", "core", "services.py"
    )
    spec = importlib.util.spec_from_file_location(
        "fletx_core_services_standalone", services_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)


    return module.FletXService, module.ServiceState, module.HTTPClient


FletXService, ServiceState, HTTPClient = _load_services_and_deps()


def test_service_initial_state():
    s = FletXService(auto_start=False)
    assert s.state == ServiceState.IDLE
    assert not s.is_ready
    assert not s.is_loading
    assert not s.has_error


def test_service_start_transitions():
    s = FletXService(auto_start=False)
    s.start()
    assert s.state == ServiceState.READY


def test_service_start_async():
    import asyncio

    async def run():
        s = FletXService(auto_start=False)
        await s.start_async()
        assert s.state == ServiceState.READY

    asyncio.run(run())


def test_service_set_error():
    s = FletXService()
    try:
        raise ValueError("test error")
    except ValueError as e:
        s.set_error(e)
    assert s.has_error
    assert isinstance(s.error, ValueError)
    assert s.state == ServiceState.ERROR


def test_service_data():
    s = FletXService()
    s.set_data("key", "value")
    assert s.get_data("key") == "value"
    assert s.data == {"key": "value"}
    s.clear_data()
    assert s.get_data("key") is None
    assert s.data == {}


def test_service_dispose():
    s = FletXService()
    s.dispose()
    assert s._disposed
    assert s.state == ServiceState.DISPOSED


def test_service_stop():
    """stop() transitions a READY service back to IDLE."""
    s = FletXService()
    assert s.state == ServiceState.READY
    s.stop()
    assert s.state == ServiceState.IDLE


def test_service_stop_when_idle():
    """stop() on an IDLE service is a no-op."""
    s = FletXService(auto_start=False)
    assert s.state == ServiceState.IDLE
    s.stop()  # should not raise
    assert s.state == ServiceState.IDLE


def test_service_restart():
    """restart() stops then starts the service."""
    s = FletXService()
    assert s.state == ServiceState.READY
    s.restart()
    assert s.state == ServiceState.READY


def test_service_auto_start():
    """auto_start=True starts the service immediately."""
    s = FletXService(auto_start=True)
    assert s.state == ServiceState.READY


def test_service_name_default():
    """Default name is the class name."""
    s = FletXService(auto_start=False)
    assert s.name == "FletXService"


def test_service_custom_name():
    """Custom name is stored."""
    s = FletXService(name="MyService", auto_start=False)
    assert s.name == "MyService"


def test_service_dispose_idempotent():
    """Calling dispose twice does not raise."""
    s = FletXService()
    s.dispose()
    s.dispose()
    assert s._disposed


def test_service_set_data_after_dispose_raises():
    """set_data raises RuntimeError after dispose."""
    s = FletXService()
    s.dispose()
    try:
        s.set_data("key", "value")
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass


def test_service_set_error_after_dispose_raises():
    """set_error raises RuntimeError after dispose."""
    s = FletXService()
    s.dispose()
    try:
        s.set_error(ValueError("oops"))
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass


def test_service_start_already_started():
    """start() on a non-IDLE service is a no-op (logged warning)."""
    s = FletXService()  # auto-starts to READY
    s.start()  # should not raise or change state
    assert s.state == ServiceState.READY


def test_service_start_after_dispose_raises():
    """start() after dispose raises RuntimeError."""
    s = FletXService()
    s.dispose()
    try:
        s.start()
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass


def test_service_str():
    """__str__ includes name and state."""
    s = FletXService(name="TestSvc", auto_start=False)
    text = str(s)
    assert "TestSvc" in text
    assert "IDLE" in text or "idle" in text


def test_service_repr():
    """__repr__ includes name, state and created_at."""
    s = FletXService(name="TestSvc", auto_start=False)
    text = repr(s)
    assert "TestSvc" in text
    assert "created_at" in text


def test_service_http_client_property():
    """http_client property returns the injected client."""
    s = FletXService(auto_start=False, http_client=None)
    assert s.http_client is None


def test_service_data_returns_copy():
    """data property returns a copy, not the original dict."""
    s = FletXService()
    s.set_data("k", "v")
    d = s.data
    d["k"] = "modified"
    assert s.get_data("k") == "v"  # original unchanged


def test_service_is_properties():
    """is_ready, is_loading, has_error work correctly."""
    s = FletXService(auto_start=False)
    assert not s.is_ready
    assert not s.is_loading
    assert not s.has_error
    s.start()
    assert s.is_ready


async def test_service_start_async():
    """Async start transitions to READY."""
    import asyncio
    s = FletXService(auto_start=False)
    await s.start_async()
    assert s.state == ServiceState.READY

