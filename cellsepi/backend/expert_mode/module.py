import threading

from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable
from typing import List

import flet as ft

from backend.expert_mode.event_manager import EventManager
from backend.expert_mode.listener import ProgressEvent
from backend.expert_mode.limits import Limit
from backend.expert_mode.ports import *


class FilePath:
    """
    Type to specify FilePath's
    """
    def __init__(self, path: str = "", suffix: List[str]=None):
        self.path = path
        self.suffix = suffix


class DirectoryPath:
    """
    Type to specify DirectoryPath's
    """
    def __init__(self, path: str = ""):
        self.path = path



class Categories(Enum):
    """
    Categories of the different modules, each with its own color.

    Warning:
        Red and green are reserved for pipeline status indicators
        and must not be used for new categories.
    """
    INPUTS = ft.Colors.ORANGE
    OUTPUTS = ft.Colors.LIGHT_BLUE
    FILTERS = ft.Colors.PURPLE_ACCENT
    MANUAL = ft.Colors.PINK
    SEGMENTATION = ft.Colors.AMBER_ACCENT

class ModuleGuiConfig:
    """Stores configuration information for a module's GUI representation.

    Attributes:
        name (str): Display name on the module card. Must be unique.
        category (Categories): Determines the color of the module card.
        description (str): Tooltip shown when hovering the module.

    ### Example:
    ```python
    _gui_config = ModuleGuiConfig(
        "MyModule",
        Categories.FILTERS,
        "Does something useful."
    )
    ```
    """
    def __init__(self, name: str, category: Categories, description:str = None):
        self.name = name
        self.category = category
        self.description = description

class IdNumberManager:
    """
    Manages the module ID's so every module has a unique ID.
    """
    def __init__(self):
        self._occupied_id_numbers = set()
        self._next_id_number = 0

    def get_id_number(self) -> int:
        """
        Gets the next free id number.
        """
        while self._next_id_number in self._occupied_id_numbers:
            self._next_id_number += 1
        id_number = self._next_id_number
        self._occupied_id_numbers.add(id_number)
        self._next_id_number += 1
        return id_number

    def occupy_id_number(self, id_number: int):
        """
        Occupies the given id number so no other module can get it.
        """
        if id_number in self._occupied_id_numbers:
            raise ValueError(f"Number {id_number} already occupied!")
        self._occupied_id_numbers.add(id_number)
        if id_number ==  self._next_id_number:
            self._next_id_number = id_number + 1

    def free_id_number(self, id_number: int) -> None:
        """
        Frees the id number given.
        Raises:
            ValueError: if the id_number given is not occupied.
        """
        if id_number in self._occupied_id_numbers:
            self._occupied_id_numbers.discard(id_number)
            if self._next_id_number > id_number >= 0:
                self._next_id_number = id_number
        else:
            raise ValueError(f"Number {id_number} not occupied!")


class Module(ABC):
    """
    Modules are independent processes within the pipeline that perform a specific task.
    The modules should be designed to function independently of other modules,
    as long as the correct inputs are provided.

    You can specify user attributes with 'user_' as prefix.
    With these automatic overlay gets created if settings is None.
    """
    @abstractmethod
    def __init__(self,module_id: str = None):
        self.module_id:str = self.get_new_id() if module_id is None else module_id
        self.event_manager: EventManager | None = None
        self._cancel_event: threading.Event | None = None
        self.inputs: InputPorts = InputPorts()
        self.outputs: OutputPorts = OutputPorts()
        self._settings: ft.Control | None = None
        self._on_settings_dismiss: Callable[[], None] | None = lambda : None

        """
        User-defined attributes convention:        
        - Add custom attributes by prefixing them with 'user_'.
          Example: user_example: str = "Example"
        - Always initialize user attributes with a non-empty value.
        - Supported types: int, float, str, bool, FilePath, DirectoryPath, Enum.
        - Set limits for int/float attributes by defining a matching 'limit_' attribute using the Limit class.
              - Example: self.limit_user_example = Limit(min_val=0.0, max_val=10.0)        
        - User attributes are also saved when the pipeline is saved.
        - When `_settings` is None, GUI elements are automatically generated.
              - For attributes of type int, float, or str, a corresponding reference
                to the GUI element is also automatically generated, named with the
                prefix 'ref_'. Example: ref_user_example
              - For attributes of type bool or Enum, an on_change event handler 
                is automatically generated. Its name is built with the prefix 'on_change_' 
                followed by the attribute name. Example: on_change_user_example
        """


    @classmethod
    def get_new_id(cls) -> str:
        """
        Returns the module ID.
        """
        if not hasattr(cls, "_id_number_manager"):
            cls._id_number_manager = IdNumberManager()
        return cls.gui_config().name + "_" + str(cls._id_number_manager.get_id_number())

    @classmethod
    def occupy_id_number(cls,id_number: int):
        """
        Occupies the given ID number in the id number manager.
        """
        if not hasattr(cls, "_id_number_manager"):
            cls._id_number_manager = IdNumberManager()
        cls._id_number_manager.occupy_id_number(id_number)

    @classmethod
    def free_id_number(cls, id_number: int):
        """
        Gives the given id number free for other modules.
        """
        if not hasattr(cls, "_id_number_manager"):
            cls._id_number_manager = IdNumberManager()
        cls._id_number_manager.free_id_number(id_number)

    @classmethod
    def destroy_id_number_manager(cls):
        """
        Destroys the id number manager.
        """
        if hasattr(cls, "_id_number_manager"):
            del cls._id_number_manager

    @classmethod
    def gui_config(cls) -> ModuleGuiConfig:
        """
        Returns the module gui config which has the name of the module its category and a description.
        """
        return cls._gui_config

    def occupy(self):
        """
        Occupies the currently module_id the module has in the id number manager.
        """
        id_number = self.module_id.removeprefix(f"{self.gui_config().name}_")
        if id_number != "":
            number = int(id_number)
            self.occupy_id_number(number)
        else:
            raise ValueError("module_id dosen't contain a number!")

    def get_id_number(self)-> int:
        """
        Gets the module ID's number.
        """
        id_number = self.module_id.removeprefix(f"{self.gui_config().name}_")
        return int(id_number)

    def destroy(self):
        """
        Module gets destroyed so free the id_number for other modules.
        Raises:
            ValueError: If the module_id doesn't contain a number.
        """
        id_number = self.module_id.removeprefix(f"{self.gui_config().name}_")
        if id_number != "":
            number = int(id_number)
            self.free_id_number(number)
        else:
            raise ValueError("module_id doesn't contain a number!")

    def is_cancelled(self) -> bool:
        """
        Returns True if the pipeline has requested a cancel.
        Modules with long-running internal loops should check this periodically.
        """
        return self._cancel_event is not None and self._cancel_event.is_set()

    def get_mandatory_inputs(self) -> List[str]:
        """
        Returns the list of names of input ports that are required by the module.
        """
        mandatory_inputs = []
        for port in self.inputs.values():
            if not port.opt:
                mandatory_inputs.append(port.name)
        return mandatory_inputs

    @property
    def settings(self) -> ft.Control |None:
        """
        The settings overlay of the module in the gui.
        If it is None it gets generated automatically if the modules has user_attributes.
        """
        return self._settings

    def settings_init(self):
        """
        After creation of the settings this method is called.
        """
        return None

    def finished(self):
        """
        Gets executed when the module is complete finished include possible pausing.
        """
        return

    @property
    def on_settings_dismiss(self) -> Callable[[], None]:
        """
        The function called when the settings get dismiss.
        """
        return self._on_settings_dismiss

    @property
    def get_user_attributes(self) -> list[str]:
        """
        Returns the list of attributes of the module's user attributes.
        """
        keys = []
        for k in self.__dict__:
            if k.startswith("user_"):
                keys.append(k)
        return keys

    @abstractmethod
    def run(self) -> bool: #pragma: no cover
        """
        Returns True if the pipeline should pause.
        """
        pass

    def __str__(self):
        return f"module_id: {self.module_id}, category: {self.gui_config().category}, module_name: {self.gui_config().name}, inputs: {self.inputs}, outputs: {self.outputs}, user_attributes: {self.get_user_attributes}"


