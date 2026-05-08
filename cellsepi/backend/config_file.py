import ast
import json
import os
import shutil
import time
from threading import Lock

class DeletionForbidden(Exception):
    """
    Custom exception raised when a profile deletion is not allowed.

    This exception is used to indicate that a profile cannot be deleted,
    either because it is the last remaining profile or because the specified
    profile name does not exist.
    """
    pass

def load_config(file_directory):
    """
    Return the current config.json.

    It tries 5 times to read the file,
    before resetting the file to the default config.

    Args:
        file_directory (str): The directory of the file.

    Returns:
        create_default_config() (dict): If the current config.json is corrupted or not existing.
        json.load(config.json) (dict): If the current config.json is readable.
    """
    for _ in range(5):
        try:
            with open(file_directory, 'r') as file:
                return json.load(file)
        except (json.JSONDecodeError, FileNotFoundError):
            time.sleep(0.1)

    return reset_config(file_directory)


def reset_config(file_directory):
    """
    Creates a new default config and tries to save it.
    Args:
        file_directory (str): The directory of the file.

    Returns:
        create_default_config() (dict)
    """
    config = create_default_config()
    try:
        with open(file_directory, 'w') as file:
            json.dump(config, file, indent=4)
    except Exception as e:
        print(f"Error while saving config: {e}")
    return config

def create_default_config():
    """
    Create the default config.

    Returns:
        default_config (dict): the default config.json.
    """

    return {
        "Profiles": {
            "Lif": {
                "bf_channel": "2",
                "mask_suffix": "_seg",
                "channel_prefix": "c",
                "diameter": 125.0
                },
            "Tif": {
                "bf_channel": "1",
                "mask_suffix": "_seg",
                "channel_prefix": "c",
                "diameter": 250.0
                }
        },
        "Selected Profile": {
            "name": "Lif"
        },
        "Colors":{
            "mask": "(255, 0, 0)",
            "outline": "(0, 255, 0)",
        },
        "States": {
            "auto_button": False,
            "lif_slider": True,
        }
    }

class ConfigFile:
    """
    Manages the application's configuration file (config.json).

    This class provides methods to read, write, and modify the configuration
    file. It ensures proper validation of profile attributes and manages
    selected profiles.

    Attributes:
        project_root (str): The root directory of the project.
        file_directory (str): The full path to the configuration file.
        config (dict): The loaded configuration data.
        config_lock (Lock): a lock to make writing the config file save.
    """
    def __init__(self,filename="config.json"):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.file_directory = os.path.join(self.project_root, filename)
        self.config = load_config(self.file_directory)
        self.config_lock = Lock()

    def save_config(self):
        """
        Saves the current configuration to the config.json file.

        This method writes the current state of the "config" attribute
        to the "config.json" file.
        """
        with self.config_lock:
            try:
                with open(self.file_directory, 'w') as file:
                    json.dump(self.config, file, indent=4)

            except Exception as e:
                print(f"Error while saving config: {e}")


    def add_profile(self, name:str, bf_channel: int, mask_suffix:str, channel_prefix:str, diameter: float):
        """
        Adds a new profile to the config.

        Args:
            name (str): Name of the new profile.
            bf_channel (int): Bright-field channel for the profile.
            mask_suffix (str): Mask suffix for the profile.
            channel_prefix (str): Channel prefix for the profile.
            diameter (float): Diameter value for the profile.

        Invalid:
            - Strings ("mask_suffix", "channel_prefix" and "bf_channel") must not be empty ("").
            - Numeric values ("diameter") must be greater than 0.

        Raises:
            ValueError: If any provided parameter is invalid.

        Returns:
            False: If the profile name is already taken.
            True: If the profile is successfully added.
        """
        if not all([name, mask_suffix, channel_prefix, bf_channel]):
            raise ValueError("Name, mask_suffix, bf_channel, and channel_prefix must not be empty.")
        if diameter <= 0 :
            raise ValueError("diameter must be greater than 0.")
        if not name in self.config['Profiles']:
            self.config["Profiles"][name] = {
                "bf_channel": bf_channel,
                "mask_suffix": mask_suffix,
                "channel_prefix": channel_prefix,
                "diameter": diameter
            }
            self.save_config()
            return True
        else:
            return False

    def update_profile(self, name: str, bf_channel: str = None, mask_suffix: str = None,
                       channel_prefix: str = None, diameter: float = None):
        """
        Updates the attributes of a profile.

        Args:
            name (str): Name of the profile to update.
            bf_channel (str, optional): New bright-field channel.
            mask_suffix (str, optional): New mask suffix.
            channel_prefix (str, optional): New channel prefix.
            diameter (float, optional): New diameter value.

        Invalid:
            - Strings ("mask_suffix" and "channel_prefix") must not be empty ("").
            - Numeric values ("bf_channel" and "diameter") must be greater than 0.

        Raises:
            ValueError: If any provided parameter is invalid.
        """
        if name in self.config["Profiles"]:
            if bf_channel is not None:
                if not bf_channel:
                    raise ValueError("bf_channel must not be empty.")
                self.config["Profiles"][name]["bf_channel"] = bf_channel
            if mask_suffix is not None:
                if not mask_suffix:
                    raise ValueError("mask_suffix must not be empty.")
                self.config["Profiles"][name]["mask_suffix"] = mask_suffix
            if channel_prefix is not None:
                if not channel_prefix:
                    raise ValueError("channel_prefix must not be empty.")
                self.config["Profiles"][name]["channel_prefix"] = channel_prefix
            if diameter is not None:
                if diameter <= 0:
                    raise ValueError("diameter must be greater than 0.")
                self.config["Profiles"][name]["diameter"] = diameter
            self.save_config()

    def rename_profile(self,old_name: str,new_name: str):
        """
        Renames the old name to the new name.

        Args:
            old_name (str): The current/old name of the profile.
            new_name (str): The new name for the profile.

        Raises:
            ValueError: If any provided parameter is empty ("").

        Returns:
            False: If the new profile name is already taken or the old name does not exist.
            True: If the new profile is successfully renamed.
        """
        if not all([old_name,new_name]):
            raise ValueError("old_name, new_name must not be empty.")
        elif old_name == new_name:
            return True
        elif old_name in self.config["Profiles"] and new_name not in self.config["Profiles"]:
            self.config["Profiles"][new_name] = self.config["Profiles"].pop(old_name)
            self.save_config()
            if old_name == self.get_selected_profile_name():
                self.select_profile(new_name)
            return True
        else:
            return False

    def get_profile(self, name):
        """
        Gets a profile by name.

        Args:
            name (str): The name of the profile.

        Returns:
            profile (dict): A dictionary containing the profile's attributes.
        """
        if name in self.config["Profiles"]:
            return self.config["Profiles"][name]

    def delete_profile(self, name: str):
        """
        Deletes a profile by name.

        Args:
            name (str): The name of the profile.

        Raises:
             DeletionForbidden: If the profile count is equal to 1 or the profile does not exist.
        """
        if name in self.config["Profiles"] and len(self.config["Profiles"]) > 1:
            del self.config["Profiles"][name]
            if self.config["Selected Profile"]["name"] == name:
                first_key = next(iter(self.config["Profiles"]))
                self.config["Selected Profile"]["name"] = first_key
            self.save_config()
        else:
            raise DeletionForbidden


    def select_profile(self,name: str):
        """
        Selects a profile by name.

        Args:
            name (str): The name of the profile to select.

        Raises:
              ValueError: If the profile is empty ("").
        """
        if not name:
            raise ValueError("name must not be empty.")
        elif name in self.config["Profiles"]:
            self.config["Selected Profile"]["name"] = name
            self.save_config()

    def get_selected_profile_name(self):
        """
        Gets the name of the selected profile.

        Returns:
            profile name (str): The name of the selected profile or if the no profile is selected the first profile.
        """
        if self.config["Selected Profile"]["name"] is not None:
            return self.config["Selected Profile"]["name"]
        else:
            first_key = next(iter(self.config["Profiles"]))
            self.select_profile(first_key)
            return first_key

    def name_to_index(self, name: str):
        """
        Converts a profile name to its index.

        Args:
            name (str): The name of the profile.

        Raises:
            ValueError: If the profile does not exist.

        Returns:
            index (int): The index of the profile.
        """
        profiles = list(self.config["Profiles"].keys())
        if name in profiles:
            return profiles.index(name)
        else:
            raise ValueError("Profile with that name does not exists")

    def index_to_name(self, index: int):
        """
        Converts a profile index to its name.

        Args:
            index (int): The index of the profile.

        Raises:
            ValueError: If no profile is at this index.

        Returns:
            profile name (str): The name of the profile.
        """
        profiles = list(self.config["Profiles"].keys())
        if 0 <= index < len(profiles):
            return profiles[index]
        else:
            raise ValueError("Didnt find a profile at this index")

    def is_profile_existing(self, name: str):
        """
        Checks if a profile exists.

        Args:
            name (str): The name of the profile.

        Returns:
            Boolean: True if the profile exists, False otherwise.
        """
        return name in self.config["Profiles"]

    #------------------------------------------
    #getter for the selected profiles Attributes

    def get_selected_profile(self):
        """
        Gets the selected profile.

        Returns:
            profile (dict): A dictionary containing the profile's attributes.
        """
        name = self.get_selected_profile_name()
        return self.config["Profiles"][name]

    def get_bf_channel(self):
        """
        Gets the bright-field channel for the profile.

        Returns:
            bright-field channel (str): The bright-field channel for the profile.
        """
        profile = self.get_selected_profile()
        return profile["bf_channel"]

    def get_mask_suffix(self):
        """
        Gets the mask suffix for the profile.

        Returns:
            mask_suffix (str): The mask suffix for the profile.
        """
        profile = self.get_selected_profile()
        return profile["mask_suffix"]

    def get_channel_prefix(self):
        """
        Gets the channel prefix for the profile.

        Returns:
            channel_prefix (str): The channel prefix for the profile.
        """
        profile = self.get_selected_profile()
        return profile["channel_prefix"]

    def get_diameter(self):
        """
        Gets the diameter for the profile.

        Returns:
            diameter (float): The diameter for the profile.
        """
        profile = self.get_selected_profile()
        return float(profile["diameter"])

    def get_mask_color(self):
        """
        Gets the selected mask color.

        Returns:
            mask_color (tuple): The selected mask color in RGB format.
        """
        return ast.literal_eval(self.config["Colors"]["mask"])
    def get_outline_color(self):
        """
        Gets the selected outline color.

        Returns:
            outline_color (tuple): The selected mask color in RGB format.
        """
        return ast.literal_eval(self.config["Colors"]["outline"])
    def set_mask_color(self, color):
        """
        Sets the selected mask color in the config file.

        Args:
            color (tuple): The selected mask color in RGB format.

        Raises:
            ValueError: If the parameter color is invalid.
        """
        if isinstance(color, tuple) and len(color) == 3:
            self.config["Colors"]["mask"] = f"{color}"
            self.save_config()
        else:
            raise ValueError("Color must be an RGB tuple, e.g., (255, 0, 0)")
    def set_outline_color(self, color):
        """
        Sets the selected outline color in the config file.

        Args:
            color (tuple): The selected outline color in RGB format.
        Raises:
            ValueError: If the parameter color is invalid.
        """
        if isinstance(color, tuple) and len(color) == 3:
            self.config["Colors"]["outline"] = f"{color}"
            self.save_config()
        else:
            raise ValueError("Color must be an RGB tuple, e.g., (0, 255, 0)")
    def get_auto_button(self):
        """
        Gets the last state of the auto bright-field and contrast button.
        Returns:
            bool: The last state of the auto bright-field and contrast button.
        """
        return self.config["States"]["auto_button"]
    def get_lif_slider(self):
        """
        Gets the last state of the lif-slider button.
        Returns:
            bool: The last state of the lif-slider button (True means lif is active).
        """
        return self.config["States"]["lif_slider"]
    def set_auto_button(self, val:bool):
        """
        Sets the state of the auto bright-field and contrast button.
        """
        self.config["States"]["auto_button"] = val
        self.save_config()
    def set_lif_slider(self, val:bool):
        """
        Sets the state of the lif-slider button (True means lif is active).
        """
        self.config["States"]["lif_slider"] = val
        self.save_config()
    #-----------------------------------------------------
    #only for test_config
    def clear_config(self):
        """
        Only for Training
        ___________________________
        Makes a backup of the current config
        and deletes the original config.
        Then it loads the deleted config to trigger the default config to load.
        """
        backup_filepath = os.path.join(self.project_root, "config_backup.json")
        shutil.copy(self.file_directory, backup_filepath)
        open(self.file_directory, 'w').close()
        self.config = load_config(self.file_directory)

    def restore_config(self):
        """
        Only for Training
        ___________________________
        Copy's the backup back into the config.json file and
        refreshes the ConfigFile class with the "new" values.
        Then deletes the backup.
        """
        backup_filepath = os.path.join(self.project_root, "config_backup.json")
        shutil.copy(backup_filepath, self.file_directory)
        self.config = load_config(self.file_directory)
        os.remove(backup_filepath)
