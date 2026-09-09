from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import flet as ft

from modules.styles import ButtonVariant, button_style


@ft.component
def PaginatedTable(
    rows: Sequence[dict[str, Any]],
    columns: Sequence[tuple[str, str]],
    *,
    page_size: int = 10,
    searchable: bool = True,
    on_row_action: Callable[[dict[str, Any]], None] | None = None,
) -> ft.Control:
    """Tabela declarativa reutilizável com filtro textual e paginação."""
    query, set_query = ft.use_state("")
    current_page, set_current_page = ft.use_state(1)
    size, set_size = ft.use_state(page_size)
    normalized = query.casefold().strip()
    filtered = [
        row for row in rows
        if not normalized or normalized in " ".join(str(row.get(key, "")) for key, _ in columns).casefold()
    ]
    total_pages = max(1, (len(filtered) + size - 1) // size)
    current_page = min(current_page, total_pages)
    start = (current_page - 1) * size
    visible = filtered[start:start + size]

    def search(event: ft.ControlEvent) -> None:
        set_query(event.control.value or "")
        set_current_page(1)

    def change_size(event: ft.ControlEvent) -> None:
        set_size(int(event.control.value or page_size))
        set_current_page(1)

    def previous(_: ft.ControlEvent) -> None:
        set_current_page(max(1, current_page - 1))

    def next_page(_: ft.ControlEvent) -> None:
        set_current_page(min(total_pages, current_page + 1))

    table_rows: list[ft.DataRow] = []
    for row in visible:
        cells = [ft.DataCell(ft.Text(str(row.get(key, "—")))) for key, _ in columns]
        if on_row_action:
            cells.append(ft.DataCell(ft.IconButton(ft.Icons.MORE_HORIZ, tooltip="Ações", on_click=lambda _, item=row: on_row_action(item))))
        table_rows.append(ft.DataRow(cells))
    if not table_rows:
        table_rows.append(ft.DataRow([ft.DataCell(ft.Text("Nenhum registro encontrado"))] + [ft.DataCell(ft.Text("—")) for _ in range(len(columns) - 1 + int(bool(on_row_action)))]))

    header = []
    if searchable:
        header.append(ft.TextField(label="Pesquisar", prefix_icon=ft.Icons.SEARCH, dense=True, width=280, value=query, on_change=search))
    header.extend([
        ft.Container(expand=True),
        ft.Text(f"{len(filtered)} registro(s)", color=ft.Colors.ON_SURFACE_VARIANT),
        ft.Dropdown(label="Por página", dense=True, width=120, value=str(size), options=[ft.DropdownOption(str(value)) for value in (5, 10, 25, 50)], on_select=change_size),
    ])
    footer = ft.Row([
        ft.Text(f"Página {current_page} de {total_pages}", color=ft.Colors.ON_SURFACE_VARIANT),
        ft.Container(expand=True),
        ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Página anterior", disabled=current_page <= 1, on_click=previous),
        ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Próxima página", disabled=current_page >= total_pages, on_click=next_page),
    ])
    return ft.Column([ft.Row(header), ft.DataTable(columns=[ft.DataColumn(ft.Text(label)) for _, label in columns] + ([ft.DataColumn(ft.Text("Ações"))] if on_row_action else []), rows=table_rows, column_spacing=22), footer], spacing=12)
