"""
Unit tests for fletx.decorators.effects module.
Covers: use_effect.
"""

from unittest.mock import patch, Mock, MagicMock


class TestUseEffect:
    """Tests for the use_effect function."""

    def test_registers_effect_with_manager(self):
        """use_effect calls manager.useEffect with correct args."""
        mock_manager = Mock()
        mock_manager.useEffect = Mock()

        with patch("fletx.decorators.effects.FletX") as MockFletX:
            MockFletX.find.return_value = mock_manager

            from fletx.decorators.effects import use_effect

            def my_effect():
                pass

            use_effect(my_effect, dependencies=["dep1"])

            mock_manager.useEffect.assert_called_once()
            args = mock_manager.useEffect.call_args
            assert args[0][0] is my_effect
            assert args[0][1] == ["dep1"]
            # key should be generated from line number
            assert args[0][2].startswith("useEffect_")

    def test_registers_effect_without_deps(self):
        """use_effect works with default None dependencies."""
        mock_manager = Mock()
        mock_manager.useEffect = Mock()

        with patch("fletx.decorators.effects.FletX") as MockFletX:
            MockFletX.find.return_value = mock_manager

            from fletx.decorators.effects import use_effect

            def my_effect():
                pass

            use_effect(my_effect)

            mock_manager.useEffect.assert_called_once()
            args = mock_manager.useEffect.call_args
            assert args[0][1] is None

