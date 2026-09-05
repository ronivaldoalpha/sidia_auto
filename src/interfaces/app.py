from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

import flet as ft

from modules.styles import ButtonVariant, button_style, card_container_style, menu_button_style
from services.application import ApplicationService, DigifortConfig, ServiceHealth
from modules.theme import toggle_theme


class AppShell:
    """Shell responsivo sem AppBar: sidebar fixa e toolbar superior contextual."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.service = ApplicationService()
        self.page_content = ft.Container(expand=True)
        self.title = ft.Text("Visão geral", size=24, weight=ft.FontWeight.BOLD)
        self.status_text = ft.Text("Preparando serviços...", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._active_view = "dashboard"
        self._build()

    def _build(self) -> None:
        self.page.on_disconnect = lambda _: self.service.close()
        self.page.add(
            ft.Row(
                expand=True,
                spacing=0,
                controls=[self._sidebar(), ft.VerticalDivider(width=1), self._workspace()],
            )
        )
        self.show("dashboard")

    def _sidebar(self) -> ft.Control:
        def nav(label: str, icon: str, view: str) -> ft.Control:
            return ft.TextButton(
                content=ft.Row([ft.Icon(icon, size=20), ft.Text(label)], spacing=12),
                style=ft.ButtonStyle(
                    color={ft.ControlState.DEFAULT: ft.Colors.ON_SURFACE, ft.ControlState.HOVERED: ft.Colors.PRIMARY},
                    bgcolor={ft.ControlState.HOVERED: "#147D79EF"},
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
                on_click=lambda _: self.show(view),
            )

        return ft.Container(
            width=248,
            padding=20,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Container(
                        padding=ft.Padding.only(left=4, top=4, bottom=28),
                        content=ft.Row([ft.Icon(ft.Icons.HUB_OUTLINED, color=ft.Colors.PRIMARY, size=30), ft.Text("VAULT", size=20, weight=ft.FontWeight.BOLD)], spacing=10),
                    ),
                    ft.Text("OPERAÇÃO", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                    nav("Visão geral", ft.Icons.DASHBOARD_OUTLINED, "dashboard"),
                    nav("Vínculos", ft.Icons.LINK_OUTLINED, "bindings"),
                    ft.Divider(height=20),
                    ft.Text("CONFIGURAÇÃO", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                    nav("Serviços", ft.Icons.DNS_OUTLINED, "services"),
                    nav("Preferências", ft.Icons.SETTINGS_OUTLINED, "settings"),
                    ft.Container(expand=True),
                    ft.Text("Vault Site • Digifort", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
            ),
        )

    def _workspace(self) -> ft.Control:
        return ft.Container(
            expand=True,
            padding=ft.Padding.only(left=28, right=28, top=20, bottom=20),
            content=ft.Column(
                expand=True,
                spacing=20,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column([self.title, self.status_text], spacing=3),
                            ft.Row(
                                controls=[
                                    ft.IconButton(ft.Icons.REFRESH, tooltip="Atualizar dados", on_click=lambda _: self.refresh()),
                                    ft.IconButton(ft.Icons.DARK_MODE_OUTLINED, tooltip="Alternar tema", on_click=lambda _: self._theme()),
                                    ft.IconButton(ft.Icons.NOTIFICATIONS_NONE_OUTLINED, tooltip="Notificações"),
                                    ft.CircleAvatar(content=ft.Text("A"), bgcolor=ft.Colors.PRIMARY_CONTAINER, color=ft.Colors.ON_PRIMARY_CONTAINER),
                                ],
                            ),
                        ],
                    ),
                    ft.Divider(height=1),
                    self.page_content,
                ],
            ),
        )

    def _theme(self) -> None:
        toggle_theme(self.page)

    def show(self, view: str) -> None:
        self._active_view = view
        labels = {"dashboard": "Visão geral", "bindings": "Vínculos porta–câmera", "services": "Serviços e conexões", "settings": "Preferências"}
        self.title.value = labels[view]
        builders: dict[str, Callable[[], ft.Control]] = {
            "dashboard": self.dashboard,
            "bindings": self.bindings,
            "services": self.services,
            "settings": self.settings,
        }
        self.page_content.content = builders[view]()
        self.page.update()

    def refresh(self) -> None:
        self.status_text.value = "Atualizando..."
        self.page.update()
        self.service.check_all()
        self.status_text.value = f"Última atualização: {datetime.now():%d/%m/%Y %H:%M:%S}"
        self.show(self._active_view)

    def _card(self, content: ft.Control, *, accent: str | None = None) -> ft.Control:
        return ft.Container(**card_container_style(accent=accent), padding=20, content=content)

    def _metric(self, label: str, value: str, icon: str, color: str) -> ft.Control:
        return self._card(ft.Row([ft.Icon(icon, color=color, size=28), ft.Column([ft.Text(label, color=ft.Colors.ON_SURFACE_VARIANT), ft.Text(value, size=26, weight=ft.FontWeight.BOLD)], spacing=3)], spacing=14), accent=color)

    def dashboard(self) -> ft.Control:
        metrics = self.service.metrics()
        accuracy = metrics.get("taxa_acuracidade", 0.0)
        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=18,
            controls=[
                ft.Text("Saúde da integração", color=ft.Colors.ON_SURFACE_VARIANT),
                ft.ResponsiveRow(
                    columns=12,
                    spacing=14,
                    controls=[
                        ft.Container(col=3, content=self._metric("Acuracidade geral", f"{accuracy:.1f}%", ft.Icons.TRENDING_UP, ft.Colors.PRIMARY)),
                        ft.Container(col=3, content=self._metric("Eventos analisados", str(metrics.get("total_eventos", 0)), ft.Icons.INSIGHTS_OUTLINED, ft.Colors.TERTIARY)),
                        ft.Container(col=3, content=self._metric("Falhas no período", str(metrics.get("falhas", 0)), ft.Icons.WARNING_AMBER_OUTLINED, ft.Colors.ERROR)),
                        ft.Container(col=3, content=self._metric("Digifort ativos", str(sum(1 for x in self.service.state.digifort if x.enabled)), ft.Icons.DNS_OUTLINED, ft.Colors.SECONDARY)),
                    ],
                ),
                ft.ResponsiveRow(
                    columns=12,
                    spacing=16,
                    controls=[
                        ft.Container(col=7, content=self._failure_trend(metrics)),
                        ft.Container(col=5, content=self._health_panel()),
                    ],
                ),
                self._server_accuracy(metrics),
            ],
        )

    def _failure_trend(self, metrics: dict) -> ft.Control:
        rows = [ft.DataRow([ft.DataCell(ft.Text(day)), ft.DataCell(ft.Text(str(count))), ft.DataCell(ft.ProgressBar(value=min(count / 10, 1), color=ft.Colors.ERROR))]) for day, count in metrics.get("falhas_por_dia", {}).items()]
        if not rows:
            rows = [ft.DataRow([ft.DataCell(ft.Text("Sem dados no período")), ft.DataCell(ft.Text("0")), ft.DataCell(ft.ProgressBar(value=0))])]
        return self._card(ft.Column([ft.Text("Tendência de falhas diárias", size=17, weight=ft.FontWeight.BOLD), ft.DataTable(columns=[ft.DataColumn(ft.Text("Dia")), ft.DataColumn(ft.Text("Falhas")), ft.DataColumn(ft.Text("Intensidade"))], rows=rows, column_spacing=24)], spacing=14), accent=ft.Colors.ERROR)

    def _health_panel(self) -> ft.Control:
        health = list(self.service.state.health.values())
        if not health:
            health = [ServiceHealth("Serviços", "system", None, "Clique em atualizar para verificar")]
        items = []
        for item in health:
            color = ft.Colors.SECONDARY if item.online else ft.Colors.ERROR if item.online is False else ft.Colors.OUTLINE
            items.append(ft.ListTile(leading=ft.Icon(ft.Icons.CIRCLE, color=color, size=12), title=ft.Text(item.name), subtitle=ft.Text(item.label), tooltip=item.detail))
        return self._card(ft.Column([ft.Text("Status dos serviços", size=17, weight=ft.FontWeight.BOLD), *items], spacing=4), accent=ft.Colors.SECONDARY)

    def _server_accuracy(self, metrics: dict) -> ft.Control:
        rows = []
        for config in self.service.state.digifort:
            health = self.service.state.health.get(config.name)
            rows.append(ft.DataRow([ft.DataCell(ft.Text(config.name)), ft.DataCell(ft.Text(config.hostname)), ft.DataCell(ft.Text(health.label if health else "NÃO VERIFICADO")), ft.DataCell(ft.Text("—"))]))
        return self._card(ft.Column([ft.Text("Acuracidade por servidor Digifort", size=17, weight=ft.FontWeight.BOLD), ft.DataTable(columns=[ft.DataColumn(ft.Text("Servidor")), ft.DataColumn(ft.Text("Host")), ft.DataColumn(ft.Text("Status")), ft.DataColumn(ft.Text("Acuracidade"))], rows=rows or [ft.DataRow([ft.DataCell(ft.Text("Nenhum servidor cadastrado")), ft.DataCell(ft.Text("—")), ft.DataCell(ft.Text("—")), ft.DataCell(ft.Text("—"))])])], spacing=14))

    def bindings(self) -> ft.Control:
        rows = self.service.controller_tags()
        table_rows = []
        cameras = self.service.cameras()
        for item in rows:
            tag = item["TagName"]
            camera_field = ft.Dropdown(label="Câmera", dense=True, expand=True, options=[ft.dropdown.Option(c) for c in cameras], hint_text="Pesquise ou selecione")
            server_field = ft.Dropdown(label="Servidor", dense=True, options=[ft.dropdown.Option(s.name, key=s.name) for s in self.service.state.digifort], hint_text="Servidor da câmera")
            event_field = ft.Dropdown(label="Evento de alerta", dense=True, options=[ft.dropdown.Option(e) for e in self.service.event_types], width=180)
            alert = ft.Switch(label="Alerta", value=False)
            table_rows.append(ft.DataRow([ft.DataCell(ft.Text(tag, weight=ft.FontWeight.BOLD)), ft.DataCell(ft.Text(str(item["Desc"]))), ft.DataCell(camera_field), ft.DataCell(server_field), ft.DataCell(alert), ft.DataCell(event_field), ft.DataCell(ft.IconButton(ft.Icons.SAVE_OUTLINED, tooltip="Salvar vínculo", on_click=lambda _, t=tag, c=camera_field, s=server_field, a=alert, e=event_field: self._save_binding(t, c, s, a, e))) ]))
        if not table_rows:
            table_rows = [ft.DataRow([ft.DataCell(ft.Text("Nenhum TagName encontrado no banco")), *[ft.DataCell(ft.Text("—")) for _ in range(6)]])]
        return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[ft.Row([ft.Text("Defina câmera, servidor, alerta e evento por porta", color=ft.Colors.ON_SURFACE_VARIANT), ft.Container(expand=True), ft.FilledButton("Recarregar", icon=ft.Icons.REFRESH, style=button_style(ButtonVariant.NEUTRAL), on_click=lambda _: self.show("bindings"))]), self._card(ft.DataTable(columns=[ft.DataColumn(ft.Text("TagName / Porta")), ft.DataColumn(ft.Text("Descrição")), ft.DataColumn(ft.Text("Câmera Digifort")), ft.DataColumn(ft.Text("Servidor")), ft.DataColumn(ft.Text("Ativar alerta")), ft.DataColumn(ft.Text("Evento")), ft.DataColumn(ft.Text("Ação"))], rows=table_rows, column_spacing=16))])

    def _save_binding(self, tag: str, camera: ft.Dropdown, server: ft.Dropdown, alert: ft.Switch, event: ft.Dropdown) -> None:
        ok, message = self.service.save_binding(tag, camera.value or "", server.value or "", bool(alert.value), event.value or "")
        self.page.snack_bar = ft.SnackBar(ft.Text(message), open=True, bgcolor=ft.Colors.SECONDARY if ok else ft.Colors.ERROR)
        self.page.update()

    def services(self) -> ft.Control:
        cards = [self._service_card(ServiceHealth("Banco Vault Site", "database", None, r"Padrão: localhost\sqlexpress • Windows Integrated Security"))]
        cards.extend(self._service_card(ServiceHealth(item.name, "digifort", None, f"{item.hostname}:{item.port} • autenticação {item.auth_mode}")) for item in self.service.state.digifort)
        return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=16, controls=[ft.Row([ft.Text("Conexões monitoradas", color=ft.Colors.ON_SURFACE_VARIANT), ft.Container(expand=True), ft.FilledButton("Adicionar servidor Digifort", icon=ft.Icons.ADD, style=button_style(ButtonVariant.POSITIVE), on_click=lambda _: self._add_server_dialog())]), *cards])

    def _service_card(self, item: ServiceHealth) -> ft.Control:
        actual = self.service.state.health.get(item.name, item)
        color = ft.Colors.SECONDARY if actual.online else ft.Colors.ERROR if actual.online is False else ft.Colors.OUTLINE
        return self._card(ft.ListTile(leading=ft.Icon(ft.Icons.DNS_OUTLINED, color=color), title=ft.Row([ft.Text(item.name, weight=ft.FontWeight.BOLD), ft.Container(width=8), ft.Text(actual.label, size=11, color=color, weight=ft.FontWeight.BOLD)]), subtitle=ft.Text(item.detail), trailing=ft.IconButton(ft.Icons.REFRESH, tooltip=actual.detail, on_click=lambda _: self.refresh())), accent=color)

    def _add_server_dialog(self) -> None:
        name = ft.TextField(label="Nome do servidor", autofocus=True)
        host = ft.TextField(label="Hostname / IP")
        port = ft.TextField(label="Porta", value="8601", keyboard_type=ft.KeyboardType.NUMBER)
        user = ft.TextField(label="Usuário Digifort")
        password = ft.TextField(label="Senha", password=True, can_reveal_password=True)
        mode = ft.Dropdown(label="Autenticação", value="safe", options=[ft.dropdown.Option("safe"), ft.dropdown.Option("basic_http"), ft.dropdown.Option("basic_params")])
        def save(_: ft.ControlEvent) -> None:
            try:
                self.service.add_digifort(DigifortConfig(name.value or host.value, host.value, int(port.value or 8601), user.value or "", password.value or "", mode.value or "safe"))
                dialog.open = False
                self.show("services")
            except ValueError:
                port.error_text = "Informe uma porta numérica"
                self.page.update()
        dialog = ft.AlertDialog(modal=True, title=ft.Text("Adicionar servidor Digifort"), content=ft.Column([name, host, port, user, password, mode], tight=True, width=420), actions=[ft.TextButton("Cancelar", on_click=lambda _: self._close_dialog(dialog)), ft.FilledButton("Adicionar", style=button_style(ButtonVariant.POSITIVE), on_click=save)])
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _close_dialog(self, dialog: ft.AlertDialog) -> None:
        dialog.open = False
        self.page.update()

    def settings(self) -> ft.Control:
        return ft.Column(spacing=16, controls=[ft.Text("Banco de dados padrão", size=18, weight=ft.FontWeight.BOLD), self._card(ft.Column([ft.TextField(label="Servidor SQL Server", value=r"localhost\sqlexpress"), ft.TextField(label="Banco", value="DataDBEnt"), ft.Dropdown(label="Autenticação", value="Windows Integrated Security", options=[ft.dropdown.Option("Windows Integrated Security"), ft.dropdown.Option("Usuário e senha")]), ft.Row([ft.FilledButton("Testar conexão", icon=ft.Icons.NETWORK_CHECK, style=button_style(ButtonVariant.NEUTRAL)), ft.OutlinedButton("Salvar preferências", style=button_style(ButtonVariant.POSITIVE))])], spacing=14))])
