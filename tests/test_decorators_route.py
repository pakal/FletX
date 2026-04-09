"""
Unit tests for fletx.decorators.route module.
Covers: register_router.
"""

from unittest.mock import patch, MagicMock


class TestRegisterRouter:
    """Tests for the register_router decorator."""

    def test_root_module_registers(self):
        """Root module routes are registered via router_config."""
        with patch("fletx.decorators.route.router_config") as mock_config, \
             patch("fletx.decorators.reactive.asyncio.create_task"):
            from fletx.decorators.route import register_router

            class FakeRouter:
                is_root = True

                def __init__(self):
                    pass

            result_cls = register_router(FakeRouter)
            assert result_cls is FakeRouter
            mock_config.add_module_routes.assert_called_once()

    def test_non_root_module_skips(self):
        """Non-root modules do not auto-register."""
        with patch("fletx.decorators.route.router_config") as mock_config, \
             patch("fletx.decorators.reactive.asyncio.create_task"):
            from fletx.decorators.route import register_router

            class FakeRouter:
                is_root = False

                def __init__(self):
                    pass

            register_router(FakeRouter)
            mock_config.add_module_routes.assert_not_called()

