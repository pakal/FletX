"""
Unit tests for fletx.core.concurency.event_loop module.
Covers: EventLoopManager singleton, loop property, set_loop, close_loop,
        run_until_complete, run_forever, stop_loop.
"""

import asyncio
import pytest

from fletx.core.concurency.event_loop import EventLoopManager


class TestEventLoopManagerSingleton:
    """Tests for singleton behavior."""

    def test_singleton(self, event_loop_manager):
        mgr2 = EventLoopManager()
        assert mgr2 is event_loop_manager

    def test_reset_singleton(self, event_loop_manager):
        """After resetting _instance, a new instance is created."""
        EventLoopManager._instance = None
        mgr2 = EventLoopManager()
        assert mgr2 is not event_loop_manager


class TestEventLoopManagerLoop:
    """Tests for loop property and lifecycle."""

    def test_loop_creates_new_if_none(self, event_loop_manager):
        assert event_loop_manager._loop is None
        loop = event_loop_manager.loop
        assert loop is not None
        assert isinstance(loop, asyncio.AbstractEventLoop)
        assert not loop.is_closed()

    def test_loop_returns_same_instance(self, event_loop_manager):
        loop1 = event_loop_manager.loop
        loop2 = event_loop_manager.loop
        assert loop1 is loop2

    def test_loop_recreates_if_closed(self, event_loop_manager):
        loop1 = event_loop_manager.loop
        loop1.close()
        loop2 = event_loop_manager.loop
        assert loop2 is not loop1
        assert not loop2.is_closed()


class TestEventLoopManagerSetLoop:
    """Tests for set_loop."""

    def test_set_external_loop(self, event_loop_manager):
        ext_loop = asyncio.new_event_loop()
        try:
            event_loop_manager.set_loop(ext_loop, owner=False)
            assert event_loop_manager._loop is ext_loop
            assert event_loop_manager._loop_owner is False
        finally:
            ext_loop.close()

    def test_set_loop_closes_previous_owned(self, event_loop_manager):
        # First create an owned loop
        loop1 = event_loop_manager.loop  # owned
        assert event_loop_manager._loop_owner is True
        assert not loop1.is_closed()

        # Set a new loop — old one should be closed
        ext_loop = asyncio.new_event_loop()
        try:
            event_loop_manager.set_loop(ext_loop, owner=True)
            assert loop1.is_closed()
            assert event_loop_manager._loop is ext_loop
        finally:
            ext_loop.close()

    def test_set_loop_does_not_close_non_owned(self, event_loop_manager):
        ext1 = asyncio.new_event_loop()
        ext2 = asyncio.new_event_loop()
        try:
            event_loop_manager.set_loop(ext1, owner=False)
            event_loop_manager.set_loop(ext2, owner=False)
            # ext1 should NOT be closed because it wasn't owned
            assert not ext1.is_closed()
        finally:
            ext1.close()
            ext2.close()


class TestEventLoopManagerCloseLoop:
    """Tests for close_loop."""

    def test_close_owned_loop(self, event_loop_manager):
        loop = event_loop_manager.loop
        assert event_loop_manager._loop_owner is True
        event_loop_manager.close_loop()
        assert loop.is_closed()
        assert event_loop_manager._loop is None
        assert event_loop_manager._loop_owner is False

    def test_close_non_owned_loop_noop(self, event_loop_manager):
        ext = asyncio.new_event_loop()
        try:
            event_loop_manager.set_loop(ext, owner=False)
            event_loop_manager.close_loop()
            # Loop should NOT be closed
            assert not ext.is_closed()
        finally:
            ext.close()

    def test_close_when_no_loop(self, event_loop_manager):
        event_loop_manager.close_loop()  # should not raise


class TestEventLoopManagerRunMethods:
    """Tests for run_until_complete and stop_loop."""

    def test_run_until_complete(self, event_loop_manager):
        async def coro():
            return 42

        result = event_loop_manager.run_until_complete(coro())
        assert result == 42

    def test_stop_loop(self, event_loop_manager):
        loop = event_loop_manager.loop
        # Just ensure stop_loop doesn't raise on a non-running loop
        event_loop_manager.stop_loop()

    def test_stop_loop_when_no_loop(self, event_loop_manager):
        event_loop_manager._loop = None
        event_loop_manager.stop_loop()  # should not raise

    def test_stop_loop_when_closed(self, event_loop_manager):
        loop = event_loop_manager.loop
        loop.close()
        event_loop_manager.stop_loop()  # should not raise (loop is closed)

