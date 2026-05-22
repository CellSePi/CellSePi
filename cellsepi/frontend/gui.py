import asyncio
import os
import platform
import shutil
import threading
import traceback
from datetime import datetime

import flet as ft
import importlib.util
import inspect
import pathlib

from backend.constants import DirectoryManager
from backend.expert_mode.module import Module
from image_editing_view import ImageEditingView
from backend.avg_diameter import AverageDiameter
from frontend.expert_mode.gui_builder import Builder
from frontend.expert_mode.gui_expert_environment import ExpertEnvironment, PipelineStateListener
from frontend.gui_segmentation import GUISegmentation
from frontend.gui_options import Options
from frontend.gui_config import GUIConfig
from frontend.gui_directory import DirectoryCard, copy_to_clipboard
from backend.cellsepi import CellSePi
from frontend.gui_image_tuning import GUIAutoImageTuning
from frontend.gui_training_environment import Training
from frontend.gui_page_overlay import PageOverlay
from frontend.expert_mode.expert_constants import MODULE_REGISTRY

def check_for_file_picker_support():
    if not platform.system() == "Linux":
        return True
    for tool in ["zenity", "qarma", "kdialog"]:
        if shutil.which(tool) is not None:
            return True

    return False
class GUI:
    """
    Class GUI to handle the complete GUI and their attributes, also contains the CellSePi class and updates their attributes
    """

    def __init__(self, page: ft.Page):
        self.csp: CellSePi = CellSePi()
        self.error_loading_plugin = self.load_plugins(self.csp.plugins_dir)
        self.page = page
        self.directory = DirectoryCard(self)
        self.average_diameter = AverageDiameter(self)
        self.cancel_event = threading.Event()
        self.closing_event = False
        self.training_event = threading.Event()
        self.expert_running_event = threading.Event()
        self.readout_event = threading.Event()
        self.page.window.prevent_close = True
        self.page.window.on_event = lambda e: self.page.run_task(self.handle_closing_event, e)
        self.page.window.width = 1440
        self.page.window.height = 800
        self.page.title = "CellSePi"
        self.canvas = ImageEditingView(
            on_mask_change=lambda img_id, mask_added_or_removed: self.mask_update(img_id, mask_added_or_removed))
        self.canvas.mask_color = self.csp.config.get_mask_color()
        self.canvas.outline_color = self.csp.config.get_outline_color()
        self.canvas.mask_suffix = self.csp.config.get_mask_suffix()
        self.op = Options(self)
        self.ex_mode = ExpertEnvironment(self)
        gui_config = GUIConfig(self)
        self.gui_config = gui_config.create_profile_container()
        self.segmentation = GUISegmentation(self)
        seg_card, start_button, open_button, progress_bar, progress_bar_text, cancel_segmentation = self.segmentation.create_segmentation_card()
        self.cancel_segmentation = cancel_segmentation
        self.ready_to_start = False
        self.segmentation_card = seg_card
        self.open_button = open_button
        self.start_button = start_button
        self.progress_bar = progress_bar
        self.progress_bar_text = progress_bar_text
        self.progress_ring = ft.ProgressRing(visible=False)
        self.closing_sheet = ft.Stack([
            ft.Column([ft.Container(ft.ProgressRing(), alignment=ft.Alignment.CENTER)],
                      alignment=ft.MainAxisAlignment.CENTER,
                      ),
        ])

        self.brightness_slider = ft.Slider(
            min=0, max=2.0, value=1.0, disabled=True,
            on_change_end=lambda e: e.page.run_task(self.update_adjusted_image)
        )
        self.contrast_slider = ft.Slider(
            min=0, max=2.0, value=1.0, disabled=True,
            on_change_end=lambda e: e.page.run_task(self.update_adjusted_image)
        )

        self.auto_image_tuning = GUIAutoImageTuning(self)
        self.auto_brightness_contrast = ft.IconButton(icon=ft.Icons.AUTO_FIX_HIGH, icon_color=ft.Colors.GREY_700,
                                                      style=ft.ButtonStyle(
                                                          shape=ft.RoundedRectangleBorder(radius=12),
                                                      ), on_click=lambda e: e.page.run_task(
                self.auto_image_tuning.pressed), tooltip="Auto brightness and contrast")
        self.brightness_icon = ft.Icon(icon=ft.Icons.SUNNY, tooltip="Brightness")
        self.contrast_icon = ft.Icon(icon=ft.Icons.CONTRAST, tooltip="Contrast")
        self.diameter_text = ft.Text("0.00", size=14, weight=ft.FontWeight.BOLD, tooltip="Copy to clipboard")
        self.diameter_display = ft.Container(
            content=ft.Row([ft.Icon(icon=ft.Icons.STRAIGHTEN_ROUNDED, tooltip="Average diameter"),
                            ft.GestureDetector(content=self.diameter_text,
                                               on_tap=lambda e: e.page.run_task(copy_to_clipboard, page=self.page,
                                                                                value=str(self.diameter_text.value),
                                                                                name="Average diameter"),
                                               on_enter=lambda e: self.on_enter_diameter(),
                                               on_exit=lambda e: self.on_exit_diameter()), ]),
            border_radius=12,
            padding=8,
            opacity=0.5,
            visible=True,
        )
        self.training_environment = Training(self)
        self.ref_seg_environment = ft.Ref[ft.Column]()
        self.ref_training_environment = ft.Ref[ft.Column]()
        self.builder_environment = Builder(self.page)
        self.builder_environment.pipeline_running_event = self.expert_running_event
        pipeline_state_listener = PipelineStateListener(self)
        self.builder_environment.pipeline_gui.pipeline.event_manager.subscribe(listener=pipeline_state_listener)
        self.ref_builder_environment = ft.Ref[ft.Column]()
        self.ref_gallery_environment = ft.Ref[ft.Column]()
        if self.csp.config.get_auto_button():
            self.page.run_task(self.auto_image_tuning.pressed)

        def close_banner(e):
            e.control.page.pop_dialog()
        async def launch_help_link(e):
            await page.launch_url("https://github.com/CellSePi/CellSePi/blob/main/README.md")
        def ignore_warning(e):
            e.control.page.pop_dialog()
            self.csp.config.set_ignore_warning()
        self.zenity_warning = ft.Banner(
            bgcolor=ft.Colors.RED,
            leading=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.WHITE_60, size=40),
            content=ft.Text(
                "System tool 'zenity' (or similar) was not found.\n"
                "Native file selection might be unreliable or not work at all.\n"
                "Please consider installing 'zenity' via your package manager.",
                color=ft.Colors.WHITE
            ),
            actions=[
                ft.TextButton("Help",style=ft.ButtonStyle(color=ft.Colors.WHITE),on_click=launch_help_link),
                ft.TextButton("Dismiss",style=ft.ButtonStyle(color=ft.Colors.WHITE), on_click=close_banner),
                ft.TextButton("Ignore warning", style=ft.ButtonStyle(color=ft.Colors.WHITE_60), on_click=ignore_warning, tooltip="Do not show this warning again in the future"),
            ],
        )

    def build(self):
        """
        Build up the main page of the GUI
        """
        self.page.add(
            ft.Column(
                [
                    ft.Row(
                        [
                            # LEFT COLUMN that handles all elements on the left side(canvas,switch_mask,segmentation)
                            ft.Column(
                                [
                                    self.canvas,
                                    ft.Row(
                                        [
                                            self.gui_config,
                                            ft.Column(
                                                [
                                                    ft.Card(content=ft.Container(content=ft.Column(
                                                        [
                                                            ft.Row(
                                                                [
                                                                    self.brightness_icon,
                                                                    ft.Container(self.brightness_slider, padding=-15)
                                                                ]
                                                            ),
                                                            ft.Row(
                                                                [
                                                                    self.contrast_icon,
                                                                    ft.Container(self.contrast_slider, padding=-15)
                                                                ]
                                                            )
                                                        ]
                                                    ), padding=10)),
                                                    ft.Row(
                                                        [
                                                            ft.Card(content=self.auto_brightness_contrast),
                                                            ft.Card(content=self.diameter_display)
                                                        ]
                                                    )
                                                ])
                                        ]),

                                    self.segmentation_card
                                ],
                                expand=6,
                                alignment=ft.MainAxisAlignment.START,
                                visible=True,
                                ref=self.ref_seg_environment
                            ),
                            ft.Column(
                                [
                                    self.training_environment.add_parameter_container(),
                                    self.training_environment.create_training_card()
                                ],
                                expand=6,
                                alignment=ft.MainAxisAlignment.START,
                                visible=False,
                                ref=self.ref_training_environment
                            ),
                            ft.Column(
                                [
                                    self.builder_environment.builder_page_stack
                                ],
                                expand=True,
                                visible=False,
                                ref=self.ref_builder_environment
                            ),
                            # RIGHT COLUMN that handles gallery and directory_card
                            ft.Column(
                                [
                                    self.directory,
                                    ft.Card(
                                        content=ft.Stack(
                                            [
                                                ft.Container(self.directory.image_gallery, padding=20),
                                                ft.Container(self.progress_ring,
                                                             alignment=ft.Alignment.CENTER,
                                                             ignore_interactions=True)
                                            ]
                                        ),
                                        expand=True
                                    ),
                                ],
                                expand=4,
                                ref=self.ref_gallery_environment
                            ),
                            ft.Column(
                                [
                                    self.op,
                                    self.training_environment,
                                    self.ex_mode
                                ]
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        expand=True,
                    ),
                ],
                expand=True
            ),
        )
        # set the colors for the review module from the config file
        MODULE_REGISTRY["REVIEW"].update_class(mask_color=self.csp.config.get_mask_color(),
                                               outline_color=self.csp.config.get_outline_color())
        if self.error_loading_plugin:
            self.page.show_dialog(
                ft.SnackBar(
                    ft.Text(
                        "Some plugins couldn't be loaded. Check 'plugin_errors.txt' in the plugins folder for details.",
                        color=ft.Colors.WHITE
                    ),
                    bgcolor=ft.Colors.RED
                )
            )
            self.page.update()

        if not check_for_file_picker_support() and not self.csp.config.get_ignore_warning():
            self.page.show_dialog(self.zenity_warning)

    def mask_update(self, image_id, mask_added_or_removed):
        if mask_added_or_removed:
            self.directory.update_mask_check(image_id)
            self.page.run_task(self.directory.check_masks)
        self.diameter_text.value = self.average_diameter.get_avg_diameter()
        self.diameter_text.update()

    async def handle_closing_event(self, e, saved_checked: bool = False):
        """
        Handle the closing event of Flet GUI.
        """
        if e.type == ft.WindowEventType.CLOSE and not self.closing_event:
            if not await self.builder_environment.pipeline_storage.check_saved() and not saved_checked:
                def cancel_dialog(a):
                    cupertino_alert_dialog.open = False
                    a.control.page.update()

                def ok_dialog(a, gui):
                    cupertino_alert_dialog.open = False
                    a.control.page.update()
                    self.page.run_task(self.handle_closing_event, e, True)

                cupertino_alert_dialog = ft.CupertinoAlertDialog(
                    title=ft.Text("Expert Mode:\nUnsaved Changes"),
                    content=ft.Text(
                        "Closing CellSePi will discard any unsaved changes to the currently opened pipeline."),
                    actions=[
                        ft.CupertinoDialogAction(
                            "Cancel", default=True, on_click=cancel_dialog
                        ),
                        ft.CupertinoDialogAction("Ok", destructive=True, on_click=lambda a: ok_dialog(a, self)),
                    ],
                )
                self.page.overlay.append(cupertino_alert_dialog)
                cupertino_alert_dialog.open = True
                self.page.update()
                return
            self.closing_event = True
            overlay = PageOverlay(self.page, content=self.closing_sheet, modal=True)
            overlay.open()
            if self.csp.segmentation_running:
                self.cancel_segmentation()
                await asyncio.to_thread(self.cancel_event.wait)
            if self.csp.training_running:
                await asyncio.to_thread(self.training_event.wait)
            if self.csp.readout_running:
                await asyncio.to_thread(self.readout_event.wait)
            if self.builder_environment.pipeline_gui.pipeline.running:
                self.builder_environment.cancel()
                await asyncio.to_thread(self.expert_running_event.wait)
            self.page.window.prevent_close = False
            self.page.window.on_event = None
            self.page.update()

            DirectoryManager().streamline_cache()

            self.page.run_task(self.handle_window_closing)

    def on_enter_diameter(self):
        self.diameter_text.color = ft.Colors.BLUE_400
        self.diameter_text.update()

    def on_exit_diameter(self):
        self.diameter_text.color = None
        self.diameter_text.update()

    async def handle_window_closing(self):
        await self.page.window.destroy()
        os._exit(0)

    async def update_adjusted_image(self):
        self.canvas.brightness = round(self.brightness_slider.value, 2)
        self.canvas.contrast = round(self.contrast_slider.value, 2)
        await self.canvas.update_main_image_with_brightness_contrast(
            self.csp.image_paths[self.csp.image_id][self.csp.channel_id])

    def load_plugins(self, directory):
        plugin_dir = pathlib.Path(directory)
        error_log_path = plugin_dir / "plugin_errors.txt"
        errors_found = False

        # collect gui names of the modules
        used_gui_names = {
            cls.gui_config().name
            for cls in MODULE_REGISTRY.values()
            if hasattr(cls, 'gui_config')
        }

        for path in pathlib.Path(directory).rglob("*.py"):
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)

            try:
                spec.loader.exec_module(module)
            except Exception as e:
                errors_found = True
                with open(error_log_path, "a", encoding="utf-8") as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] Error loading '{path.name}':\n")
                    f.write(traceback.format_exc())
                    f.write("-" * 50 + "\n")
                continue

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Module) and obj is not Module:

                    try:
                        gui_name = obj.gui_config().name
                    except AttributeError:
                        continue

                    if gui_name in used_gui_names:  # check if the new modules gui names are duplicates of already registered ones
                        errors_found = True
                        with open(error_log_path, "a", encoding="utf-8") as f:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            f.write(
                                f"[{timestamp}] Error: Duplicate GUI name '{gui_name}' found in '{path.name}' (Class: {obj.__name__}). Module skipped.\n")
                            f.write("-" * 50 + "\n")
                        continue

                    used_gui_names.add(gui_name)
                    unique_id = f"{path.stem}.{obj.__name__}"
                    MODULE_REGISTRY[unique_id] = obj

        return errors_found
