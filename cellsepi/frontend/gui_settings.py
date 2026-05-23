from enum import Enum
from typing import get_args

import flet as ft
from pydantic import BaseModel

from backend.settings import SettingsManager
from frontend.gui_page_overlay import PageOverlay


class GUISettings:

    def __init__(self, page, gui):
        self.page = page
        self.gui = gui
        self.settings_manager = SettingsManager()
        # self.settings = self.settings_manager.settings
        self.overlay = PageOverlay(
            page,
            content=None,
            modal=False
        )
        pass

    async def _save(self):
        await self.settings_manager.save_settings_async()
        self.overlay.close()

    async def _cancel(self):
        await self.settings_manager.load_settings_async()
        self.overlay.close()

    def build(self):
        self.overlay.content = ft.Stack(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Card(
                                    content=ft.Container(
                                        content=ft.Column(
                                            controls=[
                                                ft.Text("Settings", size=20, weight=ft.FontWeight.BOLD),
                                                ft.ListView(
                                                    controls=self.build_list_items(),
                                                    # height=self.calc_height(),
                                                    expand=True,
                                                    width=self.calc_width(),
                                                    spacing=10,
                                                    padding=10,
                                                ),
                                                ft.Row(
                                                    controls=[
                                                        ft.ElevatedButton(
                                                            "Cancel",
                                                            on_click=self._cancel
                                                        ),
                                                        ft.ElevatedButton(
                                                            "Save",
                                                            on_click=self._save
                                                        )
                                                    ],
                                                    alignment=ft.MainAxisAlignment.END,
                                                    width=self.calc_width(),
                                                    spacing=10
                                                ),
                                            ],
                                            # horizontal_alignment=ft.CrossAxisAlignment.STRETCH
                                        ),
                                        expand=True,
                                        padding=15
                                    ),
                                    height=self.calc_height()  # + 120
                                )
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER),
            ]
        )
        return self.overlay

    def calc_height(self):
        return self.gui.page.height - 200

    def calc_width(self):
        return self.calc_height() + 200

    def build_list_items(self) -> list[ft.Control]:
        """
        Revamped: Automatically inspects top-level configurations
        (e.g., 'cache', 'performance') and creates structural sections.
        """
        items = []
        # Iterate over top-level sub-models (e.g., cache: CacheConfig)
        for field_name, field_info in self.settings_manager.settings.model_fields.items():
            sub_model = getattr(self.settings_manager.settings, field_name)

            if isinstance(sub_model, BaseModel):
                # Create a visual card/section for each settings module
                section = ft.Container(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    field_name.upper(),
                                    weight=ft.FontWeight.BOLD,
                                    size=16
                                ),
                                ft.Divider(),
                                # Recursively generate form fields for this model
                                self._generate_fields_for_model(sub_model)
                            ]
                        ),
                        padding=15
                    )
                )
                items.append(section)
        return items

    def _generate_fields_for_model(self, model: BaseModel) -> ft.Control:
        """
        Recursively walks through a Pydantic model to construct UI elements.
        """
        controls = []

        for field_name, field_info in model.model_fields.items():
            value = getattr(model, field_name)

            # If the value is another nested Pydantic model, recurse down
            if isinstance(value, BaseModel):
                nested_section = ft.Column(
                    [
                        ft.Text(field_name.title(), weight=ft.FontWeight.W_600, size=14),
                        ft.Container(
                            content=self._generate_fields_for_model(value),
                            padding=ft.padding.only(left=15)  # Indent nested settings
                        )
                    ]
                )
                controls.append(nested_section)
                continue

            # Determine field metadata and type definitions
            field_type = field_info.annotation
            label_text = field_name.replace("_", " ").title()

            # Handle Choice Options (Pydantic Literal -> Flet Dropdown)
            if issubclass(field_type, Enum):
                control = ft.Row(
                    controls=[
                        ft.Text(
                            label_text,
                            weight=ft.FontWeight.W_600,
                            size=14
                        ),
                        ft.CupertinoSlidingSegmentedButton(
                            selected_index=list(field_type).index(value),
                            thumb_color=ft.Colors.BLUE_400,
                            on_change=
                            lambda e, m=model, f=field_name, t=field_type:
                            self._on_change_handler(e, m, f, target_type=t),
                            padding=ft.Padding.symmetric(vertical=0, horizontal=0),
                            controls=[
                                ft.Text(v.value)
                                for v in field_type
                            ],
                        ),
                        # ft.Dropdown(
                        #     label=label_text,
                        #     value=value.value,
                        #     options=[
                        #         ft.dropdown.Option(v.value)
                        #         for v in field_type
                        #     ],
                        #     on_select=lambda e, m=model, f=field_name, t=field_type:
                        #     self._on_change_handler(e, m, f, target_type=t)
                        # )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )

            # Handle Toggles (bool -> Flet Switch)
            elif field_type is bool:
                control = ft.Row(
                    controls=[
                        ft.Text(
                            label_text,
                            weight=ft.FontWeight.W_600,
                            size=14
                        ),
                        ft.Switch(
                            label=label_text,
                            value=bool(value),
                            on_change=lambda e, m=model, f=field_name: self._on_change_handler(e, m, f, bool)
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )

            # Handle Numeric Inputs (int/float -> Flet TextField with numeric filters)
            elif field_type in (int, float):
                control = ft.Row(
                    controls=[
                        ft.Text(
                            label_text,
                            weight=ft.FontWeight.W_600,
                            size=14
                        ),
                        ft.TextField(
                            label=label_text,
                            value=str(value),
                            input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9.]*$", replacement_string=""),
                            on_change=lambda e, m=model, f=field_name, t=field_type: self._on_change_handler(e, m, f, t)
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )

            # Handle General Text Inputs (str -> Flet TextField)
            else:
                control = ft.Row(
                    controls=[
                        ft.Text(
                            label_text,
                            weight=ft.FontWeight.W_600,
                            size=14
                        ),
                        ft.TextField(
                            label=label_text,
                            value=str(value),
                            on_change=lambda e, m=model, f=field_name: self._on_change_handler(e, m, f, str)
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )

            controls.append(control)

        return ft.Column(controls=controls, spacing=10)

    def _on_change_handler(self, e, model: BaseModel, field_name: str, target_type: type):
        """
        Event handler that extracts input UI data, safely casts it,
        and mutates the internal configuration object state.
        """
        print(e)
        try:
            # Extract input values safely based on control type
            raw_value = e.control.value if hasattr(e.control, "value") else e.data

            # Cast type back to match the configuration expectation safely
            if target_type is bool:
                casted_value = bool(raw_value)
            elif raw_value == "" or raw_value is None:
                return  # Avoid breaking validation loops mid-typing
            elif issubclass(target_type, Enum):
                casted_value = list(target_type)[int(raw_value)]
            else:
                casted_value = target_type(raw_value)

            # Update the setting attribute dynamically
            setattr(model, field_name, casted_value)

        except ValueError:
            pass  # Suppress temporary typing validation errors (e.g. trailing decimal points)
