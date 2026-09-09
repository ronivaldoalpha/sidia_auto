from __future__ import annotations

import flet as ft


@ft.component
def PageLayout(*, sidebar: ft.Control, interface: ft.Control, title: str, page: ft.Page) -> ft.Control:
    def toggle_theme(_: ft.ControlEvent) -> None:
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode != ft.ThemeMode.DARK else ft.ThemeMode.LIGHT
        page.update()

    return ft.Row(expand=True, spacing=0, controls=[
        sidebar,
        ft.VerticalDivider(width=1),
        ft.Container(expand=True, padding=ft.Padding.only(left=28, right=28, top=20, bottom=20), content=ft.Column(expand=True, spacing=20, controls=[
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                ft.Row([ft.IconButton(ft.Icons.REFRESH, tooltip="Atualizar"), ft.IconButton(ft.Icons.DARK_MODE_OUTLINED, tooltip="Alternar tema", on_click=toggle_theme), ft.IconButton(ft.Icons.NOTIFICATIONS_NONE_OUTLINED, tooltip="Notificações"), ft.CircleAvatar(content=ft.Text("A"), bgcolor=ft.Colors.PRIMARY_CONTAINER, color=ft.Colors.ON_PRIMARY_CONTAINER)], spacing=4),
            ]),
            ft.Divider(height=1),
            ft.Container(expand=True, content=interface),
        ])),
    ])
