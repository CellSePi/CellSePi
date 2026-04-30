from cellsepi.backend.main_window.data_util import convert_tiffs_to_png_parallel
from cellsepi.backend.main_window.expert_mode.listener import ProgressEvent, OnPipelineChangeEvent
from cellsepi.backend.main_window.expert_mode.module import *
#from cellsepi.backend.main_window.image_tuning import auto_adjust


class Review(Module, ABC):
    mask_color = (255, 0, 0)
    mask_opacity = 128
    outline_color = (0, 255, 0)
    _instances = []
    _gui_config = ModuleGuiConfig("Review",Categories.MANUAL,"This module allows you to manually review and edit masks. Also you can create new masks when no mask are given.")
    def __init__(self, module_id: str = None) -> None:
        #regular modul
        super().__init__(module_id)
        self.inputs = {
            "image_paths": InputPort("image_paths", dict),
            "mask_paths": InputPort("mask_paths", dict,True),
        }
        self.outputs = {
            "mask_paths": OutputPort("mask_paths", dict),
        }
        self.user_segmentation_channel: str = "2"
        self.user_2_5d = False
        self.user_mask_suffix = "_seg"
        #for the own settings stack
        self._icon_x = {}
        self._icon_check = {}
        self.image_id: str | None = None
        self.channel_id: str | None = None
        self._selected_images_visualise = {}
        self._image_gallery = ft.ListView()
        self._edit_allowed = False
        self._text_field_segmentation_channel: ft.TextField | None = None
        self._text_field_mask_suffix: ft.TextField | None = None
        self._control_menu: ft.Container | None = None
        self._main_image_view: ft.Card | None = None
        Review._instances.append(self)

    @property
    def settings(self) -> ft.Stack:
        if self._settings is None:
            self._text_field_segmentation_channel = ft.TextField(
                border_color=ft.Colors.WHITE60,
                value=self.user_segmentation_channel,
                on_blur=lambda e: self.on_change_sc(e),
                tooltip="Segmentation channel",
                height=30, width=70, content_padding=ft.padding.symmetric(0, 5),
                fill_color=ft.Colors.WHITE38,
                filled=True,
                text_align=ft.TextAlign.CENTER,
                border_width=2,
                focused_border_color=ft.Colors.WHITE,
                text_style=ft.TextStyle(color=ft.Colors.BLACK,weight=ft.FontWeight.BOLD),
                cursor_color=ft.Colors.BLACK,
                expand=False,
            )
            self._text_field_mask_suffix = ft.TextField(
                border_color=ft.Colors.WHITE60,
                value=self.user_mask_suffix,
                on_blur=lambda e: self.on_change_ms(e),
                tooltip="Mask suffix",
                height=30, width=70, content_padding=ft.padding.symmetric(0, 5),
                fill_color=ft.Colors.WHITE38,
                filled=True,
                text_align=ft.TextAlign.CENTER,
                border_width=2,
                focused_border_color=ft.Colors.WHITE,
                text_style=ft.TextStyle(color=ft.Colors.BLACK, weight=ft.FontWeight.BOLD),
                cursor_color=ft.Colors.BLACK,
                visible= False,
                expand=False,
            )
            self._control_menu = ft.Container(ft.Container(ft.Row(
                [
                    self._text_field_segmentation_channel,
                    self._text_field_mask_suffix,
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER,
            ), bgcolor=ft.Colors.BLUE_400, expand=True, border_radius=ft.border_radius.vertical(top=0, bottom=12),height=38,
            )
            )
            self._main_image_view = ft.Card()
            self._settings: ft.Stack = ft.Stack([ft.Row([ft.Column([ft.Row([
                self._main_image_view,
                ft.Card(content=ft.Column([ft.Container(self._image_gallery, width=600, height=700, expand=True, padding=20),self._control_menu],expand=True,height=700,width=640)),
            ])
            ],
                alignment=ft.MainAxisAlignment.CENTER, )], alignment=ft.MainAxisAlignment.CENTER),])
        return self._settings

    def finished(self):
        self.outputs["mask_paths"].data = self.inputs["mask_paths"].data
        self._text_field_mask_suffix.visible = False
        self._text_field_mask_suffix.update()
        self._edit_allowed = False
        self._edit_button.icon_color = ft.Colors.BLACK12
        self._edit_button.disabled = True
        self._edit_button.update()

    def run(self):
        self.event_manager.notify(ProgressEvent(percent=0, process=f"Preparing: starting"))
        #reset
        self._window_image_id = ""
        self._window_bf_channel = ""
        self._window_channel_id = ""
        self._window_mask_path = ""
        self._icon_x = {}
        self._icon_check = {}
        self.image_id = None
        self.channel_id = None
        self._image_gallery.controls.clear()
        #reset image_viewer
        self._edit_allowed = True
        self.event_manager.notify(ProgressEvent(percent=100, process=f"Preparing: finished"))
        self.event_manager.notify(ProgressEvent(percent=0, process=f"Loading Images: Starting"))
        src  = convert_tiffs_to_png_parallel(self.inputs["image_paths"].data)
        n_series = len(src)
        for iN,image_id in enumerate(src):
            cur_image_paths = src[image_id]

            self._selected_images_visualise[image_id] = {}
            for iN2,channel_id in enumerate(cur_image_paths):
                self._selected_images_visualise[image_id][channel_id] = ft.Container(
                    width=154,
                    height=154,
                    border=ft.border.all(4, ft.Colors.ORANGE_700),
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
                                fit=ft.ImageFit.CONTAIN
                                ),self._selected_images_visualise[image_id][channel_id]]),width=156,height=156),
                                on_tap=lambda e, img_id=image_id, c_id=channel_id: self.update_main_image(img_id, c_id),
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
            self._icon_check[image_id] = ft.Icon(ft.Icons.CHECK, color=ft.Colors.GREEN, size=17, visible=False,
                                                tooltip="Mask is available")
            self._icon_x[image_id] = ft.Icon(ft.Icons.CLOSE, size=17, visible=True, tooltip="Mask not available")
            self.update_mask_check(image_id)
            self._image_gallery.controls.append(ft.Column([ft.Row(
            [ft.Text(f"{image_id}", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), self._icon_check[image_id], self._icon_x[image_id]], spacing=2),
                                                      group_row], spacing=10, alignment=ft.MainAxisAlignment.CENTER))
            self.event_manager.notify(ProgressEvent(percent=int((iN+1) / n_series * 100), process=f"Loading Images: {iN+1}/{n_series}"))

        self.event_manager.notify(ProgressEvent(percent=100, process=f"Loading Images: Finished"))

        return True


    def update_mask_check(self, image_id):
        """
        Updates the symbol next to series number of image to a check or x, depending on if the corresponding image is available.
        Args:
            image_id: the id of the image to check mask availability
        """
        if self.inputs["mask_paths"].data is not None and image_id in self.inputs["mask_paths"].data and self.user_segmentation_channel in self.inputs["mask_paths"].data[image_id]:
            self._icon_check[image_id].visible = True
            self._icon_x[image_id].visible = False
        else:
            self._icon_check[image_id].visible = False
            self._icon_x[image_id].visible = True
        self._image_gallery.update()

    def update_all_masks_check(self):
        """
        Updates the symbol next to series number of image for every image_id in mask_paths.
        """
        if self.inputs["image_paths"].data is not None:
            for image_id in self.inputs["image_paths"].data:
                self.update_mask_check(image_id)

    def on_change_ms(self,e):
        if str(e.control.value) == "":
            self.settings.page.open(
                ft.SnackBar(
                    ft.Text(f"Mask suffix must be not empty!",
                            color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.RED))
            e.control.value = self.user_mask_suffix
            self.settings.page.update()
            return
        self.user_mask_suffix = str(e.control.value)
        self.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    def on_change_sc(self,e):
        if str(e.control.value) == "":
            self.settings.page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"Segmentation channel must be not empty!",
                            color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.RED))
            e.control.value = self.user_segmentation_channel
            self.settings.page.update()
            return
        self.user_segmentation_channel = str(e.control.value)
        self.update_all_masks_check()
        if self.image_id is not None:
            pass
            #self.update_main_image(self.image_id, self.channel_id)
        self.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    @classmethod
    def update_class(cls):
        for instance in cls._instances:
            if instance.image_id is not None:
                instance.update_main_image(instance.image_id, instance.channel_id)

    def destroy(self):
        self._instances.remove(self)
        super().destroy()