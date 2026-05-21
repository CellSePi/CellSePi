import flet as ft

from backend.constants import ExportFileType


# fluorescence_button = ft.Button(
#     content="Readout",
#     icon=ft.Icons.FILE_DOWNLOAD,
#     tooltip="Readout fluorescence values",
#     disabled=False,
#     visible=False
# )


@ft.control
class FluorescenceReadoutControl(ft.Container):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FluorescenceReadoutControl, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, *args, **kwargs):
        if self._initialized:
            return

        super().__init__(*args, **kwargs)

        self.button = ft.Button(
            content="Readout",
            icon=ft.Icons.FILE_DOWNLOAD,
            tooltip="Readout fluorescence values",
            disabled=False,
            visible=True
        )

        self.images_and_mask_export_button = ft.Button(
            content="Export Images and Masks",
            icon=ft.Icons.FILE_DOWNLOAD,
            tooltip="Export Images and Masks",
            disabled=False,
            visible=True
        )

        self.slider = ft.CupertinoSlidingSegmentedButton(
            selected_index=0,
            thumb_color=ft.Colors.BLUE_400,
            on_change=lambda e: print(f"selected_index: {list(ExportFileType)[e.data]}"),
            padding=ft.Padding.symmetric(vertical=0, horizontal=0),
            controls=[
                ft.Text(eft.value.name)
                for eft in ExportFileType
            ],
        )

        self.content = ft.Row(
            [
                self.slider,
                self.button,
                self.images_and_mask_export_button,
            ], alignment=ft.MainAxisAlignment.CENTER,
        )
        self.visible = False
        self._initialized = True

    # def did_mount(self):
    #     if self.page and self.page.theme:
    #         self.slider.thumb_color = self.page.theme.color_scheme.primary
    #         self.update()

    # @property
    # def on_click(self):
    #     return self.button.on_click
    #
    # @on_click.setter
    # def on_click(self, handler):
    #     self.button.on_click = handler


def error_banner(gui, message):
    gui.page.show_dialog(ft.SnackBar(
        ft.Text(message)))
    gui.page.update()
