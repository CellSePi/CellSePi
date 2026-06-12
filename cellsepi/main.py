import flet as ft

from frontend.gui import GUI


def async_main(page: ft.Page):
    gui = GUI(page)
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
