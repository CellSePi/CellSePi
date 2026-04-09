import asyncio
import os
import pathlib
import platform
from collections import defaultdict
import concurrent.futures
from json.encoder import INFINITY
from time import time
import flet as ft
import tifffile

from cellsepi.backend.main_window.expert_mode.event_manager import EventManager
from cellsepi.backend.main_window.expert_mode.listener import ProgressEvent
from cellsepi.backend.main_window.expert_mode.pipeline_manager import PipelineRunningException
from cellsepi.frontend.main_window.gui_canvas import update_main_image
from cellsepi.frontend.main_window.gui_fluorescence import fluorescence_button
from cellsepi.backend.main_window.data_util import extract_from_lif_file, copy_files_between_directories, load_directory, transform_image_path, \
    convert_tiffs_to_png_parallel

def format_directory_path(dir_path: str, max_length=30):
    """
    Format the directory so that it can be shown in the card.
    Args:
        dir_path (str): Path to the directory that should be formatted.
        max_length (int): Maximum length of the directory path.
    """
    parts = dir_path.split('/')
    path = dir_path
    if len(dir_path) > max_length:
        if len(parts) > 2:
            path = f".../{parts[len(parts) - 2]}/{parts[len(parts) - 1]}"
        else:
            return f"...{path[len(parts) - (max_length - 3):]}"

    if len(path) > max_length:
        path = f"...{path[len(parts) - (max_length - 3):]}"  # 3 für '...'

    return path

async def copy_to_clipboard(page,value: str,name: str):
    """
    Adds the value in to the clipboard and opens the snack_bar and say that it has been copied.
    Args:
        page: ft.Page object.
        value (str): Value to add to the clipboard.
        name (str): Name of the thing that got copied.
    """
    await ft.Clipboard().set(value)
    page.show_dialog(ft.SnackBar(ft.Text(f"{name} copied to clipboard!")))
    page.update()


def get_image(src):
    return ft.Image(
        src=src,
        height=150,
        width=150,
        fit=ft.BoxFit.CONTAIN,
        gapless_playback=True
    )


class DirectoryCard(ft.Card):
    """
    Handles the directory card with all event handlers.
    """
    def __init__(self, gui = None):
        if gui is not None:
            super().__init__()
            self.gui = gui
            self.count_results_txt = ft.Text(value="Results: 0")
            self.directory_path = ft.Text(value='Directory Path',weight=ft.FontWeight.BOLD)
            self.formatted_path = ft.Text(value=format_directory_path(self.directory_path.value), weight=ft.FontWeight.BOLD)
            self.is_lif = self.gui.csp.config.get_lif_slider()
            if self.is_lif:
                index = 1
            else:
                index = 0
            self.lif_slider = ft.CupertinoSlidingSegmentedButton(
                selected_index=index,
                thumb_color=ft.Colors.BLUE_400,
                on_change=self.update_view,
                padding=ft.padding.symmetric(0, 0),
                controls=[
                    ft.Text("Tif"),
                    ft.Text("Lif")
                ],
            )
            self.image_gallery = ft.ListView()
            self.path_list_tile = self.create_path_list_tile()
            #self.get_directory_dialog = None
            #self.pick_files_dialog = None
            #self.create_handlers()
            self.directory_row = self.create_dir_row()
            self.files_row = self.create_files_row()
            self.lif_slider_blocker = ft.Container(
                width=80,
                height=30,
                bgcolor=ft.Colors.TRANSPARENT,
                on_click= None,
                visible= False,
            )
            self.lif_row = ft.Row([ft.Stack([self.lif_slider,self.lif_slider_blocker]),
                                                   self.directory_row,
                                                   self.files_row
                                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                                  )
            self.content = self.create_directory_container()
            self.output_dir = False
            self.is_supported_lif = True
            self.files_row.visible = self.is_lif
            self.directory_row.visible = not self.is_lif
            self.selected_images_visualise = {}
            self.icon_check = {}
            self.icon_x = {}

    def create_path_list_tile(self):
        return ft.ListTile(leading=ft.Icon(icon=ft.Icons.FOLDER_OPEN),
                    title=self.formatted_path,
                    subtitle=self.count_results_txt
                    )

    def update_results_text(self):
        self.count_results_txt.value = f"Results: {len(self.gui.csp.image_paths)}"
        self.count_results_txt.update()

    async def get_directory_result(self, e: ft.Event[ft.Button]):
        """
        Checks if the picked directory or file exists and if it worked updates everything with the new values.
        builds the canvas container for the file results on the right column of the GUI
        """
        #initiate filepicker and fetch files/directory
        self.gui.progress_ring.visible = True
        if self.is_lif:
            files = await ft.FilePicker().pick_files(allow_multiple=False)

        else:
            files = await ft.FilePicker().get_directory_path()

        if not(files is None) and len(files) > 0:
            self.image_gallery.controls.clear()
            self.gui.canvas.reset_image()
            # the window of the image display is cleared of all content
            self.gui.csp.image_id = None
            self.gui.csp.channel_id = None
            self.gui.open_button.visible = False
            self.gui.start_button.disabled = True
            self.gui.training_environment.start_button.disabled = True
            fluorescence_button.visible = False
            self.gui.progress_bar_text.value = "Waiting for Input"
            self.gui.progress_bar.value = 0
            self.gui.contrast_slider.disabled = True
            self.gui.brightness_slider.disabled = True
            self.gui.csp.current_channel_prefix = self.gui.csp.config.get_channel_prefix()
            self.gui.csp.current_mask_suffix = self.gui.csp.config.get_mask_suffix()
            self.gui.mask.mask_outputs = defaultdict(dict)
            self.gui.contrast_slider.value = 1
            self.gui.brightness_slider.value = 1
            self.gui.diameter_display.opacity = 0.5
            if not platform.system() == "Linux":
                self.gui.page.window.progress_bar = -1
            self.gui.page.update()

            #differentiate between the lif and tiff case, as there are two different file formats
            if self.is_lif:
                #is a file
                # get data
                fetched_date = files[0]
                path = str(fetched_date.path)

            else:
                #is a directory
                path = files
            if path:
                self.directory_path.value = path
                self.select_directory_parallel(path,self.is_lif,self.gui.csp.config.get_channel_prefix())
                self.load_images()
            else:
                self.image_gallery.controls.clear()
                self.image_gallery.update()

            self.formatted_path.value = format_directory_path(self.directory_path.value)
            if self.output_dir or not self.is_supported_lif:
                self.formatted_path.color = ft.Colors.RED
                self.gui.diameter_text.value = 0.0
                self.gui.diameter_display.update()
            else:
                self.gui.diameter_text.value = self.gui.average_diameter.get_avg_diameter()
                self.gui.diameter_display.opacity = 1
                self.gui.diameter_display.update()
                self.formatted_path.color = None
            self.formatted_path.update()
        else:
            self.gui.progress_ring.visible = False

    def select_directory_parallel(self, directory_path ,is_lif:bool,channel_prefix: str ,event_manager: EventManager = None):
        """
            Gets the working directory and copies the images in there.

            Args:
                directory_path (str): the selected directory_path
                is_lif (bool): if the images are lif or tif
                channel_prefix (str): the channel prefix
                event_manager (EventManager): the event manager which is used when the methode gets started as a module.
                """
        is_supported_tif = True
        if event_manager is None:
            self.is_supported_lif = True
        path = pathlib.Path(directory_path)
        # Lif Case
        if is_lif:
            if event_manager is None:
                self.output_dir = False
            working_directory = path.parent / "output/"
            os.makedirs(working_directory, exist_ok=True)
            if path.suffix.lower() == ".lif":
                # Extract from a lif file all the single series images and extract to .tif, .tiff and .npy files into subdirectory
                extract_from_lif_file(lif_path=path, target_dir=working_directory,channel_prefix=channel_prefix,event_manager=event_manager)
            else:
                if event_manager is not None:
                    raise PipelineRunningException("Type Error","Expected .lif!")
                else:
                    self.is_supported_lif = False


        # Tiff Case
        else:
            if path.name == "output":
                if event_manager is not None:
                    raise PipelineRunningException("Directory Error","Directory ’output’ is not supported!")
                else:
                    self.gui.page.show_dialog(ft.SnackBar(ft.Text("The directory path output is not allowed!")))
                    self.output_dir = True
                    self.gui.page.update()
                    self.gui.csp.image_paths = {}
                    self.gui.csp.linux_images = {}
                    self.gui.csp.mask_paths = {}
                    self.gui.ready_to_start = False
                    self.gui.progress_ring.visible = False
                    return None
            if event_manager is None:
                self.output_dir = False
            # Copy .tif, .tiff and .npy files into subdirectory
            working_directory = path / "output/"
            os.makedirs(working_directory, exist_ok=True)
            copy_files_between_directories(path, working_directory, file_types=[".tif", ".tiff", ".npy"],event_manager=event_manager)
            tiff_paths = [p for p in working_directory.iterdir() if
                          p.suffix.lower() in [".tif", ".tiff"] and p.is_file()]
            total = len(tiff_paths)
            converted_count = 0
            failed = False

            if event_manager is not None:
                event_manager.notify(ProgressEvent(percent=0, process=f"Convert TIFFs: {converted_count}/{total}"))

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(self.convert_tiffs_to_8_bit, path): path for path in tiff_paths}
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if not result:
                        failed = True
                    converted_count += 1
                    if event_manager is not None:
                        event_manager.notify(
                            ProgressEvent(percent=int(converted_count / total*100),process=f"Convert Tiff's: {converted_count}/{total}")
                        )

            if failed:
                if event_manager is not None:
                    raise PipelineRunningException("Type Error",
                                                   "The directory contains an unsupported file type. Only 8 or 16 bit .tiff files allowed.")
                else:
                    is_supported_tif = False
            else:
                if event_manager is not None:
                    event_manager.notify(
                        ProgressEvent(percent=100,
                                      process=f"Finished converting Tiff's!")
                    )

        if event_manager is not None:
            return working_directory
        else:
            self.gui.csp.working_directory = working_directory
            self.set_paths(is_supported_tif)
            return None

    def convert_tiffs_to_8_bit(self, path):
        """
        handles when the conversion should happen
        Args:
            path (str): the selected directory_path
        """
        converted=True
        if path.suffix.lower() == ".tif" or path.suffix.lower() == ".tiff":
            if path.is_file():
                converted=transform_image_path(path, path)
        return converted

    def set_paths(self, is_supported_tif):
        """
        Updates the image and mask paths in csp (CellSePi).

        Args:
             is_supported_tif (bool): True if the image types for tif are supported.
        """
        bfc = self.gui.csp.config.get_bf_channel()
        cp = self.gui.csp.config.get_channel_prefix()
        ms = self.gui.csp.config.get_mask_suffix()
        working_directory = self.gui.csp.working_directory

        if not self.is_supported_lif:
            self.gui.ready_to_start = False
            self.gui.page.show_dialog(ft.SnackBar(
                ft.Text("The selected file is not supported! Only .lif are supported.")))
            image_paths = {}
            mask_paths = {}
            self.gui.progress_ring.visible = False
            self.gui.page.update()
        else:
            image_paths, mask_paths = load_directory(working_directory, channel_prefix=cp, mask_suffix=ms)

            if len(image_paths) == 0:
                self.gui.ready_to_start = False
                self.gui.page.show_dialog(ft.SnackBar(ft.Text("The directory contains no valid files with the current channel prefix!")))
                self.gui.page.update()
                self.count_results_txt.color = ft.Colors.RED
                self.gui.progress_ring.visible = False
                if not self.is_lif:
                    os.rmdir(self.gui.csp.working_directory)
            elif not is_supported_tif:
                self.gui.ready_to_start = False
                self.gui.page.show_dialog(ft.SnackBar(ft.Text("The directory contains an unsupported file type. Only 8 or 16 bit .tiff files allowed.")))
                self.count_results_txt.color = ft.Colors.RED
                self.gui.progress_ring.visible = False
                self.gui.page.update()
                image_paths = {}
                mask_paths = {}
            else:
                self.count_results_txt.color = None
                self.gui.training_environment.start_button.disabled = False
                if self.gui.csp.model_path is not None:
                    self.gui.progress_bar_text.value = "Ready to Start"
                    self.gui.start_button.disabled = False
                self.gui.ready_to_start = True

        self.gui.csp.image_paths = image_paths
        self.gui.csp.mask_paths = mask_paths
        self.gui.canvas.set_mask_paths(self.gui.csp.mask_paths)
        self.gui.canvas.set_main_paths(self.gui.csp.image_paths)

    def load_images(self):
        """
        Load images to gallery in order and with names.
        """

        self.page.run_task(self.check_masks)

        self.gui.page.update()

        src = self.gui.csp.image_paths

        is_3d = any(
            tifffile.imread(channel_path).ndim == 3
            for outer_dict in src.values()
            for channel_path in outer_dict.values()
        )

        if platform.system() == "Linux" or is_3d:
            self.gui.csp.linux_images = convert_tiffs_to_png_parallel(self.gui.csp.image_paths)
            self.gui.csp.linux_or_3d = True
            src = self.gui.csp.linux_images

        self.selected_images_visualise = {}
        # Display groups with side-by-side images for linux_or_3d
        for image_id in src:
            cur_image_paths = src[image_id]
            self.selected_images_visualise[image_id] = {}
            for channel_id in cur_image_paths:
                self.selected_images_visualise[image_id][channel_id] = ft.Container(
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
                                content=ft.Container(ft.Stack([get_image(cur_image_paths[channel_id]), self.selected_images_visualise[image_id][channel_id]]), width=156, height=156),
                                on_tap=lambda e, img_id=image_id, c_id=channel_id:e.page.run_task(update_main_image ,img_id, c_id, self.gui),
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
            self.icon_check[image_id] = ft.Icon(ft.Icons.CHECK, color=ft.Colors.GREEN, size=17, visible=False,
                                                tooltip="Mask is available")
            self.icon_x[image_id] = ft.Icon(ft.Icons.CLOSE, size=17, visible=True, tooltip="Mask not available")
            self.update_mask_check(image_id)
            self.image_gallery.controls.append(ft.Column([ft.Row(
            [ft.Text(f"{image_id}", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), self.icon_check[image_id], self.icon_x[image_id]], spacing=2),
                                                      group_row], spacing=10, alignment=ft.MainAxisAlignment.CENTER))
        self.gui.progress_ring.visible = False
        self.gui.progress_ring.update()
        self.image_gallery.update()
        self.update_results_text()

    def update_mask_check(self, image_id):
        """
        Updates the symbol next to series number of image to a check or x, depending on if the corresponding image is available.
        Args:
            image_id: the id of the image to check mask availability
        """

        if self.gui.csp.mask_paths is not None and image_id in self.gui.csp.mask_paths and self.gui.csp.config.get_bf_channel() in self.gui.csp.mask_paths[image_id]:
            self.icon_check[image_id].visible = True
            self.icon_x[image_id].visible = False
        else:
            self.icon_check[image_id].visible = False
            self.icon_x[image_id].visible = True
        self.image_gallery.update()

    def update_all_masks_check(self):
        """
        Updates the symbol next to series number of image for every image_id in mask_paths.
        """
        if self.gui.csp.image_paths is not None:
            for image_id in self.gui.csp.image_paths:
                self.update_mask_check(image_id)


    def create_dir_row(self):
        """
        Creates the row for directory picking.
        """
        return ft.Row(
        [
            ft.Button(
                content="Open Directory",
                icon=ft.Icons.FOLDER_OPEN,
                on_click=lambda e: e.page.run_task(self.get_directory_result, e),
                disabled=self.gui.page.web,
            ),
        ], alignment=ft.MainAxisAlignment.START  # Change alignment to extend fully to the left
    )


    def create_files_row(self):
        """
        Creates the row for file picking.
        """
        return ft.Row(
        [
            ft.Button(
                content="Pick File",
                icon=ft.Icons.UPLOAD_FILE,
                on_click=lambda e: e.page.run_task(self.get_directory_result, e),
            )
        ], alignment=ft.MainAxisAlignment.START  # Change alignment to extend fully to the left
    )


    def create_handlers(self):
        """
        Creates the handlers.
        """
        #self.get_directory_dialog = ft.FilePicker(on_upload=lambda e: self.get_directory_result(e))
        #self.pick_files_dialog = ft.FilePicker(on_upload=lambda e: self.get_directory_result(e))
        #self.get_directory_dialog = ft.FilePicker()
        #self.pick_files_dialog = ft.FilePicker()

        #add the handlers to the page
        #self.gui.page.overlay.extend([ self.get_directory_dialog])

    def update_view(self,e):
        """
        Changes the visibility of the directory/file picking.
        """
        if int(e.data) == 1:
            self.is_lif = True
            self.gui.csp.config.set_lif_slider(True)
            self.files_row.visible = True
            self.directory_row.visible = False
        else:
            self.is_lif = False
            self.gui.csp.config.set_lif_slider(False)
            self.files_row.visible = False
            self.directory_row.visible = True

        self.gui.page.update()



    def create_directory_container(self):
        return ft.Container(
                content=ft.Stack(
                    [
                        ft.Container(
                            content=ft.Column(
                                [
                                    self.path_list_tile,
                                    self.lif_row
                                ]
                            )
                        ),
                        ft.Container(
                            content=ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.COPY,
                                    tooltip="Copy to clipboard",
                                    on_click=lambda e: e.page.run_task(copy_to_clipboard,self.gui.page,self.gui.directory.directory_path.value,"Directory path")
                                ),
                                alignment=ft.Alignment.TOP_RIGHT,
                            )
                        )
                    ]

                ),
                padding=10,
            )

    def disable_path_choosing(self):
        """
        Disables everything related with path choosing.
        """
        self.path_list_tile.disabled = True
        self.lif_row.disabled = True
        self.toggle_slider_state(self.lif_slider,disabled=True)

        self.gui.page.update()

    def enable_path_choosing(self):
        """
        Activates everything related with path choosing.
        """
        self.path_list_tile.disabled = False
        self.lif_row.disabled = False
        self.toggle_slider_state(self.lif_slider,disabled=False)
        self.gui.page.update()

    def toggle_slider_state(self,slider, disabled):
        """
        Toggles slider state if it is active or not.

        Args:
            slider: Slider object.
            disabled: Boolean if the slider should be disabled.
        """
        if disabled:
            slider.on_change = None
            slider.thumb_color = ft.Colors.GREY_400
            self.lif_slider_blocker.visible = True
            for control in slider.controls:
                control.color = ft.Colors.GREY_700
        else:
            slider.on_change = self.update_view
            slider.thumb_color = ft.Colors.BLUE_400
            self.lif_slider_blocker.visible = False
            for control in slider.controls:
                control.color = None

    async def check_masks(self):
        """
        Check if all masks are present (non-blocking).
        """
        if self.gui.csp.mask_paths is not None:
            bfc = self.gui.csp.config.get_bf_channel()

            loop = asyncio.get_event_loop()
            all_mask_present = await loop.run_in_executor(
                None,
                lambda: all(
                    image_id in self.gui.csp.mask_paths and bfc in self.gui.csp.mask_paths[image_id]
                    for image_id in self.gui.csp.image_paths
                )
            )

            if all_mask_present and self.gui.csp.image_paths is not None and len(self.gui.csp.image_paths) != 0 :
                fluorescence_button.visible = True
                fluorescence_button.update()
            else:
                fluorescence_button.visible = False
                fluorescence_button.update()

