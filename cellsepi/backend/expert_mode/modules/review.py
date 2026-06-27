from backend.constants import MAIN_COLOR, HIGHLIGHT_COLOR, ERROR_COLOR, SUCCESS_COLOR
from image_editing_view import ImageEditingView

from backend.data_util import convert_tiffs_to_png_parallel
from backend.expert_mode.listener import OnPipelineChangeEvent
from backend.expert_mode.module import *


class Review(Module):
    mask_color = (255, 0, 0)
    mask_opacity = 128
    outline_color = (0, 255, 0)
    _instances = []
    _gui_config = ModuleGuiConfig("Review", Categories.MANUAL,
                                  "This module allows you to manually review and edit masks. Also you can create new masks when no mask are given.")

    def __init__(self, module_id: str = None) -> None:
        super().__init__(module_id)
        self.inputs = InputPorts(
        InputPort("image_paths", dict),
            InputPort("mask_paths", dict, True),
        )
        self.outputs = OutputPorts (
            OutputPort("mask_paths", dict),
        )
        self.user_segmentation_channel: str = "2"
        self.user_2_5d = False
        self.user_mask_suffix = "_seg"
        # for the own settings stack
        self._icon_x = {}
        self._icon_check = {}
        self.image_id: str | None = None
        self.channel_id: str | None = None
        self._selected_images_visualise = {}
        self._image_gallery = ft.ListView(expand=True)
        self._edit_allowed = False
        Review._instances.append(self)
        self._text_field_segmentation_channel = ft.TextField(
            border_color=ft.Colors.WHITE60,
            value=self.user_segmentation_channel,
            on_blur=lambda e: self.on_change_sc(e),
            tooltip="Segmentation channel",
            height=30, width=70, content_padding=ft.Padding.symmetric(vertical=0, horizontal=5),
            fill_color=ft.Colors.WHITE38,
            filled=True,
            text_align=ft.TextAlign.CENTER,
            border_width=2,
            focused_border_color=ft.Colors.WHITE,
            text_style=ft.TextStyle(color=ft.Colors.BLACK, weight=ft.FontWeight.BOLD),
            cursor_color=ft.Colors.BLACK,
            expand=False,
        )
        self._text_field_mask_suffix = ft.TextField(
            border_color=ft.Colors.WHITE60,
            value=self.user_mask_suffix,
            on_blur=lambda e: self.on_change_ms(e),
            tooltip="Mask suffix",
            height=30, width=70, content_padding=ft.Padding.symmetric(vertical=0, horizontal=5),
            fill_color=ft.Colors.WHITE38,
            filled=True,
            text_align=ft.TextAlign.CENTER,
            border_width=2,
            focused_border_color=ft.Colors.WHITE,
            text_style=ft.TextStyle(color=ft.Colors.BLACK, weight=ft.FontWeight.BOLD),
            cursor_color=ft.Colors.BLACK,
            visible=False,
            expand=False,
        )
        self._control_menu = ft.Container(ft.Container(ft.Row(
            [self._text_field_segmentation_channel,
             self._text_field_mask_suffix,
             ], spacing=2, alignment=ft.MainAxisAlignment.CENTER,
        ), bgcolor=MAIN_COLOR, expand=True, border_radius=ft.BorderRadius.vertical(top=0, bottom=12),
            height=38,
        )
        )
        self._canvas = ImageEditingView(
            on_mask_change=self._mask_update_async)
        self._canvas.auto_adjust = True
        self._canvas.mask_color = self.mask_color
        self._canvas.outline_color = self.outline_color
        self._canvas.mask_opacity = self.mask_opacity
        self._settings: ft.Control = ft.Row(
            [self._canvas,
             ft.Card(
                 content=ft.Column(
                     [
                         ft.Container(
                             self._image_gallery,
                             expand=True,
                             padding=ft.Padding.only(
                                 top=20,
                                 left=20,
                                 right=20,
                                 bottom=10)
                         ),
                         self._control_menu
                     ], spacing=0, expand=True, width=640)),
             ], expand=True, margin=20)

    def finished(self):
        self.outputs.mask_paths.data = self.inputs.mask_paths.data
        self._text_field_mask_suffix.visible = False
        self._canvas.disable_editing_without_update()

    def run(self):
        self.event_manager.notify(ProgressEvent(percent=0, process=f"Preparing: starting"))
        # reset
        self._icon_x = {}
        self._icon_check = {}
        self.image_id = None
        self.channel_id = None
        self._image_gallery.controls.clear()
        self._text_field_mask_suffix.visible = True
        # reset image_viewer
        if self.inputs.mask_paths.data is None:
            self.inputs.mask_paths.data = {}
        self._canvas.set_main_paths(self.inputs.image_paths.data)
        self._canvas.set_mask_paths(self.inputs.mask_paths.data)
        self._canvas.reset_image(without_update=True)
        self._edit_allowed = True
        self.event_manager.notify(ProgressEvent(percent=100, process=f"Preparing: finished"))
        self.event_manager.notify(ProgressEvent(percent=0, process=f"Loading Images: Starting"))
        src = convert_tiffs_to_png_parallel(self.inputs.image_paths.data)

        async def select_image(img_id, c_id):
            if self.image_id is not None and self.image_id in self._selected_images_visualise:
                if self.channel_id is not None and self.channel_id in self._selected_images_visualise[
                    self.image_id]:
                    self._selected_images_visualise[self.image_id][self.channel_id].visible = False
                    self._selected_images_visualise[self.image_id][self.channel_id].update()
            self.image_id = img_id
            self.channel_id = c_id
            self._selected_images_visualise[img_id][c_id].visible = True
            self._selected_images_visualise[img_id][c_id].update()
            self._canvas.select_image(img_id, c_id,
                                      self.user_segmentation_channel)

        n_series = len(src)
        for iN, image_id in enumerate(src):
            cur_image_paths = src[image_id]
            self._selected_images_visualise[image_id] = {}
            for iN2, channel_id in enumerate(cur_image_paths):
                self._selected_images_visualise[image_id][channel_id] = ft.Container(
                    width=154,
                    height=154,
                    border=ft.Border.all(4, HIGHLIGHT_COLOR),
                    alignment=ft.Alignment.CENTER,
                    visible=False,
                    padding=5
                )
            group_row = ft.Row(
                [
                    ft.Column(
                        [
                            ft.GestureDetector(
                                content=ft.Container(ft.Stack([ft.Image(
                                    src=cur_image_paths[channel_id],
                                    height=150,
                                    width=150,
                                    fit=ft.BoxFit.CONTAIN,
                                    gapless_playback=True
                                ), self._selected_images_visualise[image_id][channel_id]]), width=156, height=156),
                                on_tap=lambda e, img_id=image_id, c_id=channel_id: self._canvas.page.run_task(
                                    select_image, img_id, c_id)
                            ),
                            ft.Text(channel_id, size=10, text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5
                    )
                    for channel_id in cur_image_paths
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            )
            self._icon_check[image_id] = ft.Icon(ft.Icons.CHECK, color=SUCCESS_COLOR, size=17, visible=False,
                                                 tooltip="Mask is available")
            self._icon_x[image_id] = ft.Icon(ft.Icons.CLOSE, size=17, visible=True, tooltip="Mask not available")
            self.update_mask_check(image_id, False)
            self._image_gallery.controls.append(ft.Column([ft.Row(
                [ft.Text(f"{image_id}", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                 self._icon_check[image_id], self._icon_x[image_id]], spacing=2),
                group_row], spacing=10, alignment=ft.MainAxisAlignment.CENTER))
            self.event_manager.notify(
                ProgressEvent(percent=int((iN + 1) / n_series * 100), process=f"Loading Images: {iN + 1}/{n_series}"))
            self._image_gallery.update()

        self.event_manager.notify(ProgressEvent(percent=100, process=f"Loading Images: Finished"))
        return True

    def update_mask_check(self, image_id, update=True):
        """
        Updates the symbol next to series number of image to a check or x, depending on if the corresponding image is available.
        Args:
            image_id: the id of the image to check mask availability
            update: True to update the gui
        """
        if self.inputs.mask_paths.data is not None and image_id in self.inputs.mask_paths.data and self.user_segmentation_channel in self.inputs.mask_paths.data[image_id]:
            self._icon_check[image_id].visible = True
            self._icon_x[image_id].visible = False
        else:
            self._icon_check[image_id].visible = False
            self._icon_x[image_id].visible = True
        if update:
            self._icon_check[image_id].update()
            self._icon_x[image_id].update()

    def update_all_masks_check(self):
        """
        Updates the symbol next to series number of image for every image_id in mask_paths.
        """
        if self.inputs.image_paths.data is not None:
            for image_id in self.inputs.image_paths.data:
                self.update_mask_check(image_id)

    async def _mask_update_async(self, image_id, mask_added_or_removed):
        if mask_added_or_removed:
            self.update_mask_check(image_id)

    def on_change_ms(self, e):
        if str(e.control.value) == "":
            self.settings.page.open(
                ft.SnackBar(
                    ft.Text(f"Mask suffix must be not empty!",
                            color=ft.Colors.WHITE),
                    bgcolor=ERROR_COLOR))
            e.control.value = self.user_mask_suffix
            self.settings.page.update()
            return
        self.user_mask_suffix = str(e.control.value)
        self._canvas.mask_suffix = str(e.control.value)
        self.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    def on_change_sc(self, e):
        if str(e.control.value) == "":
            self.settings.page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Segmentation channel must be not empty!",
                            color=ft.Colors.WHITE),
                    bgcolor=ERROR_COLOR))
            e.control.value = self.user_segmentation_channel
            self.settings.page.update()
            return
        self.user_segmentation_channel = str(e.control.value)
        self.update_all_masks_check()
        if self.image_id is not None:
            self._canvas.select_image(self.image_id, self.channel_id, self.user_segmentation_channel)
        self.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    @classmethod
    def update_class(cls, mask_color=None, outline_color=None, opacity=None):
        cls.mask_color = mask_color if mask_color is not None else cls.mask_color
        cls.outline_color = outline_color if outline_color is not None else cls.outline_color
        cls.mask_opacity = opacity if opacity is not None else cls.mask_opacity
        for instance in cls._instances:
            if instance.image_id is not None:
                instance._canvas.set_colors(mask_color, outline_color, opacity)

    def destroy(self):
        self._instances.remove(self)
        super().destroy()
