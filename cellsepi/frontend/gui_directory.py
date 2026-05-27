import asyncio
import os
import pathlib
import platform
import shutil
import threading

import flet as ft
import numpy as np

from frontend.dialogs import ChoiceDialog
from frontend.gui_fluorescence import FluorescenceReadoutControl
from backend.constants import FileType, SourceType, APP_DIR, ModelType
from backend.data_util import consistent_hash, extract_from_directory, DirectoryManager
from backend.data_util import extract_from_file, load_directory, \
    convert_tiffs_to_png_parallel
from backend.expert_mode.event_manager import EventManager
from backend.expert_mode.pipeline_manager import PipelineRunningException
from frontend.gui_canvas import update_main_image


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


async def copy_to_clipboard(page, value: str, name: str):
    """
    Adds the value in to the clipboard and opens the snack_bar and say that it has been copied.
    Args:
        page: ft.Page object.
        value (str): Value to add to the clipboard.
        name (str): Name of the thing that got copied.
    """
    await ft.Clipboard().set(value)
    page.show_dialog(
        ft.SnackBar(ft.Text(f"{name} copied to clipboard!", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN))
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

    def __init__(self, gui=None):
        if gui is not None:
            super().__init__()
            self.gui = gui
            self.count_results_txt = ft.Text(value="Results: 0")
            self.directory_path = ft.Text(value='Directory Path', weight=ft.FontWeight.BOLD)
            self.formatted_path = ft.Text(value=format_directory_path(self.directory_path.value),
                                          weight=ft.FontWeight.BOLD, tooltip="Copy to clipboard")
            self.file_type = self.gui.csp.config.get_file_type_slider()

            index = np.where([elem is self.file_type for elem in FileType])[0].item()

            self.file_type_slider = ft.CupertinoSlidingSegmentedButton(
                selected_index=index,
                thumb_color=ft.Colors.BLUE_400,
                on_change=self.update_view,
                padding=ft.Padding.symmetric(vertical=0, horizontal=0),
                controls=[
                    ft.Text(file_type.value.name) for file_type in FileType
                ],
            )
            self.image_gallery = ft.ListView()
            self.path_list_tile = self.create_path_list_tile()
            # self.get_directory_dialog = None
            # self.pick_files_dialog = None
            # self.create_handlers()
            self.directory_row = self.create_dir_row()
            self.files_row = self.create_files_row()
            self.images_and_mask_export_button = ft.Button(
                content="Export",
                icon=ft.Icons.FILE_DOWNLOAD,
                tooltip="Export Images and Masks",
                disabled=True,
                visible=True
            )
            self.buttons_row = ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    self.directory_row,
                                    self.files_row,
                                ]
                            ),
                            ft.Row(
                                [
                                    self.images_and_mask_export_button
                                ]
                            )
                        ],
                    )
                ],
                expand=True,
                alignment=ft.MainAxisAlignment.END
            )
            self.lif_slider_blocker = ft.Container(
                height=30,
                expand=True,
                bgcolor=ft.Colors.TRANSPARENT,
                on_click=None,
                visible=False,
            )
            self.file_type_selection_row = ft.Column(
                [
                    ft.Stack(
                        [
                            self.file_type_slider,
                            self.lif_slider_blocker
                        ]
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            )
            self.content = self.create_directory_container()
            self.output_dir = False
            self.is_file_type_supported = True
            self.update_source_type(file_type=self.file_type)
            self.selected_images_visualise = {}
            self.icon_check = {}
            self.icon_x = {}

    def create_path_list_tile(self):
        def on_enter_text(text_filed):
            text_filed.color = ft.Colors.BLUE_400
            text_filed.update()

        def on_exit_text(text_filed):
            text_filed.color = None
            text_filed.update()

        return ft.ListTile(leading=ft.Icon(icon=ft.Icons.FOLDER_OPEN),
                           title=ft.GestureDetector(content=self.formatted_path,
                                                    on_tap=lambda e: e.page.run_task(copy_to_clipboard, page=self.page,
                                                                                     value=self.gui.directory.directory_path.value,
                                                                                     name="Directory path"),
                                                    on_enter=lambda e: on_enter_text(self.formatted_path),
                                                    on_exit=lambda e: on_exit_text(self.formatted_path)),
                           subtitle=self.count_results_txt,
                           width=310
                           )

    def update_results_text(self):
        self.count_results_txt.value = f"Results: {len(self.gui.csp.image_paths)}"
        self.count_results_txt.update()

    async def get_directory_result(self, e: ft.Event[ft.Button]):
        """
        Checks if the picked directory or file exists and if it worked updates everything with the new values.
        builds the canvas container for the file results on the right column of the GUI
        """
        # initiate filepicker and fetch files/directory
        self.gui.progress_ring.visible = True

        previous_directory = pathlib.Path(self.directory_path.value) \
            if self.directory_path.value != "Directory Path" \
            else pathlib.Path.home() / "Downloads"
        if self.source_type == SourceType.FILE:
            allowed_extensions = self.file_type.value.extensions
            files = await ft.FilePicker().pick_files(
                initial_directory=str(previous_directory),
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=allowed_extensions
            )
        elif self.source_type == SourceType.DIRECTORY:
            files = await ft.FilePicker().get_directory_path(
                initial_directory=str(previous_directory),
            )
        else:
            raise Exception(f"Source type {self.source_type} not supported!")

        if files is None or len(files) == 0:
            self.gui.progress_ring.visible = False
            return

        self.image_gallery.controls.clear()
        self.gui.canvas.reset_image()
        # the window of the image display is cleared of all content
        self.gui.csp.image_id = None
        self.gui.csp.channel_id = None
        self.gui.open_button.visible = False
        self.gui.start_button.disabled = True
        self.gui.training_environment.start_button.disabled = True
        FluorescenceReadoutControl().visible = False
        self.gui.progress_bar_text.value = "Waiting for Input"
        self.gui.progress_bar.value = 0
        self.gui.contrast_slider.disabled = True
        self.gui.brightness_slider.disabled = True
        self.gui.csp.current_channel_prefix = self.gui.csp.config.get_channel_prefix()
        self.gui.csp.current_mask_suffix = self.gui.csp.config.get_mask_suffix()
        self.gui.contrast_slider.value = 1
        self.gui.brightness_slider.value = 1
        self.gui.diameter_display.opacity = 0.5
        if not platform.system() == "Linux":
            self.gui.page.window.progress_bar = -1
        self.gui.page.update()
        # ToDo EK: Maybe only reset screen if loading did succeed?
        # differentiate between the lif and tiff case, as there are two different file formats
        if self.source_type == SourceType.FILE:
            # is a file
            # get data
            fetched_date = files[0]
            path = str(fetched_date.path)
        elif self.source_type == SourceType.DIRECTORY:
            # is a directory
            path = files
        else:
            raise Exception(f"Source type {self.source_type} not supported!")
        self.page.run_thread(self.select_dir_and_update, path)

    def select_dir_and_update(self, path):
        if path:
            self.directory_path.value = path
            self.select_directory(path, self.file_type, self.gui.csp.config.get_channel_prefix(), self.gui.csp.config.get_mask_suffix())
            self.load_images()
        else:
            self.image_gallery.controls.clear()
            self.image_gallery.update()

        self.formatted_path.value = format_directory_path(self.directory_path.value)
        if self.output_dir or not self.is_file_type_supported:
            self.formatted_path.color = ft.Colors.RED
            self.gui.diameter_text.value = 0.0
            self.gui.diameter_display.update()
        else:
            self.gui.average_diameter.clear_cache()
            self.gui.page.run_task(self.gui.average_diameter.get_avg_diameter)
            self.gui.diameter_display.opacity = 1
            self.gui.diameter_display.update()
            self.formatted_path.color = None
        self.formatted_path.update()

    def select_directory(
            self,
            path,
            file_type: FileType,
            channel_prefix: str,
            mask_suffix: str = "_seg",
            event_manager: EventManager = None,
            overwrite: bool = True,
    ):
        """
            Gets the working directory and copies the images in there.

            Args:
                path (str): the selected path
                file_type (FileType): the type of the image (lif, tiff, nd2, czi, etc.)
                channel_prefix (str): the channel prefix
                event_manager (EventManager): the event manager which is used when the methode gets started as a module.
                overwrite (bool): if the system should overwrite already existing temp files.
        """
        if event_manager is None:
            self.is_file_type_supported = True
        path = pathlib.Path(path)

        image_source_identifier = consistent_hash(str(path.absolute()))

        working_directory = (DirectoryManager(APP_DIR)
                             .get_cache_dir_path(f"tmp_{file_type.name}_{image_source_identifier}/", makedir=False))

        # case empty folder
        if file_type.value.source == SourceType.DIRECTORY:
            has_images = any(
                any(str(file).lower().endswith(ext) for ext in file_type.value.extensions)
                for file in path.iterdir()
                if file.is_file()
            )

            if not has_images:
                if event_manager is None:
                    self.gui.page.show_dialog(
                        ft.SnackBar(ft.Text("The directory is empty.", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED))
                    self.output_dir = True
                    self.gui.page.update()
                    self.gui.csp.image_paths = {}
                    self.gui.csp.linux_images = {}
                    self.gui.csp.mask_paths = {}
                    self.gui.ready_to_start = False
                    self.gui.progress_ring.visible = False
                    return None
                else:
                    raise PipelineRunningException("Loading Error", f"The directory is empty.")

        if working_directory.exists():
            if event_manager is None:
                dialog = ChoiceDialog(
                    page=self.page,
                    title="Data already imported",
                    text="Do you want to overwrite the existing data?\nThis will erase all intermediate data and reload the original file.",
                    option_1="Overwrite",
                    option_2="Keep existing",
                )

                dialog_result = []
                dialog_finished = threading.Event()

                async def show_dialog_async():
                    res = await dialog.show()
                    dialog_result.append(res)
                    dialog_finished.set()

                self.page.run_task(show_dialog_async)

                dialog_finished.wait()

                overwrite = (dialog_result[0] == 0)

        if overwrite:
            if working_directory.exists():
                shutil.rmtree(working_directory)
            os.makedirs(working_directory, exist_ok=True)

            match file_type.value.source:
                case SourceType.FILE:  # File Case

                    if event_manager is None:
                        self.output_dir = False

                    if any(["".join(path.suffixes).lower() == f".{ext}" for ext in file_type.value.extensions]):
                        # Extract from the file all the single series images and extract to .tif, .tiff and .npy files into subdirectory
                        extract_from_file(
                            file_type=file_type,
                            path=path,
                            target_dir=working_directory,
                            channel_prefix=channel_prefix,
                            event_manager=event_manager
                        )
                    else:
                        if event_manager is not None:
                            raise PipelineRunningException("Type Error",
                                                           f"Expected filetype: {file_type.extension_string}")
                        else:
                            self.is_file_type_supported = False
                case SourceType.DIRECTORY:  # Directory Case
                    if event_manager is None:
                        self.output_dir = False

                    extract_from_directory(
                        file_type=file_type,
                        path=path,
                        target_dir=working_directory,
                        channel_prefix=channel_prefix,
                        mask_suffix=mask_suffix,
                        event_manager=event_manager
                    )
                case _:
                    raise Exception(f"File type {file_type} currently not supported!")

        if event_manager is not None:
            return working_directory
        else:
            self.gui.csp.working_directory = working_directory
            self.set_paths()
            return None

    def set_paths(self):
        """
        Updates the image and mask paths in csp (CellSePi).
        """
        ms = self.gui.csp.config.get_mask_suffix()
        working_directory = self.gui.csp.working_directory

        if not self.is_file_type_supported:
            self.gui.ready_to_start = False
            self.gui.page.show_dialog(ft.SnackBar(
                ft.Text("The selected file is not supported!", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED))
            image_paths = {}
            mask_paths = {}
            self.gui.progress_ring.visible = False
            self.gui.page.update()
        else:
            image_paths, mask_paths = load_directory(working_directory, mask_suffix=ms)

            if len(image_paths) == 0:
                self.gui.ready_to_start = False
                self.gui.page.show_dialog(
                    ft.SnackBar(ft.Text("The directory contains no valid files with the current channel prefix!",
                                        color=ft.Colors.WHITE), bgcolor=ft.Colors.RED))
                self.gui.page.update()
                self.count_results_txt.color = ft.Colors.RED
                self.gui.progress_ring.visible = False
                if not self.file_type:
                    os.rmdir(self.gui.csp.working_directory)
            else:
                self.count_results_txt.color = None
                self.gui.training_environment.start_button.disabled = False
                if ((self.gui.csp.model_path is not None and (
                        self.gui.csp.model_type == ModelType.CUSTOM))
                        or self.gui.csp.model_type == ModelType.CELLPOSE_CYTO or self.gui.csp.model_type == ModelType.CELLPOSE_NUCLEI or self.gui.csp.model_type == ModelType.CELLPOSE_SAM):
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

        src = convert_tiffs_to_png_parallel(self.gui.csp.image_paths)

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
                                content=ft.Container(
                                    ft.Stack(
                                        [
                                            get_image(cur_image_paths[channel_id]),
                                            self.selected_images_visualise[image_id][channel_id]
                                        ]
                                    ), width=156, height=156),
                                on_tap=lambda e, img_id=image_id,
                                              c_id=channel_id: e.page.run_task(update_main_image,
                                                                               img_id,
                                                                               c_id,
                                                                               self.gui),
                            ),
                            ft.Text(channel_id, size=10, text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                        tight=True
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
            self.update_mask_check(image_id, False)
            self.image_gallery.controls.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(f"{image_id}", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                                self.icon_check[image_id],
                                self.icon_x[image_id]
                            ], spacing=2),
                        group_row
                    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)
            )
            self.page.update()

        self.gui.progress_ring.visible = False
        self.gui.progress_ring.update()
        self.images_and_mask_export_button.disabled = False
        self.images_and_mask_export_button.update()
        self.update_results_text()

    def update_mask_check(self, image_id, update=True):
        """
        Updates the symbol next to series number of image to a check or x, depending on if the corresponding image is available.
        Args:
            image_id: the id of the image to check mask availability
            update: says if the method should update the icons
        """

        if self.gui.csp.mask_paths is not None and image_id in self.gui.csp.mask_paths and self.gui.csp.config.get_bf_channel() in \
                self.gui.csp.mask_paths[image_id]:
            self.icon_check[image_id].visible = True
            self.icon_x[image_id].visible = False
        else:
            self.icon_check[image_id].visible = False
            self.icon_x[image_id].visible = True
        if update:
            self.icon_check[image_id].update()
            self.icon_x[image_id].update()

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

    async def update_view(self, e):
        """
        Changes the visibility of the directory/file picking.
        """
        self.file_type = list(FileType)[int(e.data)]
        self.gui.csp.config.set_file_type_slider(self.file_type)

        self.update_source_type(self.file_type)

        self.gui.page.update()

    def update_source_type(self, file_type: FileType):
        self.source_type = file_type.value.source
        if self.source_type == SourceType.DIRECTORY:
            self.files_row.visible = False
            self.directory_row.visible = True
        else:
            self.files_row.visible = True
            self.directory_row.visible = False

    def create_directory_container(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row([ft.Column([self.path_list_tile]), self.buttons_row]),
                    self.file_type_selection_row
                ]
            ),
            padding=10,
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )

    def disable_path_choosing(self):
        """
        Disables everything related with path choosing.
        """
        self.path_list_tile.disabled = True
        self.buttons_row.disabled = True
        self.file_type_selection_row.disabled = True
        self.toggle_slider_state(self.file_type_slider, disabled=True)

        self.gui.page.update()

    def enable_path_choosing(self):
        """
        Activates everything related with path choosing.
        """
        self.path_list_tile.disabled = False
        self.buttons_row.disabled = False
        self.file_type_selection_row.disabled = False
        self.toggle_slider_state(self.file_type_slider, disabled=False)
        self.gui.page.update()

    def toggle_slider_state(self, slider, disabled):
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
            fluorescence_readout_control = FluorescenceReadoutControl()

            if all_mask_present and self.gui.csp.image_paths is not None and len(self.gui.csp.image_paths) != 0:
                fluorescence_readout_control.visible = True
                fluorescence_readout_control.update()
            else:
                fluorescence_readout_control.visible = False
                fluorescence_readout_control.update()
