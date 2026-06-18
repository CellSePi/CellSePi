from collections import deque
from typing import List, Union, Tuple

from backend.constants import SUCCESS_COLOR
from backend.expert_mode.listener import OnPipelineChangeEvent
from backend.expert_mode.pipe import Pipe
from backend.expert_mode.pipeline_manager import PipelineManager
from frontend.expert_mode.gui_lines import LinesGUI
from frontend.expert_mode.gui_module import ModuleGUI
from frontend.expert_mode.expert_constants import *

class PipelineGUI(ft.Stack):
    def __init__(self,page:ft.Page):
        super().__init__()
        self.controls = []
        self.pipeline = PipelineManager()
        self.module_count = 0 #without show_room modules
        self.loading = False
        self.interactive_view = None
        self.pipeline_name = "NewPipeline"
        self.pipeline_directory = ""
        self.pipeline_dict = {} #last saved pipeline dict
        self._page = page
        self.modules = {} #without show_room modules, identifier is the module_id
        self.show_room_size = len(MODULE_REGISTRY) if len(MODULE_REGISTRY) < SHOWROOM_MODULE_COUNT else SHOWROOM_MODULE_COUNT
        self.show_room_modules = [] #saves all modules within the show_room
        self.source_module: str = ""
        self.show_ports:bool = False
        self.show_delete_button:bool = False
        self.transmitting_ports: List[Union[str,Tuple[str,str]]] = []
        self.lines_gui = LinesGUI(self)
        self.controls.append(self.lines_gui)
        self.show_room_container = None
        self.show_room_page_number: int = 0
        self.show_room_max_page_number: int = 0
        self.page_stack = None
        self.delete_stack = ft.Stack()
        self.controls.append(self.delete_stack)
        self.expand = True

    async def reset(self):
        """
        Resets the PipelineGUI, so a other pipeline can be loaded into.
        """
        self.loading = True
        for module in list(self.modules.values()):
           await module.remove_module()
        self.pipeline.run_order = deque()
        self.pipeline.executing = ""
        self.pipeline.running = False
        self.update()
        self.loading = False

    async def load_pipeline(self):
        """
        Loads a pipeline from a dict to PipelineGUI.
        """
        self.loading = True
        for module_dict in self.pipeline_dict["modules"]:
            type_map = {mod_class.gui_config().name: mod_class for mod_class in MODULE_REGISTRY.values()}
            if module_dict["module_name"] not in type_map:
                self.loading = False
                self.pipeline.event_manager.notify(OnPipelineChangeEvent(f"Pipeline {self.pipeline_name} loaded."))
                raise ValueError(f"Module ’{module_dict['module_name']}’ not supported!")
            self.add_module(module_type=type_map[module_dict["module_name"]], x=module_dict["position"]["x"], y=module_dict["position"]["y"], module_id=module_dict["module_id"],module_dict=module_dict)

        for pipe in self.pipeline_dict["pipes"]:
            source = pipe["source"]
            target = pipe["target"]
            ports = [tuple(p) if isinstance(p, list) else p for p in pipe["ports"]]
            await self.add_connection(self.modules[source],self.modules[target],ports)

        offset_x = self.pipeline_dict["view"]["offset_x"]
        offset_y = self.pipeline_dict["view"]["offset_y"]
        scale = self.pipeline_dict["view"]["scale"]
        await self.interactive_view.set_transformation_data(offset_x=offset_x, offset_y=offset_y, scale=scale)

        self.page.show_dialog(
            ft.SnackBar(ft.Text(f"Pipeline successfully loaded.", color=ft.Colors.WHITE), bgcolor=SUCCESS_COLOR))
        self.page.update()
        self.loading = False
        self.pipeline.event_manager.notify(OnPipelineChangeEvent(f"Pipeline {self.pipeline_name} loaded."))

    async def check_all_deletable(self):
        """
        Checks for all modules if their delete_button can be maked visible.
        This is the case if the pipeline is no longer executing or all direct connection of a module are executed.
        """
        for module in self.modules.values():
            if self.check_deletable(module):
                module.delete_button.visible = True
                module.delete_button.update()
            else:
                module.delete_button.visible = False
                module.delete_button.update()

    def check_deletable(self,module:ModuleGUI):
        """
        Checks if the pipeline is no longer executing or all direct connection of the given module are executed.
        """
        if  module.module_id in self.pipeline.run_order or module.module_id == self.pipeline.executing:
            return False

        return all(not(pipe.target_module.module_id in self.pipeline.run_order or pipe.target_module.module_id == self.pipeline.executing) for pipe in self.pipeline.pipes_out[module.module_id])

    async def add_connection(self,source_module_gui,target_module_gui,ports: List[Union[str,Tuple[str,str]]]):
        """
        Adds a connection to the pipeline.
        """
        ports_copy = list(ports)
        self.pipeline.add_connection(pipe=Pipe(source_module_gui.module, target_module_gui.module, ports_copy))
        await self.lines_gui.update_line(source_module_gui, target_module_gui,ports)
        await self.lines_gui.update_gui()
        await self.update_all_port_icons()

    async def expand_connection(self,pipe:Pipe,ports:List[Union[str, Tuple[str, str]]]):
        """
        Expands a connection, so its connection also tranferes the given ports.
        """
        ports_copy = list(ports)
        self.pipeline.expand_connection(pipe,ports_copy)
        await self.lines_gui.update_line(self.modules[pipe.source_module.module_id], self.modules[pipe.target_module.module_id], pipe.ports)
        await self.lines_gui.update_gui()
        await self.update_all_port_icons()

    async def remove_connection(self,source_module_id,target_module_id):
        """
        Removes a connection from the pipeline.
        """
        print("hey!")
        self.pipeline.remove_connection(source_module_id,target_module_id)
        await self.lines_gui.remove_line(self.modules[source_module_id], self.modules[target_module_id])
        await self.update_all_port_icons()
        await self.check_for_valid_all_modules()


    async def refill_show_room(self,module_gui:ModuleGUI,visible:bool=True,index:int=None,show_room_id:int=None):
        """
        To refill the show room after a module has been added to the pipeline.

        Attributes:
            module_gui (ModuleGUI): The module GUI that is being added to the pipeline.
            visible (bool): Whether the module is visible or not.
            index (int): To add it at the same position as the old module was placed in the show_room_modules list(import for change the pages).
            show_room_id (int): So the refilled module has the same id as the one added to the pipeline.
        """
        new_module_gui = ModuleGUI(self, module_gui.module_type, x=SPACING_X + SHOWROOM_PADDING_X / 2, y=module_gui.show_offset_y, show_mode=True, visible=visible, index=index,id_number=show_room_id)
        self.page_stack.controls.insert(3,new_module_gui)
        self.page_stack.update()
        await self.update_all_port_icons()

    def build_show_room(self,page_stack:ft.Stack):
        """
        Builds the show room for the PipelineBuildingTool(ExpertMode).
        It is placed at the top left corner to add modules to the pipeline.
        """
        def _add_show_room_module(module_type: type, x: float, y: float, visible: bool = True, show_room_id: int = None):
            module_gui = ModuleGUI(self, module_type, x, y, True, visible, id_number=show_room_id)
            if visible:
                self.page_stack.controls.insert(2, module_gui)
            return module_gui

        self.page_stack = page_stack
        x = SPACING_X + SHOWROOM_PADDING_X / 2
        y = SPACING_Y
        self.show_room_container = ft.Container(top=y - SPACING_Y / 2, left=SPACING_X, width=MODULE_WIDTH + SHOWROOM_PADDING_X, height=(self.show_room_size * MODULE_HEIGHT) + (self.show_room_size * SPACING_Y), bgcolor=MENU_COLOR, border_radius=ft.BorderRadius.all(10),blur=10)
        self.page_stack.controls.insert(1,self.show_room_container)
        self.show_room_max_page_number = math.ceil(len(MODULE_REGISTRY) / SHOWROOM_MODULE_COUNT)
        for i,module_type in enumerate(MODULE_REGISTRY.values()):
            visible = i < SHOWROOM_MODULE_COUNT
            y_module = y+ (MODULE_HEIGHT + SPACING_Y) * (i%SHOWROOM_MODULE_COUNT)
            _add_show_room_module(module_type,x,y_module,visible,-1)
            _add_show_room_module(module_type,x,y_module,visible,-2)

    async def change_show_room_page(self,page_number:int):
        """
        Changes the page of the show_room to the given page number.
        """
        self.show_room_page_number = page_number
        for i,module in enumerate(self.show_room_modules):
            module_page = (i//2) // SHOWROOM_MODULE_COUNT
            if module_page == self.show_room_page_number:
                module.visible = True
                if module not in self.page_stack.controls:
                    self.page_stack.controls.insert(3, module)
            else:
                module.visible = False
                if module in self.page_stack.controls:
                    self.page_stack.controls.remove(module)

        self.page_stack.update()

    def add_module(self,module_type: type,x: float = None,y: float = None,module_id: str = None,module_dict:dict=None):
        """
        Adds a module to the PipelineGUI.
        """
        id_number = int(module_id.removeprefix(f"{module_type.gui_config().name}_")) if module_id is not None else None
        module_gui = ModuleGUI(self,module_type,x,y,id_number=id_number,module_dict=module_dict)
        self.controls.append(module_gui)
        self.update()
        return module_gui

    def set_in_background(self, module_gui:ModuleGUI,behind_delete=False):
        """
        Move a Module from it current position in the stack to the deepest intended level.
        Attribute:
            behind_delete: if the module should be render behind the delete buttons.
        """
        if module_gui in self.controls:
            self.controls.remove(module_gui)
            if behind_delete:
                self.controls.insert(1, module_gui)
            else:
                self.controls.remove(self.delete_stack)
                self.controls.insert(1, self.delete_stack)
                self.controls.insert(2, module_gui)
            self.update()

    async def remove_module(self,module_id: str):
        """
        Removes a module from the pipeline.
        """
        gui_module = self.modules.pop(module_id)
        self.controls.remove(gui_module)
        self.pipeline.remove_module(gui_module.module)
        del gui_module
        self.update()

    async def toggle_all_module_detection(self,module_id: str):
        """
        Toggles whether all modules can only be moved and are ready to be clicked to connect connections or
        are in the 'normal' mode where any tool is available.
        """
        self.source_module = module_id
        self.transmitting_ports = []
        for module in self.modules.values():
            if module.module_id != module_id:
                await module.toggle_detection()
                self.update()

    async def enables_all_stuck_in_running(self):
        """
        Disables the waiting/execution mode for all modules when some event happens that the pipeline terminated early.
        """
        for module in self.modules.values():
            await self.lines_gui.update_delete_buttons(module)
            module.enable_tools()
            module.delete_button.visible = True
            module.delete_button.update()
            module.executing_button.visible = False
            module.executing_button.update()
            module.waiting_button.visible = False
            module.waiting_button.update()
        await self.check_for_valid_all_modules()

    async def check_for_valid_all_modules(self):
        """
        Checks all modules if its valid to build a connection to the currently selected source module.
        """
        for target_module_gui in self.modules.values():
            await self.check_for_valid(target_module_gui.module_id)

    async def check_for_valid(self,module_id: str):
        """
        Checks for a module associated with the given module_id if its valid to build a connection to the currently selected source module.
        """
        target_module_gui = self.modules[module_id]
        if (target_module_gui.module_id not in self.pipeline.run_order and target_module_gui.module_id != self.pipeline.executing) or not self.pipeline.running:
            if target_module_gui.module_id != self.source_module:
                valid = True
                existing_pipe = self.pipeline.check_connections(
                    self.source_module, target_module_gui.module_id) if self.source_module != "" else None
                if existing_pipe is None:
                    valid = True
                elif any(port in existing_pipe.port_names for port in self.transmitting_ports) or existing_pipe.source_module.module_id != self.source_module or existing_pipe.target_module.module_id != target_module_gui.module_id:
                    valid = False
                if all(k in target_module_gui.module.inputs for k in
                       self.transmitting_ports) and self.transmitting_ports != [] and valid and not (
                self.pipeline.check_ports_occupied(target_module_gui.module_id, self.transmitting_ports)):
                    await target_module_gui.set_valid()
                else:
                    await target_module_gui.set_invalid()

    async def update_all_port_icons(self):
        """
        Updates for all modules the port icons.
        """
        for module_gui in self.modules.values():
            await module_gui.update_port_icons()
