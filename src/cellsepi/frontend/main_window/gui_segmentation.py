import os
import platform
import queue
import re
import subprocess
import sys
import time

import flet as ft

from cellsepi.backend.main_window.avg_diameter import AverageDiameter
from cellsepi.backend.main_window.fluorescence import Fluorescence
from cellsepi.frontend.main_window.gui_fluorescence import fluorescence_button
from cellsepi.backend.main_window.segmentation import Segmentation
from cellsepi.frontend.main_window.gui_mask import reset_mask


class GUISegmentation:
    """
    This class handles the segmentation, which can be controlled by the start, pause, resume and cancel buttons.
    """
    def __init__(self, gui):
        self.gui = gui
        self.segmentation = Segmentation(self, gui)
        self.fluorescence = Fluorescence(gui.csp, gui)
        self.segmentation_cancelling = False
        self.segmentation_pausing = False
        self.segmentation_resuming = False
        self.segmentation_currently_paused = False
        self.progress_bar = ft.ProgressBar(value=0, width=180)
        self.progress_bar_text = ft.Text("Waiting for Input")



    def create_segmentation_card(self):
        """
        This method creates a segmentation card for the GUI, which contains the progress bar and several buttons for
         controlling the run of the segmentation.

        Returns:
            segmentation_card (ft.Card): the card containing all the elements needed to run the segmentation
        """
        # creating all the necessary buttons and their initial properties
        start_button = ft.Button( # button to start the segmentation calculation
            content="Start",
            icon=ft.Icons.PLAY_CIRCLE,
            tooltip="Start the segmentation",
            disabled=True,
            on_click=None
        )
        pause_button = ft.Button( # button to pause the segmentation calculation while it is running
            content="Pause",
            icon=ft.Icons.PAUSE_CIRCLE,
            visible=False,
            on_click=None,
        )
        cancel_button = ft.Button( # button to completely cancel the currently running segmentation calculation
            content="Cancel",
            icon=ft.Icons.CANCEL,
            visible=False,
            on_click=None,
            color=ft.Colors.RED,
            icon_color=ft.Colors.RED,
        )
        resume_button = ft.Button( # button to resume the segmentation calculation after it has been paused
            content="Resume",
            icon=ft.Icons.PLAY_CIRCLE,
            visible=False,
            on_click=None,
        )

        # button to start the fluorescence readout
        fl_button = fluorescence_button

        # progress bar, which is updated throughout the segmentation calculation and fluorescence readout
        self.progress_bar = ft.ProgressBar(value=0, width=180)
        self.progress_bar_text = ft.Text("Waiting for Input")

        def open_readout(e):
            file_path = self.gui.csp.readout_path
            if os.name == "nt":  # Check if Windows
                os.startfile(file_path)
            elif os.name == "posix":  # Check if Mac or Linux
                subprocess.run(["open", file_path] if sys.platform == "darwin" else ["xdg-open", file_path])

        open_button = ft.IconButton(
            icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
            tooltip = "Open fluorescence file",
            on_click=open_readout,
            visible= False
        )

        # the following methods are called when clicking on the corresponding button
        async def pick_model_result(e: ft.Event[ft.Button]):
            """
            The result of the file selection is handled.

            Arguments:
                e (ft.Event): pseudo Event, when button pressed
            """
            files = await ft.FilePicker().pick_files(allow_multiple=False,
                                                     initial_directory=model_directory
                                                     )
            if files is None:
                #case: no model selected
                pass
            elif files[0].path is not None:
                if self.gui.ready_to_start:
                    self.progress_bar_text.value = "Ready to Start"
                    start_button.disabled = False
                model_text.value = files[0].name
                model_text.color = None
                self.gui.csp.model_path = files[0].path
                self.gui.page.update()


        def new_pick_model_result(e: ft.Event[ft.Button]):
            print(model_drop_down.value)
            if model_drop_down.value == "Choose custom model...":
                print("choose your own model selected")
                model_choose_button.visible = True
                model_text.value = "Choose model"
            #TODO save which non-custom model was selected and use that for segmentation
            elif model_drop_down.value == "CellposeSAM":
                if self.gui.ready_to_start:
                    self.progress_bar_text.value = "Ready to Start"
                    start_button.disabled = False
                model_text.value = "Cellpose SAM"
                model_choose_button.visible = False
                self.gui.csp.model_path = "CellposeSAM"
            elif model_drop_down.value == "MicroSAM":
                if self.gui.ready_to_start:
                    self.progress_bar_text.value = "Ready to Start"
                    start_button.disabled = False
                model_text.value = "Microscopy SAM"
                model_choose_button.visible = False
                self.gui.csp.model_path = "MicroSAM"
            self.gui.page.update()



        def start_segmentation(e): # called when the start button is clicked
            """
            The start of the segmentation is initialized.
            This includes error handling for the case where something other than a model is chosen.
            """
            # visibility of buttons before start of segmentation (needed in case of error)
            state_fl_button = fl_button.visible
            state_open_button = self.gui.open_button.visible
            try:
                start_button.visible = False
                pause_button.visible = True
                cancel_button.visible = True
                model_title.disabled = True
                model_chooser.disabled = True
                fl_button.visible = False
                cancel_button.color = ft.Colors.RED
                cancel_button.icon_color = ft.Colors.RED
                self.gui.open_button.visible = False
                self.gui.training_environment.disable_switch_environment()
                self.gui.directory.disable_path_choosing()

                self.gui.page.update()
                self.gui.page.run_thread(self.segmentation.run) # this will throw an error if something other than a model was chosen
            except:
                self.gui.page.show_dialog(ft.SnackBar(ft.Text("You have selected an incompatible file for the segmentation model.")))
                self.gui.training_environment.enable_switch_environment()
                start_button.visible = True
                start_button.disabled = True
                pause_button.visible = False
                cancel_button.visible = False
                model_title.disabled = False
                model_text.color = ft.Colors.RED
                model_chooser.disabled = False
                fl_button.visible = state_fl_button
                self.gui.open_button.visible = state_open_button
                self.gui.directory.enable_path_choosing()
                self.gui.csp.segmentation_running = False
                self.progress_bar_text.value = "Select new Model"
                self.gui.csp.model_path = None
                self.gui.page.update()


        def cancel_segmentation(): # called when the cancel button is clicked
            """
            The running segmentation is cancelled and everything returns to the start state.
            The masks calculated so far are deleted and the previously calculated masks are restored.
            """
            cancel_button.visible = False
            self.segmentation_cancelling = True
            self.segmentation.to_be_cancelled()
            self.gui.diameter_display.opacity = 0.5
            if self.segmentation_currently_paused:
                resume_button.visible = False
                extracted_percentage = re.search(r'\d+', self.progress_bar_text.value)
                self.progress_bar_text.value = "Cancelling: " + extracted_percentage.group(0) + " %"
                self.segmentation_currently_paused = False
                self.gui.page.update()
                self.segmentation.run()
            else:
                pause_button.visible = False
                self.progress_bar_text.value = "Cancelling: " + self.progress_bar_text.value
            self.gui.page.update()


        def pause_segmentation(e): # called when the pause button is clicked
            """
            The running segmentation is paused (the progress of the segmentation so far is stored).
            """
            pause_button.visible = False
            resume_button.visible = True
            resume_button.disabled = True
            cancel_button.disabled = True
            self.progress_bar_text.value = "Pausing: " + self.progress_bar_text.value
            cancel_button.color = None
            cancel_button.icon_color = None
            self.gui.page.update()
            self.segmentation_pausing = True
            self.segmentation.to_be_paused()

        def resume_segmentation(e): # called when the resume button is clicked
            """
            The segmentation is resumed again from the previously paused state.
            """
            self.segmentation_currently_paused = False
            resume_button.visible = False
            pause_button.visible = True
            pause_button.disabled = True
            cancel_button.disabled = True
            extracted_percentage = re.search(r'\d+', self.progress_bar_text.value)
            self.progress_bar_text.value =  extracted_percentage.group(0) + " %" # remove "paused at " from string
            cancel_button.color = None
            cancel_button.icon_color = None
            self.gui.page.update()
            self.segmentation.to_be_resumed()
            self.segmentation_resuming = True
            self.segmentation.run()


        # define behavior of buttons when they are clicked
        start_button.on_click = start_segmentation
        cancel_button.on_click = lambda e: cancel_segmentation()
        pause_button.on_click = pause_segmentation
        resume_button.on_click = resume_segmentation

        def finished_segmentation():
            """
            This method updates the segmentation card when the segmentation is finished.
            After this a new segmentation can be started again.
            """
            self.progress_bar_text.value = "Finished"
            pause_button.visible = False
            cancel_button.visible = False
            fl_button.visible = True
            fl_button.disabled = False
            start_button.visible = True
            start_button.disabled = False
            model_title.disabled = False
            model_chooser.disabled = False
            self.gui.diameter_text.value = self.gui.average_diameter.get_avg_diameter()
            self.gui.training_environment.enable_switch_environment()
            self.gui.directory.enable_path_choosing()
            self.gui.csp.segmentation_running = False
            self.gui.page.update()

        def cancelled_segmentation():
            """
            This method updates the segmentation card when the cancellation is finished.
            """
            self.progress_bar_text.value = "Ready to Start"
            self.progress_bar.value = 0
            if not platform.system() == "Linux":
                self.gui.page.window.progress_bar = -1
            start_button.visible = True
            self.gui.page.run_task(self.gui.directory.check_masks)
            if self.gui.csp.readout_path is not None:
                self.gui.open_button.visible = True
            self.segmentation_cancelling = False
            self.gui.training_environment.enable_switch_environment()
            self.gui.directory.enable_path_choosing()
            self.gui.csp.segmentation_running = False
            model_title.disabled = False
            model_chooser.disabled = False
            self.gui.diameter_display.opacity = 1
            self.gui.diameter_text.value = self.gui.average_diameter.get_avg_diameter()
            for image_id in self.gui.csp.image_paths:
                self.gui.directory.update_mask_check(image_id)
            self.gui.page.update()
            if self.gui.cancel_event is not None:
                self.gui.cancel_event.set()

        def paused_segmentation():
            """
            This method updates the segmentation card when the pausing is finished.
            """
            resume_button.disabled = False
            cancel_button.disabled = False
            extracted_percentage = re.search(r'\d+', self.progress_bar_text.value)
            self.progress_bar_text.value = "Paused at: " + extracted_percentage.group(0) + " %"
            cancel_button.color = ft.Colors.RED
            cancel_button.icon_color = ft.Colors.RED
            self.gui.page.update()
            self.segmentation_pausing = False
            self.segmentation_currently_paused = True

        def resumed_segmentation():
            """
            This method updates the segmentation card when the resuming has successfully started.
            """
            pause_button.disabled = False
            cancel_button.disabled = False
            cancel_button.color = ft.Colors.RED
            cancel_button.icon_color = ft.Colors.RED
            self.gui.page.update()
            self.segmentation_resuming = False


        def update_progress_bar(progress, current_image):
            """
            This method updates the progress bar at any point before, during and after the segmentation and fluorescence process.

            Arguments:
                progress (int): the current progress
                current_image (dict): the current image number
            """

            print("value progress", progress)
            if self.segmentation_pausing:
                self.progress_bar_text.value = "Pausing: " + str(progress)
            elif self.segmentation_cancelling:
                self.progress_bar_text.value = "Cancelling: " + str(progress)
                self.gui.diameter_display.opacity = 0.5
            else:
                self.progress_bar_text.value = progress
            extracted_num = re.search(r'\d+', progress)
            if extracted_num is not None:
                self.progress_bar.value = int(extracted_num.group()) / 100
                if not platform.system() == "Linux":
                    self.gui.page.window.progress_bar = self.progress_bar.value

            if current_image is not None:
                if current_image[
                    "image_id"] == self.gui.csp.image_id and self.segmentation.batch_image_segmentation.segmentation_channel == self.gui.csp.config.get_bf_channel():
                    self.gui.canvas.update_mask_image()
                #else:
                    #reset_mask(self.gui, current_image["image_id"],self.segmentation.batch_image_segmentation.segmentation_channel) #TODO update to new drawing window functionality

            print("at the end text value progress", self.progress_bar_text.value)

            print("value progress", self.progress_bar.value)
            self.gui.page.schedule_update()
            time.sleep(0.02)



        # listeners for getting different information from the state of the segmentation process
        self.segmentation.add_update_listener(listener=update_progress_bar)
        self.segmentation.add_completion_listener(listener=finished_segmentation)
        self.segmentation.add_cancel_listener(listener=cancelled_segmentation)
        self.segmentation.add_pause_listener(listener=paused_segmentation)
        self.segmentation.add_resume_listener(listener=resumed_segmentation)

        def fluorescence_readout(e):
            """
            Updates the segmentation card and starts readout of the fluorescence data when the fluorescence button is clicked.
            """
            self.fluorescence.readout_fluorescence()
            fl_button.disabled = True
            start_button.disabled = True
            self.gui.open_button.visible = False
            self.progress_bar_text.value = "Reading fluorescence"
            self.gui.directory.disable_path_choosing()
            model_title.disabled = True
            model_chooser.disabled = True
            self.gui.page.update()

        def start_fl(e):
            self.progress_bar.value = 0
            if not platform.system() == "Linux":
                self.gui.page.window.progress_bar = 0
            self.progress_bar_text.value = "0 %"
            self.gui.page.update()

        def complete_fl():
            self.progress_bar.value = 0
            if not platform.system() == "Linux":
                self.gui.page.window.progress_bar = -1
            if self.gui.csp.model_path is not None:
                self.progress_bar_text.value = "Ready to start"
            else:
                self.progress_bar_text.value = "Waiting for Input"
            self.gui.directory.enable_path_choosing()
            model_title.disabled = False
            model_chooser.disabled = False
            self.gui.page.update()
            if self.gui.readout_event is not None:
                self.gui.readout_event.set()


        fl_button.on_click = fluorescence_readout
        self.fluorescence.add_start_listener(listener=start_fl)
        self.fluorescence.add_update_listener(listener=update_progress_bar)
        self.fluorescence.add_completion_listener(listener=complete_fl)

        pick_model_row = ft.Row(
            [
                ft.Container(content=ft.Row([self.progress_bar,self.progress_bar_text ])),
                ft.Container(content=ft.Row([start_button, pause_button, resume_button, cancel_button, fl_button, open_button]))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        model_text = ft.Text("Choose Model")
        model_title = ft.ListTile(
                                        leading=ft.Icon(icon=ft.Icons.HUB_OUTLINED),
                                        title= model_text,
                                    )

        segmentation_container = ft.Container(
                            content=ft.Column(
                                [model_title,
                                 pick_model_row,
                                 ]
                            )
                        )

        project_root =os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_directory = os.path.join(project_root, "models")

        """model_chooser = ft.Container(
                            content=ft.IconButton(
                                icon=ft.Icons.UPLOAD_FILE,
                                tooltip="Choose model",
                                on_click=lambda e: e.page.run_task(pick_model_result,e),
                            ), alignment=ft.Alignment.BOTTOM_RIGHT,
                        )"""

        model_drop_down = ft.DropdownM2(
                width=220,
                options=[ft.dropdownm2.Option(key="CellposeSAM", text="CellposeSAM"),
                     ft.dropdownm2.Option(key="MicroSAM", text="MicroSAM"),
                     ft.dropdownm2.Option(key="Choose custom model...", text="CCM")],
                on_change=lambda e: new_pick_model_result(e))

        model_choose_button = ft.IconButton(
                icon=ft.Icons.UPLOAD_FILE,
                tooltip="Choose model",
                visible=False,
                on_click=lambda e: e.page.run_task(pick_model_result,e))

        model_chooser = ft.Container(ft.Row(
            controls = [model_drop_down, model_choose_button],
            alignment=ft.MainAxisAlignment.END,),
        alignment=ft.Alignment.BOTTOM_RIGHT)


        segmentation_card = ft.Card(
            content=ft.Container(
                content=ft.Stack(
                    [   segmentation_container,
                        model_chooser
                    ]
                ),
                padding=10
            ),
        )


        return segmentation_card,start_button,open_button,self.progress_bar,self.progress_bar_text,cancel_segmentation