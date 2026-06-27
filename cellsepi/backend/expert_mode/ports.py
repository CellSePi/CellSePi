from typing import Union, Set


class Port:
    """
    Ports defines an input or output of a module.
    Ports with the same names in different modules are considered as the same type of ports
    and their data can be transferred with pipes to each other.
    """
    def __init__(self, name: str, data_type: type, opt: bool = False, multi: Union[bool, Set[str]] = False):
        self.name = name
        self.data_type = data_type #type
        self.opt = opt #optional
        if not multi:
            self.mode = "single" #how many inputs are allowed
            self._data = None
        elif isinstance(multi, (set, list, tuple)):
            self.mode = "multi_tagged"
            if isinstance(multi, set):
                self.allowed_tags = sorted(list(multi))
            else:
                self.allowed_tags = list(dict.fromkeys(multi))
            self._data = {tag: list() for tag in self.allowed_tags}
        elif multi is True:
            self.mode = "multi_list"
            self._data = list()
        else:
            raise ValueError("Parameter multi must be False, True, or a collection of tags.")

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if value is None:
            self.clear()
            return
        if self.mode == "single":
            if not isinstance(value, self.data_type):
                raise TypeError(f"Typ error: single needs {self.data_type.__name__}, not {type(value).__name__}!")
        elif self.mode == "multi_tagged":
            if not isinstance(value, dict):
                raise TypeError(f"Typ error: multi_tagged needs a Dictionary, not {type(value).__name__}!")
        elif self.mode == "multi_list":
            if not isinstance(value, list):
                raise TypeError(f"Typ error: multi_list needs a List, not {type(value).__name__}!")

        self._data = value

    def clear(self):
        if self.mode == "single":
            self._data = None
        elif self.mode == "multi_tagged":
            self._data = {tag: list() for tag in self.allowed_tags}
        elif self.mode == "multi_list":
            self._data = list()
        else:
            raise ValueError("Parameter multi must be False, True, or a collection of tags.")

    def add_data(self, value, tag: str | None = None):
        """
        Raises:
            TypeError: If the data type is not the required type.
        """
        if not(isinstance(value, self.data_type) or value is None):
            raise TypeError(f"Expected data of type {self.data_type}, got {type(value)}!")
        if self.mode == "single":
            self._data = value
        elif self.mode == "multi_tagged":
            if tag in self._data:
                self._data[tag].append(value)
            else:
                raise ValueError(f"Tag {tag} is not valid for this port!")
        else:
            self._data.append(value)

    def __str__(self):
        return f"port_name: {self.name}, port_data_type: {self.data_type.__name__}, opt: {self.opt}, data: {self.data}, mode: {self.mode}"

class InputPort(Port):
    """
    InputPorts defines an input for a module.
    Ports with the same names in different modules are considered as the same type of ports
    and their data can be transferred with pipes to each other.

    Attributes:
        name (str): Port name. Used as attribute on 'self.inputs'.
        data_type (type): Expected Python type (for documentation).
        opt (bool): If 'True', port is optional (no warning when unconnected). Defaults to False.
        multi (Union[bool, Set[str]]): Defines if the port accepts multiple connections.
            If 'False' (default), it accepts a single connection.
            If 'True', it accepts multiple connections.
            If a set of strings is provided, it acts as a multi-port that uses these tags.

    ### Examples:
    ```python
    # Standard single input
    InputPort("image_paths", dict)

    # Optional multi-port
    InputPort("image_paths", dict, opt=True, multi=True)

    # Tagged multi-port
    InputPort("image_paths", dict, multi={"SEG", "SDM"})
    ```
    """
    def __init__(self, name: str, data_type: type, opt: bool = False,  multi: Union[bool, Set[str]] = False):
        super().__init__(name, data_type, opt,multi)

class OutputPort(Port):
    """
    OutputPorts defines an output for a module.
    Ports with the same names in different modules are considered as the same type of ports
    and their data can be transferred with pipes to each other.

    Attributes:
        name (str): Port name. Used as attribute on 'self.outputs'.
        data_type (type): Type of the data provided by this port.

    ### Example:
    ```python
    OutputPort("mask_paths", dict)
    ```
    """
    def __init__(self, name: str, data_type: type):
        super().__init__(name, data_type)


class PortCollection(dict):
    """
    Base class for a collection of Ports.
    """

    def __init__(self, *ports: Port):
        super().__init__({port.name: port for port in ports})

    def __getattr__(self, name):
        """
        Allows to use self.inputs.example instead of self.inputs["example"].
        """
        if name in self:
            return self[name]
        raise AttributeError(f"Port '{name}' does not exists.")


class InputPorts(PortCollection):
    """Collection of InputPorts"""

    def __init__(self, *ports: InputPort):
        super().__init__(*ports)


class OutputPorts(PortCollection):
    """Collection of OutputPorts"""

    def __init__(self, *ports: OutputPort):
        super().__init__(*ports)