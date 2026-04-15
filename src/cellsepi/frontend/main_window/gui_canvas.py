import asyncio

import flet as ft
import tifffile

from image_editing_view import ImageEditingView

async def update_main_image(img_id,channel_id,gui,on_click = True):
    #Method that handles what happens when the image is clicked or the main image need an update.
    if on_click:
        if gui.csp.image_id is not None and gui.csp.image_id in gui.directory.selected_images_visualise:
            if gui.csp.channel_id is not None and gui.csp.channel_id in gui.directory.selected_images_visualise[gui.csp.image_id]:
                gui.directory.selected_images_visualise[gui.csp.image_id][gui.csp.channel_id].visible = False
                gui.directory.selected_images_visualise[gui.csp.image_id][gui.csp.channel_id].update()
    gui.csp.image_id = img_id
    gui.csp.channel_id = channel_id
    gui.directory.selected_images_visualise[img_id][channel_id].visible = True
    gui.directory.selected_images_visualise[img_id][channel_id].update()
    if on_click:
        gui.contrast_slider.value = 1.0
        gui.brightness_slider.value = 1.0
        gui.canvas.brightness= 1.0
        gui.canvas.contrast= 1.0
    if not gui.canvas.auto_adjust:
        gui.contrast_slider.disabled = False
        gui.brightness_slider.disabled = False
    gui.contrast_slider.update()
    gui.brightness_slider.update()
    gui.canvas.select_image(img_id,channel_id,gui.csp.config.get_bf_channel(),on_click)