import asyncio
import inspect
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
        modal: if True, the overlay is blocking and cannot be dismissed by clicking the background.
    """

    @property
    def page(self):
        return self._page

    def __init__(self, page: ft.Page, content: ft.Control = None, on_dismiss=None, modal=False):
        super().__init__()
        self.page = page
        self.controls = []
        self._content: ft.Control | None = None
        self._content_wrapper: ft.Column | None = None
        self.on_dismiss: Any | None = on_dismiss
        self.modal = modal
        self.expand = True
        self._background = self.create_background()
        self.content = content

        self.container = ft.Container(content=self,
                                      animate_opacity=ft.Animation(duration=300,
                                                                   curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
                                      animate=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
                                      visible=False, opacity=0.0,
                                      expand=True)
        page.overlay.append(self.container)
        page.update()

    @property
    def content(self) -> ft.Control | None:
        return self._content

    @content.setter
    def content(self, new_content: ft.Control | None):
        if new_content is not None:
            if self._content_wrapper is not None and self._content_wrapper in self.controls:
                self.controls.remove(self._content_wrapper)

            self._content_wrapper = ft.Column(
                controls=[
                    ft.Row(
                        controls=[new_content],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )

            self.controls.append(self._content_wrapper)
            self._content = new_content

    def open(self):
        self.page.run_task(self._open)

    def close(self):
        self.page.run_task(self._close)

    async def _open(self):
        self.container.visible = True
        self.container.update()
        await asyncio.sleep(0.14)
        self.container.opacity = 1.0
        self.container.update()

    async def _close(self):
        self.container.opacity = 0.0
        self.container.update()
        await asyncio.sleep(0.14)
        self.container.visible = False
        self.container.update()

    def create_background(self):
        async def bg_click(e):
            if not self.modal:
                self.close()
                if self.on_dismiss is not None:
                    result = self.on_dismiss(e)
                    if inspect.isawaitable(result):
                        await result

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
