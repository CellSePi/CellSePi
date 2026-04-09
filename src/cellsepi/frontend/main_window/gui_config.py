import flet as ft
from cellsepi.frontend.main_window.gui_canvas import update_main_image
from cellsepi.backend.main_window.config_file import ConfigFile, create_default_config
from cellsepi.frontend.main_window.gui_page_overlay import PageOverlay


class GUIConfig:
    """
    Manages the GUI config and its elements.

    Attributes:
        config_class (ConfigFile): The instance of the ConfigFile class used to read and update profile data.
        page (Page): The page instance to display GUI elements.
        name_items (List): A list of buttons and text fields for editing or selecting profiles.
        profile_chooser_overlay (PageOverlay): The overlay shown when the profile name button is clicked.
        profile_ref (Ref): Reference to the currently selected profile name button.
        txt_bf_ref (Ref): Reference to the bright-field channel text field.
        txt_ms_ref (Ref): Reference to the mask suffix text field.
        txt_cp_ref (Ref): Reference to the channel prefix text field.
        txt_d_ref (Ref): Reference to the diameter text field.
    """
    def __init__(self,gui):
        """
        Initializes the GUIConfig instance.

        Args:
            gui (GUI): The GUI instance containing ConfigFile and Page references.
        """
        self.config_class: ConfigFile = gui.csp.config
        self.gui = gui
        self.page = gui.page
        self.name_items = self.create_name_items_profiles()
        self.profile_chooser_overlay = self.create_profile_overlay()
        #--------------------------------
        #creates attributes to reference to the text boxes to changes their values or color etc...
        self.profile_ref = ft.Ref[ft.Text]()
        self.txt_bf_ref = ft.Ref[ft.Text]()
        self.txt_ms_ref = ft.Ref[ft.Text]()
        self.txt_cp_ref = ft.Ref[ft.Text]()
        self.txt_d_ref = ft.Ref[ft.Text]()

    def create_profile_overlay(self):
        """
        Creates the overlay for selecting or editing profiles.

        The overlay is displayed when clicking the profile name button.
        It allows users to view, edit, or delete profiles in a scrollable list.

        Returns:
            overlay (CupertinoBottomSheet): The configured overlay for profile selection and editing.
        """
        return PageOverlay(self.page,
            content=ft.Stack([ft.Row([ft.Column(
                [ft.Card(ft.Container(ft.ListView(
                    controls=self.create_list_items(),
                    height=self.calc_height(),
                    width=350,
                    spacing=10,
                    padding=10,
                ),padding=15),height=self.calc_height()+60)],
                alignment=ft.MainAxisAlignment.CENTER,
            )],alignment=ft.MainAxisAlignment.CENTER),]),
            on_dismiss=lambda e: self.update_overlay(),
        )

    def calc_height(self):
        """
        Calculates the height of the profile list in the overlay.

        Returns:
            int: The height of the list. If the profile count exceeds 8, the height is capped at 400.
        """
        if len(self.config_class.config["Profiles"]) < 9:
            return 49 * len(self.config_class.config["Profiles"])
        else:
            return 400

    def text_field_activate(self,e, idx):
        """
        Toggles the activation of a profile's text field for editing.

        Ensures only one text field is active at a time, making the corresponding
        button invisible.

        Args:
            e (Event): The triggering event.
            idx (int): The index of the profile to activate or deactivate.
        """
        if not self.name_items[idx]["textfield"].visible:
            self.name_items[idx]["textfield"].visible = True
            self.name_items[idx]["button"].visible = False
            for i in range(len(self.config_class.config["Profiles"])):
                if not i ==  idx:
                    self.name_items[i]["textfield"].visible = False
                    self.name_items[i]["button"].visible = True
            self.page.update()
        else:
            self.name_items[idx]["textfield"].visible = False
            self.name_items[idx]["button"].visible = True
            self.page.update()

    def text_field_written(self,e, idx):
        """
        Handles the event when a text field is updated and attempts to rename
        the associated profile.

        Args:
            e (Event): The text_field update event.
            idx (int): The index of the profile try to rename.

        Behavior:
        -   Displays an error message if the name is invalid or taken.
        -   Updates the user interface on successful renaming.
        """
        try:
            renamed = self.config_class.rename_profile(self.config_class.index_to_name(idx), e.control.value)
            if not renamed:
                self.page.show_dialog(ft.SnackBar(
                    ft.Text("The name is already taken!")))
                self.page.update()
            else:
                self.name_items[idx]["textfield"].visible = False
                self.name_items[idx]["button"].visible = True
                self.name_items[idx]["textfield"].color = None
                self.profile_ref.current.value = self.config_class.get_selected_profile_name()
                self.update_overlay()
                self.page.update()
        except ValueError:
            self.page.show_dialog(ft.SnackBar(
                ft.Text("The name must be not empty!")))
            self.page.update()

    def create_name_items_profiles(self):
        """
        Creates TextField and Button for every profile and returns the set as a list.

        Returns:
            List[Dict]: A list of dictionaries, each representing a set of profile item.
        """
        return [
            {
                "textfield": ft.TextField(
                    value=profile,
                    width=200,
                    on_blur=lambda e,i=i:self.text_field_written(e,i),
                    visible = False,
                    border_color=ft.Colors.BLUE_ACCENT,
                ),
                "button": ft.TextButton(
                    content=ft.Text(profile, size=20),
                    on_click=lambda e, i=i: self.selected_profile_changed(e, i,True),
                    width=200,
                    visible = True
                )
            }
            for i, profile in enumerate(self.config_class.config["Profiles"])
        ]

    def selected_profile_changed(self,e, index, called_by_overlay: bool = None):
        """
        Handles the event when a profile is selected, updates the profile attributes,
        and closes the profile selection overlay.

        Args:
            e (Event): The event representing the user's profile selection.
            index (int): The index of the selected profile.
            called_by_overlay (bool): Whether the overlay is called by overlay.

        Behavior:
        -   Selects the profile based on the provided index.
        -   Updates the UI elements with the corresponding profile attributes (e.g.,
            channel, mask suffix, diameter, etc.).
        -   resets the colors of the input fields to their default state, clearing any error indications (such as red color).
        -   Closes the profile chooser overlay and updates the page.
        """
        self.config_class.select_profile(self.config_class.index_to_name(index))
        self.profile_ref.current.value = self.config_class.get_selected_profile_name()
        self.txt_bf_ref.current.value = self.config_class.get_bf_channel()
        self.txt_ms_ref.current.value = self.config_class.get_mask_suffix()
        self.txt_cp_ref.current.value = self.config_class.get_channel_prefix()
        self.txt_d_ref.current.value = self.config_class.get_diameter()
        self.txt_bf_ref.current.color = None
        self.txt_ms_ref.current.color = None
        self.txt_cp_ref.current.color = None
        self.txt_d_ref.current.color = None
        if called_by_overlay:
            self.profile_chooser_overlay.close()
        self.page.update()

    def remove_profile(self,e, idx):
        """
        Handles the event for removing a profile.

        This method deletes the profile at the specified index and updates the UI accordingly.
        It also ensures that the selected profile is updated and the overlay is refreshed.

        Args:
            e (Event): The event triggered by the action to remove the profile.
            idx (int): The index of the profile to be removed.
        """
        self.config_class.delete_profile(self.config_class.index_to_name(idx))
        self.profile_ref.current.value = self.config_class.get_selected_profile_name()
        self.update_overlay()
        self.page.update()

    def update_overlay(self):
        """
        Updates the profile chooser overlay with the latest list of profiles.

        This method rebuilds the list of profile items when a profile's name is changed
        or a profile is deleted. It then updates the overlay content to reflect the
        changes and ensures the profile list is displayed correctly.
        """
        new_picker_items = self.create_list_items()
        new_content = ft.Stack([ft.Row([ft.Column(
            controls=[ft.Card(
                    ft.Container(
                        ft.ListView(
                            controls=new_picker_items,
                            height=self.calc_height(),
                            width=350,
                            spacing=10,
                            padding=10,
                        )
                    ,padding=15
                    )
                ,height=self.calc_height()+60
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )],alignment=ft.MainAxisAlignment.CENTER),])
        self.profile_chooser_overlay.content = new_content

    def add_profile_pressed(self,e):
        """
        Handles the event for adding a new profile.

        Args:
            e (Event): The event triggered by the action to add a profile.
        """
        if self.gui.directory.is_lif:
            default = create_default_config()["Profiles"]["Lif"]
        else:
            default = create_default_config()["Profiles"]["Tif"]
        counter = 0
        new_name = "new Profile"

        while self.config_class.is_profile_existing(new_name):
            counter += 1
            new_name = "new Profile" + str(counter)

        self.config_class.add_profile(new_name,default["bf_channel"],default["mask_suffix"],default["channel_prefix"],default["diameter"])
        self.selected_profile_changed(e, self.config_class.name_to_index(new_name))
        self.update_overlay()
        self.page.update()

    def create_list_items(self):
        """
        Creates and returns a list of profile items with corresponding buttons for interaction.

        This method generates a list of items, where each item includes:
        -   A text field for displaying and editing the profile name.
        -   A button to select the profile by name.
        -   A delete button, which is only included if there are more than one profile.
        -   A edit button to activate the text field for profile renaming.

        Returns:
            List[ft.Row]: A list of rows containing the profile controls for interaction,
                          including buttons for deleting, editing, and selecting profiles.
        """
        self.name_items = self.create_name_items_profiles()
        if len(self.config_class.config["Profiles"]) > 1:
            return [
                ft.Row(
                    controls=[
                        self.name_items[i]["textfield"],
                        self.name_items[i]["button"],
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=ft.Colors.RED,
                            on_click=lambda e, i=i: self.remove_profile(e, i),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DRAW,
                            icon_color=ft.Colors.BLUE,
                            on_click=lambda e, i=i: self.text_field_activate(e, i),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
                for i in reversed(range(len(self.config_class.config["Profiles"])))
            ]
        else:
            return [
                ft.Row(
                    controls=[
                        self.name_items[i]["textfield"],
                        self.name_items[i]["button"],
                        ft.IconButton(
                            icon=ft.Icons.DRAW,
                            icon_color=ft.Colors.BLUE,
                            on_click=lambda e, i=i: self.text_field_activate(e, i),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
                for i in range(len(self.config_class.config["Profiles"]))
            ]


    async def bf_updater(self, e):
        """
        Handles the event of updating the bright-field (BF) channel.

        This method validates the entered value for the BF channel. If the value is invalid,
        an error message is displayed to the user. A valid BF channel is expected to be not empty.

        Args:
            e (Event): The event triggered by the user interaction, containing the new BF channel value.
        """
        try:
            self.config_class.update_profile(self.config_class.get_selected_profile_name(),
                                             bf_channel=e.control.value)
            self.txt_bf_ref.current.color = None
            self.gui.directory.update_all_masks_check()
            self.gui.diameter_text.value = self.gui.average_diameter.get_avg_diameter()
            self.page.update()
            if self.gui.csp.image_id is not None:
                await update_main_image(self.gui.csp.image_id, self.gui.csp.channel_id, self.gui, False)
            if not self.gui.csp.readout_running and not self.gui.csp.segmentation_running:
                self.gui.page.run_task(self.gui.directory.check_masks)
        except ValueError:
            self.page.open(ft.SnackBar(ft.Text("Bright field channel must be not empty!")))
            self.txt_bf_ref.current.color = ft.Colors.RED
            self.page.update()

    def ms_updater(self, e):
        """
        Handles the event of updating the mask suffix.

        This method checks if the entered mask suffix is valid. If the suffix is empty,
        an error message is displayed to the user. Otherwise, the mask suffix is updated
        for the selected profile.

        Args:
            e (Event): The event triggered by the user interaction, containing the new mask suffix value.
        """
        if e.control.value:
            self.config_class.update_profile(self.config_class.get_selected_profile_name(), mask_suffix=e.control.value)
            self.gui.canvas.mask_suffix=e.control.value
            self.txt_ms_ref.current.color = None
            self.page.update()
        else:
            self.page.open(ft.SnackBar(ft.Text("Mask suffix must be not empty!")))
            self.txt_ms_ref.current.color = ft.Colors.RED
            self.page.update()

    def cp_updater(self,e):
        """
        Handles the event of updating the channel prefix.

        This method checks if the entered channel prefix is valid. If the prefix is empty,
        an error message is displayed to the user. Otherwise, the channel prefix is updated
        for the selected profile.

        Args:
            e (Event): The event triggered by the user interaction, containing the new channel prefix value.
        """
        if e.control.value:
            self.config_class.update_profile(self.config_class.get_selected_profile_name(), channel_prefix=e.control.value)
            self.txt_cp_ref.current.color = None
            self.page.update()
        else:
            self.page.open(ft.SnackBar(ft.Text("Channel prefix must be not empty!")))
            self.txt_cp_ref.current.color = ft.Colors.RED
            self.page.update()

    def d_updater(self,e):
        """
        Handles the event of updating the diameter.

        This method checks if the entered diameter is a valid decimal number. If the value is
        invalid or not greater than 0, an error message is displayed to the user. Otherwise,
        the diameter is updated for the selected profile.

        Args:
            e (Event): The event triggered by the user interaction, containing the new diameter value.
        """
        try:
            self.config_class.update_profile(self.config_class.get_selected_profile_name(), diameter=float(e.control.value))
            self.txt_d_ref.current.color = None
            self.page.update()
        except ValueError:
            self.page.open(ft.SnackBar(ft.Text("Diameter only allows decimals numbers, greater than 0!")))
            self.txt_d_ref.current.color = ft.Colors.RED
            self.page.update()

    def create_profile_container(self):
        """
        Creates and returns the profile container for the GUI.

        This method generates a container that includes:
        -   A row with the current selected profile and a button to open the profile chooser overlay.
        -   Text fields for modifying various attributes of the selected profile:
            -   Bright-Field Channel
            -   Mask Suffix
            -   Channel Prefix
            -   Diameter

        Each text field is associated with an updater method to handle value changes and validate inputs.

        Returns:
            ft.Container: The container holding the text fields for modifying selected profile attributes and the button to open the overlay.
        """
        #--------------------------------------
        #creates the TextFields for the diffrent attributes of a profile
        tf_bf = ft.TextField(
            label="Bright-Field Channel:",
            border_color=ft.Colors.BLUE_ACCENT,
            value=self.config_class.get_bf_channel(),
            ref=self.txt_bf_ref,
            on_blur=self.bf_updater,
            width=200,
            height=60,
        )

        tf_ms = ft.TextField(
            label="Mask Suffix:",
            border_color=ft.Colors.BLUE_ACCENT,
            value=self.config_class.get_mask_suffix(),
            ref=self.txt_ms_ref,
            on_blur=lambda e: self.ms_updater(e),
            width=200,
            height=60,
        )

        tf_cp = ft.TextField(
            label="Channel Prefix:",
            border_color=ft.Colors.BLUE_ACCENT,
            value=self.config_class.get_channel_prefix(),
            ref= self.txt_cp_ref,
            on_blur=lambda e: self.cp_updater(e),
            width=200,
            height=60,
        )

        tf_d = ft.TextField(
            label="Diameter:",
            border_color=ft.Colors.BLUE_ACCENT,
            value=self.config_class.get_diameter(),
            ref=self.txt_d_ref,
            on_blur=lambda e: self.d_updater(e),
            width=200,
            height=60,
        )



        #creates the Row with the current selected Profile as button and when you click on it,
        #it opens the profile_chooser_overlay
        profiles_row = ft.Row(
            tight=True,
            controls=[
                ft.Text("Profile:", size=18),
                ft.TextButton(
                    content=ft.Text(self.config_class.get_selected_profile_name(), size=18, ref=self.profile_ref),
                    style=ft.ButtonStyle(color=ft.Colors.BLUE),
                    on_click=lambda e: self.profile_chooser_overlay.open()
                ),
                ft.IconButton(
                    icon=ft.Icons.LIBRARY_ADD_ROUNDED,
                    #content=ft.Text("Add Profile", size=18),
                    tooltip="Add new profile",
                    on_click=lambda e: self.add_profile_pressed(e)
                ),

            ],
        )

        #creates the final Container that is displayed in the GUI
        return ft.Container(ft.Column([
                            profiles_row,
                            ft.Row([tf_bf, tf_cp]),
                            ft.Row([tf_ms, tf_d])]),padding=10)




