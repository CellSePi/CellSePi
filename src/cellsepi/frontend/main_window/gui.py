import asyncio
import multiprocessing
import os
import queue
import threading
import flet as ft

from image_editing_view import ImageEditingView
from cellsepi.backend.main_window.avg_diameter import AverageDiameter
from cellsepi.frontend.main_window.expert_mode.gui_builder import Builder
from cellsepi.frontend.main_window.expert_mode.gui_expert_environment import ExpertEnvironment, PipelineStateListener
from cellsepi.frontend.main_window.gui_page_overlay import PageOverlay
from cellsepi.frontend.main_window.gui_segmentation import GUISegmentation
from cellsepi.frontend.main_window.gui_options import Options
from cellsepi.frontend.main_window.gui_config import GUIConfig
from cellsepi.frontend.main_window.gui_directory import DirectoryCard, copy_to_clipboard
from cellsepi.backend.main_window.cellsepi import CellSePi
from cellsepi.frontend.main_window.gui_mask import error_banner, reset_mask
from cellsepi.backend.main_window.image_tuning import AutoImageTuning
from cellsepi.frontend.main_window.gui_training_environment import Training
from cellsepi.frontend.main_window.gui_page_overlay import PageOverlay
from cellsepi.frontend.main_window.expert_mode.expert_constants import ModuleType

class GUI:
    """
    Class GUI to handle the complete GUI and their attributes, also contains the CellSePi class and updates their attributes
    """
    def __init__(self,page: ft.Page):
        self.csp: CellSePi = CellSePi()
        self.page = page
        self.directory = DirectoryCard(self)
        self.average_diameter = AverageDiameter(self)
        self.cancel_event = None
        self.closing_event = False
        self.training_event = None
        self.expert_running_event = None
        self.readout_event = None
        self.page.window.prevent_close = True
        self.page.window.on_event = lambda e: self.handle_closing_event(e)
        self.page.window.width = 1440
        self.page.window.height = 800
        self.page.run_task(self.handle_window_centering)
        self.page.window.min_width = self.page.window.width
        self.page.window.min_height = self.page.window.height
        self.page.title = "CellSePi"
        self.canvas = ImageEditingView(on_mask_change=lambda img_id: self.mask_update(img_id))
        self.canvas.mask_color=self.csp.config.get_mask_color()
        self.canvas.outline_color=self.csp.config.get_outline_color()
        self.op = Options(self)
        self.ex_mode = ExpertEnvironment(self)
        gui_config = GUIConfig(self)
        self.gui_config = gui_config.create_profile_container()
        self.segmentation = GUISegmentation(self)
        seg_card,start_button,open_button,progress_bar,progress_bar_text,cancel_segmentation = self.segmentation.create_segmentation_card()
        self.cancel_segmentation = cancel_segmentation
        self.ready_to_start = False
        self.segmentation_card = seg_card
        self.open_button = open_button
        self.start_button = start_button
        self.progress_bar = progress_bar
        self.progress_bar_text = progress_bar_text
        self.progress_ring = ft.ProgressRing(visible=False)
        self.closing_sheet = ft.Stack([
            ft.Column([ft.Container(ft.ProgressRing(),alignment=ft.Alignment.CENTER)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ])

        self.brightness_slider = ft.Slider(
            min=0, max=2.0, value=1.0, disabled= True,
            on_change=lambda e: e.page.run_task(self.update_adjusted_image)
        )
        self.contrast_slider = ft.Slider(
            min=0, max=2.0, value=1.0, disabled= True,
            on_change=lambda e: e.page.run_task(self.update_adjusted_image)
        )

        self.auto_image_tuning = AutoImageTuning(self)
        self.auto_brightness_contrast = ft.IconButton(icon=ft.Icons.AUTO_FIX_HIGH,icon_color=ft.Colors.GREY_700,style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=12),
                ),on_click=lambda e: e.page.run_task(self.auto_image_tuning.pressed),tooltip="Auto brightness and contrast")
        self.brightness_icon = ft.Icon(icon=ft.Icons.SUNNY,tooltip="Brightness")
        self.contrast_icon = ft.Icon(icon=ft.Icons.CONTRAST,tooltip="Contrast")
        self.diameter_text = ft.Text("0.00", size=14, weight=ft.FontWeight.BOLD,tooltip="Copy to clipboard")
        self.diameter_display = ft.Container(
            content=ft.Row([ft.Icon(icon=ft.Icons.STRAIGHTEN_ROUNDED, tooltip="Average diameter"), ft.GestureDetector(content=self.diameter_text,on_tap=lambda e: e.page.run_task(copy_to_clipboard,page=self.page,value=str(self.diameter_text.value),name="Average diameter"),on_enter=lambda e:self.on_enter_diameter(),on_exit=lambda e:self.on_exit_diameter()),]),
            border_radius=12,
            padding=8,
            opacity=0.5,
            visible=True,
        )
        self.training_environment=Training(self)
        self.ref_seg_environment = ft.Ref[ft.Column]()
        self.ref_training_environment = ft.Ref[ft.Column]()
        self.builder_environment = Builder(self.page)
        pipeline_state_listener = PipelineStateListener(self)
        self.builder_environment.pipeline_gui.pipeline.event_manager.subscribe(listener=pipeline_state_listener)
        self.ref_builder_environment = ft.Ref[ft.Column]()
        self.ref_gallery_environment = ft.Ref[ft.Column]()
        if self.csp.config.get_auto_button():
             self.page.run_task(self.auto_image_tuning.pressed)

    def build(self):
        """
        Build up the main page of the GUI
        """
        self.page.add(
            ft.Column(
                [
                    ft.Row([
                            #LEFT COLUMN that handles all elements on the left side(canvas,switch_mask,segmentation)
                            ft.Column(
                        [
                                    self.canvas,
                                    ft.Row([self.gui_config, ft.Column([ft.Card(content=ft.Container(content=ft.Column(
                                        [ft.Row([self.brightness_icon, ft.Container(self.brightness_slider, padding=-15)]),
                                         ft.Row([self.contrast_icon, ft.Container(self.contrast_slider, padding=-15)])]), padding=10)),
                                                                        ft.Row([ft.Card(content=self.auto_brightness_contrast),
                                                                                ft.Card(content=self.diameter_display)])])
                                            ]),
                                    self.segmentation_card
                                ],
                                expand=True,
                                alignment=ft.MainAxisAlignment.START,
                                visible=True,ref=self.ref_seg_environment
                            ),
                            ft.Column(
                        [
                                    self.training_environment.add_parameter_container(),
                                    self.training_environment.create_training_card()
                                ],
                                expand=True,
                                alignment=ft.MainAxisAlignment.START,
                                visible=False,ref=self.ref_training_environment
                            ),
                            ft.Column([self.builder_environment.builder_page_stack],expand=True,visible=False,ref=self.ref_builder_environment),
                            #RIGHT COLUMN that handles gallery and directory_card
                            ft.Column(
                                [
                                    self.directory,
                                    ft.Card(
                                        content=ft.Stack([ft.Container(self.directory.image_gallery,padding=20), ft.Container(self.progress_ring, alignment=ft.Alignment.CENTER, ignore_interactions=True)]),
                                        expand=True
                                    ),
                                ],
                                expand=True,ref=self.ref_gallery_environment
                            ),
                            ft.Column([self.op, self.training_environment,self.ex_mode
                                       ]),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        expand=True,
                    ),
                ],
                expand=True
            ),
        )
        #set the colors for the review module from the config file
        ModuleType.REVIEW.value.mask_color = self.csp.config.get_mask_color()
        ModuleType.REVIEW.value.outline_color = self.csp.config.get_outline_color()
        ModuleType.REVIEW.value.update_class()

    def mask_update(self, image_id):
        self.directory.update_mask_check(image_id)
        self.diameter_text.value = self.average_diameter.get_avg_diameter()
        self.diameter_text.update()

    def handle_closing_event(self, e,saved_checked:bool=False):
        """
        Handle the closing event of Flet GUI.
        """
        if e.type == ft.WindowEventType.CLOSE and not self.closing_event:

            if not self.builder_environment.pipeline_storage.check_saved() and not saved_checked:
                def cancel_dialog(a):
                    cupertino_alert_dialog.open = False
                    a.control.page.update()

                def ok_dialog(a,gui):
                    cupertino_alert_dialog.open = False
                    a.control.page.update()
                    gui.handle_closing_event(e,True)

                cupertino_alert_dialog = ft.CupertinoAlertDialog(
                    title=ft.Text("Expert Mode:\nUnsaved Changes"),
                    content=ft.Text("Closing CellSePi will discard any unsaved changes to the currently opened pipeline."),
                    actions=[
                        ft.CupertinoDialogAction(
                            "Cancel", is_default_action=True, on_click=cancel_dialog
                        ),
                        ft.CupertinoDialogAction(text="Ok", is_destructive_action=True, on_click=lambda a: ok_dialog(a,self)),
                    ],
                )
                self.page.overlay.append(cupertino_alert_dialog)
                cupertino_alert_dialog.open = True
                self.page.update()
                return
            self.closing_event = True
            overlay = PageOverlay(self.page,content=self.closing_sheet,modal=True)
            overlay.open()
            if self.csp.segmentation_running:
                self.cancel_event = multiprocessing.Event()
                self.cancel_segmentation()
                self.cancel_event.wait()
            if self.csp.training_running:
                self.training_event = multiprocessing.Event()
                self.training_event.wait()
            if self.csp.readout_running:
                self.readout_event = multiprocessing.Event()
                self.readout_event.wait()
            if self.builder_environment.pipeline_gui.pipeline.running:
                self.builder_environment.cancel()
                self.expert_running_event = multiprocessing.Event()
                self.builder_environment.pipeline_running_event = self.expert_running_event
                self.expert_running_event.wait()
            self.page.window.prevent_close = False
            self.page.window.on_event = None
            self.page.update()
            self.page.run_task(self.handle_window_closing)

    def on_enter_diameter(self):
        self.diameter_text.color = ft.Colors.BLUE_400
        self.diameter_text.update()

    def on_exit_diameter(self):
        self.diameter_text.color = None
        self.diameter_text.update()

    async def handle_window_closing(self):
        await self.page.window.close()

    async def handle_window_centering(self):
        await self.page.window.center()

    async def update_adjusted_image(self):
        self.canvas.brightness =  round(self.brightness_slider.value, 2)
        self.canvas.contrast = round(self.contrast_slider.value, 2)
        await self.canvas.update_main_image_with_brightness_contrast(self.csp.image_paths[self.csp.image_id][self.csp.channel_id])
