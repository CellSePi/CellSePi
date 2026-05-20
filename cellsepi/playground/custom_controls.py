import flet as ft

from frontend.gui_fluorescence import FluorescenceReadoutControl


@ft.control
class SplitButton(ft.Row):

    def __init__(self, button_1, button_2, *args, **kwargs):
        self.button_1 = button_1
        self.button_2 = button_2

        # self.controls = []
        super().__init__(
            controls=[
                self.button_1,
                self.button_2
            ],
            *args, **kwargs,
        )


def main(page: ft.Page):
    page.title = "Flet Split Button Demo"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT

    try:
        global_radius = page.theme.button_theme.shape.radius
    except AttributeError:
        # Fallback to standard Flet Material 3 radius if theme isn't explicitly set
        global_radius = 20
        print("Using standard Flet Material 3 radius")

    button_1 = ft.TextButton(
        "Export",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(
                radius=ft.BorderRadius.horizontal(left=global_radius, right=0)
            ),
        ),
    )
    button_2 = ft.SubmenuButton(
        content=ft.Text("Choose text style"),
        key="smbutton",
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(
                radius=ft.BorderRadius.horizontal(left=0, right=global_radius)
            ),
        ),
        # expand=True,
        menu_style=ft.MenuStyle(
            alignment=ft.Alignment.BOTTOM_LEFT, side=ft.BorderSide(1)
        ),
        controls=[
            ft.MenuItemButton(
                content=ft.Text("Underlined"),
                on_click=lambda e: print(f"{e.control.content.value}.on_click"),
            ),
        ],
    )
    split_button = SplitButton(button_1=button_1, button_2=button_2)
    fluorescene_readout_control = FluorescenceReadoutControl()

    page.add(
        ft.Text("JetBrains Style Split Button", size=20, weight=ft.FontWeight.BOLD),
        ft.Container(height=20),
        split_button,
        fluorescene_readout_control,
    )


if __name__ == '__main__':
    ft.app(target=main)
