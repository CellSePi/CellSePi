import math
import time
from threading import RLock

import flet as ft
from typing import List, Dict, Any, cast

import flet.canvas as cv

from cellsepi.frontend.main_window.expert_mode.expert_constants import MODULE_WIDTH, ARROW_PADDING, MODULE_HEIGHT, \
    ARROW_COLOR, ARROW_LENGTH, ARROW_ANGLE, VALID_COLOR, THROTTLE_UPDATE_LINES
from cellsepi.frontend.main_window.expert_mode.gui_module import ModuleGUI


def calc_angle(x1, y1, x2, y2):
    """
    Calculate the angle between two points in radiant.
    """
    delta_x = x2 - x1
    delta_y = y2 - y1
    return math.atan2(delta_y, delta_x)

def calc_line_points_outside_modules(source_x, source_y, target_x, target_y, padding: float = 0):
    """
    Calculate the points placed outside modules between two points with optional padding for the target side.
    """
    def rect_sides(x, y, target:bool=False):
        w = MODULE_WIDTH / 2 + (padding if target else 0)
        h = MODULE_HEIGHT / 2 + (padding if target else 0)
        return x - w, x + w, y - h, y + h

    def intersect_line_rect(x_1, y_1, x_2, y_2, x_min, x_max, y_min, y_max):
        dx = x_2 - x_1
        dy = y_2 - y_1
        points = []

        if dx != 0:
            t = (x_min - x_1) / dx
            y = y_1 + t * dy
            if y_min <= y <= y_max:
                points.append((x_min, y))

            t = (x_max - x_1) / dx
            y = y_1 + t * dy
            if y_min <= y <= y_max:
                points.append((x_max, y))

        if dy != 0:
            t = (y_min - y_1) / dy
            x = x_1 + t * dx
            if x_min <= x <= x_max:
                points.append((x, y_min))

            t = (y_max - y_1) / dy
            x = x_1 + t * dx
            if x_min <= x <= x_max:
                points.append((x, y_max))

        if not points:
            return 0, 0
        points.sort(key=lambda p: (p[0] - x_1) ** 2 + (p[1] - y_1) ** 2)
        return points[0]

    target_x_min, target_x_max, target_y_min, target_y_max = rect_sides(target_x, target_y, True)
    source_x_min, source_x_max, source_y_min, source_y_max = rect_sides(source_x, source_y, False)

    target_point = intersect_line_rect(source_x, source_y, target_x, target_y, target_x_min, target_x_max, target_y_min, target_y_max)
    source_point = intersect_line_rect(target_x, target_y, source_x, source_y, source_x_min, source_x_max, source_y_min, source_y_max)

    return target_point, source_point


def calc_middle_point(start_point_x,start_point_y,arrow_end_x, arrow_end_y):
    """
    Calculate the middle point between two points.
    """
    return (start_point_x+arrow_end_x)/2, (start_point_y + arrow_end_y)/2

class LinesGUI(cv.Canvas):
    def __init__(self, pipeline_gui):
        super().__init__()
        self.shapes = []
        self.connections: Dict[tuple[str, str],Dict[str, Any]] = {}
        self.pipeline_gui = pipeline_gui
        self.expand = True
        self._lock = RLock()
        self._last_update_per_module = {}

    def update_line(self,source_module_gui: ModuleGUI ,target_module_gui: ModuleGUI,ports: List[str]):
        """
        Adds a line between two modules or updates them if it already exists.
        """
        key = (source_module_gui.module_id, target_module_gui.module_id)

        if key in self.connections:
            del self.connections[key]

        source_x = cast(float, source_module_gui.left) + (MODULE_WIDTH / 2)
        source_y = cast(float, source_module_gui.top) + (MODULE_HEIGHT / 2)
        target_x = cast(float, target_module_gui.left) + (MODULE_WIDTH / 2)
        target_y = cast(float, target_module_gui.top) + (MODULE_HEIGHT / 2)
        edge = cv.Line(
            x1=source_x, y1=source_y,
            x2=target_x, y2=target_y,
            paint=ft.Paint(stroke_width=3, color=ARROW_COLOR)
        )
        edge_angle = calc_angle(source_x,source_y,target_x,target_y)

        (target_x_outside,target_y_outside),(source_x_outside,source_y_outside) = calc_line_points_outside_modules(
            source_x, source_y, target_x, target_y, padding=ARROW_PADDING)

        arrow_line_x1 = target_x_outside - ARROW_LENGTH * math.cos(edge_angle - ARROW_ANGLE)
        arrow_line_y1 = target_y_outside - ARROW_LENGTH * math.sin(edge_angle - ARROW_ANGLE)

        arrow_line_x2 = target_x_outside - ARROW_LENGTH * math.cos(edge_angle + ARROW_ANGLE)
        arrow_line_y2 = target_y_outside - ARROW_LENGTH * math.sin(edge_angle + ARROW_ANGLE)

        arrow_end_x = (arrow_line_x1 + arrow_line_x2)/2 #End is the Flat side of the Arrow
        arrow_end_y = (arrow_line_y1 + arrow_line_y2)/2
        port_x,port_y = calc_middle_point(source_x_outside, source_y_outside, arrow_end_x, arrow_end_y)

        arrow = cv.Path(
                [
                    cv.Path.MoveTo(target_x_outside,target_y_outside),
                    cv.Path.LineTo(arrow_line_x1,arrow_line_y1),
                    cv.Path.LineTo(arrow_line_x2, arrow_line_y2),
                    cv.Path.Close()
                ],
                paint=ft.Paint(
                    style=ft.PaintingStyle.FILL,color=ARROW_COLOR
                ),
            )

        port_str = ", ".join(ports)
        port_txt = None
        if self.pipeline_gui.show_ports:
            port_txt = cv.Text(
                port_x,port_y,
                str(port_str),max_width=220, style=ft.TextStyle(size=15,weight=ft.FontWeight.BOLD,bgcolor=ft.Colors.WHITE38),
                alignment=ft.Alignment.CENTER
            )

        def dummy():
            pass
        disabled = False
        opacity = 1
        if (source_module_gui.module_id in self.pipeline_gui.pipeline.run_order or target_module_gui.module_id in self.pipeline_gui.pipeline.run_order or source_module_gui.module_id == self.pipeline_gui.pipeline.executing or target_module_gui.module_id == self.pipeline_gui.pipeline.executing) and self.pipeline_gui.pipeline.running:
            disabled = True
            opacity = 0.4
        delete_button = ft.GestureDetector(top=port_y-20,left=port_x-20,on_hover=lambda e:dummy(),content=ft.IconButton(
            icon=ft.Icons.CLOSE,tooltip="Delete Connection",hover_color=VALID_COLOR,icon_color=ft.Colors.WHITE,bgcolor=ft.Colors.RED_ACCENT,opacity=opacity,on_click=lambda e,source=source_module_gui,target=target_module_gui:self.pipeline_gui.remove_connection(source,target)
            ),visible=self.pipeline_gui.show_delete_button,disabled=disabled)

        self.connections[key] = {
            "edge": edge,
            "arrow": arrow,
            "port_txt": port_txt,
            "delete_button": delete_button,
        }

    def update_delete_button(self,source_module_gui: ModuleGUI, target_module_gui: ModuleGUI,set_all: bool = False):
        """
        Checks and updates the delete button for the connection between the source module and the target module.
        """
        disabled = False
        opacity = 1
        if ((source_module_gui.module_id in self.pipeline_gui.pipeline.run_order or target_module_gui.module_id in self.pipeline_gui.pipeline.run_order or source_module_gui.module_id == self.pipeline_gui.pipeline.executing or target_module_gui.module_id == self.pipeline_gui.pipeline.executing) and self.pipeline_gui.pipeline.running) or set_all:
            disabled = True
            opacity = 0.4
        key = (source_module_gui.module_id,target_module_gui.module_id)
        if key in self.connections:
            delete_button = self.connections[key]["delete_button"]
            delete_button.content.opacity = opacity
            delete_button.content.disabled = disabled
            delete_button.content.update()

    def update_delete_buttons(self,module_gui: ModuleGUI,set_all: bool = False):
        """
        Updates all delete buttons that are connected to the given module.
        """
        for pipe in self.pipeline_gui.pipeline.pipes_in[module_gui.module.module_id]:
            self.update_delete_button(self.pipeline_gui.modules[pipe.source_module.module_id], module_gui,set_all)
        for pipe in self.pipeline_gui.pipeline.pipes_out[module_gui.module.module_id]:
            self.update_delete_button(module_gui, self.pipeline_gui.modules[pipe.target_module.module_id],set_all)

    def remove_line(self, source_module_gui: ModuleGUI, target_module_gui: ModuleGUI):
        """
        Removes a line between two modules.
        """
        key = (source_module_gui.module_id, target_module_gui.module_id)
        conn = self.connections.pop(key, None)
        if conn is not None:
            with self._lock:
                self.shapes.remove(conn["edge"])
                self.shapes.remove(conn["arrow"])
                self.shapes.remove(conn["port_txt"])
                self.pipeline_gui.delete_stack.controls.remove(conn["delete_button"])
                self.update()
                self.pipeline_gui.delete_stack.update()

    def _update_lines(self,module_gui: ModuleGUI):
        """
        Updates all lines that are connected to the given module.
        """
        for pipe in self.pipeline_gui.pipeline.pipes_in[module_gui.module_id]:
            self.update_line(self.pipeline_gui.modules[pipe.source_module.module_id],module_gui,pipe.ports)
        for pipe in self.pipeline_gui.pipeline.pipes_out[module_gui.module_id]:
            self.update_line(module_gui,self.pipeline_gui.modules[pipe.target_module.module_id],pipe.ports)

    def update_lines(self,module_gui: ModuleGUI):
        """
        Updates all lines connected to the given module,
        but only if enough time has passed since the last update
        (for throttling purposes to improve performance during drag/move).
        """
        now = time.time()
        last = self._last_update_per_module.get(module_gui.module_id, 0)
        if now - last > THROTTLE_UPDATE_LINES:
            self._last_update_per_module[module_gui.module_id] = now
            self._update_lines(module_gui)
            self.update_gui()

    def update_gui(self):
        """
        Updates the GUI to reflect the current connections.
        Uses a lock to ensure thread-safety while rebuilding the newest state.
        """
        with self._lock:
            self.shapes.clear()
            self.pipeline_gui.delete_stack.controls.clear()
            for key, data in self.connections.copy().items():
                self.shapes.append(data["edge"])
                self.shapes.append(data["arrow"])
                self.shapes.append(data["port_txt"])
                self.pipeline_gui.delete_stack.controls.append(data["delete_button"])
            self.update()
            self.pipeline_gui.delete_stack.update()

    def update_all(self):
        """
        Updates all connections for every module in the pipeline.
        """
        for module in self.pipeline_gui.modules.values():
            self._update_lines(module)
        self.update_gui()