from __future__ import annotations

import flet as ft
from collections.abc import Callable

from layouts.page_layout import PageLayout
from models.dialogs import DatabaseDialog, show_digifort_dialog, show_message
from models.paginated_table import PaginatedTable
from models.sidebar import Sidebar
from modules.styles import ButtonVariant, button_style, card_container_style
from services.application import ApplicationService, DigifortConfig, ServiceHealth


def _card(content: ft.Control, *, accent: str | None = None) -> ft.Control:
    return ft.Container(**card_container_style(accent=accent), padding=20, content=content)


def _metric(label: str, value: str, icon: str, color: str) -> ft.Control:
    return _card(ft.Row([ft.Icon(icon, color=color, size=28), ft.Column([ft.Text(label, color=ft.Colors.ON_SURFACE_VARIANT), ft.Text(value, size=26, weight=ft.FontWeight.BOLD)], spacing=3)], spacing=14), accent=color)


@ft.component
def DashboardInterface(*, service: ApplicationService, page: ft.Page) -> ft.Control:
    metrics = service.metrics()
    accuracy = metrics.get("taxa_acuracidade", 0.0)
    health_controls = [_health_row(item) for item in service.state.health.values()]
    if not health_controls:
        health_controls = [ft.Text("Clique em atualizar para consultar os serviços")]
    return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=18, controls=[
        ft.Text("Saúde da integração", color=ft.Colors.ON_SURFACE_VARIANT),
        ft.ResponsiveRow(columns=12, spacing=14, controls=[
            ft.Container(col=3, content=_metric("Acuracidade geral", f"{accuracy:.1f}%", ft.Icons.TRENDING_UP, ft.Colors.PRIMARY)),
            ft.Container(col=3, content=_metric("Eventos analisados", str(metrics.get("total_eventos", 0)), ft.Icons.INSIGHTS_OUTLINED, ft.Colors.TERTIARY)),
            ft.Container(col=3, content=_metric("Falhas no período", str(metrics.get("falhas", 0)), ft.Icons.WARNING_AMBER_OUTLINED, ft.Colors.ERROR)),
            ft.Container(col=3, content=_metric("Digifort ativos", str(sum(x.enabled for x in service.state.digifort)), ft.Icons.DNS_OUTLINED, ft.Colors.SECONDARY)),
        ]),
        _card(ft.Column([
            ft.Text("Tendência de falhas diárias", size=17, weight=ft.FontWeight.BOLD),
            PaginatedTable(metrics.get("logs", []), [("ErrorDateTime", "Data/hora"), ("TrController", "Controladora"), ("ErrorMessage", "Mensagem")], page_size=5),
        ], spacing=14), accent=ft.Colors.ERROR),
        _card(ft.Column([
            ft.Text("Status dos serviços", size=17, weight=ft.FontWeight.BOLD),
            *health_controls,
        ], spacing=4), accent=ft.Colors.SECONDARY),
    ])


def _health_row(item: ServiceHealth) -> ft.Control:
    color = ft.Colors.SECONDARY if item.online else ft.Colors.ERROR if item.online is False else ft.Colors.OUTLINE
    return ft.ListTile(leading=ft.Icon(ft.Icons.CIRCLE, color=color, size=12), title=ft.Text(item.name), subtitle=ft.Text(item.label), tooltip=item.detail)


@ft.component
def BindingsInterface(*, service: ApplicationService, page: ft.Page) -> ft.Control:
    tags = service.controller_tags()
    cameras = service.cameras()
    servers = [ft.DropdownOption(item.name) for item in service.state.digifort]
    rows: list[dict[str, object]] = []
    for item in tags:
        rows.append({"TagName": item["TagName"], "Desc": item["Desc"], "Câmera": "Selecione na edição"})

    def edit(row: dict[str, object]) -> None:
        camera = ft.Dropdown(label="Câmera Digifort", options=[ft.DropdownOption(c) for c in cameras], hint_text="Digite para pesquisar")
        server = ft.Dropdown(label="Servidor", options=servers)
        enabled = ft.Switch(label="Ativar alerta")
        event = ft.Dropdown(label="Tipo de evento", options=[ft.DropdownOption(x) for x in service.event_types])
        def save(_: ft.ControlEvent) -> None:
            ok, message = service.save_binding(str(row["TagName"]), camera.value or "", server.value or "", bool(enabled.value), event.value or "")
            page.pop_dialog()
            show_message(page, message, error=not ok)
        page.show_dialog(ft.AlertDialog(modal=True, title=ft.Text(f"Configurar {row['TagName']}"), content=ft.Column([camera, server, enabled, event], tight=True, width=430), actions=[ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()), ft.FilledButton("Salvar", style=button_style(ButtonVariant.POSITIVE), on_click=save)]))

    return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
        ft.Row([ft.Text("Todos os TagName distintos da tabela Controller", color=ft.Colors.ON_SURFACE_VARIANT), ft.Container(expand=True), ft.FilledButton("Recarregar", icon=ft.Icons.REFRESH, style=button_style(ButtonVariant.NEUTRAL), on_click=lambda _: page.navigate("/bindings"))]),
        _card(PaginatedTable(rows, [("TagName", "TagName / Porta"), ("Desc", "Descrição"), ("Câmera", "Câmera Digifort")], on_row_action=edit)),
    ])


@ft.component
def ServicesInterface(*, service: ApplicationService, page: ft.Page) -> ft.Control:
    database_dialog_open, set_database_dialog_open = ft.use_state(False)

    def add(config: DigifortConfig) -> tuple[bool, str]:
        result = service.add_digifort(config)
        if result[0]:
            page.navigate("/services")
        return result

    database = service.state.health.get("database", ServiceHealth("Banco Vault Site", "database", None, r"Padrão: localhost\sqlexpress • Windows Integrated Security"))
    cards = [_service_card(database, on_edit=lambda: set_database_dialog_open(True), on_delete=None, on_refresh=lambda: _check_database(service, page))]
    for config in service.state.digifort:
        health = service.state.health.get(config.name, ServiceHealth(config.name, "digifort", None, f"{config.hostname}:{config.port} • autenticação {config.auth_mode}"))
        cards.append(_service_card(health, on_edit=lambda item=config: show_digifort_dialog(page, lambda updated: _edit_server(service, page, item.name, updated), initial=item), on_delete=lambda item=config: _confirm_delete(service, page, item.name), on_refresh=lambda item=config: _check_server(service, page, item)))
    database_dialog = DatabaseDialog(
        open=database_dialog_open,
        database=service.database,
        on_save=lambda values: service.save_database_settings(**values),
        on_close=lambda: set_database_dialog_open(False),
        on_result=lambda result: show_message(page, result[1], error=not result[0]),
    )
    return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=16, controls=[
        ft.Row([ft.Text("Conexões monitoradas", color=ft.Colors.ON_SURFACE_VARIANT), ft.Container(expand=True), ft.FilledButton("Adicionar servidor Digifort", icon=ft.Icons.ADD, style=button_style(ButtonVariant.POSITIVE), on_click=lambda _: show_digifort_dialog(page, add))]),
        *cards,
        database_dialog,
    ])


def _status_color(item: ServiceHealth) -> str:
    if item.credential_error:
        return "#C86B00"
    return ft.Colors.SECONDARY if item.online else ft.Colors.ERROR if item.online is False else ft.Colors.OUTLINE


def _service_card(item: ServiceHealth, *, on_edit: Callable[[], None] | None, on_delete: Callable[[], None] | None, on_refresh: Callable[[], None]) -> ft.Control:
    color = _status_color(item)
    flag = ft.Icon(ft.Icons.FLAG, color=color, tooltip=item.label)
    actions = [
        ft.IconButton(ft.Icons.REFRESH, tooltip="Verificar conexão", on_click=lambda _: on_refresh()),
        ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Editar serviço", disabled=on_edit is None, on_click=lambda _: on_edit() if on_edit else None),
        ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Excluir serviço" if on_delete else "O banco padrão não pode ser excluído", disabled=on_delete is None, on_click=lambda _: on_delete() if on_delete else None),
    ]
    return _card(ft.ListTile(leading=ft.Row([flag, ft.Icon(ft.Icons.DNS_OUTLINED, color=color)], tight=True, spacing=10), title=ft.Row([ft.Text(item.name, weight=ft.FontWeight.BOLD), ft.Text(item.label, size=11, color=color, weight=ft.FontWeight.BOLD)]), subtitle=ft.Text(item.detail), trailing=ft.Row(actions, tight=True)), accent=color)


def _check_database(service: ApplicationService, page: ft.Page) -> None:
    health = service.check_database()
    show_message(page, f"Banco: {health.label} — {health.detail}", error=health.online is False)
    page.navigate("/services")


def _check_server(service: ApplicationService, page: ft.Page, config: DigifortConfig) -> None:
    health = service.check_digifort(config)
    show_message(page, f"{config.name}: {health.label}", error=health.online is False)
    page.navigate("/services")


def _edit_server(service: ApplicationService, page: ft.Page, original_name: str, config: DigifortConfig) -> tuple[bool, str]:
    result = service.update_digifort(original_name, config)
    if result[0]:
        page.navigate("/services")
    return result


def _confirm_delete(service: ApplicationService, page: ft.Page, name: str) -> None:
    def confirm(_: ft.ControlEvent) -> None:
        result = service.remove_digifort(name)
        page.pop_dialog()
        show_message(page, result[1], error=not result[0])
        if result[0]:
            page.navigate("/services")
    page.show_dialog(ft.AlertDialog(modal=True, title=ft.Text("Excluir servidor?"), content=ft.Text(f"A conexão {name} será removida da configuração local."), actions=[ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()), ft.FilledButton("Excluir", style=button_style(ButtonVariant.NEGATIVE), on_click=confirm)]))


def route_page(*, page: ft.Page, service: ApplicationService, title: str, interface: ft.Control) -> ft.Control:
    return PageLayout(sidebar=Sidebar(page), interface=interface, title=title, page=page)
