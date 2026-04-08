import asyncio
import base64
import multiprocessing
import os
import threading
from io import BytesIO
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from flet_extended_interactive_viewer import FletExtendedInteractiveViewer

from cellsepi.backend.main_window.data_util import convert_tiffs_to_png_parallel
from cellsepi.backend.main_window.expert_mode.listener import ProgressEvent, OnPipelineChangeEvent
from cellsepi.backend.main_window.expert_mode.module import *
from cellsepi.backend.main_window.image_tuning import auto_adjust
from cellsepi.frontend.drawing_window.gui_drawing import open_qt_window


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
        self._on_settings_dismiss = self.dismiss
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
        self._container_mask: ft.Container | None = None
        self._main_image: ft.Container | None = None
        self._interactive_viewer:FletExtendedInteractiveViewer | None = None
        self._mask_button:ft.IconButton | None = None
        self._edit_allowed = False
        self._edit_button:ft.IconButton | None = None
        self._slider_2d: ft.CupertinoSlidingSegmentedButton | None = None
        self._text_field_segmentation_channel: ft.TextField | None = None
        self._slider_2_5d:ft.Slider | None = None
        self._control_menu: ft.Container | None = None
        self._main_image_view: ft.Card | None = None
        self._ready = threading.Event()
        self._pipe_listener_running = True
        self._queue = None
        self._parent_conn, self._child_conn = None, None
        self._process_drawing_window = None
        self._window_image_id = ""
        self._window_bf_channel = ""
        self._window_channel_id = ""
        self._window_mask_path = ""
        self._thread = None
        Review._instances.append(self)

    @property
    def settings(self) -> ft.Stack:
        if self._settings is None:
            self._container_mask = ft.Container(
                ft.Image(src=r"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA\AAAFCAIAAAFe0wxPAAAAAElFTkSuQmCC",
                         fit=ft.ImageFit.SCALE_DOWN, ), visible=False, alignment=ft.Alignment.CENTER, width=632, height=632)

            self._main_image = ft.Container(
                ft.Image(src=r"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA\AAAFCAIAAAFe0wxPAAAAAElFTkSuQmCC",
                         fit=ft.ImageFit.SCALE_DOWN), alignment=ft.Alignment.CENTER, width=632, height=632)

            self._interactive_viewer = FletExtendedInteractiveViewer(
                content=ft.Stack([self._main_image, self._container_mask]), constrained=False, min_scale=0.1, width=632,
                height=632)
            zoom_value = 0.20
            self._mask_button = ft.IconButton(icon=ft.Icons.REMOVE_RED_EYE, icon_color=ft.Colors.BLACK12,
                                              style=ft.ButtonStyle(
                                                  shape=ft.RoundedRectangleBorder(radius=12), ),
                                              on_click=lambda e: self.show_mask(),
                                              tooltip="Show mask", hover_color=ft.Colors.WHITE12, disabled=True)
            self._edit_button = ft.IconButton(icon=ft.Icons.EDIT_SHARP, icon_color=ft.Colors.BLACK12,
                                  style=ft.ButtonStyle(
                                      shape=ft.RoundedRectangleBorder(radius=12),),
                                  on_click=lambda e: self.set_queue_drawing_window(),
                                  tooltip="Edit Mask", hover_color=ft.Colors.WHITE12,disabled=True)
            self._slider_2d = ft.CupertinoSlidingSegmentedButton(
                selected_index=0 if not self.user_2_5d else 1,
                thumb_color=ft.Colors.WHITE,
                bgcolor=ft.Colors.WHITE60,
                on_change=lambda e: self.slider_update(e),
                padding=ft.padding.symmetric(0, 0),
                controls=[
                    ft.Text("2D",color=ft.Colors.BLACK),
                    ft.Text("2.5D",color=ft.Colors.BLACK)
                ],
            )
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
                visible= False
            )
            self._slider_2_5d = ft.Slider(
                min=0, max=100, divisions=None, label="Slice: {value}", on_change=lambda e: self.slider_change(),
                opacity=1.0 if self.user_2_5d else 0.0, height=20,
                active_color=ft.Colors.WHITE60, thumb_color=ft.Colors.WHITE, disabled=True,
                animate_opacity= ft.Animation(duration=600, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
            )
            self._control_menu = ft.Container(ft.Container(ft.Row(
                [
                    ft.IconButton(icon=ft.Icons.ZOOM_IN, icon_color=ft.Colors.WHITE60,
                                  style=ft.ButtonStyle(
                                      shape=ft.RoundedRectangleBorder(radius=12), ),
                                  on_click=lambda e: self._interactive_viewer.zoom(1.0 + zoom_value), tooltip="Zoom in",
                                  hover_color=ft.Colors.WHITE12),
                    ft.IconButton(icon=ft.Icons.ZOOM_OUT, icon_color=ft.Colors.WHITE60,
                                  style=ft.ButtonStyle(
                                      shape=ft.RoundedRectangleBorder(radius=12), ),
                                  on_click=lambda e: self._interactive_viewer.zoom(1.0 - zoom_value), tooltip="Zoom out",
                                  hover_color=ft.Colors.WHITE12),
                    ft.IconButton(icon=ft.Icons.CROP_FREE, icon_color=ft.Colors.WHITE60,
                                  style=ft.ButtonStyle(
                                      shape=ft.RoundedRectangleBorder(radius=12), ),
                                  on_click=lambda e: self._interactive_viewer.reset(400),
                                  tooltip="Reset view", hover_color=ft.Colors.WHITE12),
                    self._text_field_segmentation_channel,
                    self._text_field_mask_suffix,
                    self._edit_button,
                    self._mask_button,
                    self._slider_2d,
                    ft.Container(
                        content=self._slider_2_5d,
                        theme=ft.Theme(
                            slider_theme=ft.SliderTheme(
                                value_indicator_text_style=ft.TextStyle(color=ft.Colors.BLACK, size=15,weight=ft.FontWeight.BOLD),
                            )
                        ),
                        dark_theme=ft.Theme(
                            slider_theme=ft.SliderTheme(
                                value_indicator_text_style=ft.TextStyle(color=ft.Colors.BLACK, size=15,weight=ft.FontWeight.BOLD),
                            )
                        ),
                    ),
                ], spacing=2,alignment=ft.MainAxisAlignment.CENTER,
            ), bgcolor=ft.Colors.BLUE_400, expand=True, border_radius=ft.border_radius.vertical(top=0, bottom=12),
            )
            )
            self._main_image_view = ft.Card(
                content=ft.Column([ft.Container(self._interactive_viewer, padding=ft.padding.only(top=10),
                                                alignment=ft.alignment.top_center), self._control_menu]),
                width=660, height=700,
                expand=True,
            )

            self._settings: ft.Stack = ft.Stack([ft.Row([ft.Column([ft.Row([
                self._main_image_view,
                ft.Card(content=ft.Container(self._image_gallery, width=600, height=700, expand=True, padding=20),
                        expand=True),
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
        self._pipe_listener_running = False
        self._queue.put("close")
        if self._process_drawing_window is not None and self._process_drawing_window.is_alive():
            self._process_drawing_window.join()
        self._child_conn.send("close")

        if self._thread is not None and self._thread.is_alive():
            self._thread.join()
        self._child_conn.close()
        self._parent_conn.close()
        self._queue = None
        self._parent_conn, self._child_conn = None, None
        self._process_drawing_window = None
        self._thread = None

    def run(self):
        self.event_manager.notify(ProgressEvent(percent=0, process=f"Preparing: starting"))
        self._ready.clear()
        self._pipe_listener_running = True
        self._queue = multiprocessing.Queue()
        parent_conn, child_conn = multiprocessing.Pipe()
        self._parent_conn, self._child_conn = parent_conn, child_conn
        self._process_drawing_window = self.start_drawing_window()
        self._thread = threading.Thread(target=self.child_conn_listener, daemon=True)
        self._thread.start()
        #reset
        self._window_image_id = ""
        self._window_bf_channel = ""
        self._window_channel_id = ""
        self._window_mask_path = ""
        self._icon_x = {}
        self._icon_check = {}
        self.image_id = None
        self.channel_id = None
        self._selected_images_visualise = {}
        self._image_gallery.clean()
        self._main_image.content.src=r"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA\AAAFCAIAAAFe0wxPAAAAAElFTkSuQmCC"
        self._main_image.content.src_base64 = None
        self._main_image.update()
        self._container_mask.visible = False
        self._container_mask.update()
        self._edit_allowed = True
        self._ready.wait()
        self._ready.clear()
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
                    alignment=ft.Alignment.CENTRE,
                    visible=False,
                    padding=5
                )
            group_row = ft.Row(
                [
                    ft.Column(
                    [
                            ft.GestureDetector(
                                content=ft.Container(ft.Stack([ft.Image(
                                src_base64=cur_image_paths[channel_id],
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

    def update_main_image(self,img_id,channel_id,on_click = True):
        """
        Method that handles what happens when the image is clicked or the main image need an update.
        """
        if on_click:
            if self.image_id is not None and self.image_id in self._selected_images_visualise:
                if self.channel_id is not None and self.channel_id in self._selected_images_visualise[self.image_id]:
                    self._selected_images_visualise[self.image_id][self.channel_id].visible = False
                    self._selected_images_visualise[self.image_id][self.channel_id].update()
        self.image_id = img_id
        self.channel_id = channel_id
        self._selected_images_visualise[img_id][channel_id].visible = True
        self._selected_images_visualise[img_id][channel_id].update()


        self._main_image.content.src_base64 = auto_adjust(self.inputs["image_paths"].data[img_id][channel_id], get_slice=int(self._slider_2_5d.value) if self.user_2_5d else -1)
        self._main_image.update()
        image = tifffile.imread(self.inputs["image_paths"].data[self.image_id][self.channel_id])
        self._text_field_mask_suffix.visible = not(self.inputs["mask_paths"].data is not None and self.image_id in self.inputs["mask_paths"].data and self.user_segmentation_channel in self.inputs["mask_paths"].data[self.image_id] and self.inputs["mask_paths"].data[self.image_id][self.user_segmentation_channel] is not None) and self._edit_allowed
        self._text_field_mask_suffix.update()

        if image.ndim == 3:
            if self._slider_2_5d.opacity == 1.0 and self._edit_allowed:
                self._edit_button.icon_color = ft.Colors.WHITE60
                self._edit_button.disabled = False
                self._edit_button.update()
            else:
                self._edit_button.icon_color = ft.Colors.BLACK12
                self._edit_button.disabled = True
                self._edit_button.update()
            self._slider_2_5d.value = 0 if image.shape[-2] - 1 < self._slider_2_5d.value else self._slider_2_5d.value
            self._slider_2_5d.max = image.shape[2] - 1
            self._slider_2_5d.divisions = image.shape[2] - 2
            self._slider_2_5d.disabled = False
            self._slider_2_5d.update()
        else:
            if self._edit_allowed:
                self._edit_button.icon_color = ft.Colors.WHITE60
                self._edit_button.disabled = False
                self._edit_button.update()
            self._slider_2_5d.value = 0
            self._slider_2_5d.max = 1
            self._slider_2_5d.divisions = None
            self._slider_2_5d.disabled = True
            self._slider_2_5d.update()

        if self.inputs["mask_paths"].data is not None and self.image_id in self.inputs["mask_paths"].data and self.user_segmentation_channel in self.inputs["mask_paths"].data[img_id]:
            if not self._container_mask.visible:
                self._mask_button.icon_color = ft.Colors.WHITE60
                self._mask_button.tooltip = "Show mask"
                self._mask_button.disabled = False
                self._mask_button.update()

            mask_data = np.load(Path(self.inputs["mask_paths"].data[self.image_id][self.user_segmentation_channel]), allow_pickle=True).item()

            mask= mask_data["masks"]
            outline = mask_data["outlines"]
            self._container_mask.content.src_base64 = self.convert_npy_to_canvas(mask,outline)
            self._container_mask.update()
        else:
            self._mask_button.tooltip = "Show mask"
            self._mask_button.icon_color = ft.Colors.BLACK12
            self._mask_button.disabled = True
            self._mask_button.update()
            self._container_mask.visible = False
            self._container_mask.update()

    def show_mask(self):
        self._container_mask.visible = not self._container_mask.visible
        self._container_mask.update()
        self._mask_button.icon_color = ft.Colors.WHITE if self._container_mask.visible else ft.Colors.WHITE60
        self._mask_button.tooltip="Hide mask" if self._container_mask.visible else "Show mask"
        self._mask_button.update()

    def convert_npy_to_canvas(self,mask, outline):
        """
        handles the conversion of the given file data

        Args:
            mask= the mask data stored in the numpy directory
            outline= the outline data stored in the numpy directory
        """
        buffer= BytesIO()

        if mask.ndim == 3:
            if self._slider_2_5d.opacity == 1.0:
                mask = np.take(mask, int(self._slider_2_5d.value), axis=0)
            else:
                mask = np.max(mask, axis=0)

        if outline.ndim == 3:
            if self._slider_2_5d.opacity == 1.0:
                outline = np.take(outline, int(self._slider_2_5d.value), axis=0)
            else:
                outline = np.max(outline, axis=0)

        image_mask = np.zeros(shape=(mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
        r,g,b = self.mask_color
        image_mask[mask != 0] = (r, g, b, self.mask_opacity)
        r, g, b = self.outline_color
        image_mask[outline != 0] = (r, g, b, 255)
        im= Image.fromarray(image_mask).convert("RGBA")
        im.resize(size=(700,500))

        #saves the image as a image(base64)
        im.save(buffer, format="PNG")
        buffer.seek(0)
        image_base_64= base64.b64encode(buffer.getvalue()).decode('utf-8')

        #saves the created output image.
        return image_base_64


    def slider_update(self, e):
        if int(e.data) == 1:
            self._slider_2_5d.opacity = 1.0
            self.user_2_5d = True
        else:
            self._slider_2_5d.opacity = 0.0
            self.user_2_5d = False

        self.slider_change()
        self._slider_2_5d.update()
        self.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    def slider_change(self):
        if self.image_id is not None:
            self.update_main_image(self.image_id, self.channel_id)

    def on_change_sc(self,e):
        if str(e.control.value) == "":
            self.settings.page.open(
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
            self.update_main_image(self.image_id, self.channel_id)
        self.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

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

    @classmethod
    def update_class(cls):
        for instance in cls._instances:
            if instance.image_id is not None:
                instance.update_main_image(instance.image_id, instance.channel_id)

    def destroy(self):
        self._instances.remove(self)
        super().destroy()


    def start_drawing_window(self):
        """
        Start the drawing window in multiprocessing.
        """
        process = multiprocessing.Process(target=open_qt_window,
                                args=(self._queue,self._child_conn))
        process.start()
        return process

    def set_queue_drawing_window(self):
        """
        Sets queue for drawing window with the current selected image and mask.
        """
        adjusted_image_path = os.path.join(
            Path(self.inputs["image_paths"].data[self.image_id][self.user_segmentation_channel]).parent,
            "adjusted_image.png")
        image_data = base64.b64decode(self._main_image.content.src_base64)
        buffer = BytesIO(image_data)
        image = Image.open(buffer)
        image.save(adjusted_image_path, format="PNG")

        if self._process_drawing_window is None or not self._process_drawing_window.is_alive(): #make sure that the process is running before putting new image in the queue
            if self._process_drawing_window is not None:
                try:
                    self._process_drawing_window.terminate()
                    self._process_drawing_window.join()
                except Exception as e:
                    self._settings.page.open(ft.SnackBar(ft.Text(f"Error while terminating process: {e}")))
            self._queue = multiprocessing.Queue()
            parent_conn, child_conn = multiprocessing.Pipe()
            self._parent_conn, self._child_conn = parent_conn, child_conn
            self._process_drawing_window = self.start_drawing_window()
        self._window_image_id = self.image_id
        self._window_bf_channel = self.user_segmentation_channel
        self._window_channel_id = self.channel_id

        if self._window_bf_channel in self.inputs["image_paths"].data[self.image_id]:#check if the bf has an image
            image_path = self.inputs["image_paths"].data[self.image_id][self._window_bf_channel]
            directory, filename = os.path.split(image_path)
            name, _ = os.path.splitext(filename)
            mask_file_name = f"{name}{self.user_mask_suffix}.npy"
            self._window_mask_path = os.path.join(directory, mask_file_name)

            i = len(self.image_id)
            j = len(name) - len(self._window_bf_channel)
            channel_prefix = name[i:j]
            self._queue.put((self.mask_color, self.outline_color,self.mask_opacity, self.user_segmentation_channel, self.inputs["mask_paths"].data, self._window_image_id, adjusted_image_path, self._window_mask_path,self._window_channel_id,channel_prefix,self._slider_2_5d.value if not self._slider_2_5d.disabled else None,self._slider_2_5d.max + 1 if not self._slider_2_5d.disabled else None))
        else:
            self._settings.page.open(ft.SnackBar(
                ft.Text(f"Selected bright-field channel {self._window_bf_channel} has no image!")))
            self._settings.page.update()

    def child_conn_listener(self):
        """
        Listener for the child connection.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def pipe_listener():
            while self._pipe_listener_running:
                data = await asyncio.to_thread(self._parent_conn.recv)
                split_data = data.split(".")
                if data == "close":
                    break
                elif split_data[0] == "new_mask":
                    if self._window_image_id not in self.inputs["mask_paths"].data:
                        self.inputs["mask_paths"].data[self._window_image_id] = {}
                    self.inputs["mask_paths"].data[self._window_image_id][
                        self._window_bf_channel] = self._window_mask_path
                    self.update_mask_check(split_data[1])
                    self._text_field_mask_suffix.visible = not (
                                self.image_id in self.inputs["mask_paths"].data and self.user_segmentation_channel in
                                self.inputs["mask_paths"].data[self.image_id] and
                                self.inputs["mask_paths"].data[self.image_id][
                                    self.user_segmentation_channel] is not None) and self._edit_allowed
                    self._text_field_mask_suffix.update()
                elif split_data[0] == "ready":
                    self._ready.set()
                else:
                    if self._window_image_id == self.image_id and self._window_bf_channel == self.user_segmentation_channel:
                        self.update_main_image(self.image_id,self.channel_id)
                    else:
                        self.reset_mask(self._window_image_id, self._window_bf_channel)
                        self._text_field_mask_suffix.visible = not (self.image_id in self.inputs[
                            "mask_paths"].data and self.user_segmentation_channel in self.inputs["mask_paths"].data[
                                                                        self.image_id] and
                                                                    self.inputs["mask_paths"].data[self.image_id][
                                                                        self.user_segmentation_channel] is not None) and self._edit_allowed
                        self._text_field_mask_suffix.update()
        try:
            loop.run_until_complete(pipe_listener())
        finally:
            loop.stop()
            loop.close()

    def reset_mask(self, image_id, segmentation_channel):
        if image_id in self.inputs["mask_paths"].data and segmentation_channel in self.inputs["mask_paths"].data[image_id]:
            del self.inputs["mask_paths"].data[image_id][segmentation_channel]

    def dismiss(self):
        if self._queue is not None:
            self._queue.put("hide")