import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import flet as ft
from interfaces.app import AppShell


class FakePage:
    def __init__(self):
        self.theme_mode = ft.ThemeMode.SYSTEM
        self.added = []
        self.dialog = None

    def add(self, *controls):
        self.added.extend(controls)

    def update(self):
        pass


def test_shell_builds_without_external_requests():
    page = FakePage()
    shell = AppShell(page)
    assert shell._active_view == "dashboard"
    assert shell.title.value == "Visão geral"
    shell.show("bindings")
    assert shell.title.value == "Vínculos porta–câmera"
    shell.show("services")
    assert shell.title.value == "Serviços e conexões"
    shell.service.close()
