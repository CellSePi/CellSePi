from cellsepi.backend.main_window.images import BatchImageSegmentation
from cellsepi.backend.main_window.notifier import Notifier


class Segmentation(Notifier):
    """
    This class handles connection of GUISegmentation and BatchImageSegmentation.
    """
    def __init__(self, gui_seg, gui):
        super().__init__()
        self.gui = gui
        self.gui_seg = gui_seg
        self.device = "cpu"
        self.batch_image_segmentation = BatchImageSegmentation(self, self.gui, self.device)
        self.batch_image_segmentation.add_start_listener(listener=self.start)
        self.batch_image_segmentation.add_update_listener(listener=self.update)
        self.batch_image_segmentation.add_completion_listener(listener=self.finished)

    # methods, that communicate a change in the state of the segmentation between GUISegmentation and BatchImageSegmentation
    def to_be_cancelled(self):
        self.batch_image_segmentation.cancel_action()
        self.gui.csp.segmentation_running = False

    def to_be_paused(self):
        self.batch_image_segmentation.pause_action()
        self.gui.csp.segmentation_running = False

    def to_be_resumed(self):
        self.batch_image_segmentation.resume_action()
        self.gui.csp.segmentation_running = True

    def is_resuming(self):
        self._call_resume_listeners()

    def finished(self):
        self._call_completion_listeners()

    def update(self, progress, current_image):

        self._call_update_listeners(progress, current_image)

    async def _call_update_listeners_safe(self, progress, current_image):
        self._call_update_listeners(progress, current_image)


    def start(self):
        current_percentage = round(self.batch_image_segmentation.num_seg_images / len(self.gui.csp.image_paths) * 100)
        self._call_update_listeners(str(current_percentage) + " %", None)

    def run(self):
        """
        This method starts the segmentation process and manages the different interactions.
        """
        if not self.gui_seg.segmentation_cancelling and not self.gui_seg.segmentation_pausing and not self.gui_seg.segmentation_resuming:
            self._call_update_listeners("Preparing segmentation", None)

        if self.gui.csp.segmentation_running and not self.gui_seg.segmentation_resuming:
            self._call_completion_listeners()
            return

        self.gui.csp.segmentation_running = True

        self.batch_image_segmentation.run()
        self.gui.csp.segmentation_running = False
        if self.gui_seg.segmentation_cancelling:
            self._call_cancel_listeners()
            return
        elif self.gui_seg.segmentation_pausing:
            self._call_pause_listeners()
            return
        else:
            self._call_completion_listeners()



