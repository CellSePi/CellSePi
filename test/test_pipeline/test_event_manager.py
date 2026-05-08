from backend.main_window import Module, ModuleGuiConfig
from backend.main_window import PipelineManager, PipelineRunningException
import pytest

class DummyErrorModule(Module):
    _gui_config = ModuleGuiConfig("ErrorModule", None, None)
    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self._name = module_id
        self._event_manager = None

    def run(self):
        raise PipelineRunningException("test","test")

class DummyEvent(Event):
    def __init__(self):
        self.test = "test"

class DummyListener(EventListener):
    def __init__(self):
        self.last_event: ProgressEvent | None = None
        self.event_type = ProgressEvent

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def _update(self,event: Event) -> None:
        self.last_event = event

class DummyErrorListener(EventListener):
    def __init__(self):
        self.last_event: ErrorEvent | None = None
        self.event_type = ErrorEvent

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def _update(self,event: Event) -> None:
        self.last_event = event

class DummyPipelineErrorListener(EventListener):
    def __init__(self):
        self.last_event: PipelineErrorEvent | None = None
        self.event_type = PipelineErrorEvent

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def _update(self,event: Event) -> None:
        self.last_event = event

class DummyDragDropListener(EventListener):
    def __init__(self):
        self.last_event: DragAndDropEvent | None = None
        self.event_type = DragAndDropEvent

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def _update(self,event: Event) -> None:
        self.last_event = event

class DummyPipelineStateListener(EventListener):
    def __init__(self):
        self.last_event: PipelineStateChangeEvent | None = None
        self.event_type = PipelineStateChangeEvent

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def _update(self,event: Event) -> None:
        self.last_event = event

class DummyModuleListener(EventListener):
    def __init__(self):
        self.last_event: ModuleExecutedEvent | None = None
        self.event_type = ModuleExecutedEvent

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def _update(self, event: Event) -> None:
        self.last_event = event

class DummyPauseListener(EventListener):
    def __init__(self,pipeline,cancel= False):
        self.last_event: PipelinePauseEvent | None = None
        self.event_type = PipelinePauseEvent
        self.count = 0
        self.pipeline = pipeline
        self.cancel = cancel

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def _update(self, event: Event) -> None:
        self.count += 1
        assert event.module_id.startswith("testPause"), "Something went wrong when pausing the pipeline"
        self.last_event = event
        if event.resume == False and not self.cancel:
            self.pipeline.resume()
        elif event.resume == False and self.cancel:
            self.pipeline.cancel()



def test_notify_and_pipeline_state_listener():
    manager = EventManager()
    listener = DummyListener()

    manager.subscribe(listener=listener)
    event = ProgressEvent(0,"test")
    assert manager._listeners[type(event)] == [listener]

    manager.notify(event)
    assert listener.last_event.percent == 0, "Something went wrong when notifying the listener"
    assert listener.last_event.process == "test", "Something went wrong when notifying the listener"
    assert str(listener.last_event) == "ProgressEvent: 0% - test"

    manager.unsubscribe(listener=listener)
    assert len(manager._listeners) == 0, "Something went wrong when unsubscribed"

    listener.last_event = None
    manager.notify(event)
    assert listener.last_event is None, "Listener was notified after unsubscribe"


def test_module_listener():
    manager = EventManager()
    listener = DummyModuleListener()
    listener2 = DummyModuleListener()

    manager.subscribe(listener=listener)
    manager.subscribe(listener=listener2)
    event = ModuleExecutedEvent("test")
    assert manager._listeners[type(event)] == [listener,listener2]
    manager.notify(event)
    assert listener.last_event is not None, "Listener was not notified"
    assert listener2.last_event is not None, "Listener was not notified"
    assert listener.last_event.module_id == "test", "Something went wrong when notifying the listener"
    assert listener2.last_event.module_id == "test", "Something went wrong when notifying the listener"
    manager.unsubscribe(listener=listener)
    assert manager._listeners[type(event)] == [listener2]

def test_event_listener_update_wrong_type():
    listener = DummyListener()
    with pytest.raises(TypeError):
        listener.update(DummyEvent())

def test_unsubscribe_never_subscribed():
    manager = EventManager()
    listener = DummyListener()
    with pytest.raises(ValueError):
        manager.unsubscribe(listener=listener)

def test_pipe_error_listener():
    manager = EventManager()
    error_listener = DummyErrorListener()
    manager.subscribe(listener=error_listener)
    pipeline = PipelineManager()
    pipeline.add_module(DummyErrorModule)
    pipeline.event_manager = manager
    pipeline.run()
    assert error_listener.last_event is not None, "Listener was not notified"
    assert error_listener.last_event.error_name == "test", "Something went wrong when notifying the listener"
    assert error_listener.last_event.error_msg == "test", "Something went wrong when notifying the listener"
    assert str(error_listener.last_event) == "Error_name: test Error_msg: test"

def test_drag_and_drop_event():
    manager = EventManager()
    drag_drop_listener = DummyDragDropListener()
    manager.subscribe(listener=drag_drop_listener)
    manager.notify(DragAndDropEvent(True))
    assert drag_drop_listener.last_event.drag is True, "Something went wrong when notifying the drag and drop listener"

def test_pipeline_states_event():
    manager = EventManager()
    pipeline_state_listener = DummyPipelineStateListener()
    manager.subscribe(listener=pipeline_state_listener)

    state_event = PipelineStateChangeEvent(PipelineStates.IDLE)
    manager.notify(state_event)
    assert pipeline_state_listener.last_event.pipeline_state is PipelineStates.IDLE, "Something went wrong when notifying the listener"
    state_event = PipelineStateChangeEvent(PipelineStates.RUNNING)
    manager.notify(state_event)
    assert pipeline_state_listener.last_event.pipeline_state is PipelineStates.RUNNING, "Something went wrong when notifying the listener"

