import time

import flet as ft

def error_banner(gui,message):
    gui.page.show_dialog(ft.SnackBar(
        ft.Text(message)))
    gui.page.update()

def handle_image_switch_mask_on(gui):
    """
    loads the mask into the GUI if the switch is on
    Args:
        gui (GUI):the current GUI object

    """
    if gui.switch_mask.value:
        image = gui.csp.image_id
        bfc=gui.csp.config.get_bf_channel()

       #case: mask was created during segmentation
        if image in gui.csp.mask_paths and bfc in gui.csp.mask_paths[image]:
            #if the image to the bright-field channel was not generated before
            if image not in gui.mask.mask_outputs or bfc not in gui.mask.mask_outputs[image]:
                gui.mask.load_mask_into_canvas()

            #loads mask into container

            insert_mask(gui,image,bfc)
        else:
            #case off
            error_banner(gui,f"There is no mask for {gui.csp.image_id} with bright-field channel {bfc} generated ")
            gui.canvas.container_mask.visible = False
            gui.switch_mask.value=False
    else:
        gui.canvas.container_mask.visible = False

    gui.page.update()

def handle_mask_update(gui):
    """
    The method is executed if the mask was updated in the drawing window.
    Loads the updated mask in the flet canvas.

    Args:
        gui (GUI): the current GUI object
    """

    image= gui.csp.image_id
    bfc=gui.csp.config.get_bf_channel()

    if gui.switch_mask.value:
        gui.mask.load_mask_into_canvas()
        insert_mask(gui,image,bfc)
    else:
        return

def reset_mask(gui,image_id,bf_channel):
    if image_id in gui.mask.mask_outputs and bf_channel in gui.mask.mask_outputs[image_id]:
        del gui.mask.mask_outputs[image_id][bf_channel]


def insert_mask(gui, image,bfc):

    mask = gui.mask.mask_outputs[image][bfc]
    #in version 0.84: content is a control, need to set image instead of manual assignment to content.src_base64
    gui.canvas.container_mask.content= ft.Image(src=mask)
    gui.canvas.container_mask.visible = True
    gui.canvas.container_mask.update()
