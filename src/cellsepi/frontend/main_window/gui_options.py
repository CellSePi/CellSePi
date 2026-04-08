import flet as ft

from cellsepi.frontend.main_window.gui_colors import ColorSelection, ColorOpacity


class Options(ft.Container):
    """
    Class which handles the options in the right up corner in the GUI.
    """
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.dark_light_text = ft.Text("Light Theme")
        self.dark_light_icon = ft.IconButton(
            icon=ft.Icons.BRIGHTNESS_2_OUTLINED,
            icon_color=None,
            on_click=self.theme_changed,
        )
        self.color_selection = ColorSelection(gui)
        self.color_opacity= ColorOpacity(gui)
        self.menu_button = ft.PopupMenuButton(
            items=self.create_appbar_items(),
            content=ft.Icon(ft.Icons.MENU),
            tooltip="Options",
            on_open=self.check_current_theme,
        )
        self.content = self.menu_button
        self.padding = 10
        self.alignment = ft.Alignment.TOP_RIGHT

    async def theme_changed(self, e):
        """
        Changes the theme of the page to the opposite of the current selected theme.
        """
        if self.gui.page.theme_mode == ft.ThemeMode.LIGHT:
            self.gui.page.theme_mode = ft.ThemeMode.DARK
            self.dark_light_text.value = "Dark Theme"
            self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_HIGH
        else:
            self.gui.page.theme_mode = ft.ThemeMode.LIGHT
            self.dark_light_text.value = "Light Theme"
            self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_2_OUTLINED
        self.gui.page.update()

    def check_current_theme(self,e):
        """
        Checks what the current theme is.
        """
        if self.gui.page.theme_mode == ft.ThemeMode.SYSTEM:
            if self.gui.page.platform_brightness == ft.Brightness.LIGHT:
                self.dark_light_text.value = "Light Theme"
                self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_2_OUTLINED
            else:
                self.dark_light_text.value = "Dark Theme"
                self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_HIGH
        else:
            if self.gui.page.theme_mode == ft.ThemeMode.LIGHT:
                self.dark_light_text.value = "Light Theme"
                self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_2_OUTLINED
            else:
                self.dark_light_text.value = "Dark Theme"
                self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_HIGH
        self.gui.page.update()

    def create_appbar_items(self):
        """
        Creates the appbar items that will be displayed in the GUI when the option button is clicked.
        """
        return [
            ft.PopupMenuItem(
                content=ft.Row([self.dark_light_icon, self.dark_light_text]),
                on_click=self.theme_changed,
            ),
            ft.PopupMenuItem(
                content=ft.Row([self.color_selection.color_icon_mask, ft.Text("Mask Color")]),
                on_click=self.color_selection.open_color_picker_mask,
            ),
            ft.PopupMenuItem(
                content=ft.Row([self.color_selection.color_icon_outline, ft.Text("Outline Color")]),
                on_click=self.color_selection.open_color_picker_outline,
            ),
            ft.PopupMenuItem(
                content=ft.Container(
                    content=ft.Column(
                [
                            ft.Container(
                                content=self.color_opacity.text,
                                padding=ft.padding.only(bottom=-10)
                            ),
                            ft.Container(
                                content=self.color_opacity.slider,
                                padding=ft.padding.only(bottom=-8)
                            ),
                        ],
                        spacing=0,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    padding=ft.padding.all(0),
                ),
            )
        ]

