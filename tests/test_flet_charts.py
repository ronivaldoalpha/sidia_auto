import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from modules.flet_charts import AxisSpec, ChartData, ColumnDatum, DonutDatum, LinePoint, LineSeries


def test_chart_data_is_observable_and_mutable_by_replacement():
    data = ChartData(columns=[ColumnDatum("A", 10)])
    data.set_columns([ColumnDatum("B", 20)])
    data.set_lines([LineSeries("Falhas", (LinePoint(1, 3),))])
    data.set_donut([DonutDatum("Online", 8)])
    assert data.columns[0].label == "B"
    assert data.lines[0].points[0].y == 3
    assert data.donut[0].value == 8


def test_axis_spec_has_explicit_labels_and_bounds():
    axis = AxisSpec(title="Falhas", minimum=0, maximum=100, labels=((0, "Jan"), (1, "Fev")))
    assert axis.title == "Falhas"
    assert axis.labels[1][1] == "Fev"
