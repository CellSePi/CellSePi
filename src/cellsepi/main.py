import multiprocessing
import sys
import flet as ft
from cellsepi.frontend.main_window.gui import GUI
from cellsepi.cli import build as flet_build

async def async_main(page: ft.Page):
    gui = GUI(page)
    gui.build()

def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() == "build":
        flet_build()
    else:
        multiprocessing.set_start_method("spawn")
        ft.run(main=async_main, view=ft.AppView.FLET_APP)

if __name__ == "__main__":
    main()


"""
Main to start only Expert Mode
import flet as ft
from cellsepi.frontend.main_window.expert_mode.gui_builder import Builder


def main(page: ft.Page):
    expert_builder = Builder(page)
    page.add(expert_builder.builder_page_stack)
    page.update()

ft.app(main)
"""