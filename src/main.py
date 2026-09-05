from __future__ import annotations

import flet as ft

from interfaces.app import AppShell
from modules.theme import configure_page


def main(page: ft.Page) -> None:
    configure_page(page)
    page.expand = True
    page.scroll = ft.ScrollMode.AUTO
    AppShell(page)


if __name__ == "__main__":
    ft.run(main)
