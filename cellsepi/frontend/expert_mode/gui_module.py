import asyncio
import enum
import textwrap
import flet as ft
from typing import List, Any, Dict, cast

from backend.constants import FILTER_INT, FILTER_FLOAT, FILTER_SCIENTIFIC_FLOAT, FILTER_INT_SIGNED, \
    FILTER_SCIENTIFIC_FLOAT_SIGNED, FILTER_FLOAT_0_TO_1, MAIN_COLOR, ERROR_COLOR
from backend.error_manager import ErrorManager
from backend.expert_mode.limits import Limit
from backend.expert_mode.listener import DragAndDropEvent, OnPipelineChangeEvent
from backend.expert_mode.module import FilePath, DirectoryPath
from frontend.gui_directory import format_directory_path
from frontend.gui_page_overlay import PageOverlay
from frontend.expert_mode.expert_constants import *
from frontend.expert_mode.gui_pipeline import *


class ModuleGUI(ft.GestureDetector):
    """
    Manages the GUI parts of the module.
    """

    def __init__(self, pipeline_gui, module_type: type, x: float = None, y: float = None, show_mode: bool = False,
                 visible=True, index: int = None, id_number: int = None, module_dict: dict = None):
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
        self.left = ft.BUILDER_WIDTH / 2 if x is None else x
        self.top = ft.BUILDER_HEIGHT / 2 if y is None else y
        self.old_left = None
        self.old_top = None
        self.port_selection = False
        self.module = self.pipeline_gui.pipeline.add_module(
            module_type) if id_number is None else self.pipeline_gui.pipeline.add_module_with_id(module_type,
                                                                                                 module_type.gui_config().name + "_" + str(
                                                                                                     id_number))
        self.module._page = self.pipeline_gui._page
        self.pipeline_gui._page.run_task(self.create_options)
        if module_dict is not None:
            self.update_user_attr(module_dict)
        if show_mode:
            if index is None:
                self.pipeline_gui.show_room_modules.append(self)
            else:
                self.pipeline_gui.show_room_modules.insert(index, self)
        else:
            self.pipeline_gui.modules[self.module.module_id] = self
            self.pipeline_gui.pipeline.event_manager.notify(
                OnPipelineChangeEvent(f"Added {self.module_id} to pipeline_gui.modules."))
        self.color = self.module.gui_config().category.value
        self.valid = False
        self.wrapped_description = "\n".join(textwrap.wrap(self.module.gui_config().description, width=40))
        self.block_container = ft.Container(tooltip=self.wrapped_description if self.show_mode else None,
                                            height=MODULE_HEIGHT, width=MODULE_WIDTH,
                                            visible=False if not show_mode else True,
                                            bgcolor=INVALID_COLOR if not show_mode else ft.Colors.TRANSPARENT,
                                            disabled=True if not show_mode else False,
                                            border_radius=ft.BorderRadius.all(10))
        self.click_container = ft.Container(on_click=self.add_connection,
                                            height=MODULE_HEIGHT, width=MODULE_WIDTH,
                                            bgcolor=ft.Colors.TRANSPARENT,
                                            border_radius=ft.BorderRadius.all(10))
        self.click_gesture = ft.GestureDetector(hover_interval=25, visible=False, disabled=True,
                                                content=self.click_container, on_enter=self.on_enter_click_module,
                                                on_exit=self.on_exit_click_module)

        self.connect_button = ft.IconButton(icon=ft.Icons.SHARE, icon_color=ft.Colors.WHITE60,
                                            style=ft.ButtonStyle(
                                                shape=ft.RoundedRectangleBorder(radius=12),
                                            ), on_click=self.connect_clicked,
                                            tooltip="Add connection", hover_color=ft.Colors.WHITE12,
                                            visible=self.module.outputs != {})

        self.options_button = ft.IconButton(icon=ft.Icons.TUNE, icon_color=ft.Colors.WHITE60,
                                            style=ft.ButtonStyle(
                                                shape=ft.RoundedRectangleBorder(radius=12),
                                            ), on_click=self.open_options,
                                            tooltip="Options", hover_color=ft.Colors.WHITE12,
                                            visible=True if len(self.module.get_user_attributes) != 0 else False, )
        self.copy_button = ft.IconButton(icon=ft.Icons.CONTENT_COPY, icon_color=ft.Colors.WHITE60,
                                         style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                                         on_click=self.copy_module,
                                         tooltip="Copy module", hover_color=ft.Colors.WHITE12, )

        self.paused_button = ft.Stack([ft.Container(bgcolor=ft.Colors.BLACK26, width=30, height=30, top=5, right=5,
                                                    border_radius=ft.BorderRadius.all(45)),
                                       ft.IconButton(icon=ft.Icons.PLAY_ARROW, icon_color=ft.Colors.WHITE,
                                                     disabled=True,
                                                     style=ft.ButtonStyle(
                                                         shape=ft.RoundedRectangleBorder(radius=12),
                                                     ), on_click=self.copy_module,
                                                     tooltip="Currently paused to continue\npress the resume button",
                                                     hover_color=ft.Colors.WHITE12)], top=1,
                                      left=MODULE_WIDTH - 42, visible=False, width=40, height=40)
        self.executing_button = ft.Stack([ft.Container(bgcolor=ft.Colors.BLACK26, width=30, height=30, top=5, right=5,
                                                       border_radius=ft.BorderRadius.all(45)),
                                          ft.IconButton(icon=ft.Icons.PAUSE_ROUNDED, icon_color=ft.Colors.WHITE,
                                                        disabled=True,
                                                        style=ft.ButtonStyle(
                                                            shape=ft.RoundedRectangleBorder(radius=12),
                                                        ), on_click=self.copy_module,
                                                        tooltip="Currently executed", hover_color=ft.Colors.WHITE12)],
                                         top=1,
                                         left=MODULE_WIDTH - 42, visible=False, width=40, height=40)
        self.waiting_button = ft.Stack([ft.Container(bgcolor=ft.Colors.BLACK26, width=30, height=30, top=5, right=5,
                                                     border_radius=ft.BorderRadius.all(45)),
                                        ft.IconButton(icon=ft.Icons.HOURGLASS_EMPTY_ROUNDED, icon_color=ft.Colors.WHITE,
                                                      disabled=True,
                                                      style=ft.ButtonStyle(
                                                          shape=ft.RoundedRectangleBorder(radius=12),
                                                      ), on_click=self.copy_module,
                                                      tooltip="Waiting for execution", hover_color=ft.Colors.WHITE12)],
                                       top=1,
                                       left=MODULE_WIDTH - 42, visible=False, width=40, height=40)
        self.show_ports = False
        self.ports_in_out_button = ft.IconButton(icon=ft.Icons.SYNC_ALT_ROUNDED, icon_color=ft.Colors.WHITE60,
                                                 style=ft.ButtonStyle(
                                                     shape=ft.RoundedRectangleBorder(radius=12),
                                                 ), on_click=self.ports_in_out_clicked,
                                                 tooltip="View ports", hover_color=ft.Colors.WHITE12, )

        self.tools = ft.Container(ft.Row(
            [
                self.connect_button, self.options_button, self.ports_in_out_button, self.copy_button,
            ], tight=True, spacing=7
        ), bgcolor=ft.Colors.BLACK12, expand=True, width=MODULE_WIDTH
        )

        self.delete_button = ft.IconButton(ft.Icons.CLOSE, visible=True if not show_mode else False,
                                           icon_color=ft.Colors.WHITE, hover_color=ft.Colors.WHITE12,
                                           tooltip="Delete Module", on_click=self.remove_module)
        self.port_chips = self.get_ports_row()
        self.connection_ports = ft.Container(
            self.port_chips, visible=False
        )

        control_list_ports = []
        self.in_ports_Icons = {}
        self.in_ports_Icons_occupied = {}
        for port in self.module.inputs.values():
            if not port.opt:
                self.in_ports_Icons[port.name] = ft.Stack(
                    [ft.Container(bgcolor=ft.Colors.WHITE, width=10, height=20, bottom=10, right=15,
                                  border_radius=ft.BorderRadius.all(45)), ft.Container(
                        ft.IconButton(ft.Icons.WARNING_ROUNDED, icon_size=35, disabled=True,
                                      hover_color=ft.Colors.TRANSPARENT, icon_color=ERROR_COLOR,
                                      tooltip=f"Port {port.name} is mandatory and has no incoming pipe!"), bottom=-3,
                        right=-5)], alignment=ft.Alignment.CENTER,
                    visible=not self.pipeline_gui.pipeline.check_ports_occupied(self.module_id, [port.name]), width=40,
                    height=40)
                self.in_ports_Icons_occupied[port.name] = ft.Stack(
                    [ft.Container(bgcolor=SUCCESS_COLOR, width=30, height=30, border_radius=ft.BorderRadius.all(45)),
                     ft.IconButton(ft.Icons.CHECK, disabled=True, hover_color=ft.Colors.TRANSPARENT,
                                   icon_color=ft.Colors.WHITE,
                                   tooltip=f"Port {port.name} is mandatory and is satisfied.")],
                    alignment=ft.Alignment.CENTER,
                    visible=self.pipeline_gui.pipeline.check_ports_occupied(self.module_id, [port.name]), width=40,
                    height=40)
            else:
                self.in_ports_Icons[port.name] = ft.Stack(
                    [ft.Container(bgcolor=ft.Colors.WHITE, width=10, height=20, bottom=10, right=15,
                                  border_radius=ft.BorderRadius.all(45)), ft.Container(
                        ft.IconButton(ft.Icons.WARNING_ROUNDED, icon_size=35, disabled=True,
                                      hover_color=ft.Colors.TRANSPARENT, icon_color=ERROR_COLOR,
                                      tooltip=f"Port {port.name} is optional and has no incoming pipe!"), bottom=-3,
                        right=-5)], alignment=ft.Alignment.CENTER,
                    visible=not self.pipeline_gui.pipeline.check_ports_occupied(self.module_id, [port.name]),
                    opacity=0.2, width=40, height=40)
                self.in_ports_Icons_occupied[port.name] = ft.Stack(
                    [ft.Container(bgcolor=SUCCESS_COLOR, width=30, height=30, border_radius=ft.BorderRadius.all(45)),
                     ft.IconButton(ft.Icons.CHECK, disabled=True, hover_color=ft.Colors.TRANSPARENT,
                                   icon_color=ft.Colors.WHITE,
                                   tooltip=f"Port {port.name} is optional and is satisfied.")],
                    alignment=ft.Alignment.CENTER, opacity=0.2,
                    visible=self.pipeline_gui.pipeline.check_ports_occupied(self.module_id, [port.name]), width=40,
                    height=40)

        in_ports = ft.Column([ft.Row(
            [ft.Text(port.name, width=MODULE_WIDTH / 2, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
             self.in_ports_Icons[port.name], self.in_ports_Icons_occupied[port.name]]) for port in
            self.module.inputs.values()], spacing=0)
        out_ports = ft.Column(
            [ft.Row([ft.Text(port.name, width=MODULE_WIDTH / 2, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)]) for
             port in self.module.outputs.values()])
        input_text = ft.Text("Inputs:", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        output_text = ft.Text("Outputs:", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        if self.module.inputs != {}:
            control_list_ports.append(input_text)
            control_list_ports.append(in_ports)
        if self.module.outputs != {}:
            control_list_ports.append(output_text)
            control_list_ports.append(out_ports)

        self.error_icon = ft.IconButton(ft.Icons.REPORT, icon_size=35, disabled=True,
                                        hover_color=ft.Colors.TRANSPARENT, icon_color=ERROR_COLOR,
                                        tooltip="An error occurred while executing!",
                                        highlight_color=ft.Colors.TRANSPARENT,
                                        padding=ft.Padding.all(2))
        self.error_stack = ft.Stack([ft.Container(bgcolor=ft.Colors.WHITE, width=10, height=20, bottom=16, right=23,
                                                  border_radius=ft.BorderRadius.all(45)),
                                     self.error_icon],
                                    visible=False, width=48, height=48, top=1,
                                    left=MODULE_WIDTH - 75)

        self.warning_satisfied = ft.Stack(
            [ft.Container(bgcolor=ft.Colors.WHITE, width=10, height=20, bottom=16, right=23,
                          border_radius=ft.BorderRadius.all(45)),
             ft.IconButton(ft.Icons.WARNING_ROUNDED, icon_size=35, disabled=False, hover_color=ft.Colors.TRANSPARENT,
                           icon_color=ERROR_COLOR, tooltip=f"Not all mandatory inputs are satisfied!",
                           on_click=self.ports_in_out_clicked, highlight_color=ft.Colors.TRANSPARENT,
                           padding=ft.Padding.all(2))],
            visible=not self.pipeline_gui.pipeline.check_module_satisfied(self.module_id) and not show_mode, width=48,
            height=48, top=1, left=MODULE_WIDTH - 75)
        self.name_text = ft.Text(value=self.module.gui_config().name if not DEBUG else self.module_id,
                                 weight=ft.FontWeight.BOLD,
                                 width=MODULE_WIDTH - 80,
                                 height=20, color=ft.Colors.BLACK,
                                 overflow=ft.TextOverflow.ELLIPSIS)
        self.module_container = ft.Container(
            content=ft.Column(
                [
                    ft.Container(ft.Row(
                        [
                            self.name_text,
                        ], height=20
                    ), padding=ft.Padding.only(left=5, top=5)),
                    self.tools,
                ],
                tight=True)
            , bgcolor=self.color, width=MODULE_WIDTH
            , height=MODULE_HEIGHT,
            border=ft.Border.all(4, ERROR_COLOR if not self.pipeline_gui.pipeline.check_module_satisfied(
                self.module_id) and not show_mode else ft.Colors.BLACK12),
            border_radius=ft.BorderRadius.all(10),
        )
        self.ports_column = ft.Column(controls=control_list_ports, scroll=ft.ScrollMode.HIDDEN)
        self.ports_container = ft.Container(
            content=self.ports_column, bgcolor=self.color,
            width=MODULE_WIDTH,
            border_radius=ft.BorderRadius.all(10), padding=10, top=cast(float, self.module_container.height) - 15,
            border=ft.Border.all(8, ft.Colors.BLACK12), height=0, opacity=0,
            animate_opacity=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
            animate=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
        )
        self.content = ft.Stack([
            self.ports_container,
            ft.Column([ft.Stack([
                self.module_container,
                ft.Container(content=self.delete_button, margin=ft.Margin.only(top=-7, left=7),
                             alignment=ft.Alignment.TOP_RIGHT, width=MODULE_WIDTH, ),
                self.executing_button,
                self.waiting_button,
                self.paused_button,
                self.warning_satisfied,
                self.error_stack,
                self.block_container,
                self.click_gesture,
            ]
            ),
                self.connection_ports,
            ], tight=True
            )], height=self.module_container.height,
        )
        self.page_overlay = None  # PageOverlay(self.pipeline_gui.page,self.module.settings,self.close_options)
        self._ports_lock = asyncio.Lock()

    def is_port_connected(self, port_name: str) -> bool:
        """
        Check if an import port has a connection.
        """
        if self.module_id not in self.pipeline_gui.pipeline.pipes_in:
            return False

        for pipe in self.pipeline_gui.pipeline.pipes_in[self.module_id]:
            if port_name in pipe.port_names:
                return True
        return False

    async def disable_tools(self):
        """
        Disable the tools of the modules.
        """
        self.warning_satisfied.disabled = True
        self.warning_satisfied.update()
        if self.port_selection:
            await self.connect_clicked()
        self.connect_button.disabled = True
        self.connect_button.icon_color = DISABLED_BUTTONS_COLOR
        self.options_button.disabled = True
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
            self.block_container.bgcolor = VALID_COLOR
            self.block_container.update()

    def on_exit_click_module(self):
        """
        Handles if the mouse exits hovering over the module to connect.
        """
        if self.valid:
            self.block_container.bgcolor = ft.Colors.TRANSPARENT
            self.block_container.update()

    async def update_port_icons(self):
        """
        Updates all ports_Icons of the show ports tab.
        """
        for port in self.module.inputs.keys():
            if self.is_port_connected(port):
                self.in_ports_Icons[port].visible = False
                self.in_ports_Icons_occupied[port].visible = True
            else:
                self.in_ports_Icons[port].visible = True
                self.in_ports_Icons_occupied[port].visible = False

            self.in_ports_Icons[port].update()
            self.in_ports_Icons_occupied[port].update()

            await self.check_warning()

    async def check_warning(self):
        """
        Checks if the module should have a warning.
        """
        self.module_container.border = ft.Border.all(4,
                                                     ERROR_COLOR if not self.pipeline_gui.pipeline.check_module_satisfied(
                                                         self.module_id) or self.error_stack.visible else ft.Colors.BLACK12)
        self.module_container.update()
        if not self.error_stack.visible:
            self.warning_satisfied.visible = not self.pipeline_gui.pipeline.check_module_satisfied(self.module_id)
            self.warning_satisfied.update()

    async def connect_clicked(self, update: bool = True):
        """
        Handles the event when the connection button gets pressed.
        """
        await self.pipeline_gui.toggle_all_module_detection(self.module_id)
        if not self.port_selection:
            if self.show_ports:
                self.ports_in_out_clicked(False)
            if update:
                self.pipeline_gui.set_in_background(self, True)
            self.connect_button.icon_color = ft.Colors.BLACK38
            self.delete_button.visible = False
            self.content.height = 40 + self.module_container.height
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

    def ports_in_out_clicked(self, update: bool = True, disable: bool = None):
        self.pipeline_gui.page.run_task(self.async_ports_in_out_clicked, update=update, disable=disable)

    async def async_ports_in_out_clicked(self, update: bool = True, disable: bool = None):
        """
        Handles the event when the show ports button gets pressed.
        """
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
                self.ports_column.scroll = ft.ScrollMode.ALWAYS
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

                self.ports_column.scroll = ft.ScrollMode.HIDDEN
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

    async def set_valid(self):
        """
        Sets a module valid to connect.
        """
        self.valid = True
        self.block_container.bgcolor = ft.Colors.TRANSPARENT
        self.module_container.border = ft.Border.all(4, ft.Colors.WHITE38)
        self.module_container.update()
        self.block_container.update()

    async def set_invalid(self):
        """
        Sets a module to invalid to connect.
        """
        self.valid = False
        self.block_container.bgcolor = INVALID_COLOR
        self.module_container.border = ft.Border.all(4,
                                                     ERROR_COLOR if not self.pipeline_gui.pipeline.check_module_satisfied(
                                                         self.module_id) or self.error_stack.visible else ft.Colors.BLACK12)
        self.module_container.update()
        self.block_container.update()

    async def set_running(self):
        """
        Called when the module is currently running.
        """
        self.executing_button.visible = True
        self.waiting_button.visible = False
        self.delete_button.visible = False
        self.executing_button.update()
        self.waiting_button.update()
        self.delete_button.update()

    def get_ports_row(self):
        """
        Creates the chip row for the different ports of a module.
        """
        ports_chips = ft.Row()

        for port_name in self.module.outputs.keys():
            ports_chips.controls.append(
                ft.Chip(
                    label=ft.Text(port_name),
                    on_select=lambda e, name=port_name: self.pipeline_gui.page.run_task(self.select_port,e, name),
                )
            )
        return ports_chips

    async def select_port(self, e, port_name):
        """
        Handles the event if a port gets selected for connecting.
        """
        if e.control.selected:
            self.pipeline_gui.transmitting_ports.append(port_name)
            self.port_chips.update()
        else:
            self.pipeline_gui.transmitting_ports.remove(port_name)
            self.port_chips.update()

        await self.pipeline_gui.check_for_valid_all_modules()

    async def toggle_detection(self):
        """
        Toggles between the module state 'only moveable' and  'normal mode'
        """
        if self.detection:
            self.detection = False
            self.block_container.disabled = False
            self.block_container.visible = True
            self.block_container.ignore_interactions = False
            self.block_container.update()
            self.click_gesture.disabled = False
            self.click_gesture.visible = True
            self.click_gesture.update()
            self.delete_button.visible = False
            self.delete_button.update()
        else:
            self.detection = True
            await self.set_invalid()
            self.block_container.disabled = True
            self.block_container.visible = False
            self.block_container.ignore_interactions = True
            self.block_container.update()
            self.click_gesture.disabled = True
            self.click_gesture.visible = False
            self.click_gesture.update()
            if (self.module_id not in self.pipeline_gui.pipeline.run_order and not self.pipeline_gui.pipeline.executing == self.module_id) or not self.pipeline_gui.pipeline.running:
                self.delete_button.visible = True
                self.delete_button.update()
            self.connection_ports.visible = False
            self.connect_button.update()

    async def add_connection(self, e=None):
        """
        Handles the last step of the adding event when the target gets selected.
        Opens a tag selection dialog if the target port requires it.
        """
        if self.pipeline_gui.source_module is not None and self.pipeline_gui.transmitting_ports is not None and not self.detection and self.valid:

            source_id = self.pipeline_gui.source_module
            transmitting_ports = self.pipeline_gui.transmitting_ports

            ports_needing_tags = []
            for port_name in transmitting_ports:
                in_port = self.module.inputs.get(port_name)
                if in_port is not None and in_port.mode == "multi_tagged":
                    ports_needing_tags.append((port_name, in_port))

            if not ports_needing_tags:
                await self._execute_connection(source_id, transmitting_ports)
                return

            async def valid(e):
                e.control.border_color = MAIN_COLOR
                e.control.update()


            dropdowns = {}
            for port_name, in_port in ports_needing_tags:
                dropdowns[port_name] = ft.Dropdown(
                    label=f"Tag for {port_name}",
                    border_color=MAIN_COLOR,
                    options=[ft.dropdown.Option(tag) for tag in in_port.allowed_tags],
                    on_select=valid,
                    expand=True,
                    autofocus=True
                )

            async def on_cancel(e):
                overlay.close()
                await self.pipeline_gui.check_for_valid_all_modules()

            async def on_confirm(e):
                final_ports = []
                not_selected= False
                for port_name in transmitting_ports:
                    if port_name in dropdowns:
                        selected_tag = dropdowns[port_name].value
                        if not selected_tag:
                            dropdowns[port_name].border_color=ERROR_COLOR
                            dropdowns[port_name].update()
                            not_selected = True

                        final_ports.append((port_name, selected_tag))
                    else:
                        final_ports.append(port_name)

                if not_selected:
                    ErrorManager().show_without_button(f"Please select a tag for every given port!")
                    return

                overlay.close()
                await self._execute_connection(source_id, final_ports)

            dialog_card = ft.Card(
                    width=380,
                    height=500,
                    content=ft.Container(
                        padding=20,
                        content=ft.Column(
                            tight=True,
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text("Select Tags", weight=ft.FontWeight.BOLD, size=36),
                                        ft.Text("Please select a tag for the connections:", size=14),
                                    ],
                                    tight=True,
                                    spacing=5,
                                ),
                                ft.ListView(
                                    controls=[ft.Container(height=4)] + list(dropdowns.values()),
                                    expand=True,
                                    spacing=10,
                                ),
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.END,
                                    controls=[ft.Button("Connect", on_click=on_confirm)]
                                )
                            ]
                        )
                    )
                )
            overlay = PageOverlay(
                page=self.pipeline_gui.page,
                on_dismiss = on_cancel,
                content= dialog_card,
            )
            overlay.open()



    async def _execute_connection(self, source_id: str, ports_list: list):
        """
        Helper method to finalize the connection setup.
        """
        current_pipe = self.pipeline_gui.pipeline.get_pipe(source_id, self.module_id)
        if current_pipe is None:
            await self.pipeline_gui.add_connection(
                self.pipeline_gui.modules[source_id],
                self,
                ports_list
            )
        else:
            await self.pipeline_gui.expand_connection(current_pipe, ports_list)

        await self.pipeline_gui.check_for_valid_all_modules()

    async def remove_module(self):
        """
        Removes a module and all its connections.
        """
        for pipe in list(self.pipeline_gui.pipeline.pipes_in[self.module_id]):
            await self.pipeline_gui.remove_connection(pipe.source_module.module_id, self.module_id)
        for pipe in list(self.pipeline_gui.pipeline.pipes_out[self.module_id]):
            await self.pipeline_gui.remove_connection(self.module_id, pipe.target_module.module_id)

        if self.show_mode:
            self.pipeline_gui.show_room_modules.remove(self)
            await self.pipeline_gui.pipeline.remove_module(self.module)
            self.pipeline_gui.page_stack.controls.remove(self)
            self.pipeline_gui.update()
        else:
            await self.pipeline_gui.remove_module(self.module_id)

    @property
    def module_id(self):
        """
        Returns the module id of the module.
        """
        return self.module.module_id

    async def bounce_back(self):
        """Returns card to its original position"""
        self.left = self.old_left
        self.top = self.old_top
        await self.pipeline_gui.lines_gui._update_lines(self)
        await self.pipeline_gui.lines_gui.update_gui()
        self.update()

    async def start_drag(self, e: ft.DragStartEvent):
        """
        Handles the start of the drag event to save old location to make it possible to bounce back.
        """
        self.old_left = self.left
        self.old_top = self.top
        if not self.show_mode:
            await self.pipeline_gui.lines_gui.update_lines(self)
        self.update()

    async def drag(self, e: ft.DragUpdateEvent):
        """
        Handles the drag event.
        """
        if self.show_mode:
            self.block_container.tooltip = None
            overlap_show_room = not (
                    self.left + MODULE_WIDTH < self.pipeline_gui.show_room_container.left or
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
            await self.pipeline_gui.lines_gui.update_lines(self)

        self.update()

    async def drop(self, e: ft.DragEndEvent):
        """
        Handles the drop event.
        """
        # calc the left and top values in the pipeline_gui
        offset_x, offset_y, scale = await self.pipeline_gui.interactive_view.get_transformation_data()
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
                await self.bounce_back()
                await self.pipeline_gui.lines_gui.update_lines(self)
                e.control.update()
                return

        # no need to calc cords because show_room_container and module with self.show_mode are in the same page_stack
        overlap_show_room = not (
                self.left + MODULE_WIDTH < self.pipeline_gui.show_room_container.left or
                self.left > self.pipeline_gui.show_room_container.left + self.pipeline_gui.show_room_container.width or
                self.top + MODULE_HEIGHT < self.pipeline_gui.show_room_container.top or
                self.top > self.pipeline_gui.show_room_container.top + self.pipeline_gui.show_room_container.height
        ) and self.show_mode

        if overlap_show_room:
            await self.bounce_back()
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
            await self.pipeline_gui.refill_show_room(self, self.visible, index, show_room_id)
            self.pipeline_gui.page_stack.controls.remove(self)
            self.pipeline_gui.page_stack.update()
            self.left = min(max(0, cast(int, check_left)), CANVAS_WIDTH - MODULE_WIDTH)
            self.top = min(max(0, cast(int, check_top)), CANVAS_HEIGHT - MODULE_HEIGHT)
            self.pipeline_gui.controls.append(self)
            self.block_container.disabled = True
            self.block_container.ignore_interactions = True
            self.block_container.bgcolor = INVALID_COLOR
            self.block_container.visible = False
            self.block_container.tooltip = None
            self.click_gesture.disabled = True
            self.click_gesture.visible = False
            self.delete_button.visible = True
            if self.pipeline_gui.source_module != "":
                await self.toggle_detection()
                await self.pipeline_gui.check_for_valid_all_modules()
            self.pipeline_gui.update()

        if self.show_mode:
            self.block_container.tooltip = self.wrapped_description
            self.pipeline_gui.pipeline.event_manager.notify(DragAndDropEvent(False))

        self.update()
        await self.pipeline_gui.lines_gui.update_lines(self)

    async def generate_options_overlay(self):
        """
        Generates with the user attributes tagged with the prefix 'user_' a gui overlay.
        """
        user_attributes = self.module.get_user_attributes
        element_height = 60
        spacing = 10
        padding = 20
        height = element_height * len(user_attributes) + spacing * (len(user_attributes) - 1)
        limit_reached = len(user_attributes) > USER_OPTIONS_LIMIT
        if len(user_attributes) != 0:
            return ft.Card(content= ft.Container(
                            ft.ListView(
                                controls=self.create_attribute_list(user_attributes),
                                width=500,
                                spacing=spacing,
                                height=(element_height * (USER_OPTIONS_LIMIT + 1) + spacing * ((USER_OPTIONS_LIMIT + 1) - 1)) - 30 if limit_reached else height,
                            ), padding=padding)
            )

        else:
            return None

    def create_attribute_list(self, attributes=None):
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
            if typ == str:
                ref = ft.Ref[ft.Text]()
                setattr(self.module, "ref_" + attribute_name, ref)
                items.append(
                    ft.TextField(
                        label=attribute_name.removeprefix("user_"),
                        border_color=MAIN_COLOR,
                        value=str(value),
                        ref=ref,
                        on_blur=lambda e, attr_name=attribute_name, type_atr=typ:
                        self.pipeline_gui.page.run_task(self.on_change,e,
                                       attr_name,
                                       type_atr),
                        height=60,
                    )
                )
            elif typ == int:
                min_val, max_val = None, None

                limit = getattr(self.module, f"limit_{attribute_name}", None)
                if limit and isinstance(limit, Limit):
                    min_val = limit.min_val
                    max_val = limit.max_val

                if min_val is not None and min_val >= 0:
                    current_regex = FILTER_INT
                else:
                    current_regex = FILTER_INT_SIGNED

                ref = ft.Ref[ft.Text]()
                setattr(self.module, "ref_" + attribute_name, ref)
                items.append(
                    ft.TextField(
                        label=attribute_name.removeprefix("user_"),
                        border_color=MAIN_COLOR,
                        value=str(value),
                        ref=ref,
                        input_filter=ft.InputFilter(allow=True, regex_string=current_regex, replacement_string=""),
                        on_blur=lambda e, attr_name=attribute_name, type_atr=typ,mi=min_val, ma=max_val:
                        self.pipeline_gui.page.run_task(self.on_change,e,
                                       attr_name,
                                       type_atr,
                                       mi,
                                       ma),
                        height=60,
                    )
                )
            elif typ == float:
                min_val, max_val = None, None

                limit = getattr(self.module, f"limit_{attribute_name}", None)
                if limit and isinstance(limit, Limit):
                    min_val = limit.min_val
                    max_val = limit.max_val
                if min_val == 0.0 and max_val == 1.0:
                    current_regex = FILTER_FLOAT_0_TO_1
                elif min_val is not None and min_val >= 0.0:
                    current_regex = FILTER_SCIENTIFIC_FLOAT
                else:
                    current_regex = FILTER_SCIENTIFIC_FLOAT_SIGNED

                ref = ft.Ref[ft.Text]()
                setattr(self.module, "ref_" + attribute_name, ref)
                items.append(
                    ft.TextField(
                        label=attribute_name.removeprefix("user_"),
                        border_color=MAIN_COLOR,
                        value=str(value),
                        ref=ref,
                        input_filter=ft.InputFilter(allow=True, regex_string=current_regex, replacement_string=""),
                        on_blur=lambda e, attr_name=attribute_name, type_atr=typ, mi=min_val, ma=max_val:
                        self.pipeline_gui.page.run_task(self.on_change,e,
                                       attr_name,
                                       type_atr,
                                       mi,
                                       ma),
                        height=60,
                    )
                )
            elif typ == bool:
                text = ft.Text(attribute_name.removeprefix("user_"), weight=ft.FontWeight.BOLD)
                index = 0 if not value else 1
                on_change = getattr(self.module, "on_change_" + attribute_name, None)
                if on_change is None:
                    setattr(self.module, "on_change_" + attribute_name, lambda: None)
                slider_bool = ft.CupertinoSlidingSegmentedButton(
                    selected_index=index,
                    thumb_color=MAIN_COLOR,
                    on_change=lambda e, attr_name=attribute_name: self.pipeline_gui.page.run_task(self.update_bool,e, attr_name),
                    padding=ft.Padding.symmetric(vertical=0, horizontal=0),
                    controls=[
                        ft.Text("False"),
                        ft.Text("True")
                    ],
                )
                choosing = ft.Container(ft.Row([text, slider_bool],
                        wrap=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                        padding=ft.Padding(0, 10, 0, 10))
                items.append(choosing)
            elif typ == FilePath:
                text_field = ft.TextField(
                    label=attribute_name.removeprefix("user_"),
                    border_color=MAIN_COLOR,
                    value=format_directory_path(value.path, 50),
                    height=60,
                    read_only=True,
                    disabled=True,
                    expand=True
                )
                file_picker = ft.FilePicker()
                ref = ft.Ref[ft.Stack]()
                file_stack = ft.Stack(
                        [
                            text_field,
                            ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.UPLOAD_FILE,
                                    tooltip="Pick file",
                                    on_click=lambda a, attr_name=attribute_name,
                                                    content=text_field: self.pipeline_gui.page.run_task(
                                        self.on_select_file,
                                        a,
                                        file_picker,
                                        attr_name,
                                        content),
                                ), alignment=ft.Alignment.TOP_RIGHT, right=10, top=5)
                        ],ref = ref
                    )
                setattr(self.module, "ref_" + attribute_name, ref)
                items.append(
                        file_stack
                    )
            elif typ == DirectoryPath:
                text_field = ft.TextField(
                    label=attribute_name.removeprefix("user_"),
                    border_color=MAIN_COLOR,
                    value=format_directory_path(value.path, 50),
                    height=60,
                    read_only=True,
                    disabled=True,
                    expand=True
                )
                file_picker = ft.FilePicker()
                ref = ft.Ref[ft.Stack]()
                dir_stack = ft.Stack(
                        [
                            text_field,
                            ft.Container(
                                content=ft.IconButton(
                                    icon=ft.Icons.FOLDER_OPEN,
                                    tooltip="Choose directory",
                                    on_click=lambda a, attr_name=attribute_name,
                                                    content=text_field: self.pipeline_gui.page.run_task(
                                        self.on_select_dir, a,
                                        file_picker, attr_name,
                                        content),
                                ),
                                alignment=ft.Alignment.TOP_RIGHT, right=10, top=5
                            )
                        ],ref = ref
                    )
                setattr(self.module, "ref_" + attribute_name, ref)
                items.append(
                    dir_stack
                )
            elif type(typ) == enum.EnumType:  # An enumeration
                enum_class = typ
                enum_items = list(enum_class)
                text = ft.Text(attribute_name.removeprefix("user_"), weight=ft.FontWeight.BOLD)
                index = enum_items.index(value)
                on_change = getattr(self.module, "on_change_" + attribute_name,None)
                if on_change is None:
                    setattr(self.module, "on_change_" + attribute_name, lambda: None)

                total_chars = sum(len(val.name) for val in enum_items)
                if total_chars > MAX_TOTAL_CHARS_ENUM:
                    input_control = ft.Dropdown(
                        value=enum_items[index].name,
                        options=[ft.dropdown.Option(key=val.name, text=val.name) for val in enum_items],
                        on_select=lambda e, attr_name=attribute_name,
                                         e_class=enum_class: self.pipeline_gui.page.run_task(self.update_enum, e,
                                                                                             attr_name, e_class),
                        dense=True,
                        border_color = MAIN_COLOR,
                        width=250,
                    )
                else:
                    input_control = ft.CupertinoSlidingSegmentedButton(
                        selected_index=index,
                        thumb_color=MAIN_COLOR,
                        on_change=lambda e, attr_name=attribute_name,
                                         e_class=enum_class: self.pipeline_gui.page.run_task(self.update_enum, e,
                                                                                             attr_name, e_class),
                        padding=ft.Padding.symmetric(vertical=0, horizontal=0),
                        controls=[
                            ft.Text(enum_val.name) for enum_val in enum_class
                        ],
                    )

                choosing = ft.Container(
                    ft.Row(
                        [
                            text,
                            input_control
                        ],
                        wrap=True,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    padding=ft.Padding(0, 10, 0, 10)
                )
                items.append(choosing)
            else:
                raise ValueError(f"Unsupported 'user_' attribute file type: {typ}")
        return items

    async def on_select_file(self, e: ft.Event[ft.Button], file_picker, attr_name, text):
        """
        Handles if a file is selected.
        """
        suffix = getattr(self.module, attr_name).suffix
        files = await file_picker.pick_files(allow_multiple=False,
                                                 dialog_title=attr_name.removeprefix("user_"),
                                                 file_type=ft.FilePickerFileType.CUSTOM if suffix is not None else ft.FilePickerFileType.ANY,
                                                 allowed_extensions=suffix if suffix is not None else [], )
        if files is not None and len(files) > 0:
            current_file_path = getattr(self.module, attr_name)
            current_file_path.path = files[0].path
            text.value = format_directory_path(files[0].path, 50)
            text.update()
            self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    async def on_select_dir(self, e: ft.Event[ft.Button], file_picker, attr_name, text):
        """
        Handles if a directory is selected.
        """
        dir = await file_picker.get_directory_path(dialog_title=attr_name.removeprefix("user_"))
        if dir is not None:
            setattr(self.module, attr_name, FilePath(dir))
            text.value = format_directory_path(dir, 50)
            text.update()
            self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    async def on_change(self, e, attr_name, typ: type, min_value = None, max_value = None):
        """
        Handles changes to the attribute for different types.
        """
        attribute_name_without_prefix = attr_name.removeprefix("user_")
        val = e.control.value
        if val is None or val == "":
            self.pipeline_gui.page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"{attribute_name_without_prefix} must not be empty!",
                            color=ft.Colors.WHITE),
                    bgcolor=ERROR_COLOR))
            e.control.value = str(getattr(self.module, attr_name))
            e.control.update()
            return

        if typ is float:
            if val in (".", "-", "e", "E", "1e", "1e-", "-e"):
                self.pipeline_gui.page.show_dialog(
                    ft.SnackBar(
                        ft.Text(f"{attribute_name_without_prefix} contains an incomplete number!",
                                color=ft.Colors.WHITE),
                        bgcolor=ERROR_COLOR))
                e.control.value = str(getattr(self.module, attr_name))
                e.control.update()
                return

        try:
            casted_value = typ(val)
            if typ in (int, float):
                if min_value is not None and casted_value < min_value:
                    raise ValueError(
                        f"Value for {attribute_name_without_prefix} must be at least {min_value}!")
                if max_value is not None and casted_value > max_value:
                    raise ValueError(
                        f"Value for {attribute_name_without_prefix} cannot exceed {max_value}!")

            setattr(self.module, attr_name, typ(e.control.value))
            self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))
        except ValueError as err:
            error_msg = str(err) if "Value for" in str(err) else f"{attribute_name_without_prefix} only allows {typ.__name__}'s."
            self.pipeline_gui.page.show_dialog(ft.SnackBar(
                ft.Text(error_msg, color=ft.Colors.WHITE),
                bgcolor=ERROR_COLOR))
            e.control.value = str(getattr(self.module, attr_name))
            e.control.update()


    async def update_bool(self, e, attr_name):
        """
        Handels changes to the attribute for booleans.
        """
        if int(e.data) == 1:
            setattr(self.module, attr_name, True)
        else:
            setattr(self.module, attr_name, False)
        getattr(self.module, "on_change_" + attr_name)()
        self.module.settings.update()
        self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    async def update_enum(self, e, attr_name, enum_class):
        """
        Handles changes to the attribute for enumerations.
        """
        if isinstance(e.control, ft.CupertinoSlidingSegmentedButton):
            enum_val = list(enum_class)[int(e.data)]
        else:
            enum_val = enum_class[e.control.value]
        setattr(self.module, attr_name, enum_val)
        getattr(self.module, "on_change_" + attr_name)()
        self.module.settings.update()
        self.pipeline_gui.pipeline.event_manager.notify(OnPipelineChangeEvent("user_attr_change"))

    async def create_options(self):
        if self.module.settings is None:
            self.module._settings = await self.generate_options_overlay()

        if self.page_overlay is None:
            page = self.pipeline_gui._page
            self.page_overlay = PageOverlay(page, self.module.settings, self.close_options)
        self.module.settings_init()

    async def open_options(self, e):
        """
        Open options overlay of the module.
        """
        self.page_overlay.open()
        self.options_button.icon_color = ft.Colors.BLACK38
        self.options_button.update()

    async def close_options(self, e):
        """
        Called when the overlay gets dismissed.
        """
        self.page_overlay.close()
        self.module.on_settings_dismiss() if self.module.on_settings_dismiss is not None else None
        self.options_button.icon_color = ft.Colors.WHITE60
        self.options_button.update()

    async def copy_module(self):
        """
        Called when the copy button is clicked.
        """
        self.copy_button.icon_color = ft.Colors.BLACK38
        self.copy_button.update()
        copy_dict = self.to_dict()
        new_module = self.pipeline_gui.add_module(type(self.module), x=cast(float, self.left) + 20, y=cast(float, self.top) + 20,
                                     module_dict=copy_dict)
        await new_module.toggle_detection()
        await self.pipeline_gui.check_for_valid(new_module.module_id)
        self.copy_button.icon_color = ft.Colors.WHITE60
        self.copy_button.update()

    def to_dict(self):
        """
        Translates the module into a dictionary.
        """
        user_attributes: List[Dict[str, Any]] = []
        for attr_name in self.module.get_user_attributes:
            value = getattr(self.module, attr_name)
            value_type = type(value).__name__
            if isinstance(value, FilePath) or isinstance(value, DirectoryPath):
                value = value.path
            elif isinstance(value, enum.Enum):
                value = value.name
            user_attributes.append({"name": attr_name, "value": value, "attr_type": value_type})
        return {
            "module_id": self.module_id,
            "module_name": self.module.gui_config().name,
            "position": {"x": self.left, "y": self.top},
            "user_attributes": user_attributes,
        }

    def update_user_attr(self, module_dict: dict):
        """
        Update user_attributes with a module dict.
        """
        has_load_errors = False
        error_manager = ErrorManager()
        for attr in module_dict.get("user_attributes", []):
            user_attributes = self.module.get_user_attributes
            attr_name = attr["name"]
            if attr_name in user_attributes:
                current_value = getattr(self.module, attr_name)
                try:
                    if attr["attr_type"] == FilePath.__name__ or attr["attr_type"] == DirectoryPath.__name__:
                        current_value.path = attr["value"]
                    elif isinstance(current_value, enum.Enum):
                        enum_class = type(current_value)
                        setattr(self.module, attr_name, enum_class[attr["value"]])
                    else:
                        typ = type(current_value)
                        casted_value = typ(attr["value"])

                        if typ in (int, float):
                            limit = getattr(self.module, f"limit_{attr_name}", None)
                            if limit and isinstance(limit, Limit):
                                min_val = limit.min_val
                                max_val = limit.max_val

                                if min_val is not None and casted_value < min_val:
                                    raise ValueError(f"Loaded value for {attr_name} must be at least {min_val}!")
                                if max_val is not None and casted_value > max_val:
                                    raise ValueError(f"Loaded value for {attr_name} cannot exceed {max_val}!")

                        setattr(self.module, attr_name, casted_value)
                except ValueError as e:
                    has_load_errors = True
                    error_manager.log(e)

        if has_load_errors:
            error_manager.show(f"An error occurred during updating the user attributes of the module: {self.module.gui_config().name}")