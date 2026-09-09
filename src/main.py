from __future__ import annotations

import flet as ft

from interfaces.views import BindingsInterface, DashboardInterface, ServicesInterface, route_page
from modules.theme import configure_page
from services.application import ApplicationService


def main(page: ft.Page) -> None:
    configure_page(page)
    service = ApplicationService()
    page.expand = True
    page.window.maximized = True
    page.on_disconnect = lambda _: service.close()

    def dashboard() -> ft.Control:
        return route_page(page=page, service=service, title="Visão geral", interface=DashboardInterface(service=service, page=page))

    def bindings() -> ft.Control:
        return route_page(page=page, service=service, title="Vínculos porta-câmera", interface=BindingsInterface(service=service, page=page))

    def services() -> ft.Control:
        return route_page(page=page, service=service, title="Serviços e conexões", interface=ServicesInterface(service=service, page=page))

    @ft.component
    def Root() -> ft.Control:
        return ft.Router(routes=[
            ft.Route(path="/", component=dashboard),
            ft.Route(path="/bindings", component=bindings),
            ft.Route(path="/services", component=services),
        ], not_found=dashboard)

    # Componentes declarativos precisam ser montados dentro do renderer.
    # page.add(ft.Router(...)) dispara "No current renderer is set".
    page.render(Root)


if __name__ == "__main__":
    ft.run(main)
