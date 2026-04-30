import textwrap
from typing import Type
import flet as ft
from cellsepi.backend.main_window.expert_mode.listener import EventListener, OnPipelineChangeEvent, Event, \
    ModuleExecutedEvent, ProgressEvent, ErrorEvent, ModuleStartedEvent, DragAndDropEvent, PipelinePauseEvent, \
    PipelineCancelEvent, PipelineErrorEvent

class PipelineChangeListener(EventListener):
    """
    Gets notified when a OnPipelineChangeEvent is happening and updates all GUI elements related to the event.
    """
    def __init__(self,builder):
        self.event_type = OnPipelineChangeEvent
        self.builder = builder
    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def update(self, event: OnPipelineChangeEvent) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self.builder.page.run_task(self._update,event)

    async def _update(self, event: OnPipelineChangeEvent) -> None:
        if self.builder.pipeline_gui.loading:
            return
        if event.change_type == "user_attr_change":
            if len(self.builder.pipeline_gui.pipeline.modules)-len(self.builder.pipeline_gui.show_room_modules) > 0:
                if self.builder.pipeline_gui.pipeline_directory != "":
                    if self.builder.pipeline_storage.check_saved():
                        self.builder.page.title = f"CellSePi - {self.builder.pipeline_gui.pipeline_name}"
                        self.builder.save_button.icon_color = ft.Colors.WHITE24
                        self.builder.save_button.disabled = True
                        self.builder.page.update()
                    else:
                        self.builder.page.title = f"CellSePi - {self.builder.pipeline_gui.pipeline_name}*"
                        self.builder.save_button.icon_color = ft.Colors.WHITE60
                        self.builder.save_button.disabled = False
                        self.builder.page.update()
                else:
                    if self.builder.pipeline_storage.check_saved():
                        self.builder.page.title = f"CellSePi - {self.builder.pipeline_gui.pipeline_name}"
                        self.builder.page.update()
                    else:
                        self.builder.page.title = f"CellSePi - {self.builder.pipeline_gui.pipeline_name}*"
                        self.builder.page.update()
        else:
            if len(self.builder.pipeline_gui.pipeline.modules)-len(self.builder.pipeline_gui.show_room_modules) > 0:
                self.builder.help_text.opacity = 0
                self.builder.help_text.update()
                self.builder.save_as_button.icon_color = ft.Colors.WHITE60
                self.builder.save_as_button.disabled = False
                self.builder.save_as_button.update()
                if self.builder.pipeline_gui.pipeline_directory != "":
                    if self.builder.pipeline_storage.check_saved():
                        self.builder.page.title = f"CellSePi - {self.builder.pipeline_gui.pipeline_name}"
                        self.builder.save_button.icon_color = ft.Colors.WHITE24
                        self.builder.save_button.disabled = True
                        self.builder.page.update()
                    else:
                        self.builder.page.title = f"CellSePi - {self.builder.pipeline_gui.pipeline_name}*"
                        self.builder.save_button.icon_color = ft.Colors.WHITE60
                        self.builder.save_button.disabled = False
                        self.builder.page.update()
                else:
                    if self.builder.pipeline_storage.check_saved():
                        self.builder.page.title = f"CellSePi - {self.builder.pipeline_gui.pipeline_name}"
                        self.builder.page.update()
                    else:
                        self.builder.page.title = f"CellSePi - {self.builder.pipeline_gui.pipeline_name}*"
                        self.builder.page.update()


                if not self.builder.pipeline_gui.pipeline.running:
                    self.builder.start_button.disabled = False
                    self.builder.start_button.update()
            else:
                self.builder.help_text.opacity = 1
                self.builder.help_text.update()
                self.builder.save_as_button.icon_color = ft.Colors.WHITE24
                self.builder.save_as_button.disabled = True
                self.builder.save_button.icon_color = ft.Colors.WHITE24
                self.builder.save_button.disabled = True
                self.builder.start_button.disabled = True
                self.builder.page.title = f"CellSePi - {self.builder.pipeline_gui.pipeline_name}"
                self.builder.page.update()
        if self.builder.pipeline_gui.pipeline.running:
            self.builder.update_modules_executed()
        else:
            self.builder.update_modules_executed(reset=True)

class DragAndDropListener(EventListener):
    """
    Gets notified when a DragAndDropEvent is happening and updates all GUI elements related to the event.
    """
    def __init__(self,builder):
        self.event_type = DragAndDropEvent
        self.builder = builder
    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def update(self, event: DragAndDropEvent) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self.builder.page.run_task(self._update,event)

    async def _update(self, event: DragAndDropEvent) -> None:
        if len(self.builder.pipeline_gui.modules) == 0:
            if event.drag:
                self.builder.help_text.opacity = 0.60
                self.builder.help_text.update()
            else:
                self.builder.help_text.opacity = 1
                self.builder.help_text.update()

class ModuleExecutedListener(EventListener):
    """
    Gets notified when a ModuleExecutedEvent is happening and updates all GUI elements related to the event.
    """
    def __init__(self,builder):
        self.event_type = ModuleExecutedEvent
        self.builder = builder
    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def update(self, event: ModuleExecutedEvent) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self.builder.page.run_task(self._update,event)

    async def _update(self, event: ModuleExecutedEvent) -> None:
        self.builder.pipeline_gui.modules[event.module_id].enable_tools()
        if self.builder.pipeline_gui.source_module != "":
            self.builder.pipeline_gui.check_for_valid(event.module_id)
        self.builder.pipeline_gui.lines_gui.update_delete_buttons(self.builder.pipeline_gui.modules[event.module_id])
        self.builder.pipeline_gui.check_all_deletable()
        self.builder.pipeline_gui.modules[event.module_id].executing_button.visible = False
        self.builder.pipeline_gui.modules[event.module_id].waiting_button.visible = False
        self.builder.pipeline_gui.modules[event.module_id].executing_button.update()
        self.builder.pipeline_gui.modules[event.module_id].waiting_button.update()
        self.builder.update_modules_executed()


class ModuleStartedListener(EventListener):
    """
    Gets notified when a ModuleStartedEvent is happening and updates all GUI elements related to the event.
    """
    def __init__(self,builder):
        self.event_type = ModuleStartedEvent
        self.builder = builder

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def update(self, event: ModuleStartedEvent) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self.builder.page.run_task(self._update,event)

    async def _update(self, event: ModuleStartedEvent) -> None:
        self.builder.pipeline_gui.modules[event.module_id].set_running()
        self.builder.category_icon.color = self.builder.pipeline_gui.modules[event.module_id].module.gui_config().category.value
        self.builder.category_icon.update()
        self.builder.running_module.value = self.builder.pipeline_gui.modules[event.module_id].module.gui_config().name
        self.builder.running_module.update()

class PipelinePauseListener(EventListener):
    """
    Gets notified when a PipelinePauseEvent is happening and updates all GUI elements related to the event.
    """
    def __init__(self,builder):
        self.event_type = PipelinePauseEvent
        self.builder = builder
        self.last_info_text = ""
        self.last_info_spans = []
        self.last_running_module = ""

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def update(self, event: PipelinePauseEvent) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self.builder.page.run_task(self._update,event)

    async def _update(self, event: PipelinePauseEvent) -> None:
        if event.resume:
            self.builder.pipeline_gui.modules[event.module_id].disable_pause()
            self.builder.pipeline_gui.modules[event.module_id].paused_button.visible = False
            self.builder.pipeline_gui.modules[event.module_id].paused_button.update()
            self.builder.pipeline_gui.modules[event.module_id].executing_button.visible = True
            self.builder.pipeline_gui.modules[event.module_id].executing_button.update()
            self.builder.info_text.value = self.last_info_text
            self.builder.info_text.spans = self.last_info_spans
            self.builder.info_text.update()
            self.builder.running_module.value = self.last_running_module
            self.builder.running_module.update()
            self.builder.cancel_button.visible = True
            self.builder.cancel_button.update()
            self.builder.resume_button.visible = False
            self.builder.resume_button.update()
            return

        self.builder.pipeline_gui.modules[event.module_id].enable_pause()
        self.builder.pipeline_gui.modules[event.module_id].paused_button.visible = True
        self.builder.pipeline_gui.modules[event.module_id].paused_button.update()
        self.builder.pipeline_gui.modules[event.module_id].executing_button.visible = False
        self.builder.pipeline_gui.modules[event.module_id].executing_button.update()
        self.last_running_module = self.builder.running_module.value
        self.builder.running_module.value = f"Paused: {self.builder.running_module.value}"
        self.builder.running_module.update()
        self.last_info_text = self.builder.info_text.value
        self.last_info_spans = self.builder.info_text.spans.copy()
        self.builder.info_text.value = "Pipeline paused: press resume button to carry on"
        self.builder.info_text.spans = []
        self.builder.info_text.update()
        self.builder.resume_button.visible = True
        self.builder.resume_button.update()
        self.builder.cancel_button.visible = False
        self.builder.cancel_button.update()

class ModuleProgressListener(EventListener):
    """
    Gets notified when a ProgressEvent is happening and updates all GUI elements related to the event.
    """
    def __init__(self, builder):
        self.event_type = ProgressEvent
        self.builder = builder

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def update(self, event: ProgressEvent) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self.builder.page.run_task(self._update,event)

    async def _update(self, event: ProgressEvent) -> None:
        if self.builder.pipeline_gui.pipeline._cancel_event.is_set():
            self.builder.info_text.value = ""
            self.builder.info_text.spans = [
                ft.TextSpan("Canceling: ", style=ft.TextStyle(weight=ft.FontWeight.BOLD, color=ft.Colors.RED)),
                ft.TextSpan(event.process, style=ft.TextStyle(color=ft.Colors.WHITE60)), ]
            self.builder.info_text.update()
        else:
            self.builder.info_text.value = event.process
            self.builder.info_text.spans = []
            self.builder.info_text.update()
        self.builder.progress_bar_module.value = event.percent / 100
        self.builder.progress_bar_module.update()
        self.builder.progress_bar_module_text.value = f"{event.percent}%"
        self.builder.page.update()

class ModuleErrorListener(EventListener):
    """
    Gets notified when a ErrorEvent is happening and updates all GUI elements related to the event.
    """
    def __init__(self, builder):
        self.event_type = ErrorEvent
        self.builder = builder

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def update(self, event: ErrorEvent) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self.builder.page.run_task(self._update,event)

    async def _update(self, event: ErrorEvent) -> None:
            self.builder.cancel_button.visible = False
            self.builder.cancel_button.disabled = False
            self.builder.cancel_button.color = ft.Colors.RED
            self.builder.cancel_button.update()
            self.builder.pipeline_gui.modules[self.builder.pipeline_gui.pipeline.executing].error_stack.visible = True
            self.builder.pipeline_gui.modules[self.builder.pipeline_gui.pipeline.executing].error_stack.update()
            wrapped_text = "\n".join(textwrap.wrap(event.error_msg, width=30))
            self.builder.pipeline_gui.modules[self.builder.pipeline_gui.pipeline.executing].error_icon.tooltip = f"An error occurred while executing!\nError: {wrapped_text}"
            self.builder.pipeline_gui.modules[self.builder.pipeline_gui.pipeline.executing].error_icon.update()
            self.builder.pipeline_gui.modules[
                self.builder.pipeline_gui.pipeline.executing].module_container.border = ft.border.all(4,
                                                                                                      ft.Colors.RED)
            self.builder.pipeline_gui.modules[self.builder.pipeline_gui.pipeline.executing].module_container.update()
            self.builder.pipeline_gui.enables_all_stuck_in_running()
            self.builder.info_text.value = ""
            self.builder.info_text.spans = [
            ft.TextSpan("Error: ", style=ft.TextStyle(weight=ft.FontWeight.BOLD, color=ft.Colors.RED)),
            ft.TextSpan(event.error_msg, style=ft.TextStyle(color=ft.Colors.WHITE60)),]
            self.builder.info_text.update()
            self.builder.category_icon.color = ft.Colors.RED
            self.builder.category_icon.update()
            self.builder.progress_bar_module_text.value = f"{0}%"
            self.builder.progress_bar_module.value = 0
            self.builder.page.update()


class PipelineCancelListener(EventListener):
    """
    Gets notified when a PipelineCancelEvent is happening and updates all GUI elements related to the event.
    """
    def __init__(self, builder):
        self.event_type = PipelineCancelEvent
        self.builder = builder

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def update(self, event: PipelineCancelEvent) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self.builder.page.run_task(self._update,event)

    async def _update(self, event: PipelineCancelEvent) -> None:
        self.builder.info_text.spans = []
        self.builder.info_text.value = "Idle, waiting for start."
        self.builder.info_text.update()
        self.builder.pipeline_gui.enables_all_stuck_in_running()
        self.builder.running_module.value = "Module"
        self.builder.running_module.update()
        self.builder.category_icon.color = ft.Colors.GREEN
        self.builder.category_icon.update()
        self.builder.resume_button.visible = False
        self.builder.resume_button.update()
        self.builder.cancel_button.visible = True
        self.builder.cancel_button.disabled = False
        self.builder.cancel_button.color = ft.Colors.RED
        self.builder.cancel_button.update()
        self.builder.progress_bar_module_text.value = f"{0}%"
        self.builder.progress_bar_module.value = 0
        self.builder.page.update()

class PipelineErrorListener(EventListener):
    """
    Gets notified when a PipelineErrorEvent is happening and updates all GUI elements related to the event.
    """
    def __init__(self, builder):
        self.event_type = PipelineErrorEvent
        self.builder = builder

    def get_event_type(self) -> Type[Event]:
        return self.event_type

    def update(self, event: PipelineErrorEvent) -> None:
        if not isinstance(event, self.get_event_type()):
            raise TypeError("The given event is not the right event type!")
        self.builder.page.run_task(self._update,event)

    async def _update(self, event: PipelineErrorEvent) -> None:
        self.builder.info_text.value = ""
        self.builder.info_text.spans = [
            ft.TextSpan("Error: ", style=ft.TextStyle(weight=ft.FontWeight.BOLD, color=ft.Colors.RED)),
            ft.TextSpan(event.error_msg, style=ft.TextStyle(color=ft.Colors.WHITE60)), ]
        self.builder.info_text.update()
        self.builder.pipeline_gui.enables_all_stuck_in_running()
        self.builder.running_module.value = "Pipeline"
        self.builder.running_module.update()
        self.builder.category_icon.color = ft.Colors.RED
        self.builder.category_icon.update()
        self.builder.progress_bar_module_text.value = f"{0}%"
        self.builder.progress_bar_module.value = 0
        self.builder.page.update()
