"""
Shared test utilities for FletX tests.
"""

import sys
import functools


def backup_sys_modules(*module_keys):
    """Decorator that saves relevant sys.modules entries before calling the wrapped
    function and restores them in a finally block, ensuring test isolation.

    Entries which didn't exist at the start of the wrapped function are cleared at the end.

    Usage:
        @backup_sys_modules("fletx", "fletx.utils", "fletx.utils.exceptions")
        def _load_something():
            sys.modules["fletx"] = ...
            # ... load standalone module ...
            return result
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            saved = {k: sys.modules[k] for k in module_keys if k in sys.modules}
            try:
                return func(*args, **kwargs)
            finally:
                for key in module_keys:
                    if key in saved:
                        sys.modules[key] = saved[key]
                    else:
                        sys.modules.pop(key, None)
        return wrapper
    return decorator

