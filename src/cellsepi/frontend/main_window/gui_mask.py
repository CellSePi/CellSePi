import time

import flet as ft

def error_banner(gui,message):
    gui.page.show_dialog(ft.SnackBar(
        ft.Text(message)))
    gui.page.update()

def reset_mask(gui,image_id,bf_channel):
    if image_id in gui.mask.mask_outputs and bf_channel in gui.mask.mask_outputs[image_id]:
        del gui.mask.mask_outputs[image_id][bf_channel]

def insert_mask(gui, image,bfc):
    mask = gui.mask.mask_outputs[image][bfc]
    #in version 0.84: content is a control, need to set image instead of manual assignment to content.src_base64
    gui.canvas.container_mask.content= ft.Image(src=mask)
    gui.canvas.container_mask.visible = True
    gui.canvas.container_mask.update()
