import pytest
from fletx.core.controller import FletXController, ControllerState

def test_default_initialization_registers_instance():
    controller = FletXController()
    
    # State should auto-initialize and then transition to READY
    assert controller.state.value == ControllerState.READY

    # It should be in the global instances list
    assert controller in FletXController.get_all_instances()
    
    # Should have an event bus and context
    assert controller.event_bus is not None
    assert controller.context is not None
    assert controller.effects is not None


def test_initialization_with_auto_initialize_false():
    controller = FletXController(auto_initialize=False)
    
    # Should remain CREATED
    assert controller.state.value == ControllerState.CREATED
    
    # After explicit initialize, it transitions to INITIALIZED then READY
    controller.initialize()
    assert controller.state.value == ControllerState.READY


def test_repr_contains_state_and_id():
    controller = FletXController()
    text = repr(controller)
    assert "FletXController" in text
    assert "initialized" in text or "ready" in text
