from typing import Union

import logging
import flet as ft
from flet import SnackBarAction

from backend.constants import APP_DIR, ERROR_COLOR
import os
import sys
import subprocess


class ErrorManager:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, page: ft.Page|None = None, log_filename: str = "app_errors.log"):
        if not hasattr(self, "page"):
            self.page = None

        if self._initialized:
            if page is not None:
                self.page = page
            return

        if page is not None:
            self.page = page

        self.log_dir = APP_DIR / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / log_filename

        self.logger = logging.getLogger("cellsepi")
        self.logger.setLevel(logging.ERROR)
        self.logger.propagate = False
        self.logger.handlers.clear()

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

        self._initialized = True

    def show(self,user_message: str):
        if self.page is not None:
            self.page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(user_message, color=ft.Colors.WHITE),
                    bgcolor=ERROR_COLOR,
                    action=SnackBarAction(text_color=ft.Colors.WHITE, label="Open log", on_click=self.open_log_file),
                )
            )
            self.page.update()

    def show_without_button(self,user_message: str):
        if self.page is not None:
            self.page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(user_message, color=ft.Colors.WHITE),
                    bgcolor=ERROR_COLOR,
                )
            )
            self.page.update()

    def log_and_show(self, user_message: str, ex: Union[Exception, str]):
        if self.page is None:
            self.log(ex)
            return

        if isinstance(ex, str):
            self.logger.error(f"User Message: {user_message}\n{ex}")
        else:
            self.logger.error(f"User Message: {user_message}", exc_info=ex)

        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(user_message, color=ft.Colors.WHITE),
                bgcolor=ERROR_COLOR,
                action=SnackBarAction(text_color=ft.Colors.WHITE,label="Open log",on_click=self.open_log_file),
            )
        )
        self.page.update()

    def log(self,ex: Union[Exception, str]):
        if isinstance(ex, str):
            self.logger.error(f"Error logged\n{ex}")
        else:
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