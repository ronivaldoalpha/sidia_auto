"""Sistema visual centralizado do aplicativo Flet.

O módulo mantém os tokens de design em um único lugar. Os controles devem
preferir cores semânticas do ColorScheme (por exemplo, ``page.theme.color_scheme``)
em vez de hexadecimais espalhados pela aplicação.
"""

from __future__ import annotations

import flet as ft

# Paleta de marca fornecida pelo produto.
PRIMARY = "#7D79EF"       # Indigo/lavanda: ação principal e navegação
SECONDARY = "#7AF27A"     # Verde: sucesso, saúde e confirmação
TERTIARY = "#0A4B89"      # Azul: informação e elementos institucionais
INK = "#011B49"           # Azul-marinho: texto forte e contraste
CANVAS = "#F8FAF9"        # Branco esverdeado: superfícies claras
BRAND_SEED = PRIMARY


def _transitions() -> ft.PageTransitionsTheme:
    """Transições discretas e consistentes entre rotas em cada plataforma."""
    return ft.PageTransitionsTheme(
        android=ft.PageTransitionTheme.FADE_UPWARDS,
        ios=ft.PageTransitionTheme.CUPERTINO,
        linux=ft.PageTransitionTheme.ZOOM,
        macos=ft.PageTransitionTheme.ZOOM,
        windows=ft.PageTransitionTheme.FADE_FORWARDS,
    )


def light_theme() -> ft.Theme:
    """Tema claro, com superfícies frias e contraste adequado para dashboards."""
    return ft.Theme(
        use_material3=True,
        color_scheme_seed=BRAND_SEED,
        color_scheme=ft.ColorScheme(
            primary=PRIMARY,
            on_primary=INK,
            primary_container="#E5E3FF",
            on_primary_container=INK,
            secondary=SECONDARY,
            on_secondary=INK,
            secondary_container="#D7F8D5",
            on_secondary_container="#053B22",
            tertiary=TERTIARY,
            on_tertiary="#FFFFFF",
            tertiary_container="#D3E5FF",
            on_tertiary_container="#001B36",
            error="#BA1A4B",
            on_error="#FFFFFF",
            error_container="#FFD9E2",
            on_error_container="#3F0015",
            surface=CANVAS,
            on_surface=INK,
            surface_container_lowest="#FFFFFF",
            surface_container_low="#F1F5F3",
            surface_container="#EAF0ED",
            surface_container_high="#E3EAE7",
            surface_container_highest="#DCE4E0",
            on_surface_variant="#3E4A47",
            outline="#6D7975",
            outline_variant="#BEC9C4",
            inverse_surface=INK,
            on_inverse_surface="#E9F1FF",
            inverse_primary="#B9B6FF",
            scrim="#000000",
        ),
        scaffold_bgcolor=CANVAS,
        canvas_color=CANVAS,
        card_bgcolor="#FFFFFF",
        divider_color="#C2C7CF",
        page_transitions=_transitions(),
        font_family="Inter",
    )


def dark_theme() -> ft.Theme:
    """Tema escuro, evitando preto absoluto e preservando hierarquia de superfícies."""
    return ft.Theme(
        use_material3=True,
        color_scheme_seed=BRAND_SEED,
        color_scheme=ft.ColorScheme(
            primary="#AAA7FF",
            on_primary=INK,
            primary_container="#5B58C7",
            on_primary_container="#F0EFFF",
            secondary=SECONDARY,
            on_secondary="#003A18",
            secondary_container="#1D6B35",
            on_secondary_container="#B3FFAE",
            tertiary="#74A9E3",
            on_tertiary="#002E59",
            tertiary_container="#063A6B",
            on_tertiary_container="#D3E5FF",
            error="#FFB1C1",
            on_error="#5E0023",
            error_container="#8E123F",
            on_error_container="#FFD9E2",
            surface=INK,
            on_surface="#E9F1FF",
            surface_container_lowest="#000F2B",
            surface_container_low="#061F45",
            surface_container="#0B2852",
            surface_container_high="#14345F",
            surface_container_highest="#1D406D",
            on_surface_variant="#C2D0E5",
            outline="#8B9AB1",
            outline_variant="#415675",
            inverse_surface="#E9F1FF",
            on_inverse_surface=INK,
            inverse_primary="#5B58C7",
            scrim="#000000",
        ),
        scaffold_bgcolor=INK,
        canvas_color=INK,
        card_bgcolor="#0B2852",
        divider_color="#415675",
        page_transitions=_transitions(),
        font_family="Inter",
    )


def configure_page(page: ft.Page, *, mode: ft.ThemeMode = ft.ThemeMode.SYSTEM) -> None:
    """Aplica os temas globais e configurações de acessibilidade à página."""
    page.theme = light_theme()
    page.dark_theme = dark_theme()
    page.theme_mode = mode
    page.padding = 0
    page.spacing = 0
    page.bgcolor = ft.Colors.SURFACE
    page.title = "Vault Site"


def toggle_theme(page: ft.Page) -> None:
    """Alterna entre claro e escuro, preservando SYSTEM como estado inicial."""
    page.theme_mode = (
        ft.ThemeMode.DARK if page.theme_mode != ft.ThemeMode.DARK else ft.ThemeMode.LIGHT
    )
    page.update()
