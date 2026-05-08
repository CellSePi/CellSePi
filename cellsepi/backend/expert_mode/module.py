from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable
from typing import Dict,List

import flet as ft

from backend.main_window import EventManager

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


class Port:
    """
    Ports defines an input or output of a module.
    Ports with the same names in different modules are considered as the same type of ports
    and their data can be transferred with pipes to each other.
    """
    def __init__(self, name: str, data_type: type, opt: bool = False):
        self.name = name
        self.data_type = data_type #type
        self.opt = opt #optional
        self._data = None

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        """
        Raises:
            TypeError: If the data type is not the required type.
        """
        if isinstance(value, self.data_type) or value is None:
            self._data = value
        else:
            raise TypeError(f"Expected data of type {self.data_type}, got {type(value)}!")

    def __str__(self):
        return f"port_name: '{self.name}', port_data_type: '{self.data_type.__name__}', opt: {self.opt}, data: {self.data}"

class InputPort(Port):
    """
    InputPorts defines an input of a module.
    Ports with the same names in different modules are considered as the same type of ports
    and their data can be transferred with pipes to each other.
    """
    def __init__(self, name: str, data_type: type, opt: bool = False):
        super().__init__(name, data_type, opt)

class OutputPort(Port):
    """
    OutputPorts defines an output of a module.
    Ports with the same names in different modules are considered as the same type of ports
    and their data can be transferred with pipes to each other.
    """
    def __init__(self, name: str, data_type: type):
        super().__init__(name, data_type)

class Categories(Enum):
    """
    Categories of the different modules, each with its own color.
    It is forbidden to use red or green, as they are reserved to indicate specific statuses.
    """
    INPUTS = ft.Colors.ORANGE
    OUTPUTS = ft.Colors.LIGHT_BLUE
    FILTERS = ft.Colors.PURPLE_ACCENT
    MANUAL = ft.Colors.PINK
    SEGMENTATION = ft.Colors.AMBER_ACCENT

class ModuleGuiConfig:
    """
    Stores configuration information for a module's GUI representation.
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
        self.inputs: Dict[str,InputPort] = {}
        self.outputs: Dict[str,OutputPort] = {}
        self._settings: ft.Stack | None = None
        self._on_settings_dismiss: Callable[[], None] | None = lambda : None
        """
        User-defined attributes convention:        
        - Add custom attributes by prefixing them with 'user_'.
          Example: user_example: str = "Example"
        - Always initialize user attributes with a non-empty value.
        - Supported types: int, float, str, bool, FilePath, DirectoryPath.        
        - User attributes are also saved when the pipeline is saved.
        - When `_settings` is None, GUI elements are automatically generated.
              - For attributes of type int, float, or str, a corresponding reference
                to the GUI element is also automatically generated, named with the
                prefix 'ref_'. Example: ref_user_example
              - For attributes of type bool, an on_change event handler is automatically
                generated. Its name is built with the prefix 'on_change_' followed by the 
                attribute name. Example: on_change_user_example
        """


    @classmethod
    def get_new_id(cls) -> str:
        """
        Returns the module ID.
        """
        if not hasattr(cls, "_id_number_manager"):
            cls._id_number_manager = IdNumberManager()
        return cls.gui_config().name + str(cls._id_number_manager.get_id_number())

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
        id_number = self.module_id.removeprefix(self.gui_config().name)
        if id_number != "":
            number = int(id_number)
            self.occupy_id_number(number)
        else:
            raise ValueError("module_id dosen't contain a number!")

    def get_id_number(self)-> int:
        """
        Gets the module ID's number.
        """
        id_number = self.module_id.removeprefix(self.gui_config().name)
        return int(id_number)

    def destroy(self):
        """
        Module gets distroyed so free the id_number for other modules.
        Raises:
            ValueError: If the module_id dosen't contain a number.
        """
        id_number = self.module_id.removeprefix(self.gui_config().name)
        if id_number != "":
            number = int(id_number)
            self.free_id_number(number)
        else:
            raise ValueError("module_id dosen't contain a number!")

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
    def settings(self) -> ft.Stack|None:
        """
        The settings overlay of the module in the gui.
        If it is None it gets generated automatically if the modules has user_attributes.
        """
        return self._settings

    def finished(self):
        """
        Gets executed when the module is complety finished include possible pausing.
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
        return f"module_id: '{self.module_id}', category: '{self.gui_config().category}', module_name: {self.gui_config().name}, inputs: {self.inputs}, outputs: {self.outputs}, user_attributes: {self.get_user_attributes}"


