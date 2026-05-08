from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Type, TypeVar, Generic

class Event(ABC):
    """
    Abstract base class for all event types.
    Subclass this to define specific event types.
    """
    pass

class ProgressEvent(Event):
    def __init__(self,percent: int,process: str):
        self.percent = percent
        self.process = process

    def __str__(self):
        return f"ProgressEvent: {self.percent}% - {self.process}"

class OnPipelineChangeEvent(Event):
    def __init__(self,change_type: str):
        self.change_type = change_type

class ModuleExecutedEvent(Event):
    def __init__(self,module_id: str):
        self.module_id = module_id

class ModuleStartedEvent(Event):
    def __init__(self,module_id: str):
        self.module_id = module_id

class ErrorEvent(Event):
    def __init__(self,error_name: str, error_msg: str):
        self.error_name = error_name
        self.error_msg = error_msg

    def __str__(self):
        return f"Error_name: {self.error_name} Error_msg: {self.error_msg}"

class PipelineStates(Enum):
    IDLE = 0
    RUNNING = 1

class PipelineStateChangeEvent(Event):
    def __init__(self,pipeline_state: PipelineStates):
        self.pipeline_state = pipeline_state

class DragAndDropEvent(Event):
    def __init__(self,drag:bool):
        self.drag = drag #False if it is no longer dragging or not valid dragging

class PipelinePauseEvent(Event):
    def __init__(self,module_id: str,resume: bool= False):
        self.module_id = module_id
        self.resume = resume

class PipelineCancelEvent(Event):
    def __init__(self,module_id: str):
        self.module_id = module_id

class PipelineErrorEvent(Event):
    def __init__(self,error_name: str,error_msg:str):
        self.error_name = error_name
        self.error_msg = error_msg

class EventListener(ABC):
    """
    Abstract base class for event listeners.
    Subclasses must define the type of event they handle and implement the update logic.
    """
    @abstractmethod
    def get_event_type(self) -> Type[Event]: #pragma: no cover
        pass

    def update(self, event: Event) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self._update(event)

    @abstractmethod
    def _update(self, event: Event) -> None: #pragma: no cover
        pass
