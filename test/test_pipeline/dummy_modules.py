from backend.main_window import ModuleGuiConfig, OutputPort, InputPort
from backend.main_window import Module


class DummyModule1(Module):
    _gui_config = ModuleGuiConfig("test1", None, None)
    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self.outputs = {
            "port1": OutputPort("port1", int),
            "port5": OutputPort("port5", str),
        }
        self._on_settings_dismiss = self.test
        self._event_manager = None
        self.user_test1: int = 1
        self.user_test2: int = 2
        self.user_test3: int = 3
        self.user_test4: int = 4

    def test(self):
        self.user_test4 +=1

    def run(self):
        result = 42 + 25
        self.outputs["port1"].data = result


class DummyModule2(Module):
    _gui_config = ModuleGuiConfig("test2", None, None)
    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self.inputs = {
            "port1": InputPort("port1", int),
            "port5": InputPort("port5", str,True),
        }
        self.outputs = {
            "port2": OutputPort("port2", str)
        }

    def run(self):
        port1 = self.inputs["port1"].data
        self.outputs["port2"].data = f"The resulting data is: {port1}"

class DummyModule3(Module):
    _gui_config = ModuleGuiConfig("test3", None, None)
    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self.inputs = {
            "port1": InputPort("port1", str),
        }

    def run(self): #pragma: no cover
            pass

class DummyModule4(Module):
    _gui_config = ModuleGuiConfig("test4", None, None)
    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self.inputs = {
            "port1": InputPort("port1", int),
            "port2": InputPort("port2", str),
            "port4": InputPort("port4", str,True),
            "port5": InputPort("port5", str,True),
        }
        self.outputs = {
            "port!": OutputPort("port1", int),
            "port3": OutputPort("port3", str),
        }
    def run(self):
        result = self.inputs["port2"].data + " == " + str(self.inputs["port1"].data)
        self.outputs["port3"].data = result

class DummyPauseModule(Module):
    _gui_config = ModuleGuiConfig("testPause", None, None)
    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self.inputs = {
            "port1": InputPort("port1", int),
        }
        self.outputs = {
            "port1": OutputPort("port1", int)
        }
        self._event_manager = None
        self.user_test1: int = 1
        self.user_test2: int = 2
        self.user_test3: int = 3
        self.user_test4: int = 4

    def run(self):
        result = 42 + 25
        self.outputs["port1"].data = result
        return True