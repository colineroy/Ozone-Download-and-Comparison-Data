import os
import sys
import threading
import concurrent.futures
import traceback
from datetime import datetime, date

import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gs_comparison import (
    read_saoz_raw, read_pandora_raw, read_bts_raw,
    read_sonde_raw, read_s5p_raw, read_gome2_raw,
    read_brewer_raw, read_omi_total_column, read_omps_total_column,
    STYLES,
)

_MARKER_MAP = {
    "s": "square",
    "o": "circle",
    "^": "triangle-up",
    "D": "diamond",
    "v": "triangle-down",
    ".": "circle",
}

READERS = [
    ("SAOZ",    read_saoz_raw,          False),
    ("Pandora", read_pandora_raw,       False),
    ("BTS",     read_bts_raw,           False),
    ("Sonde",   read_sonde_raw,         False),
    ("S5P",     read_s5p_raw,           False),
    ("GOME2",   read_gome2_raw,         True),
    ("Brewer",  read_brewer_raw,        True),
    ("OMI",     read_omi_total_column,  False),
    ("OMPS",    read_omps_total_column, False),
]

_reader_cache = {}
_cache_lock = threading.Lock()

def _filter_by_date(data, returns_dict, dt_start, dt_end):
    if returns_dict:
        result = {}
        for k, pts in data.items():
            filtered = [p for p in pts if dt_start <= p[0].date() <= dt_end]
            if filtered:
                result[k] = filtered
        return result
    return [p for p in data if dt_start <= p[0].date() <= dt_end]

def load_all_data(dt_start, dt_end):
    result = {}
    futures = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for name, reader, returns_dict in READERS:
            with _cache_lock:
                if name in _reader_cache:
                    cached_data, c_start, c_end = _reader_cache[name]
                    if dt_start >= c_start and dt_end <= c_end:
                        r = _filter_by_date(cached_data, returns_dict, dt_start, dt_end)
                        if r:
                            result.update(r if returns_dict else {name: r})
                        continue
            print(f"  Loading {name}...")
            futures[name] = (ex.submit(reader, dt_start, dt_end), returns_dict)

        for name, (fut, returns_dict) in futures.items():
            try:
                all_data = fut.result()
            except Exception as e:
                print(f"    [!] {name} failed: {e}")
                continue
            with _cache_lock:
                _reader_cache[name] = (all_data, dt_start, dt_end)
            r = _filter_by_date(all_data, returns_dict, dt_start, dt_end)
            if r:
                result.update(r if returns_dict else {name: r})

    counts = {k: len(v) for k, v in result.items() if v}
    if counts:
        print(f"  -> {', '.join(f'{k}={v}' for k,v in counts.items())}")
    return result


def _clear_cache():
    with _cache_lock:
        _reader_cache.clear()
    print("  [cache cleared]")


app = dash.Dash(__name__)
app.title = "NDACC — Sodankyla O3 Comparison"

DEFAULT_START = date(2026, 4, 10)
DEFAULT_END   = date(2026, 4, 17)

app.layout = html.Div([
    html.H3("Sodankyla — Ozone Total Column Comparison"),
    html.Div([
        html.Label("Du:"),
        dcc.DatePickerSingle(id="date-start", date=DEFAULT_START,
                             display_format="YYYY-MM-DD",
                             style={"margin-right": "8px"}),
        html.Label("au:", style={"margin-left": "12px"}),
        dcc.DatePickerSingle(id="date-end", date=DEFAULT_END,
                             display_format="YYYY-MM-DD",
                             style={"margin-right": "16px"}),
        html.Button("Vider cache", id="clear-cache-btn", n_clicks=0,
                    style={"margin-left": "16px"}),
    ], style={"margin-bottom": "10px"}),
    dcc.Loading(
        id="loading",
        type="circle",
        color="#1f77b4",
        children=dcc.Graph(id="main-graph", style={"height": "75vh"}),
    ),
    html.Div(
        "No data for the selected period.",
        id="no-data-msg",
        style={"display": "none", "text-align": "center", "font-size": "18px",
               "color": "#888", "margin-top": "40px"},
    ),
])


@app.callback(
    Output("main-graph", "figure"),
    Output("no-data-msg", "style"),
    Input("date-start", "date"),
    Input("date-end", "date"),
    Input("clear-cache-btn", "n_clicks"),
)
def update_graph(start_str, end_str, _clicks):
    no_data_style = {"display": "none", "text-align": "center", "font-size": "18px",
                     "color": "#888", "margin-top": "40px"}
    try:
        if not start_str or not end_str:
            return go.Figure(), no_data_style
        try:
            start_date = datetime.strptime(start_str[:10], "%Y-%m-%d").date()
            end_date   = datetime.strptime(end_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return go.Figure(), no_data_style
        if start_date > end_date:
            return go.Figure(), no_data_style

        ctx = dash.callback_context
        if ctx.triggered and "clear-cache-btn" in ctx.triggered[0]["prop_id"]:
            _clear_cache()

        data = load_all_data(start_date, end_date)

        fig = go.Figure()
        for key in sorted(data.keys()):
            pts = data[key]
            if not pts:
                continue
            style = STYLES.get(key, {"color": "#999", "marker": "o", "label": key})
            dts = [p[0] for p in pts]
            vals = [p[1] for p in pts]
            marker = _MARKER_MAP.get(style.get("marker", "o"), "circle")
            fig.add_trace(go.Scattergl(
                x=dts, y=vals,
                mode="markers",
                name=style["label"],
                marker=dict(
                    color=style["color"],
                    symbol=marker,
                    size=6,
                    line=dict(width=0.5, color="rgba(0,0,0,0.3)"),
                ),
                hovertemplate=(
                    f"<b>{style['label']}</b><br>"
                    "Date: %{x|%Y-%m-%d %H:%M}<br>"
                    "O3: %{y:.1f} DU<br>"
                    "<extra></extra>"
                ),
            ))

        fig.update_layout(
            title=f"Sodankyla O<sub>3</sub> Total Column &mdash; {start_date} &rarr; {end_date}",
            xaxis_title="Datetime",
            yaxis_title="Total Ozone (DU)",
            template="plotly_white",
            hovermode="closest",
            hoverlabel=dict(bgcolor="white", font_size=13),
            legend=dict(
                title=dict(text="Instrument"),
                itemsizing="constant",
            ),
            margin=dict(l=60, r=30, t=50, b=60),
        )
        fig.update_xaxes(
            range=[datetime(start_date.year, start_date.month, start_date.day),
                   datetime(end_date.year, end_date.month, end_date.day, 23, 59)],
        )
        fig.update_yaxes(title="Total Ozone (DU)")
        has_any = any(len(v) > 0 for v in data.values())
        if not has_any:
            return fig, {"display": "block", "text-align": "center", "font-size": "18px",
                         "color": "#888", "margin-top": "40px"}
        return fig, no_data_style
    except Exception:
        traceback.print_exc()
        return go.Figure(), no_data_style


if __name__ == "__main__":
    print("Starting GUI at http://127.0.0.1:8050")
    print("First load is slow (GOME2 ~38s); subsequent date changes within range are instant.")
    print("Press Ctrl+C to stop.")
    app.run(debug=False, host="127.0.0.1", port=8050)
