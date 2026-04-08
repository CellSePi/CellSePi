import flet as ft
from cellpose import models, train, io
import os

from cellsepi.frontend.main_window.gui_directory import format_directory_path, copy_to_clipboard


class Training(ft.Container):

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
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
            on_click=lambda e : e.page.run_thread(self.start_training,e),
        )

        self.model = "nuclei"
        self.batch_size = 100
        self.epochs = 100
        self.learning_rate = 0.001
        self.pre_trained = None
        self.diameter_default = True
        self.diameter = self.gui.average_diameter.get_avg_diameter()
        self.weight = 1e-4  # standard value for the weight
        self.model_name = "new_model"
        self.re_train_model_name = None
        self.color = ft.Colors.BLUE_400
        self.progress_bar_text = ft.Text("")

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.model_directory = os.path.join(project_root, "models")

        # Changed from TextField to Dropdown for model type selection
        self.model_dropdown = ft.Dropdown(
            label="Model Type",
            value="nuclei",
            options=[
                ft.dropdown.Option("nuclei"),
                ft.dropdown.Option("cyto"),
                ft.dropdown.Option("cyto2"),
                ft.dropdown.Option("cyto3")
            ],border_color=ft.Colors.BLUE_400,
            on_select=lambda e: self.changed_input("modeltype", e),expand=True,
        )
        self.re_train_model = ft.Checkbox(value=False, label="Retrain Model",on_change=lambda e: self.change_re_train_model())

        # the following methods are called when clicking on the corresponding button
        async def pick_model_result(e: ft.Event[ft.Button]):
            """
            The result of the file selection is handled.

            Arguments:
                e (ft.FilePicker): pseudo Event, indicating the event structure
            """
            files = await ft.FilePicker().pick_files(allow_multiple=False,
                                                     initial_directory=self.model_directory)


            if files is None:
                #case: no model selected
                pass
            elif files[0].path is not None:
                self.gui.csp.re_train_model_path = files[0].path
                self.field_model_name.value = files[0].name
                self.re_train_model_name = files[0].name
                self.field_model_name.color = ft.Colors.BLUE_400
                self.gui.page.update()


        self.re_train_model_chooser = ft.IconButton(
                icon=ft.Icons.UPLOAD_FILE,
                tooltip="Choose model to retrain",
                on_click=lambda e: e.page.run_task(pick_model_result,e)

            )
        self.field_model_name = ft.TextField(label="Model Name", value=self.model_name, border_color=self.color,on_change=lambda e: self.changed_input("model_name", e))
        self.model_stack = ft.Stack([self.field_model_name, self.re_train_model_chooser],alignment=ft.Alignment.TOP_RIGHT)
        self.field_model = ft.Row([self.model_dropdown, self.model_stack])
        # New field for custom model input, visible only if "custom" is selected
        self.field_custom_model = ft.TextField(label="Custom Model", value="", border_color=self.color, visible=False,
                                               on_change=lambda e: self.changed_input("custom_model", e))

        self.field_batch = ft.TextField(label="Batch Size", value=self.batch_size, border_color=self.color,
                                        on_change=lambda e: self.changed_input("batch_size", e))
        self.field_epoch = ft.TextField(label="Epochs", value=self.epochs, border_color=self.color,
                                        on_change=lambda e: self.changed_input("epochs", e))
        self.field_lr = ft.TextField(label="Learning Rate", value=self.learning_rate, border_color=self.color,
                                     on_change=lambda e: self.changed_input("learning_rate", e))
        self.field_diameter = ft.TextField(label="Diameter", value=self.diameter, border_color=self.color,
                                           on_change=lambda e: self.changed_input("diameter", e))
        self.field_weights = ft.TextField(label="Weight Decay", value=self.weight, border_color=self.color,
                                          on_change=lambda e: self.changed_input("weight", e))
        self.field_directory = ft.TextField(label="Directory", value=format_directory_path(self.model_directory,60), border_color=self.color,
                                            read_only=True,disabled=True)

        self.directory_stack = ft.Stack([self.field_directory,ft.Container(
                            content=ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.COPY,
                                    tooltip="Copy to clipboard",
                                    on_click=lambda e: e.page.run_task(copy_to_clipboard,self.gui.page,self.model_directory,"Model directory")
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
                self.field_model_name.color = ft.Colors.BLUE_400
            else:
                self.field_model_name.value = None
        else:
            self.re_train_model_chooser.disabled = True
            self.field_diameter.disabled = False
            self.field_diameter.value = self.diameter
            self.field_model_name.color = None
            self.field_model_name.value = self.model_name
            self.model_dropdown.visible = True
        self.gui.page.update()

    def go_to_training_environment(self, e):
        # delete the content of the page and reset the reference to the page (reference get sometimes lost)
        self.gui.ref_training_environment.current.visible = True
        self.gui.ref_gallery_environment.current.visible = True
        #self.gui.ref_builder_environment.current.visible = False
        self.gui.ref_seg_environment.current.visible = False
        self.page.title = "CellSePi"
        self.gui.page.update()
        self.text.value = "Exit Training"
        #self.gui.ex_mode.text.value = "Go To Expert Mode"

    def add_parameter_container(self):
        return ft.Container(
            ft.Column(
                [self.field_model,self.re_train_model, self.field_custom_model, self.field_batch, self.field_epoch, self.field_weights,
                 self.field_lr, self.field_diameter, self.directory_stack
                 ]
            ), padding=10,
        )

    def changed_input(self, field, e):
        """
        Changing the value of one of the parameters for training.
        Arguments:
            field: the parameter to change
            e = the change event
        """
        updated_value = e.control.value

        if field == "modeltype":
            self.model = updated_value
            self.field_model.value = updated_value
            if updated_value == "custom":
                self.field_custom_model.visible = True
            else:
                self.field_custom_model.visible = False
        elif field == "custom_model":
            self.model = updated_value
            self.field_custom_model.value = updated_value
        elif field == "batch_size":
            self.batch_size = int(updated_value)
            self.field_batch.value = updated_value
        elif field == "epochs":
            self.epochs = int(updated_value)
            self.field_epoch.value = updated_value
        elif field == "learning_rate":
            self.learning_rate = float(updated_value)
            self.field_lr.value = updated_value
        elif field == "pre_trained":
            self.pre_trained = updated_value
            self.field_trained.value = updated_value
        elif field == "weight":
            self.weight = float(updated_value)
            self.field_weights.value = updated_value
        elif field == "model_name":
            self.model_name = updated_value
        else:
            self.diameter_default = False
            self.diameter = float(updated_value)
            self.field_diameter.value = updated_value

        self.gui.page.update()

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
                ft.Container(content=ft.Row([self.progress_ring, self.progress_bar_text]),padding=5),
                ft.Container(
                    content=ft.Row([self.start_button]))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        test_container = ft.Container(
            content=ft.Column(
                [title,
                 pick_model_row,
                 ]
            )
        )

        progress_card = ft.Card(
            content=ft.Container(
                content=ft.Stack(
                    [test_container]
                ),
                padding=10
            ),
        )

        return progress_card

    def start_training(self, e):
        """
        This method starts the training process with the selected parameters and model.
        """
        self.start_button.disabled = True
        self.re_train_model_chooser.disabled =True
        self.gui.directory.disable_path_choosing()
        self.progress_ring.visible = True
        self.progress_bar_text.value = ""
        self.disable_switch_environment()
        self.gui.page.update()

        # checks if the right model type was selected
        if self.re_train_model.value and self.re_train_model_name is None:
            self.page.show_dialog(ft.SnackBar(
                ft.Text(f"The model you inserted is not a retrained model!")))
            self.gui.directory.enable_path_choosing()
            self.start_button.disabled = False
            self.re_train_model_chooser.disabled = False
            self.progress_ring.visible = False
            self.progress_bar_text.value = ""
            self.enable_switch_environment()
            self.page.update()
            return
        self.gui.csp.training_running = True
        self.gui.queue.put("delete_mask")
        try:
            mask_filter = f"{self.gui.csp.current_mask_suffix}.npy"

            # loads the mask files out of the directory to start training
            output = io.load_train_test_data(train_dir=str(self.gui.csp.working_directory),
                                             mask_filter=mask_filter,
                                             look_one_level_down=False)
            images, labels, image_names, test_images, test_labels, image_names_test = output

        except Exception as e:
            self.page.show_dialog(ft.SnackBar(
                ft.Text(f"Something went wrong while gather training data: {str(e)}")))
            self.gui.directory.enable_path_choosing()
            self.start_button.disabled = False
            self.progress_ring.visible = False
            self.re_train_model_chooser.disabled = False
            self.progress_bar_text.value = ""
            self.enable_switch_environment()
            self.page.update()
            self.gui.csp.training_running = False
            if self.gui.training_event is not None:
                self.gui.training_event.set()
            return
        if len(images) == 0 or len(labels) == 0:
            self.page.show_dialog(ft.SnackBar(
                ft.Text(f"You need images and suitable masks to train a model!")))
            self.gui.directory.enable_path_choosing()
            self.start_button.disabled = False
            self.progress_ring.visible = False
            self.re_train_model_chooser.disabled = False
            self.progress_bar_text.value = ""
            self.enable_switch_environment()
            self.page.update()
            self.gui.csp.training_running = False
            if self.gui.training_event is not None:
                self.gui.training_event.set()
            return
        try:
            # initializing variables, who differ if pretrained or not (Initialized with not pretrained)
            sgd_value = False
            model_name = self.model_name
            model = models.CellposeModel(model_type=self.model, diam_mean=self.diameter)
            if self.re_train_model.value:
                sgd_value = True
                model_name = self.re_train_model_name
                model = models.CellposeModel(model_type=None, pretrained_model=self.gui.csp.re_train_model_path)

            # start the training epochs
            train.train_seg(model.net,
                            train_data=images, train_labels=labels,
                            channels=[1, 2], normalize=True,
                            test_data=test_images, test_labels=test_labels,
                            weight_decay=self.weight, SGD=sgd_value, learning_rate=self.learning_rate,
                            n_epochs=self.epochs, model_name=model_name,
                            save_path=os.path.dirname(self.model_directory))
            self.progress_bar_text.value = "Finished Training"

        except Exception as e:
            self.page.show_dialog(ft.SnackBar(
                ft.Text(f"Something went wrong while training: {str(e)}")))
            self.progress_bar_text.value = ""
            self.page.update()
        self.gui.directory.enable_path_choosing()
        self.start_button.disabled = False
        self.progress_ring.visible = False
        self.re_train_model_chooser.disabled =False
        self.enable_switch_environment()
        self.page.update()
        print("finished training")
        self.gui.csp.training_running = False
        if self.gui.training_event is not None:
            self.gui.training_event.set()

    def disable_switch_environment(self):
        self.switch_icon.color = ft.Colors.GREY_400
        self.button_training_environment_menu.disabled = True
        self.button_training_environment_menu.update()
        #self.gui.ex_mode.switch_icon.color = ft.Colors.GREY_400
        #self.gui.ex_mode.button_expert_environment_menu.disabled = True
        #self.gui.ex_mode.button_expert_environment_menu.update()

    def enable_switch_environment(self):
        self.switch_icon.color = None
        self.button_training_environment_menu.disabled = False
        self.button_training_environment_menu.update()
        #self.gui.ex_mode.switch_icon.color = None
        #self.gui.ex_mode.button_expert_environment_menu.disabled = False
        #self.gui.ex_mode.button_expert_environment_menu.update()
