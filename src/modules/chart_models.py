"""Modelos observáveis e independentes da camada visual dos gráficos."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import flet as ft


@dataclass(frozen=True, slots=True)
class AxisSpec:
    """Configuração semântica de um eixo do gráfico."""

    title: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    labels: tuple[tuple[float, str], ...] = ()
    show_labels: bool = True
    label_size: int = 36
    title_size: int = 32


@dataclass(frozen=True, slots=True)
class ColumnDatum:
    label: str
    value: float
    color: str | ft.Colors | None = None
    tooltip: str | None = None


@dataclass(frozen=True, slots=True)
class LinePoint:
    x: float
    y: float
    label: str | None = None
    tooltip: str | None = None


@dataclass(frozen=True, slots=True)
class LineSeries:
    name: str
    points: tuple[LinePoint, ...]
    color: str | ft.Colors | None = None
    curved: bool = True
    stroke_width: float = 3


@dataclass(frozen=True, slots=True)
class DonutDatum:
    label: str
    value: float
    color: str | ft.Colors | None = None
    title: str | None = None


@ft.observable
class ChartData:
    """Store reativo compartilhado pelos componentes de gráfico."""

    def __init__(
        self,
        *,
        columns: Sequence[ColumnDatum] = (),
        lines: Sequence[LineSeries] = (),
        donut: Sequence[DonutDatum] = (),
    ) -> None:
        self.columns = list(columns)
        self.lines = list(lines)
        self.donut = list(donut)

    def set_columns(self, values: Sequence[ColumnDatum]) -> None:
        self.columns = list(values)

    def set_lines(self, values: Sequence[LineSeries]) -> None:
        self.lines = list(values)

    def set_donut(self, values: Sequence[DonutDatum]) -> None:
        self.donut = list(values)

    def clear(self) -> None:
        self.columns = []
        self.lines = []
        self.donut = []


DEFAULT_CHART_COLORS: tuple[str, ...] = (
    "#7D79EF", "#7AF27A", "#0A4B89", "#011B49", "#C86B00", "#B455D9",
)


def resolved_color(value: str | ft.Colors | None, index: int) -> str | ft.Colors:
    return value or DEFAULT_CHART_COLORS[index % len(DEFAULT_CHART_COLORS)]


def axis_labels(spec: AxisSpec):
    import flet_charts as fch

    return [fch.ChartAxisLabel(value=value, label=ft.Text(label)) for value, label in spec.labels]


def chart_axis(spec: AxisSpec):
    import flet_charts as fch

    kwargs: dict[str, object] = {
        "show_labels": spec.show_labels,
        "label_size": spec.label_size,
        "title_size": spec.title_size,
    }
    if spec.title:
        kwargs["title"] = ft.Text(spec.title)
    if spec.labels:
        kwargs["labels"] = axis_labels(spec)
    return fch.ChartAxis(**kwargs)


def bounds(values: Sequence[float], minimum: float | None, maximum: float | None) -> tuple[float, float]:
    if not values:
        return minimum if minimum is not None else 0, maximum if maximum is not None else 1
    low = minimum if minimum is not None else min(0.0, min(values))
    high = maximum if maximum is not None else max(1.0, max(values))
    return low, high


__all__ = [
    "AxisSpec", "ColumnDatum", "LinePoint", "LineSeries", "DonutDatum", "ChartData",
    "DEFAULT_CHART_COLORS", "resolved_color", "chart_axis", "bounds",
]


@dataclass(slots=True)
class ChartEvent:
    """Evento normalizado para o callback opcional da camada de aplicação."""

    chart_type: str
    index: int | None = None
    series: int | None = None
    label: str | None = None
    value: float | None = None
    raw: object | None = None
