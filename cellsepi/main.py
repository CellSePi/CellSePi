import flet as ft
from frontend.gui import GUI


def async_main(page: ft.Page):
    def window_event(e: ft.WindowEvent):
        if e.type == ft.WindowEventType.CLOSE:
            page.show_dialog(ft.Text("Are you sure you want to exit?"),
                on_confirm=lambda _: page.window.close())
            page.update()

    page.window.prevent_close = True
    page.window.on_event = window_event


    # page.title = "CellSePi"
    # page.update()
    # # page.window.icon = "assets/icon.png"
    # page.add(
    #     ft.MenuBar(
    #         expand=True,
    #         controls=[
    #             ft.SubmenuButton(
    #                 content=ft.Text("File"),
    #                 controls=[
    #                     ft.MenuItemButton(content=ft.Text("New File")),
    #                     ft.MenuItemButton(content=ft.Text("Save")),
    #                 ]
    #             ),
    #         ]
    #     )
    # )

    gui = GUI(page)
    gui.build()


def main():
    ft.run(main=async_main, view=ft.AppView.FLET_APP)


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
