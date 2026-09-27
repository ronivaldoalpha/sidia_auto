from __future__ import annotations

from collections.abc import Callable
from typing import Any

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


@ft.component
def DigifortDialog(
    *,
    open: bool,
    initial: DigifortConfig | None = None,
    on_save: Callable[[DigifortConfig], tuple[bool, str] | None],
    on_close: Callable[[], None],
    on_result: Callable[[tuple[bool, str]], None] | None = None,
) -> ft.Control:
    """Diálogo de servidor Digifort declarativo com ``ft.use_dialog``.

    Substitui a função imperativa ``show_digifort_dialog``. Suporta criação e
    edição de servidores Digifort. O formulário é reiniciado via ``ft.use_effect``
    quando ``initial`` muda (troca do servidor em edição).
    """
    editing = initial is not None
    name_val, set_name = ft.use_state(initial.name if initial else "")
    host_val, set_host = ft.use_state(initial.hostname if initial else "")
    port_val, set_port = ft.use_state(str(initial.port if initial else 8601))
    user_val, set_user = ft.use_state(initial.username if initial else "")
    pass_val, set_pass = ft.use_state(initial.password if initial else "")
    mode_val, set_mode = ft.use_state(initial.auth_mode if initial else "safe")
    error_val, set_error = ft.use_state("")

    def sync_initial() -> None:
        """Reinicia os campos quando o servidor sendo editado muda."""
        set_name(initial.name if initial else "")
        set_host(initial.hostname if initial else "")
        set_port(str(initial.port if initial else 8601))
        set_user(initial.username if initial else "")
        set_pass(initial.password if initial else "")
        set_mode(initial.auth_mode if initial else "safe")
        set_error("")

    ft.use_effect(sync_initial, dependencies=[initial])

    def save(_: ft.ControlEvent) -> None:
        try:
            config = DigifortConfig(
                name_val or host_val, host_val, int(port_val or "8601"),
                user_val, pass_val, mode_val,
            )
            if not config.hostname:
                raise ValueError("Hostname é obrigatório")
            result = on_save(config)
            if result is not None:
                ok, message = result
                if ok:
                    on_close()
                    if on_result:
                        on_result(result)
                else:
                    # Mantém o diálogo aberto e exibe o erro inline.
                    set_error(message)
            else:
                on_close()
        except ValueError as exc:
            set_error(str(exc))

    ft.use_dialog(ft.AlertDialog(
        modal=True,
        title=ft.Text("Editar servidor Digifort" if editing else "Adicionar servidor Digifort"),
        content=ft.Column([
            ft.TextField(label="Nome do servidor", value=name_val, autofocus=True,
                         on_change=lambda e: set_name(e.control.value or "")),
            ft.TextField(label="Hostname / IP", value=host_val,
                         on_change=lambda e: set_host(e.control.value or "")),
            ft.TextField(label="Porta", value=port_val, keyboard_type=ft.KeyboardType.NUMBER,
                         on_change=lambda e: set_port(e.control.value or "")),
            ft.TextField(label="Usuário Digifort", value=user_val,
                         on_change=lambda e: set_user(e.control.value or "")),
            ft.TextField(label="Senha", value=pass_val, password=True, can_reveal_password=True,
                         on_change=lambda e: set_pass(e.control.value or "")),
            ft.Dropdown(
                label="Autenticação", value=mode_val,
                options=[ft.DropdownOption("safe"), ft.DropdownOption("basic_http"), ft.DropdownOption("basic_params")],
                on_select=lambda e: set_mode(e.control.value or "safe"),
            ),
            ft.Text(error_val, color=ft.Colors.ERROR, visible=bool(error_val)),
        ], tight=True, width=420),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: on_close()),
            ft.FilledButton(
                "Salvar" if editing else "Adicionar",
                style=button_style(ButtonVariant.POSITIVE),
                on_click=save,
            ),
        ],
    ) if open else None)
    return ft.Container()


@ft.component
def ConfirmDeleteDialog(
    *,
    deleting_name: str | None,
    on_confirm: Callable[[str], None],
    on_cancel: Callable[[], None],
) -> ft.Control:
    """Diálogo de confirmação de exclusão de servidor declarativo com ``ft.use_dialog``."""
    ft.use_dialog(ft.AlertDialog(
        modal=True,
        title=ft.Text("Excluir servidor?"),
        content=ft.Text(f"A conexão {deleting_name} será removida da configuração local."),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: on_cancel()),
            ft.FilledButton(
                "Excluir",
                style=button_style(ButtonVariant.NEGATIVE),
                on_click=lambda _: on_confirm(deleting_name),  # type: ignore[arg-type]
            ),
        ],
    ) if deleting_name is not None else None)
    return ft.Container()


@ft.component
def EditBindingDialog(
    *,
    row: dict[str, Any] | None,
    cameras: list[str],
    servers: list[ft.DropdownOption],
    event_types: list[str],
    on_save: Callable,
    on_close: Callable[[], None],
) -> ft.Control:
    """Diálogo de configuração de vínculo porta-câmera declarativo com ``ft.use_dialog``.

    Os campos são reiniciados via ``ft.use_effect`` cada vez que uma nova
    linha é selecionada para edição (``row`` muda).
    """
    camera_val, set_camera = ft.use_state("")
    server_val, set_server = ft.use_state("")
    enabled_val, set_enabled = ft.use_state(False)
    event_val, set_event = ft.use_state("")

    def reset_form() -> None:
        set_camera("")
        set_server("")
        set_enabled(False)
        set_event("")

    ft.use_effect(reset_form, dependencies=[row])

    ft.use_dialog(ft.AlertDialog(
        modal=True,
        title=ft.Text(f"Configurar {row['TagName']}") if row else ft.Text(""),
        content=ft.Column([
            ft.Dropdown(
                label="Câmera Digifort",
                options=[ft.DropdownOption(c) for c in cameras],
                value=camera_val or None,
                hint_text="Digite para pesquisar",
                on_select=lambda e: set_camera(e.control.value or ""),
            ),
            ft.Dropdown(
                label="Servidor",
                options=servers,
                value=server_val or None,
                on_select=lambda e: set_server(e.control.value or ""),
            ),
            ft.Switch(
                label="Ativar alerta",
                value=enabled_val,
                on_change=lambda e: set_enabled(bool(e.control.value)),
            ),
            ft.Dropdown(
                label="Tipo de evento",
                options=[ft.DropdownOption(x) for x in event_types],
                value=event_val or None,
                on_select=lambda e: set_event(e.control.value or ""),
            ),
        ], tight=True, width=430),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: on_close()),
            ft.FilledButton(
                "Salvar",
                style=button_style(ButtonVariant.POSITIVE),
                on_click=lambda _: on_save(row, camera_val, server_val, enabled_val, event_val) if row else None,
            ),
        ],
    ) if row is not None else None)
    return ft.Container()
