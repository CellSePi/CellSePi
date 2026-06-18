from backend.expert_mode.module import ModuleGuiConfig, OutputPort, InputPort
from backend.expert_mode.module import Module
from backend.expert_mode.listener import Event, EventListener, PipelineCancelEvent
from typing import Type

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

class DummyModule5(Module):
    _gui_config = ModuleGuiConfig("test5", None, None)
    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self.outputs = {
            "port5": OutputPort("port5", int),
        }
        self._event_manager = None

    def run(self):
        result = 900
        self.outputs["port5"].data = result

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

class DummyMultiModule(Module):
    _gui_config = ModuleGuiConfig("testMulti", None, None)
    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self.inputs = {
            "port1": InputPort("port1", int,multi=["cat","dog"]),
            "port5": InputPort("port5",int,multi=True)
        }
        self.outputs = {
            "port7": OutputPort("port7", int),
            "port8": OutputPort("port8", int),
            "port9": OutputPort("port9", int)
        }


    def run(self):
        result1 = 0
        for value in self.inputs["port1"].data["dog"]:
            result1 += value
        self.outputs["port7"].data = result1

        result2 = 1

        for value in self.inputs["port1"].data["cat"]:
            result2 *= value
        self.outputs["port8"].data = result2

        result3 = 0
        for value in self.inputs["port5"].data:
            result3 += value
        self.outputs["port9"].data = result3


class DummyCancelDuringRunModule(Module):
    _gui_config = ModuleGuiConfig("CancelDuringRun", None, None)

    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self.pipeline_manager_ref = None

    def run(self):
        if self.pipeline_manager_ref is not None:
            self.pipeline_manager_ref.cancel()
        return False


class DummyCancelListener(EventListener):
    def __init__(self):
        self.last_event: PipelineCancelEvent | None = None
        self.event_type = PipelineCancelEvent

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def _update(self, event: Event) -> None:
        self.last_event = event