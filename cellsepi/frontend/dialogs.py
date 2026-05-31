import asyncio
import flet as ft


class ChoiceDialog:
    def __init__(self, page: ft.Page, title: str, text: str, option_1: str, option_2: str = None):
        self.page = page
        self.result = None
        # asyncio.Event manages the pause/resume state of the execution flow
        self.event = asyncio.Event()

        # Build the reusable AlertDialog control template
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(text),
            actions=[
                # ft.TextButton("Cancel", on_click=self._on_cancel),
                ft.FilledButton(option_1, color=ft.Colors.WHITE, bgcolor=ft.Colors.PRIMARY, on_click=self._on_opt_1),
                ft.Button(option_2, on_click=self._on_opt_2) if option_2 else None,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    # Event handlers update choice state and clear the thread block
    async def _on_opt_1(self, e):
        self.result = 0
        await self._close()

    async def _on_opt_2(self, e):
        self.result = 1
        await self._close()

    async def _on_cancel(self, e):
        self.result = "cancel"
        await self._close()

    async def _close(self):
        self.dialog.open = False
        self.page.update()
        self.event.set()  # Unblocks the await statement in show()

    # The primary method to call from your main app flow
    async def show(self) -> str:
        self.result = None
        self.event.clear()

        self.page.overlay.append(self.dialog)
        self.dialog.open = True
        self.page.update()

        # execution halts here until self.event.set() runs
        await self.event.wait()
        return self.result
