import asyncio
import textwrap
from typing import List, Any, Dict, cast

from cellsepi.backend.main_window.expert_mode.listener import DragAndDropEvent, OnPipelineChangeEvent
from cellsepi.backend.main_window.expert_mode.module import FilePath, DirectoryPath
from cellsepi.frontend.main_window.expert_mode.expert_constants import *
from cellsepi.frontend.main_window.gui_directory import format_directory_path
from cellsepi.frontend.main_window.gui_page_overlay import PageOverlay


class ModuleGUI(ft.GestureDetector):
    """
    Manages the GUI parts of the module.
    """
    def __init__(self, pipeline_gui,module_type: ModuleType,x: float = None,y: float = None,show_mode:bool=False,visible=True,index:int=None,id_number:int=None,module_dict:dict=None):
        super().__init__()
        self.pipeline_gui = pipeline_gui
        self.detection: bool = True
        self.module_type = module_type
        self.mouse_cursor = ft.MouseCursor.MOVE
        self.show_mode = show_mode
        self.drag_interval = 5
        self.visible = visible
        self.on_pan_start = self.start_drag
        self.on_pan_update = self.drag
        self.on_pan_end = self.drop
        self.show_offset_y = y
        self.left = ft.BUILDER_WIDTH/2 if x is None else x
        self.top = ft.BUILDER_HEIGHT/2 if y is None else y
        self.old_left = None
        self.old_top = None
        self.port_selection = False
        self.module = self.pipeline_gui.pipeline.add_module(module_type.value) if id_number is None else self.pipeline_gui.pipeline.add_module_with_id(module_type.value,module_type.value.gui_config().name + str(id_number))
        if module_dict is not None:
            self.update_user_attr(module_dict)
        if self.module.settings is None and hasattr(self.module, "_settings"):
            self.module._settings = self.generate_options_overlay()
        if show_mode:
            if index is None:
                self.pipeline_gui.show_room_modules.append(self)
            else:
                self.pipeline_gui.show_room_modules.insert(index,self)
        else:
            self.pipeline_gui.modules[self.module.module_id] = self
            self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent(f"Added {self.module_id} to pipeline_gui.modules."))
        self.color = self.module.gui_config().category.value
        self.valid = False
        self.wrapped_description = "\n".join(textwrap.wrap(self.module.gui_config().description, width=40))
        self.click_container = ft.Container(on_click=self.add_connection,tooltip=self.wrapped_description if self.show_mode else None, height=MODULE_HEIGHT, width=MODULE_WIDTH,
                                            visible=False if not show_mode else True,bgcolor=INVALID_COLOR if not show_mode else ft.Colors.TRANSPARENT,disabled=True if not show_mode else False,border_radius=ft.border_radius.all(10), ignore_interactions=True if not show_mode else False)
        self.click_gesture = ft.GestureDetector(visible=False if not show_mode else True,disabled=True if not show_mode else False,content=self.click_container,on_enter=self.on_enter_click_module,on_exit=self.on_exit_click_module)

        self.connect_button = ft.IconButton(icon=ft.Icons.SHARE, icon_color=ft.Colors.WHITE60,
                                            style=ft.ButtonStyle(
                                                          shape=ft.RoundedRectangleBorder(radius=12),
                                                      ), on_click=self.connect_clicked,
                                            tooltip="Add connection", hover_color=ft.Colors.WHITE12, visible=self.module.outputs!={})

        self.options_button = ft.IconButton(icon=ft.Icons.TUNE, icon_color=ft.Colors.WHITE60,
                                            style=ft.ButtonStyle(
                                                          shape=ft.RoundedRectangleBorder(radius=12),
                                                      ), on_click=lambda e: self.open_options(e),
                                            tooltip="Options", hover_color=ft.Colors.WHITE12, visible=True if self.module.settings is not None else False,)
        self.copy_button = ft.IconButton(icon=ft.Icons.CONTENT_COPY, icon_color=ft.Colors.WHITE60,
                                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                                            on_click=self.copy_module,
                                            tooltip="Copy module", hover_color=ft.Colors.WHITE12,)
        self.test_button = ft.IconButton(icon=ft.Icons.FORMAT_QUOTE_SHARP, on_hover= lambda e: print("test button clicked"))

        self.paused_button = ft.Stack([ft.Container(bgcolor=ft.Colors.BLACK26, width=30, height=30, top=5, right=5, border_radius=ft.border_radius.all(45)), ft.IconButton(icon=ft.Icons.PLAY_ARROW, icon_color=ft.Colors.WHITE, disabled=True,
                                                                                                                                                                           style=ft.ButtonStyle(
                                              shape=ft.RoundedRectangleBorder(radius=12),
                                          ), on_click=self.copy_module,
                                                                                                                                                                           tooltip="Currently paused to continue\npress the resume button", hover_color=ft.Colors.WHITE12)], top=1,
                                      left=MODULE_WIDTH - 42, visible=False, width=40, height=40)
        self.executing_button = ft.Stack([ft.Container(bgcolor=ft.Colors.BLACK26, width=30, height=30, top=5, right=5, border_radius=ft.border_radius.all(45)), ft.IconButton(icon=ft.Icons.PAUSE_ROUNDED, icon_color=ft.Colors.WHITE, disabled=True,
                                                                                                                                                                              style=ft.ButtonStyle(
                                              shape=ft.RoundedRectangleBorder(radius=12),
                                          ), on_click=self.copy_module,
                                                                                                                                                                              tooltip="Currently executed", hover_color=ft.Colors.WHITE12)], top=1,
                                         left=MODULE_WIDTH - 42, visible=False, width=40, height=40)
        self.waiting_button = ft.Stack([ft.Container(bgcolor=ft.Colors.BLACK26,width=30,height=30,top=5,right=5,border_radius=ft.border_radius.all(45)),ft.IconButton(icon=ft.Icons.HOURGLASS_EMPTY_ROUNDED, icon_color=ft.Colors.WHITE,disabled=True,
                                          style=ft.ButtonStyle(
                                              shape=ft.RoundedRectangleBorder(radius=12),
                                          ), on_click=self.copy_module,
                                          tooltip="Waiting for execution", hover_color=ft.Colors.WHITE12)],top=1,
                                          left=MODULE_WIDTH - 42,visible=False,width=40,height=40)
        self.show_ports = False
        self.ports_in_out_button = ft.IconButton(icon=ft.Icons.SYNC_ALT_ROUNDED, icon_color=ft.Colors.WHITE60,
                                                 style=ft.ButtonStyle(
                                              shape=ft.RoundedRectangleBorder(radius=12),
                                          ), on_click=self.ports_in_out_clicked,
                                                 tooltip="View ports", hover_color=ft.Colors.WHITE12,)

        self.tools = ft.Container(ft.Row(
                                            [
                                                self.connect_button,self.options_button,self.ports_in_out_button,self.copy_button,
                                            ],tight=True,spacing=7
                                        ),bgcolor=ft.Colors.BLACK12,expand=True,width=MODULE_WIDTH
                                        )

        self.delete_button = ft.IconButton(ft.Icons.CLOSE,visible=True if not show_mode else False,icon_color=ft.Colors.WHITE,hover_color=ft.Colors.WHITE12,tooltip="Delete Module",on_click=self.remove_module)
        self.port_chips = self.get_ports_row()
        self.connection_ports = ft.Container(
            self.port_chips,visible=False
        )

        control_list_ports = []
        self.in_ports_Icons = {}
        self.in_ports_Icons_occupied = {}
        for port in self.module.inputs.values():
            if not port.opt:
                self.in_ports_Icons[port.name] = ft.Stack([ft.Container(bgcolor=ft.Colors.WHITE,width=10,height=20,bottom=10,right=15,border_radius=ft.border_radius.all(45)),ft.Container(ft.IconButton(ft.Icons.WARNING_ROUNDED,icon_size=35,disabled=True,hover_color=ft.Colors.TRANSPARENT,icon_color=ft.Colors.RED,tooltip=f"Port '{port.name}' is mandatory and has no incoming pipe!"),bottom=-3,right=-5)],alignment=ft.Alignment.CENTER,visible=not self.pipeline_gui.pipeline.check_ports_occupied(self.module_id,[port.name]),width=40,height=40)
                self.in_ports_Icons_occupied[port.name] = ft.Stack([ft.Container(bgcolor=ft.Colors.GREEN,width=30,height=30,border_radius=ft.border_radius.all(45)),ft.IconButton(ft.Icons.CHECK,disabled=True,hover_color=ft.Colors.TRANSPARENT,icon_color=ft.Colors.WHITE,tooltip=f"Port '{port.name}' is mandatory and is satisfied.")],alignment=ft.Alignment.CENTER,visible= self.pipeline_gui.pipeline.check_ports_occupied(self.module_id,[port.name]),width=40,height=40)
            else:
                self.in_ports_Icons[port.name] = ft.Stack([ft.Container(bgcolor=ft.Colors.WHITE,width=10,height=20,bottom=10,right=15,border_radius=ft.border_radius.all(45)),ft.Container(ft.IconButton(ft.Icons.WARNING_ROUNDED,icon_size=35,disabled=True,hover_color=ft.Colors.TRANSPARENT,icon_color=ft.Colors.RED,tooltip=f"Port '{port.name}' is optional and has no incoming pipe!"),bottom=-3,right=-5)],alignment=ft.Alignment.CENTER,visible=not self.pipeline_gui.pipeline.check_ports_occupied(self.module_id,[port.name]),opacity=0.2,width=40,height=40)
                self.in_ports_Icons_occupied[port.name] = ft.Stack([ft.Container(bgcolor=ft.Colors.GREEN,width=30,height=30,border_radius=ft.border_radius.all(45)),ft.IconButton(ft.Icons.CHECK,disabled=True,hover_color=ft.Colors.TRANSPARENT,icon_color=ft.Colors.WHITE,tooltip=f"Port '{port.name}' is optional and is satisfied.")],alignment=ft.Alignment.CENTER,opacity=0.2,visible= self.pipeline_gui.pipeline.check_ports_occupied(self.module_id,[port.name]),width=40,height=40)

        in_ports = ft.Column([ft.Row([ft.Text(port.name,width=MODULE_WIDTH/2,weight=ft.FontWeight.BOLD,color=ft.Colors.WHITE),self.in_ports_Icons[port.name],self.in_ports_Icons_occupied[port.name]]) for port in self.module.inputs.values()],spacing=0)
        out_ports = ft.Column([ft.Row([ft.Text(port.name,width=MODULE_WIDTH/2,weight=ft.FontWeight.BOLD,color=ft.Colors.WHITE)]) for port in self.module.outputs.values()])
        input_text=ft.Text("Inputs:",size=20,weight=ft.FontWeight.BOLD,color=ft.Colors.WHITE)
        output_text=ft.Text("Outputs:",size=20,weight=ft.FontWeight.BOLD,color=ft.Colors.WHITE)
        if self.module.inputs != {}:
            control_list_ports.append(input_text)
            control_list_ports.append(in_ports)
        if self.module.outputs != {}:
            control_list_ports.append(output_text)
            control_list_ports.append(out_ports)

        self.error_icon = ft.IconButton(ft.Icons.REPORT, icon_size=35, disabled=True,
                                                         hover_color=ft.Colors.TRANSPARENT, icon_color=ft.Colors.RED,
                                                         tooltip="An error occurred while executing!",
                                                         highlight_color=ft.Colors.TRANSPARENT,
                                                         padding=ft.padding.all(2))
        self.error_stack = ft.Stack([ft.Container(bgcolor=ft.Colors.WHITE, width=10, height=20, bottom=16, right=23,
                                                        border_radius=ft.border_radius.all(45)),
                                           self.error_icon],
                                          visible=False, width=48, height=48, top=1,
                                          left=MODULE_WIDTH - 75)

        self.warning_satisfied = ft.Stack([ft.Container(bgcolor=ft.Colors.WHITE,width=10,height=20,bottom=16,right=23,border_radius=ft.border_radius.all(45)),ft.IconButton(ft.Icons.WARNING_ROUNDED,icon_size=35,disabled=False,hover_color=ft.Colors.TRANSPARENT,icon_color=ft.Colors.RED,tooltip=f"Not all mandatory inputs are satisfied!",on_click=self.ports_in_out_clicked,highlight_color=ft.Colors.TRANSPARENT,padding=ft.padding.all(2))],visible=not self.pipeline_gui.pipeline.check_module_satisfied(self.module_id) and not show_mode,width=48,height=48,top=1,left=MODULE_WIDTH-75)
        self.name_text = ft.Text(value=self.module.gui_config().name if not DEBUG else self.module_id,
                                weight=ft.FontWeight.BOLD,
                                width=MODULE_WIDTH-80,
                                height=20,color=ft.Colors.BLACK,
                                overflow=ft.TextOverflow.ELLIPSIS)
        self.module_container = ft.Container(
                    content=ft.Column(
                                [
                                        ft.Container(ft.Row(
                                                [
                                                    self.name_text,
                                                ],height=20
                                              ),padding=ft.padding.only(left=5, top=5)),
                                            self.tools,
                                       ],
                                    tight=True)
                    ,bgcolor=self.color,width=MODULE_WIDTH
                    ,height=MODULE_HEIGHT,
                    border=ft.border.all(4, ft.Colors.RED if not self.pipeline_gui.pipeline.check_module_satisfied(self.module_id) and not show_mode else ft.Colors.BLACK12),
                    border_radius=ft.border_radius.all(10),
                )
        self.ports_column = ft.Column(controls=control_list_ports, scroll=ft.ScrollMode.HIDDEN)
        self.ports_container = ft.Container(
            content=self.ports_column, bgcolor=self.color,
            width=MODULE_WIDTH,
            border_radius=ft.border_radius.all(10), padding=10, top=cast(float, self.module_container.height)-15,
            border=ft.border.all(8, ft.Colors.BLACK12), height=0,opacity=0,
            animate_opacity=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
            animate=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
        )
        self.ignore_interactions_container = ft.Container(self.click_gesture, ignore_interactions=True if not show_mode else False)
        self.content = ft.Stack([
            self.ports_container,
            ft.Column([ft.Stack([
                self.module_container,
                ft.Container(content=self.delete_button, margin=ft.margin.only(top=-7, left=7),
                             alignment=ft.Alignment.TOP_RIGHT, width=MODULE_WIDTH, ),
                self.executing_button,
                self.waiting_button,
                self.paused_button,
                self.warning_satisfied,
                self.error_stack,
                self.ignore_interactions_container,
        ]
        ),
        self.connection_ports,
        ],tight=True
        )],height=self.module_container.height,
        )
        self.page_overlay = None #PageOverlay(self.pipeline_gui.page,self.module.settings,self.close_options)
        self._ports_lock = asyncio.Lock()

    def disable_tools(self):
        """
        Disable the tools of the modules.
        """
        self.warning_satisfied.disabled = True
        self.warning_satisfied.update()
        if self.port_selection:
            self.connect_clicked()
        self.connect_button.disabled=True
        self.connect_button.icon_color = DISABLED_BUTTONS_COLOR
        self.options_button.disabled=True
        self.options_button.icon_color = DISABLED_BUTTONS_COLOR
        self.copy_button.disabled = True
        self.copy_button.icon_color = DISABLED_BUTTONS_COLOR
        self.ports_in_out_clicked(disable=True)
        self.connect_button.update()
        self.options_button.update()
        self.copy_button.update()

    def enable_pause(self):
        """
        Enable the options button while be in a pausing state.
        """
        self.options_button.disabled = False
        self.options_button.icon_color = ft.Colors.WHITE60
        self.options_button.update()

    def disable_pause(self):
        """
        Disable the options button after a pausing state.
        """
        self.options_button.disabled = True
        self.options_button.icon_color = DISABLED_BUTTONS_COLOR
        self.options_button.update()

    def enable_tools(self):
        """
        Enable the tools of the module.
        """
        self.warning_satisfied.disabled = False
        self.warning_satisfied.update()
        self.connect_button.disabled = False
        self.connect_button.icon_color = ft.Colors.WHITE60
        self.options_button.disabled = False
        self.options_button.icon_color = ft.Colors.WHITE60
        self.copy_button.disabled = False
        self.copy_button.icon_color = ft.Colors.WHITE60
        self.ports_in_out_clicked(disable=False)
        self.connect_button.update()
        self.options_button.update()
        self.copy_button.update()

    def on_enter_click_module(self):
        """
        Handles if the mouse enters hovering over the module to connect.
        """
        if self.valid:
            self.click_container.bgcolor = VALID_COLOR
            self.click_container.update()

    def on_exit_click_module(self):
        """
        Handles if the mouse exits hovering over the module to connect.
        """
        if self.valid:
            self.click_container.bgcolor = ft.Colors.TRANSPARENT
            self.click_container.update()

    def update_port_icons(self):
        """
        Updates all ports_Icons of the show ports tab.
        """
        for port in self.module.inputs.keys():
            if self.pipeline_gui.pipeline.check_ports_occupied(self.module_id, [port]):
                self.in_ports_Icons[port].visible = False
                self.in_ports_Icons_occupied[port].visible = True
            else:
                self.in_ports_Icons[port].visible = True
                self.in_ports_Icons_occupied[port].visible = False

            self.in_ports_Icons[port].update()
            self.in_ports_Icons_occupied[port].update()

            self.check_warning()

    def check_warning(self):
        """
        Checks if the module should have a warning.
        """
        self.module_container.border = ft.border.all(4,
                                                     ft.Colors.RED if not self.pipeline_gui.pipeline.check_module_satisfied(
                                                         self.module_id) or self.error_stack.visible else ft.Colors.BLACK12)
        self.module_container.update()
        if not self.error_stack.visible:
            self.warning_satisfied.visible = not self.pipeline_gui.pipeline.check_module_satisfied(self.module_id)
            self.warning_satisfied.update()

    def connect_clicked(self,update:bool=True):
        """
        Handles the event when the connection button gets pressed.
        """
        print("connect button clicked")
        self.pipeline_gui.toggle_all_module_detection(self.module_id)
        if not self.port_selection:
            if self.show_ports:
                self.ports_in_out_clicked(False)
            if update:
                self.pipeline_gui.set_in_background(self,True)
            self.connect_button.icon_color = ft.Colors.BLACK38
            self.delete_button.visible = False
            self.content.height = 40+self.module_container.height
            self.connection_ports.visible = True
            self.connection_ports.update()
            self.port_selection = True
        else:
            self.valid = False
            self.connection_ports.visible = False
            self.connection_ports.update()
            self.port_chips = self.get_ports_row()
            self.connection_ports.content = self.port_chips
            self.connect_button.icon_color = ft.Colors.WHITE60
            self.delete_button.visible = True
            self.content.height = self.module_container.height
            self.port_selection = False
            self.pipeline_gui.source_module = ""

        self.delete_button.update()
        self.content.update()
        self.connect_button.update()
        self.pipeline_gui.page.update()

    def ports_in_out_clicked(self, update: bool = True,disable:bool = None):
        self.pipeline_gui.page.run_task(self.async_ports_in_out_clicked, update=update,disable=disable)

    async def async_ports_in_out_clicked(self, update:bool=True,disable:bool=None):
        """
        Handles the event when the show ports button gets pressed.
        """
        print("show ports button clicked")
        async with self._ports_lock:
            if self.module_id not in self.pipeline_gui.modules:
                return
            if not self.show_ports and disable is None:
                if self.port_selection:
                    self.connect_clicked(False)
                    await asyncio.sleep(0.02)

                self.ports_in_out_button.icon_color = ft.Colors.BLACK38
                self.ports_in_out_button.update()
                self.content.height = MODULE_HEIGHT * 2 + self.module_container.height - 15
                if self.module_id in self.pipeline_gui.modules:
                    self.content.update()
                self.ports_container.height = MODULE_HEIGHT * 2
                self.ports_container.opacity = 1
                if self.module_id in self.pipeline_gui.modules:
                    self.ports_container.update()
                await asyncio.sleep(0.14)
                self.ports_column.scroll=ft.ScrollMode.ALWAYS
                if self.module_id in self.pipeline_gui.modules:
                    self.ports_column.update()
                self.show_ports = True
            else:
                if not disable:
                    self.ports_in_out_button.disabled = False
                    self.ports_in_out_button.icon_color = ft.Colors.WHITE60
                    if self.module_id in self.pipeline_gui.modules:
                        self.ports_in_out_button.update()
                else:
                    self.ports_in_out_button.disabled = True
                    self.ports_in_out_button.icon_color = DISABLED_BUTTONS_COLOR
                    if self.module_id in self.pipeline_gui.modules:
                        self.ports_in_out_button.update()

                self.ports_column.scroll=ft.ScrollMode.HIDDEN
                if self.module_id in self.pipeline_gui.modules:
                    self.ports_column.update()
                self.ports_container.height = 0
                self.ports_container.opacity = 0
                if self.module_id in self.pipeline_gui.modules:
                    self.ports_container.update()
                await asyncio.sleep(0.22)
                self.content.height = self.module_container.height
                if self.module_id in self.pipeline_gui.modules:
                    self.content.update()
                self.show_ports = False


    def set_valid(self):
        """
        Sets a module valid to connect.
        """
        self.valid = True
        self.click_container.bgcolor = ft.Colors.TRANSPARENT
        self.module_container.border = ft.border.all(4, ft.Colors.WHITE38)
        self.module_container.update()
        self.click_container.update()

    def set_invalid(self):
        """
        Sets a module to invalid to connect.
        """
        self.valid = False
        self.click_container.bgcolor = INVALID_COLOR
        self.module_container.border = ft.border.all(4, ft.Colors.RED if not self.pipeline_gui.pipeline.check_module_satisfied(self.module_id) or self.error_stack.visible else ft.Colors.BLACK12)
        self.module_container.update()
        self.click_container.update()

    def set_running(self):
        """
        Called when the module is currently running.
        """
        self.executing_button.visible = True
        self.waiting_button.visible = False
        self.executing_button.update()
        self.waiting_button.update()

    def get_ports_row(self):
        """
        Creates the chip row for the different ports of a module.
        """
        ports_chips = ft.Row()

        for port_name in self.module.outputs.keys():
            ports_chips.controls.append(
                ft.Chip(
                    label=ft.Text(port_name),
                    on_select=lambda e,name = port_name: self.select_port(e,name),
                )
            )
        return ports_chips

    def select_port(self,e, port_name):
        """
        Handles the event if a port gets selected for connecting.
        """
        if e.control.selected:
            self.pipeline_gui.transmitting_ports.append(port_name)
            self.port_chips.update()
        else:
            self.pipeline_gui.transmitting_ports.remove(port_name)
            self.port_chips.update()

        self.pipeline_gui.check_for_valid_all_modules()

    def toggle_detection(self):
        """
        Toggles between the module state 'only moveable' and  'normal mode'
        """
        if self.detection:
            self.detection = False
            self.click_container.disabled = False
            self.click_container.visible = True
            self.ignore_interactions_container.ignore_interactions = False
            self.ignore_interactions_container.update()
            self.click_container.update()
            self.click_gesture.disabled = False
            self.click_gesture.visible = True
            self.click_gesture.update()
            self.delete_button.visible = False
            self.delete_button.update()
        else:
            self.detection = True
            self.set_invalid()
            self.click_container.disabled = True
            self.click_container.visible = False
            self.ignore_interactions_container.ignore_interactions = True
            self.ignore_interactions_container.update()
            self.click_container.update()
            self.click_gesture.disabled = True
            self.click_gesture.visible = False
            self.click_gesture.update()
            if (self.module_id not in self.pipeline_gui.pipeline.run_order and not self.pipeline_gui.pipeline.executing == self.module_id) or not self.pipeline_gui.pipeline.running:
                self.delete_button.visible = True
                self.delete_button.update()
            self.connection_ports.visible = False
            self.connect_button.update()


    def add_connection(self):
        """
        Handles the last step of the adding event when the target gets selected.
        """
        if self.pipeline_gui.source_module is not None and self.pipeline_gui.transmitting_ports is not None and not self.detection and self.valid:
            current_pipe = self.pipeline_gui.pipeline.get_pipe(self.pipeline_gui.source_module,self.module_id)
            if current_pipe is None:
                self.pipeline_gui.add_connection(self.pipeline_gui.modules[self.pipeline_gui.source_module],self,self.pipeline_gui.transmitting_ports)
            else:
                self.pipeline_gui.expand_connection(current_pipe,self.pipeline_gui.transmitting_ports)
            self.pipeline_gui.check_for_valid_all_modules()

    def remove_module(self):
        """
        Removes a module and all its connections.
        """
        for pipe in list(self.pipeline_gui.pipeline.pipes_in[self.module_id]):
            self.pipeline_gui.remove_connection(self.pipeline_gui.modules[pipe.source_module.module_id],self)
        for pipe in list(self.pipeline_gui.pipeline.pipes_out[self.module_id]):
            self.pipeline_gui.remove_connection(self,self.pipeline_gui.modules[pipe.target_module.module_id])

        if self.show_mode:
            self.pipeline_gui.show_room_modules.remove(self)
            self.pipeline_gui.pipeline.remove_module(self.module)
            self.pipeline_gui.page_stack.controls.remove(self)
            self.pipeline_gui.update()
        else:
            self.pipeline_gui.remove_module(self.module_id)

    @property
    def module_id(self):
        """
        Returns the module id of the module.
        """
        return self.module.module_id

    def bounce_back(self):
        """Returns card to its original position"""
        self.left = self.old_left
        self.top = self.old_top
        self.pipeline_gui.lines_gui._update_lines(self)
        self.pipeline_gui.lines_gui.update_gui()
        self.update()

    def start_drag(self, e: ft.DragStartEvent):
        """
        Handles the start of the drag event to save old location to make it possible to bounce back.
        """
        self.old_left = self.left
        self.old_top = self.top
        self.pipeline_gui.lines_gui.update_lines(self)
        self.update()

    def drag(self, e: ft.DragUpdateEvent):
        """
        Handles the drag event.
        """
        if self.show_mode:
            self.click_container.tooltip = None
            self.click_container.update()
            overlap_show_room = not (
                    self.left + MODULE_WIDTH  < self.pipeline_gui.show_room_container.left or
                    self.left > self.pipeline_gui.show_room_container.left + self.pipeline_gui.show_room_container.width or
                    self.top + MODULE_HEIGHT < self.pipeline_gui.show_room_container.top or
                    self.top > self.pipeline_gui.show_room_container.top + self.pipeline_gui.show_room_container.height
            ) and self.show_mode
            if not overlap_show_room:
                self.pipeline_gui.pipeline.event_manager.notify(DragAndDropEvent(True))
            else:
                self.pipeline_gui.pipeline.event_manager.notify(DragAndDropEvent(False))

        if self.show_mode:
            self.top = self.top + e.local_delta.y
            self.left = self.left + e.local_delta.x
        else:
            self.top = min(max(0, self.top + e.local_delta.y), CANVAS_HEIGHT - MODULE_HEIGHT)
            self.left = min(max(0, self.left + e.local_delta.x), CANVAS_WIDTH - MODULE_WIDTH)
        self.pipeline_gui.lines_gui.update_lines(self)
        self.update()

    def drop(self,e: ft.DragEndEvent):
        """
        Handles the drop event.
        """
        if self.show_mode:
            self.click_container.tooltip = self.wrapped_description
            self.click_container.update()
            self.pipeline_gui.pipeline.event_manager.notify(DragAndDropEvent(False))
        # calc the left and top values in the pipeline_gui
        offset_x, offset_y, scale = (0,0,1) #self.pipeline_gui.interactive_view.get_transformation_data()
        check_left = self.left if not self.show_mode else (self.left - offset_x) / scale
        check_top = self.top if not self.show_mode else (self.top - offset_y) / scale

        for module in self.pipeline_gui.modules.values():
            if module is self:
                continue



            overlap = not (
                    check_left + MODULE_WIDTH < module.left or
                    check_left > module.left + MODULE_WIDTH or
                    check_top + MODULE_HEIGHT < module.top or
                    check_top > module.top + MODULE_HEIGHT
            )

            if overlap:
                self.bounce_back()
                self.pipeline_gui.lines_gui.update_lines(self)
                e.control.update()
                return

        #no need to calc cords because show_room_container and module with self.show_mode are in the same page_stack
        overlap_show_room = not(
                self.left + MODULE_WIDTH  < self.pipeline_gui.show_room_container.left or
                self.left > self.pipeline_gui.show_room_container.left + self.pipeline_gui.show_room_container.width or
                self.top + MODULE_HEIGHT < self.pipeline_gui.show_room_container.top or
                self.top > self.pipeline_gui.show_room_container.top + self.pipeline_gui.show_room_container.height
        ) and self.show_mode

        if overlap_show_room:
            self.bounce_back()
            e.control.update()
            return
        elif self.show_mode:
            self.show_mode = False
            index = self.pipeline_gui.show_room_modules.index(self)
            self.pipeline_gui.show_room_modules.remove(self)
            show_room_id = self.module.get_id_number()
            self.pipeline_gui.pipeline.get_new_module_id(self.module_id)
            self.pipeline_gui.modules[self.module_id] = self
            if DEBUG:
                self.name_text.value = self.module_id
            self.pipeline_gui.refill_show_room(self,self.visible,index,show_room_id)
            self.pipeline_gui.page_stack.controls.remove(self)
            self.pipeline_gui.page_stack.update()
            self.left = min(max(0,cast(int, check_left)),CANVAS_WIDTH-MODULE_WIDTH)
            self.top = min(max(0,cast(int, check_top)),CANVAS_HEIGHT-MODULE_HEIGHT)
            self.pipeline_gui.controls.append(self)
            self.click_container.disabled = True
            self.ignore_interactions_container.ignore_interactions = True
            self.ignore_interactions_container.update()
            self.click_container.bgcolor = INVALID_COLOR
            self.click_container.visible = False
            self.click_container.tooltip = None
            self.click_gesture.disabled = True
            self.click_gesture.visible = False
            self.delete_button.visible = True
            if self.pipeline_gui.source_module != "":
                self.toggle_detection()
                self.pipeline_gui.check_for_valid_all_modules()
            self.pipeline_gui.update()

        e.control.update()
        self.pipeline_gui.lines_gui.update_lines(self)

    def generate_options_overlay(self):
        """
        Generates with the user attributes tagged with the prefix 'user_' a gui overlay.
        """
        user_attributes = self.module.get_user_attributes
        element_height= 60
        spacing = 10
        padding = 20
        height = element_height* len(user_attributes) + spacing * (len(user_attributes)-1)
        limit_reached = len(user_attributes) > USER_OPTIONS_LIMIT
        if len(user_attributes) != 0:
            return ft.Stack([ft.Row([ft.Column([ft.Card(
                content=ft.Column(
                    [ft.Container(ft.ListView(
                        controls=self.create_attribute_list(user_attributes),
                        width=500,
                        spacing=spacing,
                        height=(element_height* (USER_OPTIONS_LIMIT+1) + spacing * ((USER_OPTIONS_LIMIT+1)-1))-30  if limit_reached else height,
                    ),padding=padding)]
                )
            )],
            alignment=ft.MainAxisAlignment.CENTER,)],alignment=ft.MainAxisAlignment.CENTER)],alignment=ft.Alignment.CENTER)
        else:
            return None

    def create_attribute_list(self,attributes=None):
        """
        Creates a text field for each user attribute and combines them into a single list.
        Allowed types are:
            int
            float
            string
            boolean
            FilePath
            DirectoryPath
        """
        items = []
        for attribute_name in attributes:
            value = getattr(self.module, attribute_name)
            typ = type(value)
            if typ in (int, float, str):
                ref = ft.Ref[ft.Text]()
                setattr(self.module,"ref_" + attribute_name, ref)
                items.append(ft.TextField(
                            label=attribute_name.removeprefix("user_"),
                            border_color=ft.Colors.BLUE_ACCENT,
                            value=str(value),
                            ref=ref,
                            on_blur=lambda e,attr_name= attribute_name,reference=ref,type_atr = typ: self.on_change(e,attr_name,reference,type_atr),
                            height=60,
                        ))
            elif typ == bool:
                text = ft.Text(attribute_name.removeprefix("user_"),weight=ft.FontWeight.BOLD)
                index = 0 if not value else 1
                setattr(self.module,"on_change_" + attribute_name, lambda: None)
                slider_bool = ft.CupertinoSlidingSegmentedButton(
                    selected_index=index,
                    thumb_color=ft.Colors.BLUE_400,
                    on_change=lambda e, attr_name=attribute_name: self.update_bool(e,attr_name),
                    padding=ft.padding.symmetric(0, 0),
                    controls=[
                        ft.Text("False"),
                        ft.Text("True")
                    ],
                )
                bool_choosing = ft.Container(ft.Row([text, slider_bool], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=ft.Padding(0, 10, 0, 10))
                items.append(bool_choosing)
            elif typ == FilePath:
                text_field = ft.TextField(
                    label=attribute_name.removeprefix("user_"),
                    border_color=ft.Colors.BLUE_ACCENT,
                    value=format_directory_path(value.path,50),
                    height=60,
                    read_only=True,
                    disabled=True,
                    expand=True
                )
                attr = getattr(self.module, attribute_name)
                file_picker = ft.FilePicker()
                self.pipeline_gui._page.services.append(file_picker)
                items.append(ft.Stack([text_field,ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.UPLOAD_FILE,
                                    tooltip="Pick file",
                                    on_click=lambda a,attr_name= attribute_name,content=text_field: self.pipeline_gui.page.run_task(self.on_select_file,a,file_picker,attr.suffix,attr_name,content),
                                ),
                                alignment=ft.Alignment.TOP_RIGHT
                            ,right=10,top=5)
                    ]))
            elif typ == DirectoryPath:
                text_field = ft.TextField(
                    label=attribute_name.removeprefix("user_"),
                    border_color=ft.Colors.BLUE_ACCENT,
                    value=format_directory_path(value.path, 50),
                    height=60,
                    read_only=True,
                    disabled=True,
                    expand=True
                )
                file_picker = ft.FilePicker()
                items.append(ft.Stack([text_field, ft.Container(
                        content=ft.IconButton(
                            icon=ft.Icons.FOLDER_OPEN,
                            tooltip="Choose directory",
                            on_click=lambda a, attr_name=attribute_name, content=text_field: self.pipeline_gui.page.run_task(self.on_select_dir,a,file_picker, attr_name, content),
                        ),
                        alignment=ft.Alignment.TOP_RIGHT,right=10,top=5
                    )
                ]))
            else:
                raise ValueError(f"Unsupported 'user_' attribute file type: {typ}")
        return items

    async def on_select_file(self,e: ft.Event[ft.Button],file_picker,suffix,attr_name,text):
        """
        Handles if a file is selected.
        """
        files = await file_picker.pick_files(allow_multiple=False,file_type=ft.FilePickerFileType.CUSTOM if suffix is not None else ft.FilePickerFileType.ANY,allowed_extensions=suffix if suffix is not None else [],)
        if files is not None and len(files) > 0:
            current_file_path = getattr(self.module, attr_name)
            current_file_path.path = files[0].path
            text.value = format_directory_path(files[0].path,50)
            text.update()
            self.pipeline_gui.page.update()
            self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    async def on_select_dir(self,e: ft.Event[ft.Button],file_picker,attr_name,text):
        """
        Handles if a directory is selected.
        """
        dir = await file_picker.get_directory_path()
        if dir is not None:
            setattr(self.module, attr_name, FilePath(dir))
            text.value = format_directory_path(dir,50)
            text.update()
            self.pipeline_gui.page.update()
            self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    def on_change(self,e,attr_name,reference,typ:type):
        """
        Handles changes to the attribute for different types.
        """
        attribute_name_without_prefix = attr_name.removeprefix("user_")
        if str(e.control.value) == "":
            self.pipeline_gui.page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"{attribute_name_without_prefix} must not be empty!",
                            color=ft.Colors.WHITE),
                    bgcolor=ft.Colors.RED))
            e.control.value = str(getattr(self.module, attr_name))
            self.pipeline_gui.page.update()
            return
        try:
            setattr(self.module, attr_name, typ(e.control.value))
            self.pipeline_gui.page.update()
            self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))
        except ValueError:
            self.pipeline_gui.page.show_dialog(ft.SnackBar(ft.Text(f"{attribute_name_without_prefix} only allows {typ.__name__}'s.",color=ft.Colors.WHITE),bgcolor=ft.Colors.RED))
            reference.current.value = str(getattr(self.module, attr_name))
            self.pipeline_gui.page.update()

    def update_bool(self,e,attr_name):
        """
        Handels changes to the attribute for booleans.
        """
        if int(e.data) == 1:
            setattr(self.module, attr_name, True)
        else:
            setattr(self.module, attr_name, False)
        getattr(self.module, "on_change_" + attr_name)()
        self.pipeline_gui.page.update()
        self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    def open_options(self,e):
        """
        Open options overlay of the module.
        """
        if self.page_overlay is None:
            page = self.pipeline_gui.page
            self.page_overlay = PageOverlay(page, self.module._settings, self.close_options)
        if self.module._settings is None:
            self.module._settings = self.generate_options_overlay()
        self.page_overlay.open()
        self.options_button.icon_color = ft.Colors.BLACK38
        self.options_button.update()

    def close_options(self,e):
        """
        Called when the overlay gets dismissed.
        """
        self.page_overlay.close()
        self.module.on_settings_dismiss() if self.module.on_settings_dismiss is not None else None
        self.options_button.icon_color = ft.Colors.WHITE60
        self.options_button.update()

    def copy_module(self):
        """
        Called when the copy button is clicked.
        """
        print("copy button clicked")
        self.copy_button.icon_color = ft.Colors.BLACK38
        self.copy_button.update()
        copy_dict = self.to_dict()
        self.pipeline_gui.add_module(ModuleType(type(self.module)),x=cast(float, self.left)+20,y=cast(float, self.top)+20,module_dict=copy_dict)
        self.copy_button.icon_color = ft.Colors.WHITE60
        self.copy_button.update()

    def to_dict(self):
        """
        Translates the module into a dictionary.
        """
        user_attributes: List[Dict[str, Any]] = []
        for attr_name in self.module.get_user_attributes:
            value = getattr(self.module,attr_name)
            value_type = type(value).__name__
            if isinstance(value,FilePath) or isinstance(value,DirectoryPath):
                value = value.path
            user_attributes.append({"name": attr_name,"value": value,"attr_type":value_type})
        return {
            "module_id": self.module_id,
            "module_name": self.module.gui_config().name,
            "position": {"x":self.left, "y":self.top},
            "user_attributes": user_attributes,
        }

    def update_user_attr(self,module_dict:dict):
        """
        Update user_attributes with a module dict.
        """
        for attr in module_dict.get("user_attributes", []):
            user_attributes = self.module.get_user_attributes
            if attr["name"] in user_attributes:
                if attr["attr_type"] == FilePath.__name__ or attr["attr_type"] == DirectoryPath.__name__:
                    getattr(self.module, attr["name"]).path = attr["value"]
                else:
                    setattr(self.module, attr["name"], attr["value"])

