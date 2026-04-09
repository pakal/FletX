"""
Page Transition Management

This module defines various transition types and logic for animating
UI changes when navigating between routes in a Flet app.
"""

import asyncio
import enum
import flet as ft
from typing import List, Optional, Dict, Any, Callable

from fletx.utils import get_logger, ui_friendly_sleep


####
##      TRANSITION TYPE
#####
class TransitionType(enum.Enum):
    """Supported transition types."""

    NONE = "none"
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    SLIDE_FADE_LEFT = "slide_fade_left"
    SLIDE_FADE_RIGHT = "slide_fade_right"
    SLIDE_FADE_UP = "slide_fade_up"
    SLIDE_FADE_DOWN = "slide_fade_down"
    FADE_THROUGH = "fade_through"
    SCALE_FADE = "scale_fade"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    FLIP_HORIZONTAL = "flip_horizontal"
    FLIP_VERTICAL = "flip_vertical"
    ROTATE = "rotate"
    PUSH_LEFT = "push_left"
    PUSH_RIGHT = "push_right"
    PUSH_UP = "push_up"
    PUSH_DOWN = "push_down"
    SCALE = "scale"
    CUSTOM = "custom"


####
##      TRANSITION DIRECTION
#####
class TransitionDirection(enum.Enum):
    """Direction for directional transitions."""

    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


####
##      EASING FUNCTION CHOICES
#####
class EasingFunction(enum.Enum):
    """Easing functions for smooth animations."""

    LINEAR = "linear"
    EASE_IN = "easeIn"
    EASE_OUT = "easeOut"
    EASE_IN_OUT = "easeInOut"
    BOUNCE_IN = "bounceIn"
    BOUNCE_OUT = "bounceOut"
    ELASTIC_IN = "elasticIn"
    ELASTIC_OUT = "elasticOut"
    CUBIC_BEZIER = "cubicBezier"


####
##      ROUTE TRANSITION
#####
class RouteTransition:
    """
    Route transition configuration and execution.
    
    Handles page transitions with various animation types, durations,
    and easing functions for smooth navigation experiences.
    """
    
    def __init__(
        self,
        transition_type: TransitionType = TransitionType.FADE,
        duration: int = 300,
        easing: EasingFunction = EasingFunction.EASE_IN_OUT,
        direction: Optional[TransitionDirection] = None,
        custom_transition: Optional[Callable] = None,
        reverse_on_back: bool = True,
        **kwargs
    ):
        """
        Initialize route transition.
        
        Args:
            transition_type: Type of transition animation
            duration: Duration in milliseconds
            easing: Easing function for smooth animation
            direction: Direction for directional transitions
            custom_transition: Custom transition function
            reverse_on_back: Reverse transition when going back
            **kwargs: Additional transition parameters
        """
        self.type = transition_type
        self.duration = duration
        self.easing = easing
        self.direction = direction
        self.custom = custom_transition
        self.reverse_on_back = reverse_on_back
        self.params = kwargs
        self._logger = get_logger('FletX.RouteTransition')
        self._animation_complete = False
        self._current_animation = None
    
    def _get_animation_curve(self) -> str:
        """Convert EasingFunction to Flet animation curve."""

        return self.easing.value
    
    def _create_animation(self, duration: Optional[int] = None) -> ft.Animation:
        """Create Flet animation object with proper configuration."""

        return ft.Animation(
            duration = duration or self.duration,
            curve = self._get_animation_curve()
        )
    
    # @worker_task(priority=Priority.CRITICAL)
    async def apply(
        self, 
        page: ft.Page, 
        new_controls: List[ft.Control],
        old_controls: List[ft.Control] = None,
        is_back_navigation: bool = False
    ) -> List[ft.Control]:
        """
        Apply transition to controls.
        
        Args:
            page: Flet page object
            new_controls: New controls to transition in
            old_controls: Old controls to transition out
            is_back_navigation: Whether this is back navigation
            
        Returns:
            List of controls after transition
        """
        try:
            if self.type == TransitionType.NONE:
                return new_controls
            
            # Determine actual transition type (reverse if back navigation)
            actual_type = self._get_actual_transition_type(is_back_navigation)
            
            # Apply the transition
            if actual_type == TransitionType.FADE:
                return await self._apply_fade(page, new_controls, old_controls)
            
            # Slides
            elif actual_type in [
                TransitionType.SLIDE_LEFT, TransitionType.SLIDE_RIGHT, 
                TransitionType.SLIDE_UP, TransitionType.SLIDE_DOWN
            ]:
                return await self._apply_slide(page, new_controls, old_controls, actual_type)
            
            # Zoom
            elif actual_type in [TransitionType.ZOOM_IN, TransitionType.ZOOM_OUT]:
                return await self._apply_zoom(page, new_controls, old_controls, actual_type)
            
            # Composite: Slide + Fade
            elif actual_type in [
                TransitionType.SLIDE_FADE_LEFT,
                TransitionType.SLIDE_FADE_RIGHT,
                TransitionType.SLIDE_FADE_UP,
                TransitionType.SLIDE_FADE_DOWN
            ]:
                return await self._apply_slide_fade(page, new_controls, old_controls, actual_type)

            # Composite: Fade Through (Material-like)
            elif actual_type == TransitionType.FADE_THROUGH:
                return await self._apply_fade_through(page, new_controls, old_controls)

            # Composite: Scale + Fade
            elif actual_type == TransitionType.SCALE_FADE:
                return await self._apply_scale_fade(page, new_controls, old_controls)

            # Pushes
            elif actual_type in [
                TransitionType.PUSH_LEFT, TransitionType.PUSH_RIGHT,
                TransitionType.PUSH_UP, TransitionType.PUSH_DOWN
            ]:
                return await self._apply_push(page, new_controls, old_controls, actual_type)
            
            # Scale
            elif actual_type == TransitionType.SCALE:
                return await self._apply_scale(page, new_controls, old_controls)
            
            # Flip
            elif actual_type in [TransitionType.FLIP_HORIZONTAL, TransitionType.FLIP_VERTICAL]:
                return await self._apply_flip(page, new_controls, old_controls, actual_type)
            
            # Rotate 
            elif actual_type == TransitionType.ROTATE:
                return await self._apply_rotate(page, new_controls, old_controls)
            
            # Custom Transition
            elif actual_type == TransitionType.CUSTOM and self.custom:
                return await self._apply_custom(page, new_controls, old_controls)
            
            else:
                self._logger.warning(f"Unsupported transition type: {actual_type}")
                return new_controls
                
        except Exception as e:
            self._logger.error(f"Transition failed: {e}")
            return new_controls
    
    def _get_actual_transition_type(self, is_back_navigation: bool) -> TransitionType:
        """Get the actual transition type, considering back navigation."""

        if not is_back_navigation or not self.reverse_on_back:
            return self.type
        
        # Reverse transitions for back navigation
        reverse_map = {
            TransitionType.SLIDE_LEFT: TransitionType.SLIDE_RIGHT,
            TransitionType.SLIDE_RIGHT: TransitionType.SLIDE_LEFT,
            TransitionType.SLIDE_UP: TransitionType.SLIDE_DOWN,
            TransitionType.SLIDE_DOWN: TransitionType.SLIDE_UP,
            TransitionType.SLIDE_FADE_LEFT: TransitionType.SLIDE_FADE_RIGHT,
            TransitionType.SLIDE_FADE_RIGHT: TransitionType.SLIDE_FADE_LEFT,
            TransitionType.SLIDE_FADE_UP: TransitionType.SLIDE_FADE_DOWN,
            TransitionType.SLIDE_FADE_DOWN: TransitionType.SLIDE_FADE_UP,
            TransitionType.ZOOM_IN: TransitionType.ZOOM_OUT,
            TransitionType.ZOOM_OUT: TransitionType.ZOOM_IN,
            TransitionType.PUSH_LEFT: TransitionType.PUSH_RIGHT,
            TransitionType.PUSH_RIGHT: TransitionType.PUSH_LEFT,
            TransitionType.PUSH_UP: TransitionType.PUSH_DOWN,
            TransitionType.PUSH_DOWN: TransitionType.PUSH_UP,
        }
        
        return reverse_map.get(self.type, self.type)
    
    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_fade(
        self, 
        page: ft.Page, 
        new_controls: List[ft.Control],
        old_controls: List[ft.Control] = None
    ) -> List[ft.Control]:
        """Apply fade transition using Flet's animate_opacity."""

        # Create animation complete event
        # animation_complete = asyncio.Event()

        # Create container for new controls with fade animation
        new_container = ft.Container(
            content = ft.Column(new_controls, tight=True, expand=True),
            opacity = 0,
            animate_opacity = self._create_animation(),
            expand = True
        )
        
        if old_controls:
            # Create container for old controls
            old_container = ft.Container(
                content = ft.Column(old_controls, tight=True, expand=True),
                opacity = 1,
                animate_opacity = self._create_animation(self.duration // 2),
                expand = True
            )
            
            # Use Stack to overlay containers
            stack = ft.Stack([old_container, new_container], expand=True)
            page.clean()
            page.add(stack)
            page.update()
            
            # Start fade out of old content
            await asyncio.sleep(0.01)
            old_container.opacity = 0
            page.update()
            
            # Wait for half duration, then fade in new content
            # await ui_friendly_sleep((self.duration // 2) / 1000, page)
            await asyncio.sleep((self.duration // 2) / 1000)
            new_container.opacity = 1
            page.update()
            
            # Wait for animation to complete
            await asyncio.sleep((self.duration // 2) / 1000)
            # await ui_friendly_sleep((self.duration // 2) / 1000, page)
        else:
            # Just fade in new content
            page.clean()
            page.add(new_container)
            page.update()
            
            await asyncio.sleep(0.01)
            new_container.opacity = 1
            page.update()
            await asyncio.sleep(self.duration / 1000)

        # await animation_complete.wait()
        
        # Replace with final controls
        page.clean()
        page.add(*new_controls)
        page.update()
        
        return new_controls
    
    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_slide_fade(
        self,
        page: ft.Page,
        new_controls: List[ft.Control],
        old_controls: List[ft.Control],
        slide_fade_type: TransitionType
    ) -> List[ft.Control]:
        """Apply slide + fade transition using offset and opacity."""

        direction_map = {
            TransitionType.SLIDE_FADE_LEFT: (ft.Offset(1, 0)),
            TransitionType.SLIDE_FADE_RIGHT: (ft.Offset(-1, 0)),
            TransitionType.SLIDE_FADE_UP: (ft.Offset(0, 1)),
            TransitionType.SLIDE_FADE_DOWN: (ft.Offset(0, -1)),
        }

        start_offset = direction_map[slide_fade_type]

        new_container = ft.Container(
            content = ft.Column(new_controls, tight=True, expand=True),
            offset = start_offset,
            animate_offset = self._create_animation(),
            opacity = 0,
            animate_opacity = self._create_animation(),
            expand = True
        )

        if old_controls:
            old_container = ft.Container(
                content = ft.Column(old_controls, tight=True, expand=True),
                offset = ft.Offset(0, 0),
                animate_offset = self._create_animation(),
                opacity = 1,
                animate_opacity = self._create_animation(),
                expand = True
            )

            stack = ft.Stack([old_container, new_container], expand=True)
            page.clean()
            page.add(stack)
            page.update()

            await asyncio.sleep(0.01)
            old_container.opacity = 0
            new_container.offset = ft.Offset(0, 0)
            new_container.opacity = 1
            page.update()
            await asyncio.sleep(self.duration / 1000)
        else:
            page.clean()
            page.add(new_container)
            page.update()

            await asyncio.sleep(0.01)
            new_container.offset = ft.Offset(0, 0)
            new_container.opacity = 1
            page.update()
            await asyncio.sleep(self.duration / 1000)

        page.clean()
        page.add(*new_controls)
        page.update()
        return new_controls

    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_fade_through(
        self,
        page: ft.Page,
        new_controls: List[ft.Control],
        old_controls: List[ft.Control]
    ) -> List[ft.Control]:
        """Apply Material fade-through: old fades out, new fades in with slight scale."""

        mid_scale = 0.92

        new_container = ft.Container(
            content = ft.Column(new_controls, tight=True, expand=True),
            opacity = 0,
            animate_opacity = self._create_animation(),
            scale = ft.Scale(mid_scale),
            animate_scale = self._create_animation(),
            expand = True
        )

        if old_controls:
            old_container = ft.Container(
                content = ft.Column(old_controls, tight=True, expand=True),
                opacity = 1,
                animate_opacity = self._create_animation(self.duration // 2),
                expand = True
            )
            stack = ft.Stack([old_container, new_container], expand=True)
            page.clean()
            page.add(stack)
            page.update()

            await asyncio.sleep(0.01)
            old_container.opacity = 0
            page.update()
            await asyncio.sleep((self.duration // 2) / 1000)

            new_container.opacity = 1
            new_container.scale = ft.Scale(1)
            page.update()
            await asyncio.sleep((self.duration // 2) / 1000)
        else:
            page.clean()
            page.add(new_container)
            page.update()

            await asyncio.sleep(0.01)
            new_container.opacity = 1
            new_container.scale = ft.Scale(1)
            page.update()
            await asyncio.sleep(self.duration / 1000)

        page.clean()
        page.add(*new_controls)
        page.update()
        return new_controls

    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_scale_fade(
        self,
        page: ft.Page,
        new_controls: List[ft.Control],
        old_controls: List[ft.Control]
    ) -> List[ft.Control]:
        """Apply scale + fade in for new content while old fades out."""

        new_container = ft.Container(
            content = ft.Column(new_controls, tight=True, expand=True),
            opacity = 0,
            animate_opacity = self._create_animation(),
            scale = ft.Scale(0.9),
            animate_scale = self._create_animation(),
            expand = True
        )

        if old_controls:
            old_container = ft.Container(
                content = ft.Column(old_controls, tight=True, expand=True),
                opacity = 1,
                animate_opacity = self._create_animation(),
                expand = True
            )
            stack = ft.Stack([old_container, new_container], expand=True)
            page.clean()
            page.add(stack)
            page.update()

            await asyncio.sleep(0.01)
            old_container.opacity = 0
            new_container.opacity = 1
            new_container.scale = ft.Scale(1)
            page.update()
            await asyncio.sleep(self.duration / 1000)
        else:
            page.clean()
            page.add(new_container)
            page.update()
            await asyncio.sleep(0.01)
            new_container.opacity = 1
            new_container.scale = ft.Scale(1)
            page.update()
            await asyncio.sleep(self.duration / 1000)

        page.clean()
        page.add(*new_controls)
        page.update()
        return new_controls

    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_slide(
        self, 
        page: ft.Page, 
        new_controls: List[ft.Control],
        old_controls: List[ft.Control],
        slide_type: TransitionType
    ) -> List[ft.Control]:
        """Apply slide transition using Flet's animate_offset."""

        # Determine slide direction offsets
        direction_map = {
            TransitionType.SLIDE_LEFT: (ft.Offset(1, 0), ft.Offset(-1, 0)),
            TransitionType.SLIDE_RIGHT: (ft.Offset(-1, 0), ft.Offset(1, 0)),
            TransitionType.SLIDE_UP: (ft.Offset(0, 1), ft.Offset(0, -1)),
            TransitionType.SLIDE_DOWN: (ft.Offset(0, -1), ft.Offset(0, 1))
        }
        
        new_start_offset, old_end_offset = direction_map[slide_type]
        
        # Create animated containers
        new_container = ft.Container(
            content = ft.Column(new_controls, tight=True, expand=True),
            offset = new_start_offset,
            animate_offset = self._create_animation(),
            expand = True
        )
        
        if old_controls:
            old_container = ft.Container(
                content = ft.Column(old_controls, tight=True, expand=True),
                offset = ft.Offset(0, 0),
                animate_offset = self._create_animation(),
                expand = True
            )
            
            # Place both containers in a stack
            stack = ft.Stack([old_container, new_container], expand=True)
            page.clean()
            page.add(stack)
            page.update()
            
            # Start slide animation
            await asyncio.sleep(0.01)
            old_container.offset = old_end_offset
            new_container.offset = ft.Offset(0, 0)
            page.update()
            
            # Wait for animation to complete
            await asyncio.sleep(self.duration / 1000)
        else:
            page.clean()
            page.add(new_container)
            page.update()
            
            await asyncio.sleep(0.01)
            new_container.offset = ft.Offset(0, 0)
            page.update()
            await asyncio.sleep(self.duration / 1000)
        
        # Replace with final controls
        page.clean()
        page.add(*new_controls)
        page.update()
        
        return new_controls
    
    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_zoom(
        self, 
        page: ft.Page, 
        new_controls: List[ft.Control],
        old_controls: List[ft.Control],
        zoom_type: TransitionType
    ) -> List[ft.Control]:
        """Apply zoom transition using Flet's animate_scale."""

        initial_scale = 0.0 if zoom_type == TransitionType.ZOOM_IN else 1.5
        
        # Create animated container with scale
        new_container = ft.Container(
            content = ft.Column(new_controls, tight=True, expand=True),
            scale = ft.Scale(initial_scale),
            animate_scale = self._create_animation(),
            expand = True
        )
        
        if old_controls:
            # Create old container with fade out
            old_container = ft.Container(
                content = ft.Column(old_controls, tight=True, expand=True),
                opacity = 1,
                animate_opacity = self._create_animation(self.duration // 2),
                expand = True
            )
            
            stack = ft.Stack([old_container, new_container], expand=True)
            page.clean()
            page.add(stack)
            page.update()
            
            # Start animations
            await asyncio.sleep(0.01)
            old_container.opacity = 0
            new_container.scale = ft.Scale(1.0)
            page.update()
        else:
            page.clean()
            page.add(new_container)
            page.update()
            
            # Start zoom animation
            # await asyncio.sleep(0.01)
            new_container.scale = ft.Scale(1.0)
            page.update()
        
        # Wait for animation
        await asyncio.sleep(self.duration / 1000)
        
        # Replace with final controls
        page.clean()
        page.add(*new_controls)
        page.update()
        
        return new_controls
    
    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_scale(
        self, 
        page: ft.Page, 
        new_controls: List[ft.Control],
        old_controls: List[ft.Control]
    ) -> List[ft.Control]:
        """Apply scale transition (similar to zoom but with different behavior)."""
        
        return await self._apply_zoom(
            page, 
            new_controls, 
            old_controls, 
            TransitionType.ZOOM_IN
        )
    
    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_rotate(
        self, 
        page: ft.Page, 
        new_controls: List[ft.Control],
        old_controls: List[ft.Control]
    ) -> List[ft.Control]:
        """Apply rotation transition using Flet's animate_rotation."""
        
        from math import pi
        
        # Create animated container with rotation
        new_container = ft.Container(
            content = ft.Column(new_controls, tight=True, expand=True),
            rotate = ft.Rotate(pi/2, alignment=ft.alignment.center),
            animate_rotation = self._create_animation(),
            opacity = 0,
            animate_opacity = self._create_animation(self.duration // 2),
            expand = True
        )
        
        if old_controls:
            old_container = ft.Container(
                content = ft.Column(old_controls, tight=True, expand=True),
                rotate = ft.Rotate(0, alignment=ft.alignment.center),
                animate_rotation = self._create_animation(),
                opacity = 1,
                animate_opacity = self._create_animation(self.duration // 2),
                expand = True
            )
            
            stack = ft.Stack([old_container, new_container], expand=True)
            page.clean()
            page.add(stack)
            page.update()
            
            # Start rotation and fade
            await asyncio.sleep(0.01)
            old_container.rotate = ft.Rotate(-pi/2, alignment=ft.alignment.center)
            old_container.opacity = 0
            new_container.rotate = ft.Rotate(0, alignment=ft.alignment.center)
            new_container.opacity = 1
            page.update()
        else:
            page.clean()
            page.add(new_container)
            page.update()
            
            await asyncio.sleep(0.01)
            new_container.rotate = ft.Rotate(0, alignment=ft.alignment.center)
            new_container.opacity = 1
            page.update()
        
        # Wait for animation
        await asyncio.sleep(self.duration / 1000)
        
        # Replace with final controls
        page.clean()
        page.add(*new_controls)
        page.update()
        
        return new_controls
    
    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_flip(
        self, 
        page: ft.Page, 
        new_controls: List[ft.Control],
        old_controls: List[ft.Control],
        flip_type: TransitionType
    ) -> List[ft.Control]:
        """Apply flip transition using scale animation to simulate 3D flip."""
        
        # Use scale to simulate flip effect
        if flip_type == TransitionType.FLIP_HORIZONTAL:
            # Horizontal flip uses X-axis scale
            mid_scale = ft.Scale(scale_x=0, scale_y=1)
        else:
            # Vertical flip uses Y-axis scale
            mid_scale = ft.Scale(scale_x=1, scale_y=0)
        
        if old_controls:
            # First half: scale old content to 0
            old_container = ft.Container(
                content=ft.Column(old_controls, tight=True, expand=True),
                scale=ft.Scale(1),
                animate_scale=self._create_animation(self.duration // 2),
                expand=True
            )
            
            page.clean()
            page.add(old_container)
            page.update()
            
            await asyncio.sleep(0.01)
            old_container.scale = mid_scale
            page.update()
            await asyncio.sleep((self.duration // 2) / 1000)
        
        # Second half: scale new content from 0 to 1
        new_container = ft.Container(
            content=ft.Column(new_controls, tight=True, expand=True),
            scale=mid_scale,
            animate_scale=self._create_animation(self.duration // 2),
            expand=True
        )
        
        page.clean()
        page.add(new_container)
        page.update()
        
        await asyncio.sleep(0.01)
        new_container.scale = ft.Scale(1)
        page.update()
        await asyncio.sleep((self.duration // 2) / 1000)
        
        # Replace with final controls
        page.clean()
        page.add(*new_controls)
        page.update()
        
        return new_controls
    
    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_push(
        self, 
        page: ft.Page, 
        new_controls: List[ft.Control],
        old_controls: List[ft.Control],
        push_type: TransitionType
    ) -> List[ft.Control]:
        """Apply push transition (similar to slide but both move together)."""
        
        # Push is similar to slide but both containers move
        return await self._apply_slide(
            page, new_controls, old_controls, 
            self._push_to_slide_type(push_type)
        )
    
    def _push_to_slide_type(self, push_type: TransitionType) -> TransitionType:
        """Convert push type to equivalent slide type."""
        push_to_slide = {
            TransitionType.PUSH_LEFT: TransitionType.SLIDE_LEFT,
            TransitionType.PUSH_RIGHT: TransitionType.SLIDE_RIGHT,
            TransitionType.PUSH_UP: TransitionType.SLIDE_UP,
            TransitionType.PUSH_DOWN: TransitionType.SLIDE_DOWN,
        }
        return push_to_slide.get(push_type, TransitionType.SLIDE_LEFT)
    
    # @worker_task(priority=Priority.CRITICAL)
    async def _apply_custom(
        self, 
        page: ft.Page, 
        new_controls: List[ft.Control],
        old_controls: List[ft.Control]
    ) -> List[ft.Control]:
        """Apply custom transition function."""
        
        if self.custom:
            try:
                return await self.custom(page, new_controls, old_controls, self.duration)
            except Exception as e:
                self._logger.error(f"Custom transition failed: {e}")
        
        # Fallback to fade if custom fails
        return await self._apply_fade(page, new_controls, old_controls)
    
    def set_animation_end_callback(self, callback: Callable):
        """Set callback to be called when animation ends."""

        self._animation_end_callback = callback
    
    # @worker_task(priority=Priority.CRITICAL)
    async def wait_for_completion(self):
        """Wait for the current animation to complete."""

        await asyncio.sleep(self.duration / 1000)
        self._animation_complete = True


# Utility functions for creating common transitions
def create_slide_transition(
    direction: TransitionDirection, 
    duration: int = 300
) -> RouteTransition:
    """Create a slide transition in the specified direction."""

    transition_map = {
        TransitionDirection.LEFT: TransitionType.SLIDE_LEFT,
        TransitionDirection.RIGHT: TransitionType.SLIDE_RIGHT,
        TransitionDirection.UP: TransitionType.SLIDE_UP,
        TransitionDirection.DOWN: TransitionType.SLIDE_DOWN,
    }
    return RouteTransition(transition_map[direction], duration)

def create_fade_transition(duration: int = 300) -> RouteTransition:
    """Create a simple fade transition."""

    return RouteTransition(TransitionType.FADE, duration)

def create_zoom_transition(zoom_in: bool = True, duration: int = 300) -> RouteTransition:
    """Create a zoom transition."""

    transition_type = TransitionType.ZOOM_IN if zoom_in else TransitionType.ZOOM_OUT
    return RouteTransition(transition_type, duration)

def create_slide_fade_transition(direction: TransitionDirection, duration: int = 300) -> RouteTransition:
    """Create a slide+fade transition in the specified direction."""

    transition_map = {
        TransitionDirection.LEFT: TransitionType.SLIDE_FADE_LEFT,
        TransitionDirection.RIGHT: TransitionType.SLIDE_FADE_RIGHT,
        TransitionDirection.UP: TransitionType.SLIDE_FADE_UP,
        TransitionDirection.DOWN: TransitionType.SLIDE_FADE_DOWN,
    }
    return RouteTransition(transition_map[direction], duration)

def create_fade_through_transition(duration: int = 300) -> RouteTransition:
    """Create a fade-through transition."""

    return RouteTransition(TransitionType.FADE_THROUGH, duration)

def create_scale_fade_transition(duration: int = 300) -> RouteTransition:
    """Create a scale+fade transition."""

    return RouteTransition(TransitionType.SCALE_FADE, duration)