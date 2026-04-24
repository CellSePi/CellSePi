import math
import threading

from collections import deque
from itertools import chain

from cellsepi.backend.main_window.expert_mode.event_manager import EventManager
from cellsepi.backend.main_window.expert_mode.listener import ErrorEvent, OnPipelineChangeEvent, ModuleExecutedEvent, \
    ModuleStartedEvent, PipelinePauseEvent, PipelineCancelEvent, PipelineErrorEvent, PipelineStateChangeEvent, \
    PipelineStates
from cellsepi.backend.main_window.expert_mode.module import Module,Port
from cellsepi.backend.main_window.expert_mode.pipe import Pipe
from typing import List, Dict, Type


class PipelineManager:
    def __init__(self):
        self.modules: List[Module] = [] #running order
        self.module_map: Dict[str, Module] = {} #mapping for fast access to the modules
        self.pipes_in: Dict[str,List[Pipe]] = {} #dict[target,[Pipe]]
        self.pipes_out: Dict[str,List[Pipe]] = {} #dict[source,[Pipe]]
        self.run_order: deque[str] = deque()
        self.modules_executed = 0
        self.executing: str = ""
        self.running: bool = False
        self._continue_event = threading.Event()
        self._cancel_event = threading.Event()
        self.event_manager: EventManager = EventManager()

    def add_module(self, module_class: Type[Module]) -> Module:
        """
        Creates a module of the given class and adds it to the pipeline.
        """
        module = module_class()
        return self._add_module(module,module_class)

    def add_module_with_id(self, module_class: Type[Module],module_id: str) -> Module:
        """
        Creates a module of the given class with the given module_id and adds it to the pipeline.
        """
        if not module_id.startswith(module_class.gui_config().name):
            raise ValueError(f"Invalid module id '{module_id}' for the module_class '{module_class.gui_config().name}'")
        module = module_class(module_id=module_id)
        module.occupy()
        return self._add_module(module,module_class)

    def _add_module(self, module: Module,module_class: Type[Module]) -> Module:
        self.modules.append(module)
        self.module_map[module.module_id] = module
        module.event_manager = self.event_manager
        self.pipes_in[module.module_id] = []
        self.pipes_out[module.module_id] = []
        self.event_manager.notify(OnPipelineChangeEvent(f"Added module {module_class.gui_config().name}"))
        return module

    def get_new_module_id(self, module_id_old: str):
        """
        Gets a new module id for the module with the given module_id_old.
        """
        if not module_id_old in self.module_map:
            raise ValueError(f"Module id '{module_id_old}' doesen't exists")
        self.module_map[module_id_old].free_id_number(self.module_map[module_id_old].get_id_number())
        module_id_new = self.module_map[module_id_old].get_new_id()
        self.module_map[module_id_old].module_id = module_id_new
        self.module_map[module_id_new] = self.module_map[module_id_old]
        del self.module_map[module_id_old]
        self.pipes_in[module_id_new] = self.pipes_in[module_id_old]
        del self.pipes_in[module_id_old]
        self.pipes_out[module_id_new] = self.pipes_out[module_id_old]
        del self.pipes_out[module_id_old]

    def remove_module(self, module: Module) -> None:
        """
        Removes a module from the pipeline.
        Raises:
            RuntimeError: If the module is still connected to other modules.
            ValueError: If the module is not part of the pipeline.
        """
        if module in self.modules:
            if not self.is_disconnected(module.module_id):
                raise RuntimeError(
                    f"Cannot remove module '{module.module_id}' from pipeline while connections to other modules still exists.")
            self.modules.remove(module)
            del self.module_map[module.module_id]
            del self.pipes_in[module.module_id]
            del self.pipes_out[module.module_id]
            module.destroy()
            self.event_manager.notify(OnPipelineChangeEvent(f"Removed module {module.gui_config().name}"))
        else:
            raise ValueError(f"Module '{module.module_id}' does not exist in the pipeline.")

    def is_disconnected(self, module_name: str) -> bool:
        """
        Checks if a module has no connected modules.
        """
        return len(self.pipes_in[module_name]) == 0 and len(self.pipes_out[module_name]) == 0

    def remove_connection(self,source_id: str, target_id: str) -> None:
        """
        Removes a pipe between the source and target modules.
        Raises:
            ValueError: If a pipe between the source and target modules does not exist.
        """
        pipe = self.get_pipe(source_id, target_id)
        if pipe is None:
            raise ValueError(f"Pipe between source module '{source_id}' and target module '{target_id}' does not exist.")

        for port in pipe.ports:
            pipe.target_module.inputs[port].data = None

        self.pipes_in[target_id].remove(pipe)
        self.pipes_out[source_id].remove(pipe)
        self.event_manager.notify(OnPipelineChangeEvent(f"Removed connection between {target_id} and {source_id}"))

    def get_pipe(self, source_name: str, target_name: str) -> Pipe | None:
        """
        Returns the pipe between source module and target module or if it does not exist it returns None.
        """
        for pipe in self.pipes_in.get(target_name, []):
            if pipe.source_module.module_id == source_name:
                return pipe
        return None

    def add_connection(self, pipe: Pipe) -> None:
        """
        Adds a pipe to the pipeline.
        Raises:
            ModuleNotFoundError: if the target or source module is not already added in the pipeline.
            ValueError: If a pipe between the target and source module exists already in the pipeline.
        """
        if pipe.source_module not in self.modules:
            raise ModuleNotFoundError(f"Source module '{pipe.source_module.module_id}' not found in the pipeline.")
        if pipe.target_module not in self.modules:
            raise ModuleNotFoundError(f"Target module '{pipe.target_module.module_id}' not found in the pipeline.")

        if self.check_connections(pipe.source_module.module_id, pipe.target_module.module_id) is not None:
                raise ValueError(f"Pipe between source module '{pipe.source_module.module_id}' and target module '{pipe.target_module.module_id}' already exists.")

        self.pipes_in[pipe.target_module.module_id].append(pipe)
        self.pipes_out[pipe.source_module.module_id].append(pipe)

        self.event_manager.notify(OnPipelineChangeEvent(f"Added connection between {pipe.target_module.module_id} and {pipe.source_module.module_id}"))

    def expand_connection(self,pipe:Pipe, ports: List[str]) -> None:
        """
        Expands the ports tranfered with the pipe between the source and target modules with the given ports.
        """
        pipe.ports.extend(ports)
        self.event_manager.notify(OnPipelineChangeEvent(
            f"Expanded the connection between {pipe.target_module.module_id} and {pipe.source_module.module_id}"))

    def check_connections(self,source_module_id:str,target_module_id:str) -> Pipe | None:
        """
        Checks if a pipe between the source and target modules exist in the pipeline.
        """
        for existing_pipe in self.pipes_in[target_module_id]:
            if existing_pipe.source_module.module_id == source_module_id:
                return existing_pipe
        return None

    def check_ports_occupied(self,module_id: str,ports:List[str]) -> bool:
        """
        Checks if the given module ports are occupied by existing pipes.
        """
        for port in ports:
            for pipe in self.pipes_in[module_id]:
                if port in pipe.ports:
                    return True
        return False

    def setup_incoming_degree(self) -> Dict[str, int]:
        """
        Returns a dictionary mapping module names to incoming degree (incoming degree is how many pipes are going into a module).
        """
        result = {}
        for module in self.modules:
            result[module.module_id] = len(self.pipes_in[module.module_id])
        return result

    def get_run_order(self) -> deque[str]:
        """
        Get the topologic orders with Kahn's algorithm.
        For this, the algorithm uses the graph given by the pipes of the pipeline.
        """
        topological_order: deque[str] = deque()
        in_degree = self.setup_incoming_degree()
        queue = deque()
        for module_name, degree in in_degree.items():
            if degree == 0:
                queue.append(module_name)
        while queue:
            module_name = queue.popleft()
            topological_order.append(module_name)
            del in_degree[module_name]
            for pipe in self.pipes_out[module_name]:
                in_degree[pipe.target_module.module_id] -= 1
                if in_degree[pipe.target_module.module_id] == 0:
                    queue.append(pipe.target_module.module_id)
        if len(topological_order) != len(self.modules):
            raise RuntimeError(f"The pipeline contains a cycle, only acyclic graphs are supported.")
        return topological_order

    def check_pipeline_runnable(self,ignore:List[str]=None) -> bool:
        """
        Checks if every module input is satisfied.
        """
        for module in self.modules:
            if module.module_id in ignore:
                continue
            if not self.check_module_satisfied(module.module_id):
                return False
        return True

    def check_module_satisfied(self,module_id: str) -> bool:
        """
        Checks if a modules inputs are satisfied.
        """
        module_pipes = self.pipes_in[module_id]
        delivered_ports = set(chain.from_iterable(pipe.ports for pipe in module_pipes))
        if not all(port_name in delivered_ports for port_name in self.module_map[module_id].get_mandatory_inputs()):
            return False
        else:
            return True

    def check_module_runnable(self,module_name: str) -> bool:
        """
        Checks if the module input port data from the given module_name is not None.
        """
        if not all(self.module_map[module_name].inputs[port_name].data is not None for port_name in self.module_map[module_name].get_mandatory_inputs()):
            return False
        else:
            return True

    def run(self,ignore_modules: List[str] = None) -> None:
        """
        Executes the steps of the pipeline.
        Skips steps of the pipeline if min. one of the mandatory inputs is None.

        Arguments:
            ignore_modules: List of modules to ignore.
        """
        self.modules_executed = 0
        self._continue_event.clear()
        try:
            self.run_order = self.get_run_order()
        except RuntimeError as e:
            self.event_manager.notify(PipelineErrorEvent("Cycle in pipeline",e.args[0]))
            return
        while self.run_order:
            self.running = True
            self.event_manager.notify(PipelineStateChangeEvent(PipelineStates.RUNNING))
            module_name = self.run_order.popleft()
            if ignore_modules is not None and module_name in ignore_modules:
                continue
            module = self.module_map[module_name]
            module_pipes = self.pipes_in[module.module_id]
            for pipe in module_pipes:
                pipe.run()
            if self.check_module_runnable(module_name):
                try:
                    self.executing = module_name
                    self.event_manager.notify(ModuleStartedEvent(module_name))
                    pause = module.run() #if the run of a module returns True, the module wants to stop the pipeline.
                    if pause and not self._cancel_event.is_set():
                        self.event_manager.notify(PipelinePauseEvent(module_name))
                        self._continue_event.wait()
                        self.event_manager.notify(PipelinePauseEvent(module_name,True))
                        self._continue_event.clear()
                    module.finished()
                    self.executing = ""
                    self.modules_executed += 1
                    self.event_manager.notify(ModuleExecutedEvent(module_name))
                    if self._cancel_event.is_set():
                        self.running = False
                        self.event_manager.notify(PipelineStateChangeEvent(PipelineStates.IDLE))
                        self.event_manager.notify(PipelineCancelEvent(self.executing))
                        self._cancel_event.clear()
                        return

                except PipelineRunningException as e:
                    self.running = False
                    self.event_manager.notify(PipelineStateChangeEvent(PipelineStates.IDLE))
                    self.event_manager.notify(ErrorEvent(e.error_type,e.description))
                    self.executing = ""
                    self._cancel_event.clear()
                    return
            else:
                self.modules_executed += 1
                self.event_manager.notify(ModuleExecutedEvent(module_name))
                continue
        self.running = False
        self.event_manager.notify(PipelineStateChangeEvent(PipelineStates.IDLE))

    def resume(self):
        """
        Resumes the pipeline after the execution of the pipeline got paused.
        """
        self._continue_event.set()

    def cancel(self):
        """
        Cancels the pipeline after the currently executed module is finished.
        """
        self._cancel_event.set()
        self._continue_event.set()

class PipelineRunningException(Exception):
    """
    Exception raised if a module in the pipeline has an error and the pipeline needs to stop.
    """
    def __init__(self, error_type: str, description: str):
        self.error_type = error_type
        self.description = description
        super().__init__(f"{error_type}: {description}")