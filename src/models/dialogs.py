from __future__ import annotations

from collections.abc import Callable

import flet as ft

from modules.styles import ButtonVariant, button_style
from services.application import DigifortConfig


def show_message(page: ft.Page, message: str, *, error: bool = False) -> None:
    """Exibe SnackBar pelo ciclo de diálogo gerenciado da Page."""
    page.show_dialog(ft.SnackBar(content=ft.Text(message), bgcolor=ft.Colors.ERROR if error else ft.Colors.SECONDARY))


@ft.component
def DatabaseCredentialFields(*, enabled: bool, username: str, password: str, on_username: Callable[[str], None], on_password: Callable[[str], None]) -> ft.Control:
    """Campos filhos do AlertDialog; ``enabled`` vem do estado declarativo do pai."""
    username_field = ft.TextField(label="Usuário do banco", value=username, disabled=not enabled)
    password_field = ft.TextField(label="Senha", value=password, password=True, can_reveal_password=True, disabled=not enabled)
    username_field.on_change = lambda event: on_username(event.control.value or "")
    password_field.on_change = lambda event: on_password(event.control.value or "")
    return ft.Column([
        username_field,
        password_field,
        ft.Text("Em edição, deixe a senha vazia para manter a senha atual.", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
    ], tight=True)


@ft.component
def DatabaseDialog(*, open: bool, database: object, on_save: Callable[[dict[str, str]], tuple[bool, str]], on_close: Callable[[], None], on_result: Callable[[tuple[bool, str]], None]) -> ft.Control:
    """Diálogo de banco montado declarativamente com ``ft.use_dialog``."""
    auth = getattr(database, "auth", None)
    initial_mode = "sql" if auth else "windows"
    auth_mode, set_auth_mode = ft.use_state(initial_mode)
    error, set_error = ft.use_state("")
    username_value, set_username_value = ft.use_state(str(auth[0]) if auth else "")
    password_value, set_password_value = ft.use_state("")
    hostname = ft.TextField(label="Servidor SQL Server", value=str(getattr(database, "hostname", r"localhost\sqlexpress")))
    db_name = ft.TextField(label="Banco de dados", value=str(getattr(database, "database", "DataDBEnt")))
    driver = ft.TextField(label="Driver ODBC", value=str(getattr(database, "driver", "ODBC Driver 18 for SQL Server")))
    authentication = ft.Dropdown(label="Autenticação", value=auth_mode, options=[
        ft.DropdownOption(key="windows", text="Usuário do Windows (integrado)"),
        ft.DropdownOption(key="sql", text="Usuário do banco (SQL Server)"),
    ])

    def change_auth(event: ft.ControlEvent) -> None:
        set_auth_mode(event.control.value or "windows")

    def save(_: ft.ControlEvent) -> None:
        if auth_mode == "sql" and not username_value:
            set_error("Informe o usuário do banco, por exemplo: sa.")
            return
        result = on_save({
            "hostname": hostname.value or "", "database": db_name.value or "", "driver": driver.value or "",
            "auth_mode": auth_mode, "username": username_value, "password": password_value,
        })
        on_result(result)
        if result[0]:
            on_close()
        else:
            set_error(result[1])

    authentication.on_change = change_auth

    ft.use_dialog(ft.AlertDialog(
        modal=True,
        title=ft.Text("Editar conexão do banco de dados"),
        content=ft.Column([
            hostname, db_name, driver,
            authentication,
            DatabaseCredentialFields(
                enabled=auth_mode == "sql",
                username=username_value,
                password=password_value,
                on_username=set_username_value,
                on_password=set_password_value,
            ),
            ft.Text(error, color=ft.Colors.ERROR, visible=bool(error)),
        ], tight=True, width=460),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: on_close()),
            ft.FilledButton("Salvar conexão", style=button_style(ButtonVariant.POSITIVE), on_click=save),
        ],
        on_dismiss=on_close,
    ) if open else None)
    return ft.Container()


def show_digifort_dialog(page: ft.Page, on_save: Callable[[DigifortConfig], tuple[bool, str] | None], *, initial: DigifortConfig | None = None) -> None:
    editing = initial is not None
    name = ft.TextField(label="Nome do servidor", value=initial.name if initial else "", autofocus=True)
    host = ft.TextField(label="Hostname / IP", value=initial.hostname if initial else "")
    port = ft.TextField(label="Porta", value=str(initial.port if initial else 8601), keyboard_type=ft.KeyboardType.NUMBER)
    user = ft.TextField(label="Usuário Digifort", value=initial.username if initial else "")
    password = ft.TextField(label="Senha", value=initial.password if initial else "", password=True, can_reveal_password=True)
    mode = ft.Dropdown(label="Autenticação", value=initial.auth_mode if initial else "safe", options=[
        ft.DropdownOption("safe"), ft.DropdownOption("basic_http"), ft.DropdownOption("basic_params")
    ])

    def save(_: ft.ControlEvent) -> None:
        try:
            config = DigifortConfig(name.value or host.value, host.value, int(port.value or 8601), user.value or "", password.value or "", mode.value or "safe")
            if not config.hostname:
                raise ValueError("Hostname é obrigatório")
            result = on_save(config)
            page.pop_dialog()
            if result is not None:
                ok, message = result
                show_message(page, message, error=not ok)
        except ValueError as exc:
            port.error_text = str(exc)
            page.update()

    page.show_dialog(ft.AlertDialog(
        modal=True,
        title=ft.Text("Editar servidor Digifort" if editing else "Adicionar servidor Digifort"),
        content=ft.Column([name, host, port, user, password, mode], tight=True, width=420),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()),
            ft.FilledButton("Salvar" if editing else "Adicionar", style=button_style(ButtonVariant.POSITIVE), on_click=save),
        ],
    ))
