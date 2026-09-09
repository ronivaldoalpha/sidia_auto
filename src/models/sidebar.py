from __future__ import annotations

import flet as ft

from modules.styles import ButtonVariant, button_style


@ft.component
def Sidebar(page: ft.Page) -> ft.Control:
    def go(route: str):
        return lambda _: page.navigate(route)

    def item(label: str, icon: str, route: str) -> ft.Control:
        return ft.TextButton(
            content=ft.Row([ft.Icon(icon, size=20), ft.Text(label)], spacing=12),
            style=button_style(ButtonVariant.NEUTRAL),
            on_click=go(route),
        )

    return ft.Container(
        width=248,
        padding=20,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        content=ft.Column([
            ft.Container(padding=ft.Padding.only(left=4, top=4, bottom=28), content=ft.Row([
                ft.Icon(ft.Icons.HUB_OUTLINED, color=ft.Colors.PRIMARY, size=30),
                ft.Text("Manolo", size=20, weight=ft.FontWeight.BOLD),
            ], spacing=10)),
            ft.Text("OPERAÇÃO", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
            item("Visão geral", ft.Icons.DASHBOARD_OUTLINED, "/"),
            item("Vínculos", ft.Icons.LINK_OUTLINED, "/bindings"),
            ft.Divider(height=20),
            ft.Text("CONFIGURAÇÃO", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
            item("Serviços", ft.Icons.DNS_OUTLINED, "/services"),
            ft.Container(expand=True),
            ft.Text("Vault Site • Digifort", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text("Powerred By AlphaFormat", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
        ], spacing=8),
    )
