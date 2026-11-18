from pathlib import Path

import flet as ft
import pandas as pd

from backend.expert_mode.module import Categories, InputPort, InputPorts, Module, ModuleGuiConfig


class TableViewer(Module):
    _gui_config = ModuleGuiConfig("Table Viewer", Categories.MANUAL, "View and export tables.")
    _port_names = ("table", "cytoplasm_table", "nuclei_table", "spot_table", "colocalization_table")
    _column_width = 180

    def __init__(self, module_id: str = None):
        super().__init__(module_id)
        self.inputs = InputPorts(*(InputPort(name, pd.DataFrame, opt=True, multi=True)
                                   for name in self._port_names))
        self._tables = []
        self._selected_columns = []
        self._sort_column = None
        self._sort_ascending = True
        self._selector = ft.Dropdown(label="Table", options=[], on_select=self._change_table, width=260)
        self._format = ft.Dropdown(label="Format", value="xlsx", width=120,
                                   options=[ft.dropdown.Option(x) for x in ("xlsx", "tsv", "csv", "json")])
        self._scope = ft.Dropdown(label="Export", value="view", width=170,
                                  options=[ft.dropdown.Option("view", "Current view"),
                                           ft.dropdown.Option("full", "Full table")])
        self._columns = ft.Row(scroll=ft.ScrollMode.AUTO)
        self._header = ft.Row(spacing=0)
        self._body = ft.ListView(expand=True, spacing=0)
        self._grid = ft.Column([self._header, self._body], width=self._column_width, spacing=0)
        self._message = ft.Text("Run the pipeline to view tables.")
        self._settings = ft.Column(
            [
                ft.Row([self._selector, self._format, self._scope,
                        ft.Button("Export", on_click=self._export)], wrap=True),
                ft.Text("Visible columns"), self._columns, self._message,
                ft.Row([self._grid], scroll=ft.ScrollMode.AUTO, expand=True,
                       vertical_alignment=ft.CrossAxisAlignment.STRETCH),
            ],
            expand=True, spacing=5
        )

    def run(self):
        self._tables = [(f"{name} {i + 1}", table)
                        for name in self._port_names
                        for i, table in enumerate(self.inputs[name].data)
                        if table is not None]
        self._selector.options = [ft.dropdown.Option(str(i), name)
                                  for i, (name, _) in enumerate(self._tables)]
        self._selector.value = "0" if self._tables else None
        self._reset_table()
        self._update()
        return bool(self._tables)

    def _update(self):
        try:
            self._settings.page
        except RuntimeError:
            return
        self._settings.update()

    def _current_table(self):
        return self._tables[int(self._selector.value)][1] if self._selector.value is not None else None

    def _reset_table(self):
        table = self._current_table()
        self._selected_columns = list(range(len(table.columns))) if table is not None else []
        self._sort_column = None
        self._sort_ascending = True
        self._columns.controls = [
            ft.Checkbox(label=str(name), value=True, on_change=lambda e, i=i: self._toggle_column(i, e.control.value))
            for i, name in enumerate(table.columns)
        ] if table is not None else []
        self._render()

    def _change_table(self, e):
        self._reset_table()
        self._update()

    def _toggle_column(self, index, visible):
        if visible:
            self._selected_columns.append(index)
            self._selected_columns.sort()
        else:
            self._selected_columns.remove(index)
        self._render()
        self._update()

    def _sort(self, index):
        self._sort_ascending = not self._sort_ascending if self._sort_column == index else True
        self._sort_column = index
        self._render()
        self._update()

    def _view(self):
        table = self._current_table()
        if self._sort_column is not None:
            values = table.iloc[:, self._sort_column].reset_index(drop=True)
            try:
                order = values.sort_values(ascending=self._sort_ascending, kind="stable").index
            except TypeError:
                order = values.astype("string").sort_values(ascending=self._sort_ascending, kind="stable").index
            table = table.iloc[order]
        return table.iloc[:, self._selected_columns]

    def _render(self):
        table = self._current_table()
        self._header.controls = []
        self._body.controls = []
        self._grid.width = max(1, len(self._selected_columns)) * self._column_width
        if table is None:
            self._message.value = "No tables available."
            return
        self._message.value = f"{len(table)} rows" if self._selected_columns else "Select at least one column."
        self._header.controls = [
            ft.Container(ft.TextButton(
                f"{table.columns[i]}{' ↑' if self._sort_ascending else ' ↓'}"
                if self._sort_column == i else str(table.columns[i]),
                on_click=lambda e, index=i: self._sort(index)), width=self._column_width)
            for i in self._selected_columns
        ]
        view = self._view()
        self._body.controls = [
            ft.Row([ft.Container(ft.Text(str(value), selectable=True), width=self._column_width, padding=5)
                    for value in row], spacing=0)
            for row in view.itertuples(index=False, name=None)
        ]

    async def _export(self, e):
        if self._current_table() is None:
            return
        extension = self._format.value
        path = await ft.FilePicker().save_file(dialog_title="Export table", file_name=f"table.{extension}",
                                               allowed_extensions=[extension], file_type=ft.FilePickerFileType.CUSTOM)
        if not path:
            return
        path = Path(path)
        if not path.suffix:
            path = path.with_suffix(f".{extension}")
        try:
            self._export_to(path, extension, self._scope.value)
            self._message.value = f"Exported to {path}"
        except Exception as exc:
            self._message.value = f"Export failed: {exc}"
        self._update()

    def _export_to(self, path, extension, scope):
        table = self._view() if scope == "view" else self._current_table()
        if extension == "xlsx":
            table.to_excel(path, index=False)
        elif extension in ("csv", "tsv"):
            table.to_csv(path, index=False, sep="\t" if extension == "tsv" else ",")
        elif extension == "json":
            table.to_json(path, orient="records", force_ascii=False)
        else:
            raise ValueError(f"Unsupported export format: {extension}")
