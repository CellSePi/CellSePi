import flet as ft

from frontend.gui_canvas import update_main_image


class GUIAutoImageTuning:
    def __init__(self, gui):
        self.gui = gui

    async def pressed(self):
        if self.gui.canvas.auto_adjust:
            self.gui.canvas.auto_adjust = False
            self.gui.csp.config.set_auto_button(False)
            self.gui.auto_brightness_contrast.icon_color = ft.Colors.GREY_700
            self.gui.auto_brightness_contrast.update()
            if self.gui.csp.image_id is not None:
                self.gui.brightness_slider.disabled = False
                self.gui.contrast_slider.disabled = False
                self.gui.brightness_slider.update()
                self.gui.contrast_slider.update()
            self.gui.brightness_icon.color = None
            self.gui.contrast_icon.color = None
            self.gui.brightness_icon.update()
            self.gui.contrast_icon.update()
            if self.gui.csp.image_id is not None:
                self.gui.page.run_task(self.gui.update_adjusted_image)
        else:
            self.gui.canvas.auto_adjust = True
            self.gui.csp.config.set_auto_button(True)
            self.gui.auto_brightness_contrast.icon_color = ft.Colors.ORANGE_700
            self.gui.auto_brightness_contrast.update()
            if self.gui.csp.image_id is not None:
                self.gui.brightness_slider.disabled = True
                self.gui.contrast_slider.disabled = True
                self.gui.brightness_slider.update()
                self.gui.contrast_slider.update()
            self.gui.brightness_icon.color = ft.Colors.GREY_700
            self.gui.contrast_icon.color = ft.Colors.GREY_700
            self.gui.brightness_icon.update()
            self.gui.contrast_icon.update()
            if self.gui.csp.image_id is not None:
                self.gui.page.run_task(update_main_image, self.gui.csp.image_id, self.gui.csp.channel_id, self.gui,
                                       False)
