import threading

from backend.images import BatchImageReadout
from backend.cellsepi import CellSePi
from backend.notifier import Notifier
from frontend.gui_fluorescence import error_banner,fluorescence_button

class Fluorescence(Notifier):
    """
    class handles the readout of fluorescence values

    Attributes:
        csp= current CellSePi object
        gui= current gui object
    """
    def __init__(self,csp: CellSePi,gui):
        super().__init__()
        self.csp= csp
        self.gui=gui


    def readout_fluorescence(self):
        """
        starts the readout of fluorescence and creates an Excel list if possible

        """

        if self.check_readout_possible():
            self._call_start_listeners(True)
            def on_update(progress,current_image):
                self._call_update_listeners(progress, current_image)

            def completed_readout(readout, readout_path):
                self.csp.readout= readout
                self.csp.readout_path=readout_path
                self.csp.readout_running=False
                if readout_path is not None:
                    self.gui.open_button.visible=True
                self.gui.page.run_task(self.gui.directory.check_masks)
                fluorescence_button.disabled = False
                if self.csp.model_path is not None:
                    self.gui.start_button.disabled =False
                self._call_completion_listeners()


            self.csp.readout_running=True
            self.gui.readout_event.clear()
            fluorescence_button.disabled=True

            brightfield_channel = self.csp.config.get_bf_channel()
            prefix = self.csp.current_channel_prefix
            working_directory = self.csp.working_directory

            #creates the readout image and fills the mask_path
            batch_image_readout = BatchImageReadout(image_paths=self.csp.image_paths,
                                                          mask_paths=self.csp.mask_paths,
                                                          segmentation_channel=brightfield_channel,
                                                          channel_prefix=prefix,
                                                          directory=working_directory)
            batch_image_readout.add_update_listener(listener=on_update)
            batch_image_readout.add_completion_listener(listener=completed_readout)

            target = batch_image_readout.run
            self.csp.readout_thread = threading.Thread(target=target)

            self._call_start_listeners(False)
            self.csp.readout_thread.start()


        else:
            self._call_start_listeners(False)
            return


    def check_readout_possible(self):
        """
         -error handling. All error that can possibly occur
         -creates a banner visible in the GUI if an error is important
        """

        if self.csp.readout_running:
            return False,
        if self.csp.readout_thread is not None and self.csp.readout_thread.is_alive():
            return False
        if self.csp.image_paths is None or len(self.csp.image_paths) ==0 :
            error_banner(self.gui, "No image to process")
            return False

        return True


