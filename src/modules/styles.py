"""Design system de componentes Flet.

Use as fábricas deste módulo em vez de criar ``ButtonStyle`` ou ``MenuStyle``
localmente. Toda variação visual fica centralizada e pode ser ajustada sem
percorrer as telas do aplicativo.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import flet as ft

from .theme import CANVAS, INK, PRIMARY, SECONDARY, TERTIARY


class ButtonVariant(StrEnum):
    """Intenção semântica de um botão."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    ALERT = "alert"


# Cores de estado: o valor DEFAULT é sempre explicitado para evitar depender
# de defaults implícitos diferentes entre versões do Flet.
_VARIANTS: dict[ButtonVariant, dict[str, str]] = {
    ButtonVariant.POSITIVE: {
        "default": SECONDARY, "hovered": "#99F795", "focused": "#62D963",
        "pressed": "#4CBC50", "disabled": "#B9D8BA", "foreground": INK,
    },
    ButtonVariant.NEGATIVE: {
        "default": "#BA1A4B", "hovered": "#D63D6B", "focused": "#A31340",
        "pressed": "#820B31", "disabled": "#D9B7C0", "foreground": "#FFFFFF",
    },
    ButtonVariant.NEUTRAL: {
        "default": TERTIARY, "hovered": "#1766A9", "focused": "#063B70",
        "pressed": "#052C55", "disabled": "#AABACB", "foreground": "#FFFFFF",
    },
    ButtonVariant.ALERT: {
        "default": "#C86B00", "hovered": "#E48713", "focused": "#A95400",
        "pressed": "#854100", "disabled": "#D6B99A", "foreground": "#FFFFFF",
    },
}


def _state_map(default: Any, *, hovered: Any = None, focused: Any = None,
               pressed: Any = None, disabled: Any = None) -> dict[Any, Any]:
    """Cria um mapa de estados com fallback explícito em DEFAULT."""
    values = {ft.ControlState.DEFAULT: default}
    if hovered is not None:
        values[ft.ControlState.HOVERED] = hovered
    if focused is not None:
        values[ft.ControlState.FOCUSED] = focused
    if pressed is not None:
        values[ft.ControlState.PRESSED] = pressed
    if disabled is not None:
        values[ft.ControlState.DISABLED] = disabled
    return values


def button_style(variant: ButtonVariant | str = ButtonVariant.NEUTRAL) -> ft.ButtonStyle:
    """Retorna o estilo padrão de botão para a intenção informada.

    Exemplo::

        ft.FilledButton("Salvar", style=button_style(ButtonVariant.POSITIVE))
        ft.OutlinedButton("Excluir", style=button_style("negative"))
    """
    variant = ButtonVariant(variant)
    colors = _VARIANTS[variant]
    transparent = "#00000000"
    return ft.ButtonStyle(
        color=_state_map(
            colors["foreground"],
            disabled="#6E7775",
        ),
        icon_color=_state_map(colors["foreground"], disabled="#6E7775"),
        bgcolor=_state_map(
            colors["default"], hovered=colors["hovered"], focused=colors["focused"],
            pressed=colors["pressed"], disabled=colors["disabled"],
        ),
        overlay_color=_state_map(
            transparent,
            hovered="#227FFFFF", focused="#447FFFFF", pressed="#557FFFFF",
        ),
        side=_state_map(
            ft.BorderSide(1, colors["default"]),
            hovered=ft.BorderSide(2, colors["hovered"]),
            focused=ft.BorderSide(2, colors["focused"]),
            disabled=ft.BorderSide(1, colors["disabled"]),
        ),
        shape=_state_map(
            ft.RoundedRectangleBorder(radius=10),
            hovered=ft.RoundedRectangleBorder(radius=12),
            focused=ft.RoundedRectangleBorder(radius=12),
        ),
        elevation=_state_map(1, hovered=4, focused=3, pressed=0, disabled=0),
        shadow_color=_state_map("#33011B49", hovered="#66011B49"),
        padding=_state_map(ft.Padding.symmetric(horizontal=18, vertical=12), hovered=ft.Padding.symmetric(horizontal=18, vertical=13)),
        animation_duration=180,
        enable_feedback=True,
    )


def positive_button_style() -> ft.ButtonStyle:
    return button_style(ButtonVariant.POSITIVE)


def negative_button_style() -> ft.ButtonStyle:
    return button_style(ButtonVariant.NEGATIVE)


def neutral_button_style() -> ft.ButtonStyle:
    return button_style(ButtonVariant.NEUTRAL)


def alert_button_style() -> ft.ButtonStyle:
    return button_style(ButtonVariant.ALERT)


def card_style(*, accent: str | None = None) -> dict[str, Any]:
    """Retorna propriedades visuais reutilizáveis para ``ft.Card`` ou Container.

    O retorno como dicionário permite aplicar apenas onde o controle aceitar a
    propriedade, por exemplo ``ft.Card(**card_style())``.
    """
    return {
        "color": ft.Colors.SURFACE_CONTAINER_LOWEST,
        "elevation": 2,
        "shadow_color": "#33011B49",
        "surface_tint_color": accent or PRIMARY,
        "shape": ft.RoundedRectangleBorder(radius=14),
    }


def card_container_style(*, accent: str | None = None) -> dict[str, Any]:
    """Propriedades para ``ft.Container`` usado como cartão customizado."""
    return {
        "bgcolor": ft.Colors.SURFACE_CONTAINER_LOWEST,
        "border": ft.Border.all(1, accent or ft.Colors.OUTLINE_VARIANT),
        "border_radius": 14,
        "shadow": [
            ft.BoxShadow(
                color="#26011B49",
                blur_radius=0.12,
                spread_radius=0,
                offset=ft.Offset(0, 0.4),
                blur_style=ft.BlurStyle.NORMAL
            )
        ],
    }


def menu_style() -> ft.MenuStyle:
    """Estilo de menus, com borda e dimensões consistentes."""
    return ft.MenuStyle(
        bgcolor=_state_map(ft.Colors.SURFACE_CONTAINER, hovered=ft.Colors.SURFACE_CONTAINER_HIGH),
        shadow_color="#66011B49",
        elevation=_state_map(6, hovered=8),
        padding=ft.Padding.symmetric(vertical=8),
        shape=ft.RoundedRectangleBorder(radius=12),
        side=_state_map(ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT), hovered=ft.BorderSide(1, PRIMARY)),
    )


def menu_button_style() -> ft.ButtonStyle:
    """Estilo para botões que abrem menus, mantendo o mesmo foco dos botões."""
    return ft.ButtonStyle(
        color=_state_map(ft.Colors.ON_SURFACE, hovered=PRIMARY, focused=PRIMARY),
        bgcolor=_state_map("#00000000", hovered="#147D79EF", focused="#227D79EF"),
        shape=_state_map(ft.RoundedRectangleBorder(radius=10), hovered=ft.RoundedRectangleBorder(radius=10)),
        side=_state_map(ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT), focused=ft.BorderSide(2, PRIMARY)),
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        animation_duration=160,
    )
