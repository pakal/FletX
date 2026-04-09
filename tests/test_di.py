import os
import sys
import types
import importlib.util
import pytest


def _load_di_and_errors():
    # Save original sys.modules state for keys we're about to stub
    _saved_modules = {}
    for key in ('fletx', 'fletx.utils', 'fletx.utils.exceptions'):
        if key in sys.modules:
            _saved_modules[key] = sys.modules[key]

    # Stub minimal 'fletx.utils' and 'fletx.utils.exceptions' to avoid heavy deps
    if 'fletx' not in sys.modules:
        sys.modules['fletx'] = types.ModuleType('fletx')

    utils_mod = types.ModuleType('fletx.utils')
    # Minimal logger stub
    class _Logger:
        def debug(self, *args, **kwargs):
            pass
        def error(self, *args, **kwargs):
            pass
    def get_logger(_name: str):
        return _Logger()
    utils_mod.get_logger = get_logger

    exceptions_mod = types.ModuleType('fletx.utils.exceptions')
    class DependencyNotFoundError(Exception):
        pass
    exceptions_mod.DependencyNotFoundError = DependencyNotFoundError

    sys.modules['fletx.utils'] = utils_mod
    sys.modules['fletx.utils.exceptions'] = exceptions_mod

    # Load fletx/core/di.py directly without importing package __init__
    di_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fletx', 'core', 'di.py')
    spec = importlib.util.spec_from_file_location('fletx_core_di_standalone', di_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    # Patch DI logger attribute to a simple logger to avoid @classmethod @property descriptor issues
    simple_logger = get_logger("test.DI")
    try:
        module.DI._logger = simple_logger
        module.DI.logger = simple_logger  # override descriptor on class
    except Exception:
        pass

    # Restore original sys.modules so other tests can import real modules
    for key in ('fletx', 'fletx.utils', 'fletx.utils.exceptions'):
        if key in _saved_modules:
            sys.modules[key] = _saved_modules[key]
        else:
            sys.modules.pop(key, None)

    return module.DI, DependencyNotFoundError


DI, DependencyNotFoundError = _load_di_and_errors()


class _Disposable:
    def __init__(self):
        self.disposed = False

    def dispose(self):
        self.disposed = True


class _ServiceA:
    def __init__(self, value: int = 1):
        self.value = value


class _ServiceB:
    pass


def teardown_function():
    # Ensure we start from a clean container for every test
    DI.reset()


def test_put_and_find_returns_same_instance():
    service = _ServiceA(42)
    DI.put(service)

    found = DI.find(_ServiceA)
    assert found is service
    assert found.value == 42


def test_put_with_tag_and_find_by_tag():
    default_instance = _ServiceA(1)
    tagged_instance = _ServiceA(2)

    DI.put(default_instance)
    DI.put(tagged_instance, tag="v2")

    assert DI.find(_ServiceA, tag="v2") is tagged_instance
    # When tag provided but not found, it should fallback to untagged
    assert DI.find(_ServiceA, tag="v1") is default_instance


def test_get_raises_dependency_not_found_when_missing():
    with pytest.raises(DependencyNotFoundError) as exc:
        DI.get(_ServiceB)

    # Error message contains computed key
    expected_key = f"{_ServiceB.__module__}.{_ServiceB.__name__}"
    assert expected_key in str(exc.value)


def test_delete_removes_instance_and_calls_dispose_when_present():
    disposable = _Disposable()
    DI.put(disposable)

    removed = DI.delete(_Disposable)
    assert removed is True
    assert disposable.disposed is True
    # Ensure it's gone
    assert DI.find(_Disposable) is None


def test_delete_returns_false_when_not_found():
    assert DI.delete(_ServiceB) is False


def test_reset_clears_all_and_disposes_instances():
    a1 = _Disposable()
    a2 = _Disposable()
    DI.put(a1)
    DI.put(a2, tag="t")

    DI.reset()

    # Both should have been disposed and container emptied
    assert a1.disposed is True
    assert a2.disposed is True
    assert DI.find(_Disposable) is None
    assert DI.find(_Disposable, tag="t") is None


def test_list_instances_returns_copy_not_live():
    a = _ServiceA()
    DI.put(a)

    listed = DI.list_instances()
    assert isinstance(listed, dict)
    # Mutate copy should not affect DI internal map
    listed.clear()
    assert DI.find(_ServiceA) is a


def test_tag_key_generation_isolated_paths():
    # Register two different classes; their keys must be different
    DI.put(_ServiceA())
    DI.put(_ServiceB())
    instances = DI.list_instances()
    keys = list(instances.keys())
    assert any(key.endswith("_ServiceA") for key in keys)
    assert any(key.endswith("_ServiceB") for key in keys)


