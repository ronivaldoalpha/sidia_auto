"""Controles declarativos de gráficos baseados em flet-charts 0.86.5."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import flet as ft
import flet_charts as fch

from .chart_models import AxisSpec, ChartData, ChartEvent, chart_axis, bounds, resolved_color

EventHandler = Callable[[ChartEvent], None]


def _event_handler(handler: EventHandler | None, event: object, chart_type: str, *, index: int | None = None, series: int | None = None, label: str | None = None, value: float | None = None) -> None:
    if handler:
        handler(ChartEvent(chart_type=chart_type, index=index, series=series, label=label, value=value, raw=event))


@ft.component
def ColumnChart(*, data: ChartData, bottom_axis: AxisSpec = AxisSpec(), left_axis: AxisSpec = AxisSpec(), interactive: bool = True, on_event: EventHandler | None = None, expand: bool = True, height: int | float | None = None) -> ft.Control:
    """Gráfico de colunas reativo às mudanças em ``ChartData.columns``."""
    values = list(data.columns)
    maximum = left_axis.maximum if left_axis.maximum is not None else max([1.0, *(item.value + item.failure for item in values)], default=1.0)
    groups = []
    for index, item in enumerate(values):
        rods = [fch.BarChartRod(from_y=0, to_y=item.value, color=resolved_color(item.color, index), tooltip=item.tooltip or f"{item.label}: sucesso", border_radius=4)]
        if item.failure:
            rods.append(fch.BarChartRod(from_y=0, to_y=item.failure, color=ft.Colors.ERROR, tooltip=f"{item.label}: falha", border_radius=4))
        groups.append(fch.BarChartGroup(x=index, rods=rods, spacing=4))
    labels = bottom_axis if bottom_axis.labels else replace(bottom_axis, labels=tuple((index, item.label) for index, item in enumerate(values)))
    def event(event: object) -> None:
        index = getattr(event, "group_index", None)
        item = values[index] if isinstance(index, int) and 0 <= index < len(values) else None
        _event_handler(on_event, event, "column", index=index, label=item.label if item else None, value=item.value if item else None)
    chart = fch.BarChart(groups=groups, bottom_axis=chart_axis(labels), left_axis=chart_axis(left_axis), max_y=maximum, min_y=left_axis.minimum, interactive=interactive, on_event=event if on_event else None, expand=expand, height=height)
    return chart


@ft.component
def LineChart(*, data: ChartData, bottom_axis: AxisSpec = AxisSpec(), left_axis: AxisSpec = AxisSpec(), interactive: bool = True, on_event: EventHandler | None = None, expand: bool = True, height: int | float | None = None) -> ft.Control:
    """Gráfico de linhas com múltiplas séries observáveis."""
    series = list(data.lines)
    points = [point for item in series for point in item.points]
    low_y, high_y = bounds([point.y for point in points], left_axis.minimum, left_axis.maximum)
    low_x, high_x = bounds([point.x for point in points], None, None)
    data_series = [fch.LineChartData(points=[fch.LineChartDataPoint(point.x, point.y, tooltip=point.tooltip or point.label) for point in item.points], color=resolved_color(item.color, index), curved=item.curved, stroke_width=item.stroke_width, point=True) for index, item in enumerate(series)]
    chart = fch.LineChart(data_series=data_series, min_x=low_x, max_x=high_x, min_y=low_y, max_y=high_y, bottom_axis=chart_axis(bottom_axis), left_axis=chart_axis(left_axis), interactive=interactive, on_event=lambda event: _event_handler(on_event, event, "line") if on_event else None, expand=expand, height=height)
    return chart


@ft.component
def DonutChart(*, data: ChartData, center_space_radius: float = 42, interactive: bool = True, on_event: EventHandler | None = None, expand: bool = True, height: int | float | None = None) -> ft.Control:
    """Gráfico de rosca baseado nas fatias de ``ChartData.donut``."""
    values = list(data.donut)
    sections = [fch.PieChartSection(value=item.value, title=item.title or item.label, color=resolved_color(item.color, index), radius=90) for index, item in enumerate(values)]
    def event(event: object) -> None:
        index = getattr(event, "section_index", None)
        item = values[index] if isinstance(index, int) and 0 <= index < len(values) else None
        _event_handler(on_event, event, "donut", index=index, label=item.label if item else None, value=item.value if item else None)
    # PieChart não possui a propriedade ``interactive``; a interação é
    # habilitada quando o callback de evento é fornecido.
    return fch.PieChart(sections=sections, center_space_radius=center_space_radius, sections_space=2, on_event=event if interactive and on_event else None, expand=expand, height=height)


__all__ = ["ColumnChart", "LineChart", "DonutChart", "EventHandler"]
