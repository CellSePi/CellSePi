import flet as ft

from frontend.gui import GUI


async def async_main(page: ft.Page):
    page.window.prevent_close = True
    gui = GUI(page)
    page.title = "CellSePi"
    page.window.width = 1440
    page.window.height = 800
    page.window.on_event = lambda e: page.run_task(gui.handle_closing_event, e)
    page.update()
    await page.window.center()
    gui.build()
    page.window.visible = True
    page.update()

def main():
    ft.run(main=async_main, view=ft.AppView.FLET_APP_HIDDEN)


if __name__ == "__main__":
    main()

"""

#Main to start only Expert Mode
import flet as ft
from cellsepi.frontend.main_window.expert_mode.gui_builder import Builder


def main(page: ft.Page):
    expert_builder = Builder(page)
    page.add(expert_builder.builder_page_stack)
    page.update()

ft.run(main)
"""
