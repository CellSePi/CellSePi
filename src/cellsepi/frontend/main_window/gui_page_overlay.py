import asyncio
from typing import Any

import flet as ft

class PageOverlay(ft.Stack):
    """
    Overlay which gets placed above the normal page with half transparent background
    and can be dismissed when clicking on the background when modal is False.

    Attributes:
        page: the page of Flet
        content: the content which gets viewed in front of the background
        on_dismiss: callback when the overlay gets dismissed
        modal: Whether this bottom sheet can be dismissed/closed by clicking the area outside of it.
    """

    @property
    def page(self):
        return self._page

    def __init__(self,page: ft.Page,content: ft.Stack = None,on_dismiss = None,modal = False):
        super().__init__()
        self.page =page
        self.controls = []
        self._content: ft.Stack | None = None
        self.on_dismiss: Any | None = on_dismiss
        self.modal = modal
        self._background = self.create_background()
        self.content = content

        self.container = ft.Container(content=self,
                                      animate_opacity=ft.Animation(duration=300,
                                                                   curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
                                      animate=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT), visible=False,opacity=0.0)
        page.overlay.append(self.container)

    @property
    def content(self) -> ft.Stack | None:
        return self._content

    @content.setter
    def content(self, new_content: ft.Stack):
        if new_content is not None:
            if self._content is not None:
                self.controls.remove(self._content)
            self.controls.append(new_content)
            self._content = new_content

    def open(self):
        self.page.run_task(self._open)

    def close(self):
        self.page.run_task(self._close)

    async def _open(self):
        self.container.visible = True
        self.page.update()
        await asyncio.sleep(0.14)
        self.container.opacity = 1.0
        self.container.update()

    async def _close(self):
        self.container.opacity = 0.0
        self.container.update()
        await asyncio.sleep(0.14)
        self.container.visible = False
        self.page.update()

    def create_background(self):
        def bg_click(e):
            if not self.modal:
                self.close()
                if self.on_dismiss is not None:
                    self.on_dismiss(e)

        background = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.BASIC,
            on_tap=bg_click,
            content=ft.Container(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            )
        )
        self.controls.append(background)
        return background

    @page.setter
    def page(self, value):
        self._page = value

