from __future__ import annotations

import flet as ft

from interfaces.views import BindingsInterface, DashboardInterface, DashboardReportInterface, ServicesInterface, route_page
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

    def dashboard_detail() -> ft.Control:
        return route_page(page=page, service=service, title="Relatório detalhado", interface=DashboardReportInterface(service=service, page=page))

    def services() -> ft.Control:
        return route_page(page=page, service=service, title="Serviços e conexões", interface=ServicesInterface(service=service, page=page))

    @ft.component
    def Root() -> ft.Control:
        return ft.Router(routes=[
            ft.Route(path="/", component=dashboard),
            ft.Route(path="/dashboard/detail", component=dashboard_detail),
            ft.Route(path="/bindings", component=bindings),
            ft.Route(path="/services", component=services),
        ], not_found=dashboard)

    # Componentes declarativos precisam ser montados dentro do renderer.
    # page.add(ft.Router(...)) dispara "No current renderer is set".
    page.render(Root)


if __name__ == "__main__":
    # Hash strategy evita que o servidor Web precise resolver cada rota
    # como um caminho físico e preserva deep links no Flet Web.
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=8601,route_url_strategy="hash")
