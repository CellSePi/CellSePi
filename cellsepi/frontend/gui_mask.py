import flet as ft

def error_banner(gui,message):
    gui.page.show_dialog(ft.SnackBar(
        ft.Text(message)))
    gui.page.update()
