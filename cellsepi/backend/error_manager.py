import logging
import flet as ft
from flet import SnackBarAction

from backend.constants import APP_DIR
import os
import sys
import subprocess


class ErrorManager:
    def __init__(self, page: ft.Page|None = None, log_filename: str = "app_errors.log"):
        self.page = page

        self.log_dir = APP_DIR / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / log_filename

        self.logger = logging.getLogger("cellsepi")
        self.logger.setLevel(logging.ERROR)

        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_path)
            formatter = logging.Formatter(
                '\n============================================================\n'
                '[%(asctime)s] %(levelname)s - %(name)s\n'
                '%(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log_and_show(self, user_message: str, ex: Exception):
        if self.page is None:
            self.log(ex)
            return

        self.logger.error(f"User Message: {user_message}", exc_info=ex)

        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(user_message, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED,
                action=SnackBarAction(text_color=ft.Colors.WHITE,label="Open logs",on_click=self.open_log_file),
            )
        )
        self.page.update()

    def log(self, ex: Exception):
        self.logger.error("Error logged", exc_info=ex)

    def open_log_file(self, e=None):
        path = str(self.log_path)
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
        except Exception as ex:
            pass