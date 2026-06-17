import queue

import multiprocessing
import pathlib

import flet as ft
import torch
import os

from backend.constants import ModelType, FILTER_INT, FILTER_SCIENTIFIC_FLOAT, FILTER_FLOAT, MAIN_COLOR, ERROR_COLOR, \
    SUCCESS_COLOR
from backend.training import run_cellpose_training
from frontend.gui_directory import format_directory_path, copy_to_clipboard


def create_terminal_text(text, is_bold=False,color=None):
    return ft.Text(
        text,
        size=12,
        color=color,
        font_family="Cascadia Code",
        weight=ft.FontWeight.BOLD if is_bold else ft.FontWeight.NORMAL,
    )

class Training(ft.Container):

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.log_queue = None
        self.training_process = None
        self.epoch_bar_control = None
        self.last_tqdm_control = None
        self.text = ft.Text("Go To Training")
        self.button_event = ft.PopupMenuItem(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.EXIT_TO_APP),
                    self.text,
                ]
            ),
            on_click=lambda e: self.change_environment(e),
        )
        self.switch_icon = ft.Icon(ft.Icons.MODEL_TRAINING)
        self.button_training_environment_menu = ft.PopupMenuButton(
            items=[self.button_event],
            content=self.switch_icon,
            tooltip="Training",
            on_open=lambda _: self.text.update(),
        )
        self.content = self.button_training_environment_menu
        self.padding = 10
        self.alignment = ft.Alignment.TOP_RIGHT
        self.start_button = ft.Button(
            content="Start",
            icon=ft.Icons.PLAY_CIRCLE,
            tooltip="Start the training epochs",
            disabled=True,
            visible=True,
            on_click=lambda e: e.page.run_task(self.start_training),
        )
        self.cancel_button = ft.Button(
            content="Cancel",
            icon=ft.Icons.CANCEL,
            icon_color=ERROR_COLOR,
            color= ERROR_COLOR,
            tooltip="Cancel the running training",
            disabled=True,
            visible=False,
            on_click=lambda e: e.page.run_task(self.cancel_training),
        )

        self.model = "nuclei"
        self.batch_size = 100
        self.epochs = 100
        self.learning_rate = 0.001
        self.pre_trained = None
        self.diameter_default = True
        self.diameter = 0.0
        self.weight = 1e-4  # standard value for the weight
        self.model_name = "new_model"
        self.re_train_model_name = None
        self.color = MAIN_COLOR
        self.progress_bar_text = ft.Text("")
        self.model_directory = self.gui.csp.models_dir
        self.terminal_list = ft.ListView(expand=True, spacing=2,scroll=ft.ScrollMode.ALWAYS, auto_scroll=True)
        self.terminal_container = ft.Container(
            content=ft.SelectionArea(content=self.terminal_list),
            height=200,
            ink=True,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
            expand=True,
            border=ft.Border.all(2, MAIN_COLOR),
            border_radius=5,
            padding=10,
            margin=5,
        )
        # Changed from TextField to Dropdown for model type selection
        self.model_dropdown = ft.Dropdown(
            label="Model Type",
            value=ModelType.CP_CYTO.value.name,
            options=[
                ft.dropdown.Option(key=v.value.name, text=v.value.name)
                for v in ModelType if v != ModelType.CUSTOM
            ], border_color=MAIN_COLOR,
            on_select=lambda e: self.changed_input("modeltype", e),
            expand=True,
        )
        self.re_train_model = ft.Checkbox(
            value=False,
            label="Retrain Model",
            on_change=lambda e: self.change_re_train_model()
        )

        # the following methods are called when clicking on the corresponding button
        async def pick_model_result(e: ft.Event[ft.Button]):
            """
            The result of the file selection is handled.

            Arguments:
                e (ft.FilePicker): pseudo Event, indicating the event structure
            """
            files = await ft.FilePicker().pick_files(
                                                     dialog_title="Select model",
                                                     allow_multiple=False,
                                                     initial_directory=str(pathlib.Path(self.model_directory))
                                                     )

            if files is None or len(files) == 0:
                # case: no model selected
                pass
            elif files[0].path is not None:
                self.gui.csp.re_train_model_path = files[0].path
                self.field_model_name.value = files[0].name
                self.re_train_model_name = files[0].name
                self.field_model_name.color = MAIN_COLOR
                self.gui.page.update()

        self.re_train_model_chooser = ft.IconButton(
            icon=ft.Icons.UPLOAD_FILE,
            tooltip="Select model to retrain",
            on_click=lambda e: e.page.run_task(pick_model_result, e),
            disabled=True
        )
        self.field_model_name = ft.TextField(label="Model Name", value=self.model_name, border_color=self.color,
                                             on_blur=lambda e: self.changed_input("model_name", e))
        self.model_stack = ft.Stack([self.field_model_name, self.re_train_model_chooser],
                                    alignment=ft.Alignment.TOP_RIGHT)
        self.field_model = ft.Row([self.model_dropdown, self.model_stack])
        # New field for custom model input, visible only if "custom" is selected
        self.field_custom_model = ft.TextField(label="Custom Model", value="", border_color=self.color, visible=False,
                                               on_blur=lambda e: self.changed_input("custom_model", e))

        self.field_batch = ft.TextField(label="Batch Size", value=self.batch_size, border_color=self.color,
                                        input_filter=ft.InputFilter(allow=True, regex_string=FILTER_INT,
                                                                    replacement_string=""),
                                        on_blur=lambda e: self.changed_input("batch_size", e), expand=True)
        self.field_epoch = ft.TextField(label="Epochs", value=self.epochs, border_color=self.color,
                                        input_filter=ft.InputFilter(allow=True, regex_string=FILTER_INT,
                                                                    replacement_string=""),
                                        on_blur=lambda e: self.changed_input("epochs", e), expand=True)
        self.field_lr = ft.TextField(label="Learning Rate", value=self.learning_rate, border_color=self.color,
                                     input_filter=ft.InputFilter(allow=True, regex_string=FILTER_SCIENTIFIC_FLOAT,
                                                                 replacement_string=""),
                                     on_blur=lambda e: self.changed_input("learning_rate", e), expand=True)
        self.field_diameter = ft.TextField(label="Diameter", value=self.diameter, border_color=self.color,
                                           input_filter=ft.InputFilter(allow=True, regex_string=FILTER_FLOAT,
                                                                       replacement_string=""),
                                           on_blur=lambda e: self.changed_input("diameter", e), expand=True)
        self.field_weights = ft.TextField(label="Weight Decay", value=self.weight, border_color=self.color,
                                          input_filter=ft.InputFilter(allow=True, regex_string=FILTER_SCIENTIFIC_FLOAT,
                                                                      replacement_string=""),
                                          on_blur=lambda e: self.changed_input("weight", e), expand=True)
        self.field_directory = ft.TextField(label="Directory",
                                            value=format_directory_path(str(self.model_directory), max_length=60),
                                            border_color=self.color,
                                            read_only=True, disabled=True, expand=True)

        self.directory_stack = ft.Stack([self.field_directory, ft.Container(
            content=ft.Container(
                content=ft.IconButton(
                    icon=ft.Icons.COPY,
                    tooltip="Copy to clipboard",
                    on_click=lambda e: e.page.run_task(copy_to_clipboard, self.gui.page, str(self.model_directory),
                                                       "Model directory")
                ),
                alignment=ft.Alignment.TOP_RIGHT,
            )
        )])
        self.progress_ring = ft.ProgressRing(visible=False)
        self.train_loss = None
        self.test_loss = None

    def change_re_train_model(self):
        """
        Choosing a model to retrain.
        """
        self.field_model_name.disabled = self.re_train_model.value
        if self.re_train_model.value is True:
            self.re_train_model_chooser.disabled = False
            self.field_diameter.disabled = True
            self.field_diameter.value = None
            self.model_dropdown.visible = False
            if self.re_train_model_name is not None:
                self.field_model_name.value = self.re_train_model_name
                self.field_model_name.color = MAIN_COLOR
            else:
                self.field_model_name.value = None
        else:
            self.re_train_model_chooser.disabled = True
            if self.model == "CP Sam":
                self.field_diameter.disabled = True
                self.field_diameter.value = None
            else:
                self.field_diameter.disabled = False
                self.field_diameter.value = str(self.diameter)

            self.field_model_name.color = None
            self.field_model_name.value = self.model_name
            self.model_dropdown.visible = True
        self.gui.page.update()

    def go_to_training_environment(self, e):
        # delete the content of the page and reset the reference to the page (reference get sometimes lost)
        self.gui.ref_training_environment.current.visible = True
        self.gui.ref_gallery_environment.current.visible = True
        self.gui.ref_builder_environment.current.visible = False
        self.gui.ref_seg_environment.current.visible = False
        self.page.title = "CellSePi"
        self.gui.page.update()
        self.text.value = "Exit Training"
        self.gui.ex_mode.text.value = "Go To Expert Mode"

    def add_parameter_container(self):
        return ft.Container(
            ft.Column(
                [self.field_model, self.re_train_model, self.field_custom_model, self.field_batch, self.field_epoch,
                 self.field_weights,
                 self.field_lr, self.field_diameter, self.directory_stack
                 ]
            ),
            padding=10,
        )

    def changed_input(self, field, e):
        """
        Changing the value of one of the parameters for training.
        Arguments:
            field: the parameter to change
            e = the change event
        """
        updated_value = e.control.value

        try:
            if updated_value in ("", ".", "-", "e", "E", "1e", "1e-"):
                raise ValueError("Field cannot be empty or incomplete.")

            if field == "modeltype":
                self.model = updated_value
                self.field_model.value = updated_value
                if updated_value == "custom":
                    self.field_custom_model.visible = True
                else:
                    self.field_custom_model.visible = False
                if updated_value == "CP Cyto" or updated_value == "CP Nuclei":
                    self.batch_size = 100
                    self.field_batch.value = 100
                    self.epochs = 100
                    self.field_epoch.value = 100
                    self.learning_rate = 0.001
                    self.field_lr.value = 0.001
                    self.weight = 1e-4
                    self.field_weights.value = 1e-4
                    self.field_diameter.disabled = False
                    self.field_diameter.value = str(self.diameter)
                elif updated_value == "CP Sam":
                    self.batch_size = 1
                    self.field_batch.value = 1
                    self.epochs = 100
                    self.field_epoch.value = 100
                    self.learning_rate = 0.00001
                    self.field_lr.value = 0.00001
                    self.weight = 0.1
                    self.field_weights.value = 0.1
                    self.field_diameter.disabled = True
                    self.field_diameter.value = None
            elif field == "custom_model":
                self.model = updated_value
                self.field_custom_model.value = updated_value
            elif field == "batch_size":
                val = int(updated_value)
                if val <= 0:
                    raise ValueError("Batch size must be greater than 0.")
                self.batch_size = val
                self.field_batch.value = str(val)
            elif field == "epochs":
                val = int(updated_value)
                if val <= 0:
                    raise ValueError("Epochs must be greater than 0.")
                self.epochs = val
                self.field_epoch.value = str(val)
            elif field == "learning_rate":
                val = float(updated_value)
                if val <= 0 or val > 1:
                    raise ValueError("Must be between 0 and 1.")
                self.learning_rate = val
                self.field_lr.value = str(val)
            elif field == "pre_trained":
                self.pre_trained = updated_value
                self.field_trained.value = updated_value
            elif field == "weight":
                val = float(updated_value)
                if val < 0 or val > 1:
                    raise ValueError("Must be between 0 and 1.")
                self.weight = val
                self.field_weights.value = str(val)
            elif field == "model_name":
                self.model_name = updated_value
            elif field == "diameter":
                self.diameter_default = False
                if not self.field_diameter.disabled:
                    val = float(updated_value)
                    if val < 0:
                        raise ValueError("Diameter cannot be negative.")
                    self.diameter = val
                    self.field_diameter.value = str(val)
                else:
                    self.field_diameter.value = None

            else:
                return

            e.control.color = None
            e.control.text_style = None
            self.gui.page.update()
        except ValueError as err:
            e.control.color = ERROR_COLOR
            e.control.text_style = ft.TextStyle(weight=ft.FontWeight.BOLD)
            e.control.update()

            error_msg = f"Invalid input for {field.replace('_', ' ').title()}! {err}"
            self.gui.error_manager.show_without_button(error_msg)

    def change_environment(self, e):
        if self.text.value == "Go To Training":
            self.go_to_training_environment(e)
        else:
            self.gui.ref_training_environment.current.visible = False
            self.gui.ref_seg_environment.current.visible = True
            self.gui.page.update()
            self.text.value = "Go To Training"

    def create_training_card(self):
        """
        This method creates a card for the GUI, which contains the progress bar and several buttons for
         controlling the run of the training.

        Returns:
            training_card (ft.Card): the card containing all the elements needed to run the training
        """

        # progress bar, which is updated throughout the training periods

        text = ft.Text("Training")
        title = ft.ListTile(
            leading=ft.Icon(icon=ft.Icons.HUB_OUTLINED),
            title=text,
        )
        pick_model_row = ft.Row(
            [
                ft.Container(content=ft.Row([self.progress_ring, self.progress_bar_text]), padding=5),
                ft.Container(
                    content=ft.Row([self.start_button,self.cancel_button]), padding=5),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        test_container = ft.Container(
            content=ft.Column(
                [title,
                 pick_model_row,
                 ]
            ),
            padding=10
        )

        progress_card = ft.Card(
            content=ft.Column(
                    [test_container,self.terminal_container,]
                ),
            expand=True
        )

        return progress_card

    async def start_training(self):
        """
        This method starts the training process with the selected parameters and model.
        """
        self.start_button.disabled = True
        self.start_button.visible = False
        self.start_button.update()
        self.cancel_button.disabled = False
        self.cancel_button.visible = True
        self.cancel_button.update()
        self.re_train_model_chooser.disabled = True
        self.re_train_model_chooser.update()
        self.gui.directory.disable_path_choosing()
        self.progress_ring.visible = True
        self.progress_ring.update()
        self.progress_bar_text.value = ""
        self.progress_bar_text.update()
        self.terminal_list.controls.clear()
        self.terminal_list.update()
        self.epoch_bar_control = None
        self.last_tqdm_control = None
        self.disable_switch_environment()

        if self.re_train_model.value:
            try:
                state_dict = torch.load(self.gui.csp.re_train_model_path,weights_only=False,
                                        map_location=torch.device("cuda" if self.gui.csp.gpu else "cpu"))
                w2_data = state_dict.get('W2', None)
                if w2_data is None:
                    model_type = ModelType.CP_CYTO
                else:
                    model_type = ModelType.CP_SAM
            except Exception as ex:
                msg= f"The input for the retrained model is invalid!"
                self.gui.error_manager.show_without_button(msg)
                self.training_error_terminal(msg)
                self.gui.directory.enable_path_choosing()
                self.start_button.disabled = False
                self.start_button.visible = True
                self.cancel_button.disabled = True
                self.cancel_button.visible = False
                self.re_train_model_chooser.disabled = False
                self.progress_ring.visible = False
                self.progress_bar_text.value = ""
                self.enable_switch_environment()
                self.page.update()
                return
        else:
            model_type = self.model_dropdown.value
            try:
                model_type = [elem for elem in ModelType if elem.value.name == model_type][0]
            except IndexError:
                msg = f"Model type {model_type} not supported!"
                self.gui.error_manager.show_without_button(msg)
                self.training_error_terminal(msg)
                self.gui.directory.enable_path_choosing()
                self.start_button.disabled = False
                self.start_button.visible = True
                self.cancel_button.disabled = True
                self.cancel_button.visible = False
                self.re_train_model_chooser.disabled = False
                self.progress_ring.visible = False
                self.progress_bar_text.value = ""
                self.enable_switch_environment()
                self.page.update()
                return

        self.gui.csp.training_running = True
        self.gui.training_event.clear()

        mask_filter = f"{self.gui.csp.current_mask_suffix}.npy"

        if self.re_train_model.value:
            sgd_value = True
        else:
            sgd_value = False

        ctx = multiprocessing.get_context("spawn")
        self.log_queue = ctx.Queue()
        self.training_process = ctx.Process(
            target=run_cellpose_training,
            args=(
                self.log_queue,
                model_type,
                str(self.gui.csp.working_directory),
                mask_filter,
                self.weight,
                sgd_value,
                self.learning_rate,
                self.epochs,
                self.model_name,
                str(os.path.dirname(self.model_directory)),
                self.gui.csp.gpu,
                self.gui.csp.re_train_model_path if self.re_train_model.value else None,
                self.diameter
            )
        )
        self.training_process.daemon = True

        self.training_process.start()

        self.gui.page.run_thread(self.queue_listener)

    async def update_terminal(self,msg):
        if msg["type"] == "error":
            if  not msg["error_obj"]:
                self.gui.error_manager.show_without_button(msg["text"])
            else:
                self.gui.error_manager.log_and_show(msg["text"], msg["error_obj"])
            self.training_error_terminal(msg["text"])

        elif msg["type"] == "finished":
            self.training_finished_terminal()
            self.progress_bar_text.value = "Finished"
            self.progress_bar_text.update()
        elif msg["type"] == "cancel":
            self.progress_bar_text.value = "Cancelled"
            self.progress_bar_text.update()

        elif msg["type"] == "tqdm":
            self.update_tqdm_ui(text=msg["text"],
                                percent=msg.get("percent"),
                                current=msg.get("current"),
                                total=msg.get("total"),
                                elapsed=msg.get("elapsed"))

        elif msg["type"] == "epoch":
            self.update_epoch_ui(msg["text"], msg["percent"])

        elif msg["type"] == "log":
            self.terminal_list.controls.append(
                create_terminal_text(msg["text"])
            )
            self.terminal_list.update()

    async def finish_training(self):
        self.progress_ring.visible = False
        self.progress_ring.update()

        self.start_button.disabled = False
        self.start_button.visible = True
        self.start_button.update()

        self.cancel_button.disabled = True
        self.cancel_button.visible = False
        self.cancel_button.update()

        self.re_train_model_chooser.disabled = False
        self.re_train_model_chooser.update()

        self.gui.directory.enable_path_choosing()

        self.enable_switch_environment()
        self.gui.csp.training_running = False
        self.gui.training_event.set()

    def queue_listener(self):
        while True:
            msg = self.log_queue.get()
            self.gui.page.run_task(self.update_terminal,msg)
            if msg["type"] == "error" or msg["type"] == "finished" or msg["type"] == "cancel":
                break

        if self.training_process:
            self.training_process.join(timeout=1.0)

            if self.training_process.is_alive():
                self.training_process.terminate()
                self.training_process.join(timeout=0.5)

        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break

        self.gui.page.run_task(self.finish_training)


    def update_tqdm_ui(self, text, percent=None, current=None, total=None, elapsed=None):
        if percent is not None:
            bar_length = 30
            filled = int(bar_length * percent)
            bar = '█' * filled + '░' * (bar_length - filled)

            info = f"{current}/{total}" if current and total else ""
            time_info = f" [{elapsed}]" if elapsed else ""
            display_text = f"Progress: [{bar}] {percent:.0%}  {info}{time_info}"
        else:
            display_text = text

        is_last_item = (len(self.terminal_list.controls) > 0 and
                        self.terminal_list.controls[-1] == self.last_tqdm_control)
        if self.last_tqdm_control and is_last_item:
            self.last_tqdm_control.value = display_text
        else:
            self.last_tqdm_control = create_terminal_text(display_text, color=SUCCESS_COLOR, is_bold=True)
            self.terminal_list.controls.append(self.last_tqdm_control)
        self.terminal_list.update()

    def update_epoch_ui(self, text, percent):
        bar_length = 30
        filled_length = int(bar_length * percent)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        bar_text = f"Progress: [{bar}] {percent:.0%}"

        if self.epoch_bar_control in self.terminal_list.controls:
            self.terminal_list.controls.remove(self.epoch_bar_control)

        self.epoch_bar_control = create_terminal_text(bar_text,color=SUCCESS_COLOR, is_bold=True)

        self.terminal_list.controls.append(create_terminal_text(text))
        self.terminal_list.controls.append(self.epoch_bar_control)
        self.terminal_list.update()

    async def cancel_training(self):
        if self.training_process and self.training_process.is_alive():
            self.training_process.terminate()

            self.terminal_list.controls.append(
                create_terminal_text(">>> Training cancelled.",is_bold=True, color=ERROR_COLOR)
            )
            self.terminal_list.update()

            self.log_queue.put({"type": "cancel", "text": "cancelled"})

            self.cancel_button.disabled = True
            self.cancel_button.update()
            self.epoch_bar_control = None
            self.last_tqdm_control = None

    def training_finished_terminal(self):
            self.terminal_list.controls.append(
                create_terminal_text(">>> Training finished.",is_bold=True, color=SUCCESS_COLOR)
            )
            self.terminal_list.update()

    def training_error_terminal(self,msg):
            self.terminal_list.controls.append(
                create_terminal_text(f">>> {msg}",is_bold=True, color=ERROR_COLOR)
            )
            self.terminal_list.update()

    def disable_switch_environment(self):
        self.switch_icon.color = ft.Colors.GREY_400
        self.button_training_environment_menu.disabled = True
        self.button_training_environment_menu.update()
        self.gui.ex_mode.switch_icon.color = ft.Colors.GREY_400
        self.gui.ex_mode.button_expert_environment_menu.disabled = True
        self.gui.ex_mode.button_expert_environment_menu.update()

    def enable_switch_environment(self):
        self.switch_icon.color = None
        self.button_training_environment_menu.disabled = False
        self.button_training_environment_menu.update()
        self.gui.ex_mode.switch_icon.color = None
        self.gui.ex_mode.button_expert_environment_menu.disabled = False
        self.gui.ex_mode.button_expert_environment_menu.update()
