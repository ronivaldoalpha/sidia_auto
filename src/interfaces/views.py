from __future__ import annotations

import flet as ft
from collections.abc import Callable
from datetime import datetime, timedelta

from layouts.page_layout import PageLayout
from models.dialogs import ConfirmDeleteDialog, DatabaseDialog, DigifortDialog, EditBindingDialog, show_message
from models.paginated_table import PaginatedTable
from models.sidebar import Sidebar
from modules.styles import ButtonVariant, button_style, card_container_style
from modules.mycharts import AxisSpec, ChartData, ColumnChart, ColumnDatum, DonutChart, DonutDatum, LineChart, LinePoint, LineSeries
from services.application import ApplicationService, DigifortConfig, ServiceHealth


def _card(content: ft.Control, *, accent: str | None = None) -> ft.Control:
    return ft.Container(**card_container_style(accent=accent), padding=20, content=content)


def _metric(label: str, value: str, icon: str, color: str) -> ft.Control:
    return _card(ft.Row([ft.Icon(icon, color=color, size=28), ft.Column([ft.Text(label, color=ft.Colors.ON_SURFACE_VARIANT), ft.Text(value, size=26, weight=ft.FontWeight.BOLD)], spacing=3)], spacing=14), accent=color)


@ft.component
def DashboardInterface(*, service: ApplicationService, page: ft.Page) -> ft.Control:
    today = datetime.now().date()
    default_start = (today - timedelta(days=29)).isoformat()
    start_text, set_start_text = ft.use_state(default_start)
    end_text, set_end_text = ft.use_state(today.isoformat())
    applied_start, set_applied_start = ft.use_state(default_start)
    applied_end, set_applied_end = ft.use_state(today.isoformat())
    error, set_error = ft.use_state("")

    def parse_period() -> tuple[datetime, datetime] | None:
        try:
            start = datetime.strptime(applied_start, "%Y-%m-%d")
            end = datetime.strptime(applied_end, "%Y-%m-%d") + timedelta(days=1)
            if start >= end:
                raise ValueError
            return start, end
        except ValueError:
            return None

    period = parse_period()
    if period is None:
        metrics = {"total": 0, "sucessos": 0, "falhas": 0, "acuracidade": 0.0, "dias": [], "servidores": [], "rows": []}
        set_error("Use as datas no formato AAAA-MM-DD e confirme um período válido.")
    else:
        start, end = period
        service.state.dashboard_start, service.state.dashboard_end = start, end
        metrics = service.metrics(start=start, end=end)

    start_field = ft.TextField(label="Início", value=start_text, width=150)
    end_field = ft.TextField(label="Fim", value=end_text, width=150)
    start_field.on_change = lambda event: set_start_text(event.control.value or "")
    end_field.on_change = lambda event: set_end_text(event.control.value or "")

    def apply(_: ft.ControlEvent) -> None:
        set_applied_start(start_text)
        set_applied_end(end_text)
        set_error("")

    def detail(_: ft.ControlEvent) -> None:
        if period:
            page.navigate("/dashboard/detail")
        else:
            set_error("Corrija o período antes de detalhar.")

    chart_data = ChartData(
        lines=[
            LineSeries("Sucessos", tuple(LinePoint(i, item["sucessos"], label=item["data"].strftime("%d/%m")) for i, item in enumerate(metrics["dias"])), color="#7AF27A"),
            LineSeries("Falhas", tuple(LinePoint(i, item["falhas"], label=item["data"].strftime("%d/%m")) for i, item in enumerate(metrics["dias"])), color=ft.Colors.ERROR),
        ],
        donut=[DonutDatum("Sucessos", metrics["sucessos"], color="#7AF27A", title=f"{metrics['acuracidade']:.1f}%"), DonutDatum("Falhas", metrics["falhas"], color=ft.Colors.ERROR, title=f"{100 - metrics['acuracidade']:.1f}%")],
        columns=[ColumnDatum(item["servidor"], item["sucessos"], failure=item["falhas"], color="#7AF27A") for item in metrics["servidores"]],
    )
    line_axis = AxisSpec(title="Dia", labels=tuple((i, item["data"].strftime("%d/%m")) for i, item in enumerate(metrics["dias"]) if i % 5 == 0))
    health_controls = [_health_row(item) for item in service.state.health.values()] or [ft.Text("Serviços ainda não verificados")]
    return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=18, controls=[
        ft.Row([ft.Text("Indicadores operacionais", color=ft.Colors.ON_SURFACE_VARIANT), ft.Container(expand=True), start_field, end_field, ft.FilledButton("Aplicar", icon=ft.Icons.FILTER_ALT, on_click=apply), ft.FilledButton("Detalhar", icon=ft.Icons.OPEN_IN_NEW, style=button_style(ButtonVariant.NEUTRAL), on_click=detail)]),
        ft.Text(error, color=ft.Colors.ERROR, visible=bool(error)),
        ft.ResponsiveRow(columns=12, spacing=14, controls=[
            ft.Container(col=3, content=_metric("Acuracidade global", f"{metrics['acuracidade']:.1f}%", ft.Icons.TRENDING_UP, ft.Colors.PRIMARY)),
            ft.Container(col=3, content=_metric("Sucessos", str(metrics["sucessos"]), ft.Icons.CHECK_CIRCLE_OUTLINE, ft.Colors.SECONDARY)),
            ft.Container(col=3, content=_metric("Falhas", str(metrics["falhas"]), ft.Icons.WARNING_AMBER_OUTLINED, ft.Colors.ERROR)),
            ft.Container(col=3, content=_metric("Eventos analisados", str(metrics["total"]), ft.Icons.INSIGHTS_OUTLINED, ft.Colors.TERTIARY)),
        ]),
        ft.ResponsiveRow(columns=12, spacing=14, controls=[
            ft.Container(col=8, content=_card(ft.Column([ft.Text("Tendência diária: sucessos e falhas", size=17, weight=ft.FontWeight.BOLD), ft.Container(height=300, content=LineChart(data=chart_data, bottom_axis=line_axis, left_axis=AxisSpec(title="Eventos", minimum=0), interactive=True))], spacing=12), accent=ft.Colors.PRIMARY)),
            ft.Container(col=4, content=_card(ft.Column([ft.Text("Acuracidade global", size=17, weight=ft.FontWeight.BOLD), ft.Container(height=300, content=DonutChart(data=chart_data, center_space_radius=62, interactive=True))], spacing=12), accent=ft.Colors.SECONDARY)),
        ]),
        _card(ft.Column([ft.Text("Acuracidade por servidor", size=17, weight=ft.FontWeight.BOLD), ft.Container(height=300, content=ColumnChart(data=chart_data, left_axis=AxisSpec(title="Eventos", minimum=0), interactive=True))], spacing=12), accent=ft.Colors.ERROR),
        _card(ft.Column([ft.Text("Status dos serviços", size=17, weight=ft.FontWeight.BOLD), *health_controls], spacing=4), accent=ft.Colors.SECONDARY),
    ])


@ft.component
def DashboardReportInterface(*, service: ApplicationService, page: ft.Page) -> ft.Control:
    start = service.state.dashboard_start or (datetime.now() - timedelta(days=29))
    end = service.state.dashboard_end or datetime.now()
    metrics = service.metrics(start=start, end=end)
    rows = [{**row, "DataHora": row["DataHora"].strftime("%d/%m/%Y %H:%M:%S")} for row in metrics["rows"]]
    return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=16, controls=[
        ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Voltar", on_click=lambda _: page.navigate("/")), ft.Text("Relatório detalhado", size=22, weight=ft.FontWeight.BOLD), ft.Container(expand=True), ft.Text(f"{start:%d/%m/%Y} a {(end - timedelta(microseconds=1)):%d/%m/%Y}", color=ft.Colors.ON_SURFACE_VARIANT)]),
        _card(ft.Column([ft.Text(f"{len(rows)} registros usados nos indicadores", color=ft.Colors.ON_SURFACE_VARIANT), PaginatedTable(rows, [("DataHora", "Data/hora"), ("Status", "Status"), ("Servidor", "Servidor"), ("Controladora", "Controladora"), ("Mensagem", "Mensagem")], page_size=10)], spacing=12), accent=ft.Colors.PRIMARY),
    ])


def _health_row(item: ServiceHealth) -> ft.Control:
    color = ft.Colors.SECONDARY if item.online else ft.Colors.ERROR if item.online is False else ft.Colors.OUTLINE
    return ft.ListTile(leading=ft.Icon(ft.Icons.CIRCLE, color=color, size=12), title=ft.Text(item.name), subtitle=ft.Text(item.label), tooltip=item.detail)


@ft.component
def BindingsInterface(*, service: ApplicationService, page: ft.Page) -> ft.Control:
    reload, set_reload = ft.use_state(0)
    editing_row, set_editing_row = ft.use_state(None)

    tags = service.controller_tags()
    cameras = service.cameras()
    servers = [ft.DropdownOption(item.name) for item in service.state.digifort]
    rows: list[dict[str, object]] = [
        {"TagName": item["TagName"], "Desc": item["Desc"], "Câmera": "Selecione na edição"}
        for item in tags
    ]

    def save_binding(row: dict, camera: str, server: str, enabled: bool, event: str) -> None:
        ok, message = service.save_binding(str(row["TagName"]), camera, server, enabled, event)
        set_editing_row(None)
        show_message(page, message, error=not ok)

    return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[
        ft.Row([
            ft.Text("Todos os TagName distintos da tabela Controller", color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Container(expand=True),
            ft.FilledButton("Recarregar", icon=ft.Icons.REFRESH, style=button_style(ButtonVariant.NEUTRAL),
                           on_click=lambda _: set_reload(reload + 1)),
        ]),
        _card(PaginatedTable(rows, [("TagName", "TagName / Porta"), ("Desc", "Descrição"), ("Câmera", "Câmera Digifort")],
              on_row_action=lambda row: set_editing_row(row))),
        EditBindingDialog(
            row=editing_row,
            cameras=cameras,
            servers=servers,
            event_types=service.event_types,
            on_save=save_binding,
            on_close=lambda: set_editing_row(None),
        ),
    ])


@ft.component
def ServicesInterface(*, service: ApplicationService, page: ft.Page) -> ft.Control:
    database_dialog_open, set_database_dialog_open = ft.use_state(False)
    digifort_dialog_open, set_digifort_dialog_open = ft.use_state(False)
    editing_config, set_editing_config = ft.use_state(None)
    deleting_name, set_deleting_name = ft.use_state(None)

    def handle_save_digifort(config: DigifortConfig) -> tuple[bool, str]:
        if editing_config is not None:
            return service.update_digifort(editing_config.name, config)
        return service.add_digifort(config)

    def open_edit_digifort(item: DigifortConfig) -> None:
        set_editing_config(item)
        set_digifort_dialog_open(True)

    def close_digifort_dialog() -> None:
        set_digifort_dialog_open(False)
        set_editing_config(None)

    def confirm_delete(name: str) -> None:
        result = service.remove_digifort(name)
        set_deleting_name(None)
        show_message(page, result[1], error=not result[0])

    database = service.state.health.get("database", ServiceHealth("Banco Vault Site", "database", None, r"Padrão: localhost\sqlexpress • Windows Integrated Security"))
    cards = [_service_card(
        database,
        on_edit=lambda: set_database_dialog_open(True),
        on_delete=None,
        on_refresh=lambda: _check_database(service, page),
    )]
    for config in service.state.digifort:
        health = service.state.health.get(config.name, ServiceHealth(config.name, "digifort", None, f"{config.hostname}:{config.port} • autenticação {config.auth_mode}"))
        cards.append(_service_card(
            health,
            on_edit=lambda item=config: open_edit_digifort(item),
            on_delete=lambda item=config: set_deleting_name(item.name),
            on_refresh=lambda item=config: _check_server(service, page, item),
        ))

    return ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=16, controls=[
        ft.Row([
            ft.Text("Conexões monitoradas", color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Container(expand=True),
            ft.FilledButton("Adicionar servidor Digifort", icon=ft.Icons.ADD, style=button_style(ButtonVariant.POSITIVE),
                           on_click=lambda _: set_digifort_dialog_open(True)),
        ]),
        *cards,
        DatabaseDialog(
            open=database_dialog_open,
            database=service.database,
            on_save=lambda values: service.save_database_settings(**values),
            on_close=lambda: set_database_dialog_open(False),
            on_result=lambda result: show_message(page, result[1], error=not result[0]),
        ),
        DigifortDialog(
            open=digifort_dialog_open,
            initial=editing_config,
            on_save=handle_save_digifort,
            on_close=close_digifort_dialog,
            on_result=lambda result: show_message(page, result[1], error=not result[0]),
        ),
        ConfirmDeleteDialog(
            deleting_name=deleting_name,
            on_confirm=confirm_delete,
            on_cancel=lambda: set_deleting_name(None),
        ),
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
    # AppState é @ft.observable — ServicesInterface re-renderiza automaticamente.


def _check_server(service: ApplicationService, page: ft.Page, config: DigifortConfig) -> None:
    health = service.check_digifort(config)
    show_message(page, f"{config.name}: {health.label}", error=health.online is False)
    # AppState é @ft.observable — ServicesInterface re-renderiza automaticamente.


def route_page(*, page: ft.Page, service: ApplicationService, title: str, interface: ft.Control) -> ft.Control:
    return PageLayout(sidebar=Sidebar(page), interface=interface, title=title, page=page)
