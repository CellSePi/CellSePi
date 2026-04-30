import asyncio
from pathlib import Path
from typing import cast

#from flet_extended_interactive_viewer import FletExtendedInteractiveViewer

from cellsepi.frontend.main_window.expert_mode.gui_pipeline import PipelineGUI
from cellsepi.frontend.main_window.expert_mode.expert_constants import *
from cellsepi.frontend.main_window.expert_mode.gui_pipeline_listener import PipelineChangeListener, ModuleExecutedListener, ModuleStartedListener, \
    ModuleProgressListener, ModuleErrorListener, DragAndDropListener, PipelinePauseListener, PipelineCancelListener, PipelineErrorListener
from cellsepi.frontend.main_window.expert_mode.pipeline_storage import PipelineStorage

def is_rendert(control):
    """
    Checks if a control is really render by checking the parents of the control.
    """
    if not control.visible:
        return False

    #checks iterative the parents if they are visible, because they effect if the child is rendert
    parent = control.parent
    while parent is not None:
        if not parent.visible:
            return False
        parent = parent.parent

    return True

class Builder:
    def __init__(self,page: ft.Page):
        self.page = page
        self.builder_page_stack = ft.Stack()
        self.pipeline_gui = PipelineGUI(self.page)
        self.pipeline_gui.interactive_view = None
        self.pipeline_running_event = None
        self.help_text =  ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Move Modules",
                        size=50,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_500
                    ),
                    ft.Row([
                        ft.Text(
                            "here",
                            size=40,
                            italic=True,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREY_400
                        ),
                        ft.Icon(ft.Icons.CROP_FREE,size=50,color=ft.Colors.GREY_400),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=2,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
            ,alignment=ft.Alignment.CENTER,
            width=self.page.width,
            height=self.page.height,
            animate_opacity= ft.Animation(duration=600, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
        )
        self.pipeline_storage = PipelineStorage(self.pipeline_gui)
        self.file_picker = ft.FilePicker()
        self.file_saver = ft.FilePicker()
        self.load_button = ft.IconButton(icon=ft.Icons.UPLOAD_FILE, on_click=self.click_load_file,
                                         icon_color=MAIN_ACTIVE_COLOR,
                                         style=ft.ButtonStyle(
                                             shape=ft.RoundedRectangleBorder(radius=12), ),
                                         tooltip="Load pipeline\n[Ctrl + L]", hover_color=ft.Colors.WHITE12)
        self.save_as_button = ft.IconButton(icon=ft.Icons.SAVE_AS_ROUNDED, on_click=self.click_save_as_file,
                                            icon_color=MAIN_ACTIVE_COLOR if len(self.pipeline_gui.modules) > 0 else ft.Colors.WHITE24, disabled=False if len(self.pipeline_gui.modules) > 0 else True,
                                            style=ft.ButtonStyle(
                                               shape=ft.RoundedRectangleBorder(radius=12), ),
                                            tooltip="Save as pipeline\n[Ctrl + Shift + S]", hover_color=ft.Colors.WHITE12)

        self.page.on_keyboard_event = lambda e: self.on_keyboard(e)
        self.save_button = ft.IconButton(icon=ft.Icons.SAVE_ROUNDED, on_click=lambda e: self.click_save_file(),
                                         icon_color=MAIN_ACTIVE_COLOR if self.pipeline_gui.pipeline_directory != "" else ft.Colors.WHITE24,
                                         disabled=False if self.pipeline_gui.pipeline_directory != "" else True,
                                         style=ft.ButtonStyle(
                                             shape=ft.RoundedRectangleBorder(radius=12), ),
                                         tooltip="Save pipeline\n[Ctrl + S]", hover_color=ft.Colors.WHITE12)
        self.run_menu_button = ft.IconButton(icon=ft.Icons.PLAY_ARROW, on_click=lambda e: self.run_menu_click(),
                                             icon_color=MAIN_ACTIVE_COLOR,
                                             style=ft.ButtonStyle(
                                             shape=ft.RoundedRectangleBorder(radius=12), ),
                                             tooltip="Show run menu\n[Ctrl + R]", hover_color=ft.Colors.WHITE12)
        self.delete_button = ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e: self.delete_button_click(), icon_color=MAIN_ACTIVE_COLOR,
                                           style=ft.ButtonStyle(
                                              shape=ft.RoundedRectangleBorder(radius=12),),
                                           tooltip="Show delete buttons\n[Ctrl + D]", hover_color=ft.Colors.WHITE12)
        self.port_button = ft.IconButton(icon=ft.Icons.VISIBILITY, on_click=lambda e: self.port_button_click(),
                                         icon_color=MAIN_ACTIVE_COLOR,
                                         style=ft.ButtonStyle(
                                               shape=ft.RoundedRectangleBorder(radius=12), ),
                                         tooltip="Show which ports get transferred\n[Ctrl + P]", hover_color=ft.Colors.WHITE12)

        self.left_tools = ft.Container(ft.Container(ft.Column(
                [
                    self.load_button, self.save_as_button,self.save_button,self.run_menu_button,self.delete_button,self.port_button
                ], tight=True,spacing=2
            ), bgcolor=MENU_COLOR, expand=True
            ),bgcolor=ft.Colors.TRANSPARENT,border_radius=ft.border_radius.all(10),
            bottom=BOTTOM_SPACING,left=SPACING_X,width=40,blur=10)


        self.start_button = ft.Button(  # button to start the pipeline
            content="Start",
            icon=ft.Icons.PLAY_CIRCLE,
            tooltip="Start the pipeline",
            disabled=False if len(self.pipeline_gui.modules) > 0 else True,
            on_click=lambda e:
                self.page.run_task(self.run),
            opacity=0.75,
        )

        self.resume_button = ft.Button(  # button to resume the pipeline
            content="Resume",
            tooltip="Resume the pipeline",
            icon=ft.Icons.PLAY_CIRCLE,
            visible=False,
            on_click=lambda e: self.pipeline_gui.pipeline.resume(),
            opacity=0.75
        )


        self.cancel_button = ft.Button(  # button to cancel the pipeline
            content="Cancel",
            tooltip="Cancel the pipeline",
            icon=ft.Icons.STOP_CIRCLE_ROUNDED,
            color=ft.Colors.RED,
            on_click=lambda e: self.cancel(),
            visible=False,
            opacity=0.75
        )
        self.progress_bar_module = ft.ProgressBar(value=0, width=220,bgcolor=ft.Colors.WHITE24,color=ft.Colors.BLUE_400)
        self.progress_pipeline = ft.ProgressRing(value=0,width=50,height=50,stroke_width=8,bgcolor=ft.Colors.WHITE24,color=ft.Colors.BLUE_400)
        self.progress_text = ft.Text(f"{self.pipeline_gui.pipeline.modules_executed}/{len(self.pipeline_gui.pipeline.modules)}", weight=ft.FontWeight.BOLD, tooltip="How many modules has been executed", color=MAIN_ACTIVE_COLOR)
        self.progress_stack = ft.Stack([self.progress_pipeline,ft.Container(self.progress_text,alignment=ft.Alignment.CENTER)],width=50,height=50,)
        self.progress_bar_module_text = ft.Text("0%", color=MAIN_ACTIVE_COLOR)
        self.progress_and_start = ft.Column([ft.Container(self.progress_stack,alignment=ft.Alignment.CENTER),
            ft.Container(
                content=ft.Stack([self.start_button, self.resume_button,self.cancel_button]),alignment=ft.Alignment.CENTER)],width=110,spacing=20
        )
        self.running_module = ft.Text("Module",color=ft.Colors.WHITE70,width=230,overflow=ft.TextOverflow.ELLIPSIS,max_lines=1,theme_style=ft.TextThemeStyle.HEADLINE_SMALL)
        self.info_text = ft.Text("Idle, waiting for start.", color=MAIN_ACTIVE_COLOR, width=250, overflow=ft.TextOverflow.ELLIPSIS, max_lines=2)
        self.category_icon = ft.Icon(ft.Icons.CATEGORY_ROUNDED,color=ft.Colors.GREEN)
        self.run_infos = ft.Column([ft.Row([self.category_icon,self.running_module]),self.info_text])
        self.left_run_menu = ft.Column([
            self.run_infos,ft.Row([ft.Container(self.progress_bar_module),self.progress_bar_module_text],width=260),
        ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.zoom_menu_button = ft.IconButton(icon=ft.Icons.SEARCH, on_click=lambda e: self.zoom_menu_click(),
                                              icon_color=MAIN_ACTIVE_COLOR,
                                              style=ft.ButtonStyle(
                                                 shape=ft.RoundedRectangleBorder(radius=12), ),
                                              tooltip="Show zoom menu\n[Ctrl + M]", hover_color=ft.Colors.WHITE12)

        self.right_tools = ft.Container(ft.Container(ft.Column(
            [
                self.zoom_menu_button,
            ], tight=True, spacing=2
        ), bgcolor=MENU_COLOR, expand=True
        ), bgcolor=ft.Colors.TRANSPARENT, border_radius=ft.border_radius.all(10),
            bottom=BOTTOM_SPACING, right=SPACING_X+10, width=40, blur=10)

        self.interactive_view = None
        self.zoom_menu = ft.Container(ft.Container(ft.Row(
            [
                ft.IconButton(icon=ft.Icons.ZOOM_IN, icon_color=MAIN_ACTIVE_COLOR,
                              style=ft.ButtonStyle(
                                                 shape=ft.RoundedRectangleBorder(radius=12), ), on_click=self.zoom_in, tooltip="Zoom in\n[Ctrl + .]", hover_color=ft.Colors.WHITE12),
                ft.IconButton(icon=ft.Icons.ZOOM_OUT, icon_color=MAIN_ACTIVE_COLOR,
                              style=ft.ButtonStyle(
                                                 shape=ft.RoundedRectangleBorder(radius=12), ), on_click=self.zoom_out, tooltip="Zoom out\n[Ctrl + ,]", hover_color=ft.Colors.WHITE12),
                ft.IconButton(icon=ft.Icons.CROP_FREE, icon_color=MAIN_ACTIVE_COLOR,
                              style=ft.ButtonStyle(
                               shape=ft.RoundedRectangleBorder(radius=12), ),
                              on_click=self.reset_view, tooltip="Reset view\n[Ctrl + -]", hover_color=ft.Colors.WHITE12),
            ], spacing=2
        ), bgcolor=MENU_COLOR, expand=True
        ), bgcolor=ft.Colors.TRANSPARENT, border_radius=ft.border_radius.all(10),
            bottom=BOTTOM_SPACING, right=cast(float, self.right_tools.right) + cast(float, self.right_tools.width) + 5, blur=10, opacity=0,
            animate_opacity=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
            animate=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
        )

        self.run_menu = ft.Container(ft.Container(ft.Row(
            [
                ft.Container(self.left_run_menu,padding=10),ft.VerticalDivider(), ft.Column([ft.Row([ft.Container(self.progress_and_start,padding=10)],alignment=ft.MainAxisAlignment.CENTER)],alignment=ft.MainAxisAlignment.CENTER),
            ], spacing=2
        ), bgcolor=MENU_COLOR, expand=True, padding=10
        ), bgcolor=ft.Colors.TRANSPARENT, border_radius=ft.border_radius.all(10),width=0,height=150,
            bottom=BOTTOM_SPACING, left=cast(float, self.left_tools.left) + cast(float, self.left_tools.width) + 5,blur=10,opacity=0,
            animate_opacity=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
            animate=ft.Animation(duration=300, curve=ft.AnimationCurve.LINEAR_TO_EASE_OUT),
            )
        self.setup()
        self.page_forward = ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT_SHARP, on_click=lambda e: self.press_page_forward(),
                                          icon_color=MAIN_ACTIVE_COLOR,
                                          style=ft.ButtonStyle(
                                         shape=ft.RoundedRectangleBorder(radius=12), ),
                                          tooltip="Get to the next page\n[Ctrl + E]", hover_color=ft.Colors.WHITE12)
        self.page_backward = ft.IconButton(icon=ft.Icons.CHEVRON_LEFT_SHARP, on_click=lambda e: self.press_page_backward(),
                                           icon_color=ft.Colors.WHITE24,
                                           style=ft.ButtonStyle(
                                           shape=ft.RoundedRectangleBorder(radius=12), ), disabled=True,
                                           tooltip="Return to the last page\n[Ctrl + Q]", hover_color=ft.Colors.WHITE12,)
        self.pipeline_gui.build_show_room(self.builder_page_stack)
        self.pipeline_gui.interactive_view = self.interactive_view
        self.switch_pages = ft.Container(ft.Container(ft.Row(
                    [
                        self.page_backward, self.page_forward,
                    ], tight=True,spacing=2
                ), bgcolor=MENU_COLOR, expand=True, height=40
                ), bgcolor=ft.Colors.TRANSPARENT, border_radius=ft.border_radius.all(10),
                    top=self.pipeline_gui.show_room_container.top + self.pipeline_gui.show_room_container.height + 5,
                    left=self.pipeline_gui.show_room_container.left,blur=10,visible=True if self.pipeline_gui.show_room_max_page_number > 1 else False)
        self.builder_page_stack.controls.insert(1, self.switch_pages)
        self.add_all_listeners()

    def cancel(self):
        """
        To cancel the pipeline after the currently executed module is finished.
        """
        if self.cancel_button.visible:
            self.running_module.value = f"Pipeline"
            self.running_module.update()
            self.category_icon.color = ft.Colors.RED
            self.category_icon.update()
            self.cancel_button.disabled = True
            self.cancel_button.color = None
            self.cancel_button.update()
            self.info_text.value = ""
            self.info_text.spans = [
                ft.TextSpan("Canceling: ", style=ft.TextStyle(weight=ft.FontWeight.BOLD, color=ft.Colors.RED)),
                ft.TextSpan("...", style=ft.TextStyle(color=ft.Colors.WHITE60)), ]
            self.info_text.update()
            self.page.update()

        self.pipeline_gui.pipeline.cancel()

    async def run(self,ignore_check=False):
        """
        To run the pipeline.

        Arguments:
            ignore_check (bool): if a warning should appear when you have not satisfied modules in the pipeline.
        """
        show_room_module_ids = [m.module_id for m in self.pipeline_gui.show_room_modules]
        if not ignore_check and not self.pipeline_gui.pipeline.check_pipeline_runnable(show_room_module_ids):
            def dismiss_dialog(e):
                cupertino_alert_dialog.open = False
                e.control.page.update()
                for mod in self.pipeline_gui.modules.values():
                    if not self.pipeline_gui.pipeline.check_module_satisfied(mod.module_id):
                        if not mod.show_ports:
                            mod.ports_in_out_clicked()
            def dismiss_dialog_ignore(e):
                cupertino_alert_dialog.open = False
                e.control.page.update()
                self.page.run_task(self.run,True)
            cupertino_alert_dialog = ft.CupertinoAlertDialog(
                title=ft.Text("Mandatory Input Warning"),
                content=ft.Text("Not all mandatory inputs are satisfied."),
                actions=[
                    ft.CupertinoDialogAction(
                        "Change modules",default=True, on_click=dismiss_dialog
                    ),
                    ft.CupertinoDialogAction(content="Skip modules", destructive=True, on_click=dismiss_dialog_ignore),
                ],
            )
            self.page.overlay.append(cupertino_alert_dialog)
            cupertino_alert_dialog.open = True
            self.page.update()
            return
        self.info_text.spans = []
        self.info_text.value = "Idle, waiting for start."
        self.info_text.update()
        self.start_button.visible = False
        self.start_button.update()
        self.cancel_button.visible = True
        self.cancel_button.update()
        self.load_button.disabled = True
        self.load_button.icon_color = ft.Colors.WHITE24
        self.load_button.update()
        for module in self.pipeline_gui.modules.values():
            self.pipeline_gui.lines_gui.update_delete_buttons(module,True)
            module.waiting_button.visible = True
            module.delete_button.visible = False
            module.waiting_button.update()
            module.delete_button.update()
            module.disable_tools()
            module.error_stack.visible = False
            module.error_stack.update()
            module.check_warning()
        self.update_modules_executed(reset=True)
        await asyncio.to_thread(self.pipeline_gui.pipeline.run,show_room_module_ids)
        if len(self.pipeline_gui.pipeline.modules) - len(ModuleType) * 2 != self.pipeline_gui.module_count or self.pipeline_gui.module_count != self.pipeline_gui.pipeline.modules_executed:
            self.update_modules_executed(reset=True)
        self.start_button.visible = True
        self.start_button.update()
        self.cancel_button.visible = False
        self.cancel_button.update()
        self.load_button.disabled = False
        self.load_button.icon_color = MAIN_ACTIVE_COLOR
        self.load_button.update()
        if self.pipeline_running_event is not None:
            self.pipeline_running_event.set()

    def add_all_listeners(self):
        """
        Adds all listeners to this pipeline.
        """
        pipeline_change_listener = PipelineChangeListener(self)
        self.pipeline_gui.pipeline.event_manager.subscribe(listener=pipeline_change_listener)
        module_executed_listener =ModuleExecutedListener(self)
        self.pipeline_gui.pipeline.event_manager.subscribe(listener=module_executed_listener)
        module_started_listener =ModuleStartedListener(self)
        self.pipeline_gui.pipeline.event_manager.subscribe(listener=module_started_listener)
        module_progress_listener =ModuleProgressListener(self)
        self.pipeline_gui.pipeline.event_manager.subscribe(listener=module_progress_listener)
        module_error_listener =ModuleErrorListener(self)
        self.pipeline_gui.pipeline.event_manager.subscribe(listener=module_error_listener)
        drag_and_drop_listener =DragAndDropListener(self)
        self.pipeline_gui.pipeline.event_manager.subscribe(listener=drag_and_drop_listener)
        pipeline_pause_listener =PipelinePauseListener(self)
        self.pipeline_gui.pipeline.event_manager.subscribe(listener=pipeline_pause_listener)
        pipeline_cancel_listener =PipelineCancelListener(self)
        self.pipeline_gui.pipeline.event_manager.subscribe(listener=pipeline_cancel_listener)
        pipeline_error_listener =PipelineErrorListener(self)
        self.pipeline_gui.pipeline.event_manager.subscribe(listener=pipeline_error_listener)

    def on_keyboard(self,e: ft.KeyboardEvent):
        """
        All Keyboard shortcuts of the ExpertMode.
        Only working when ExpertMode visible
        """
        if self.builder_page_stack is None or not is_rendert(self.builder_page_stack):
            return
        if e.shift and e.ctrl and e.key == "S" and not e.alt and not e.meta:
            if not self.save_as_button.disabled:
                asyncio.create_task(self.click_save_as_file())
        if e.ctrl and e.key == "S" and not e.alt and not e.shift and not e.meta:
            if not self.save_button.disabled:
                self.click_save_file()
        if e.ctrl and e.key == "L" and not e.alt and not e.shift and not e.meta:
            if not self.load_button.disabled:
                asyncio.create_task(self.click_load_file())
        if e.ctrl and e.key == "R" and not e.alt and not e.shift and not e.meta:
            self.run_menu_click()
        if e.ctrl and e.key == "D" and not e.alt and not e.shift and not e.meta:
            self.delete_button_click()
        if e.ctrl and e.key == "P" and not e.alt and not e.shift and not e.meta:
            self.port_button_click()
        if e.ctrl and e.key == "Q" and not e.alt and not e.shift and not e.meta:
            if not self.page_backward.disabled:
                self.press_page_backward()
        if e.ctrl and e.key == "E" and not e.alt and not e.shift and not e.meta:
            if not self.page_forward.disabled:
                self.press_page_forward()
        if e.ctrl and e.key == "M" and not e.alt and not e.shift and not e.meta:
            self.zoom_menu_click()
        if e.ctrl and e.key == "." and not e.alt and not e.shift and not e.meta:
            asyncio.create_task(self.interactive_view.zoom(1.0+ZOOM_VALUE))
        if e.ctrl and e.key == "," and not e.alt and not e.shift and not e.meta:
            asyncio.create_task(self.interactive_view.zoom(1.0-ZOOM_VALUE))
        if e.ctrl and e.key == "-" and not e.alt and not e.shift and not e.meta:
            asyncio.create_task(self.interactive_view.reset(400))

    def update_modules_executed(self,reset:bool=False):
        """
        Updates the gui of the run menu how many modules were executed.

        Arguments:
            reset (bool): To reset the pipeline modules executed to 0, because the pipeline changed.
        """
        if reset:
            self.pipeline_gui.pipeline.modules_executed = 0
        current =self.pipeline_gui.pipeline.modules_executed
        if not self.pipeline_gui.pipeline.running:
            total = len(self.pipeline_gui.pipeline.modules) - len(ModuleType) * 2
            self.progress_pipeline.value = (current / total) if total > 0 else 0
            self.pipeline_gui.module_count = total
            self.progress_text.value = f"{current}/{total}"
        else:
            self.progress_pipeline.value = (current / self.pipeline_gui.module_count) if self.pipeline_gui.module_count > 0 else 0
            self.progress_text.value = f"{current}/{self.pipeline_gui.module_count}"
        self.progress_text.update()
        self.page.update()

    async def zoom_in(self, e):
        await self.interactive_view.zoom(1.0 + ZOOM_VALUE)

    async def zoom_out(self, e):
        await self.interactive_view.zoom(1.0 - ZOOM_VALUE)

    async def reset_view(self, e):
        await self.interactive_view.reset(400)

    def click_save_file(self):
        """
        Called when clicked a file should be saved.
        """
        self.save_button.icon_color = ft.Colors.BLUE_400
        self.save_button.update()
        path = self.pipeline_storage.save_pipeline()
        self.pipeline_gui.page.show_dialog(
            ft.SnackBar(ft.Text(f"Pipeline saved at {path}", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN))
        self.pipeline_gui.page.update()

        self.page.title = f"CellSePi - {self.pipeline_gui.pipeline_name}"
        self.save_button.icon_color = ft.Colors.WHITE24
        self.save_button.disabled = True
        self.page.update()

    async def click_load_file(self, e: ft.Event[ft.Button]):
        """
        Handles if pipline file is selected.
        """
        files = await self.file_picker.pick_files(file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["csp"],
                                    allow_multiple=False)
        self.load_button.icon_color = ft.Colors.BLUE_400
        self.load_button.update()
        if files is not None and len(files) > 0:
            if not self.pipeline_storage.check_saved():
                def cancel_dialog(a):
                    cupertino_alert_dialog.open = False
                    a.control.page.update()

                def ok_dialog(a):
                    cupertino_alert_dialog.open = False
                    a.control.page.update()
                    if self.pipeline_gui.pipeline.running:
                        self.pipeline_gui.page.show_dialog(
                            ft.SnackBar(
                                ft.Text(f"Failed to load pipeline: a previous pipeline execution is still active!",
                                        color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.RED))
                        self.pipeline_gui.page.update()
                        return
                    try:
                        self.pipeline_storage.load_pipeline(files[0].path)
                        self.pipeline_gui.reset()
                        self.pipeline_gui.load_pipeline()
                    except Exception as exception2:
                        self.pipeline_gui.page.show_dialog(
                            ft.SnackBar(
                                ft.Text(f"Failed to load pipeline: {exception2}",
                                        color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.RED))
                        self.pipeline_gui.page.update()

                cupertino_alert_dialog = ft.CupertinoAlertDialog(
                    title=ft.Text("Unsaved Changes"),
                    content=ft.Text("Loading will discard any unsaved changes to the currently opened pipeline."),
                    actions=[
                        ft.CupertinoDialogAction(
                            "Cancel",default=True, on_click=cancel_dialog
                        ),
                        ft.CupertinoDialogAction(content="Ok", destructive=True, on_click=ok_dialog),
                    ],
                )
                self.page.overlay.append(cupertino_alert_dialog)
                cupertino_alert_dialog.open = True
                self.page.update()
                self.load_button.icon_color = MAIN_ACTIVE_COLOR
                self.load_button.update()
                return
            else:
                if self.pipeline_gui.pipeline.running:
                    self.pipeline_gui.page.show_dialog(
                        ft.SnackBar(ft.Text(f"Failed to load pipeline: a previous pipeline execution is still active!", color=ft.Colors.WHITE),
                                    bgcolor=ft.Colors.RED))
                    self.pipeline_gui.page.update()
                    return
                try:
                    self.pipeline_storage.load_pipeline(files[0].path)
                    self.pipeline_gui.reset()
                    self.pipeline_gui.load_pipeline()
                except Exception as exception1:
                    self.pipeline_gui.page.show_dialog(
                        ft.SnackBar(
                            ft.Text(f"Failed to load pipeline: {exception1}",
                                    color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.RED))
                    self.pipeline_gui.page.update()

        self.load_button.icon_color = MAIN_ACTIVE_COLOR
        self.load_button.update()

    async def click_save_as_file(self, e: ft.Event[ft.Button]):
        """
        Called to save a file is at a specific location.
        """
        dir = await self.file_saver.save_file(file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["csp"],
                             dialog_title="Save Pipeline", file_name=self.pipeline_gui.pipeline_name,
                             initial_directory=self.pipeline_gui.pipeline_directory)
        self.save_as_button.icon_color = ft.Colors.BLUE_400
        self.save_as_button.update()
        if dir is not None:
            if Path(dir).suffix == "":
                dir = dir + ".csp"
            if Path(dir).suffix != ".csp":
                self.pipeline_gui.page.show_dialog(ft.SnackBar(ft.Text(f"Pipeline name must have .csp suffix!",color=ft.Colors.WHITE),bgcolor=ft.Colors.RED))
                self.pipeline_gui.page.update()
                self.page.title = f"CellSePi - {self.pipeline_gui.pipeline_name}*"
                self.save_as_button.icon_color = MAIN_ACTIVE_COLOR
                self.page.update()
                return
            self.pipeline_storage.save_as_pipeline(dir)
            self.pipeline_gui.page.show_dialog(ft.SnackBar(ft.Text(f"Pipeline saved at {dir}",color=ft.Colors.WHITE),bgcolor=ft.Colors.GREEN))
            self.pipeline_gui.page.update()
            self.page.title = f"CellSePi - {self.pipeline_gui.pipeline_name}"
            self.save_button.icon_color = ft.Colors.WHITE24
            self.save_button.disabled = True
            self.page.update()

        self.save_as_button.icon_color = MAIN_ACTIVE_COLOR
        self.save_as_button.update()

    def press_page_forward(self):
        """
        Called when clicked to load the next page.
        """
        self.pipeline_gui.change_show_room_page(self.pipeline_gui.show_room_page_number + 1)
        if self.pipeline_gui.show_room_page_number > 0:
            self.page_backward.icon_color = MAIN_ACTIVE_COLOR
            self.page_backward.disabled = False
            self.page_backward.update()
        if self.pipeline_gui.show_room_page_number >= self.pipeline_gui.show_room_max_page_number-1:
            self.page_forward.icon_color = ft.Colors.WHITE24
            self.page_forward.disabled = True
            self.page_forward.update()

    def press_page_backward(self):
        """
        Called when clicked to load the previous page.
        """
        self.pipeline_gui.change_show_room_page(self.pipeline_gui.show_room_page_number - 1)
        if self.pipeline_gui.show_room_page_number == 0:
            self.page_backward.icon_color = ft.Colors.WHITE24
            self.page_backward.disabled = True
            self.page_backward.update()
        if self.pipeline_gui.show_room_page_number < self.pipeline_gui.show_room_max_page_number-1:
            self.page_forward.icon_color = MAIN_ACTIVE_COLOR
            self.page_forward.disabled = False
            self.page_forward.update()

    def run_menu_click(self):
        """
        Called when the run menu button got clicked.
        """
        if self.run_menu.opacity==1:
            self.run_menu_button.icon_color = MAIN_ACTIVE_COLOR
            self.run_menu_button.tooltip = f"Show run menu\n[Ctrl + R]"
            self.run_menu_button.update()
            self.run_menu.width = 0
            self.run_menu.opacity = 0
            self.run_menu.update()
        else:
            self.run_menu_button.icon_color = ft.Colors.BLUE_400
            self.run_menu_button.tooltip = f"Hide run menu\n[Ctrl + R]"
            self.run_menu_button.update()
            self.run_menu.width = 450
            self.run_menu.opacity = 1
            self.run_menu.update()

    def zoom_menu_click(self):
        """
        Called when the zoom menu button got clicked.
        """
        if self.zoom_menu.opacity==1:
            self.zoom_menu_button.icon_color = MAIN_ACTIVE_COLOR
            self.zoom_menu_button.tooltip = f"Show zoom menu\n[Ctrl + M]"
            self.zoom_menu_button.update()
            self.zoom_menu.width = 0
            self.zoom_menu.opacity = 0
            self.zoom_menu.update()
        else:
            self.zoom_menu_button.icon_color = ft.Colors.BLUE_400
            self.zoom_menu_button.tooltip = f"Hide zoom menu\n[Ctrl + M]"
            self.zoom_menu_button.update()
            self.zoom_menu.width = 122
            self.zoom_menu.opacity = 1
            self.zoom_menu.update()

    def delete_button_click(self):
        """
        Called when the delete button is clicked and toggles between all delete buttons be visible or be hidden.
        """
        if self.pipeline_gui.show_delete_button:
            self.delete_button.icon_color = MAIN_ACTIVE_COLOR
            self.delete_button.tooltip = f"Show delete buttons\n[Ctrl + D]"
            self.pipeline_gui.show_delete_button = False
            self.pipeline_gui.lines_gui.update_all()
        else:
            self.delete_button.icon_color = ft.Colors.BLUE_400
            self.delete_button.tooltip = f"Hide delete buttons\n[Ctrl + D]"
            self.pipeline_gui.show_delete_button = True
            if self.pipeline_gui.show_ports:
                self.port_button_click()
            self.pipeline_gui.lines_gui.update_all()

        self.delete_button.update()

    def port_button_click(self):
        """
        Called when the port button is clicked and toggles between all port text being visible or hidden.
        """
        if self.pipeline_gui.show_ports:
            self.port_button.icon_color = MAIN_ACTIVE_COLOR
            self.port_button.tooltip = f"Show which ports get transferred\n[Ctrl + P]"
            self.pipeline_gui.show_ports = False
            self.pipeline_gui.lines_gui.update_all()
        else:
            self.port_button.icon_color = ft.Colors.BLUE_400
            self.port_button.tooltip = f"Hide which ports get transferred\n[Ctrl + P]"
            self.pipeline_gui.show_ports = True
            if self.pipeline_gui.show_delete_button:
                self.delete_button_click()
            self.pipeline_gui.lines_gui.update_all()

        self.port_button.update()


    def setup(self):
        """
        Setup all the GUI elements.
        """
        canvas = ft.Stack([self.help_text,ft.Container(
            content=self.pipeline_gui,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bgcolor=ft.Colors.TRANSPARENT,
        )])

        self.interactive_view = ft.InteractiveViewer(content=canvas, constrained=False,
                                                              height=self.page.window.height,
                                                              width=self.page.window.width, scale_enabled=False,)

        def on_resize(e):
            """
            Called when the resize-event is triggered.
            Updates all relevant GUI elements.
            """
            self.interactive_view.height = self.page.window.height - 20
            self.interactive_view.width = self.page.window.width
            self.interactive_view.update()
            self.pipeline_gui.update_show_room()
            self.help_text.height = self.page.window.height
            self.help_text.width = self.page.window.width
            self.help_text.update()

        self.page.on_resize = on_resize

        self.builder_page_stack = ft.Stack([
                self.interactive_view,
                self.left_tools,
                self.right_tools,
                self.run_menu,
                self.zoom_menu,
             ]
            )
