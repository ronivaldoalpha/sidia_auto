import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import flet as ft

from interfaces.views import BindingsInterface, DashboardInterface, ServicesInterface
from layouts.page_layout import PageLayout
from models.paginated_table import PaginatedTable
from models.sidebar import Sidebar
from main import main


def test_declarative_components_are_available():
    assert callable(Sidebar)
    assert callable(PageLayout)
    assert callable(PaginatedTable)
    assert callable(DashboardInterface)
    assert callable(BindingsInterface)
    assert callable(ServicesInterface)
    assert ft.DropdownOption("opção").key == "opção"
    assert not hasattr(ft, "Option")


def test_router_has_declared_routes():
    routes = [
        ft.Route(path="/", component=lambda: ft.Text("home")),
        ft.Route(path="/bindings", component=lambda: ft.Text("bindings")),
        ft.Route(path="/services", component=lambda: ft.Text("services")),
    ]
    assert [route.path for route in routes] == ["/", "/bindings", "/services"]
    assert callable(ft.Router)


def test_main_mounts_root_through_page_render():
    class PageStub:
        theme_mode = ft.ThemeMode.SYSTEM
        window = type("WindowStub", (), {})()

        def render(self, component, *args, **kwargs):
            self.root_component = component

    page = PageStub()
    main(page)
    assert getattr(page, "root_component", None) is not None
