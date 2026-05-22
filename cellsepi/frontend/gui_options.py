import os
import subprocess
import sys

import flet as ft
import torch

from frontend.gui_colors import ColorSelection, ColorOpacity


class Options(ft.Container):
    """
    Class which handles the options in the right up corner in the GUI.
    """

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.dark_light_text = ft.Text("Light Theme")
        self.dark_light_icon = ft.Icon(
            icon=ft.Icons.BRIGHTNESS_2_OUTLINED,
            color=None,
        )
        self.color_selection = ColorSelection(gui)
        self.color_opacity = ColorOpacity(gui)
        self.slider = ft.CupertinoSlidingSegmentedButton(
            selected_index=1 if torch.cuda.is_available() else 0,
            thumb_color=ft.Colors.BLUE_400,
            disabled=True if not torch.cuda.is_available() else False,
            on_change=self.gpu_slider_change,
            padding=ft.padding.symmetric(0, 0),
            controls=[
                ft.Text("CPU"),
                ft.Text("GPU")
            ],
        )
        cuda_compiled = torch.version.cuda is not None
        self.slider_blocker = ft.Container(
            width=80,
            height=30,
            bgcolor=ft.Colors.TRANSPARENT,
            on_click=None,
            visible=False
        )
        if not torch.cuda.is_available():
            self.slider.on_change = None
            self.slider.thumb_color = ft.Colors.GREY_400
            self.slider_blocker.visible = True
            if cuda_compiled:
                self.slider_blocker.tooltip = f"GPU acceleration is unavailable.\n" \
                                              f"Use a CUDA-compatible NVIDIA card for faster segmentation,\n" \
                                              f"and ensure the required drivers are installed."
            else:
                self.slider_blocker.tooltip = f"GPU acceleration is unavailable.\n" \
                                              f"This version of cellsepi is not capable of CUDA."
            for control in self.slider.controls:
                control.color = ft.Colors.GREY_700
        else:
            self.slider.on_change = self.gpu_slider_change
            self.slider.thumb_color = ft.Colors.BLUE_400
            self.slider_blocker.visible = False
            for control in self.slider.controls:
                control.color = None
        self.plugin_folder_icon_button = ft.Icon(
            icon=ft.Icons.FOLDER_OPEN,
        )
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
        if self.gui.page.theme_mode == ft.ThemeMode.LIGHT or (
                self.gui.page.theme_mode == ft.ThemeMode.SYSTEM and self.gui.page.platform_brightness == ft.Brightness.LIGHT):
            self.gui.page.theme_mode = ft.ThemeMode.DARK
            self.dark_light_text.value = "Light Theme"
            self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_HIGH
        else:
            self.gui.page.theme_mode = ft.ThemeMode.LIGHT
            self.dark_light_text.value = "Dark Theme"
            self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_2_OUTLINED
        self.gui.page.update()

    def check_current_theme(self, e):
        """
        Checks what the current theme is.
        """
        if self.gui.page.theme_mode == ft.ThemeMode.SYSTEM:
            if self.gui.page.platform_brightness == ft.Brightness.LIGHT:
                self.dark_light_text.value = "Dark Theme"
                self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_2_OUTLINED
            else:
                self.dark_light_text.value = "Light Theme"
                self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_HIGH
        else:
            if self.gui.page.theme_mode == ft.ThemeMode.LIGHT:
                self.dark_light_text.value = "Dark Theme"
                self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_2_OUTLINED
            else:
                self.dark_light_text.value = "Light Theme"
                self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_HIGH
        self.gui.page.update()

    def create_appbar_items(self):
        """
        Creates the appbar items that will be displayed in the GUI when the option button is clicked.
        """
        return [
            ft.PopupMenuItem(
                content=ft.Row([self.dark_light_icon, self.dark_light_text], alignment=ft.MainAxisAlignment.START),
                on_click=self.theme_changed,
            ),
            ft.PopupMenuItem(
                content=ft.Container(
                    ft.Row([self.plugin_folder_icon_button, ft.Text("Plugins")], alignment=ft.MainAxisAlignment.START)),
                on_click=self.open_plugin_folder
            ),
            ft.PopupMenuItem(
                content=ft.Row([self.color_selection.color_icon_mask, ft.Text("Mask Color")],
                               alignment=ft.MainAxisAlignment.START),
                on_click=self.color_selection.open_color_picker_mask,
            ),
            ft.PopupMenuItem(
                content=ft.Row([self.color_selection.color_icon_outline, ft.Text("Outline Color")],
                               alignment=ft.MainAxisAlignment.START),
                on_click=self.color_selection.open_color_picker_outline,
            ),
            ft.PopupMenuItem(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(
                                content=self.color_opacity.text,
                                padding=ft.Padding.only(bottom=-10)
                            ),
                            ft.Container(
                                content=self.color_opacity.slider,
                                padding=ft.Padding.only(bottom=-8)
                            ),
                        ],
                        spacing=0,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    padding=ft.Padding.all(0),
                ),
            ),
            ft.PopupMenuItem(
                content=ft.Container(ft.Stack([self.slider, self.slider_blocker]), alignment=ft.Alignment.CENTER), ),
        ]

    async def gpu_slider_change(self, e):
        if e.data == 1:
            self.gui.csp.gpu = True
        else:
            self.gui.csp.gpu = False

    async def open_plugin_folder(self, e):
        folder_path = self.gui.csp.plugins_dir

        if os.name == "nt":  # Check if Windows
            os.startfile(folder_path)
        elif os.name == "posix":  # Check if Mac or Linux
            subprocess.run(["open", folder_path] if sys.platform == "darwin" else ["xdg-open", folder_path])
