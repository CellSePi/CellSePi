import flet as ft

fluorescence_button = ft.Button(content="Readout",
                                icon=ft.Icons.FILE_DOWNLOAD,
                                tooltip="Readout fluorescence values",
                                disabled=False,
                                visible=False)


@ft.control
class FluorescenceReadoutControl(ft.Container):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, )

        self.button = ft.Button(
            content="Readout",
            icon=ft.Icons.FILE_DOWNLOAD,
            tooltip="Readout fluorescence values",
            disabled=False,
            visible=True
        )

        self.slider = ft.CupertinoSlidingSegmentedButton(
            selected_index=0,
            # TODo EK: Adapt colorscheme
            thumb_color=ft.Colors.BLUE_400,
            on_change=lambda e: print(f"selected_index: {e.data}"),
            padding=ft.Padding.symmetric(vertical=0, horizontal=10),
            controls=[
                ft.Text("XLSX"),
                ft.Text("TSV"),
                ft.Text("CSV"),
                ft.Text("PDF"),
            ],
        )

        self.content = ft.Row(
            [
                # ft.Text("Readout fluorescence values"),
                self.slider,
                self.button,
                # ft.TextButton(content="Select file", on_click=lambda e: print("Select file")),
            ], alignment=ft.MainAxisAlignment.CENTER,
        )

    @property
    def on_click(self):
        return self.button.on_click

    @on_click.setter
    def on_click(self, on_click):
        self.button.on_click = on_click


def error_banner(gui, message):
    gui.page.show_dialog(ft.SnackBar(
        ft.Text(message)))
    gui.page.update()
