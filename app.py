"""
Finance App — Dash web app entry point.
Run with: python app.py
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dash_table, dcc, html
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import text

from auth import init_basic_auth
from db.connection import get_engine
from analytics.cashflow import category_breakdown, monthly_by_category, monthly_summary
from analytics.subscriptions import detect_recurring

# ── Data ─────────────────────────────────────────────────────────────────────

engine = get_engine()
df_monthly = monthly_summary(engine)
df_categories = category_breakdown(engine, months=3)
df_recurring = detect_recurring(engine)
df_monthly_cat = monthly_by_category(engine)

# ── Deep Dive dropdown options ────────────────────────────────────────────────

with engine.connect() as _conn:
    _months_df = pd.read_sql(text("""
        SELECT DISTINCT TO_CHAR(DATE_TRUNC('month', date), 'YYYY-MM') AS month
        FROM transactions
        ORDER BY month DESC
    """), _conn)
    _cats_df = pd.read_sql(text("""
        SELECT category, COUNT(*) AS cnt
        FROM transactions
        WHERE amount < 0
        GROUP BY category
        ORDER BY category
    """), _conn)

dd_month_options = [{"label": m, "value": m} for m in _months_df["month"]]
dd_month_default = _months_df["month"].iloc[0] if not _months_df.empty else None

dd_cat_options = [{"label": c, "value": c} for c in _cats_df["category"]]
dd_cat_default = (
    _cats_df.loc[_cats_df["cnt"].idxmax(), "category"]
    if not _cats_df.empty else None
)

# ── KPI calculations ──────────────────────────────────────────────────────────

avg_income = df_monthly["income"].mean() if not df_monthly.empty else 0
avg_expenses = df_monthly["expenses"].mean() if not df_monthly.empty else 0  # negative
avg_net = df_monthly["net"].mean() if not df_monthly.empty else 0
savings_rate = (avg_net / avg_income * 100) if avg_income > 0 else 0


def kpi_card(title: str, value: str, color: str = "white") -> dbc.Col:
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.P(title, className="text-muted mb-1", style={"fontSize": "0.85rem"}),
                html.H4(value, style={"color": color, "fontWeight": "bold"}),
            ]),
            className="h-100",
        ),
        xs=12, sm=6, lg=3,
    )


# ── Charts ────────────────────────────────────────────────────────────────────

PLOT_BGCOLOR = "#222"
PAPER_BGCOLOR = "#2b2b2b"
FONT_COLOR = "#e0e0e0"
GRID_COLOR = "#444"

BASE_LAYOUT = dict(
    paper_bgcolor=PAPER_BGCOLOR,
    plot_bgcolor=PLOT_BGCOLOR,
    font=dict(color=FONT_COLOR),
    margin=dict(l=40, r=20, t=40, b=40),
)


def fig_monthly_bar() -> go.Figure:
    if df_monthly.empty:
        return go.Figure(layout=BASE_LAYOUT)

    months = df_monthly["month"].astype(str)
    fig = go.Figure([
        go.Bar(name="Income",   x=months, y=df_monthly["income"],   marker_color="#2ecc71"),
        go.Bar(name="Expenses", x=months, y=df_monthly["expenses"],  marker_color="#e74c3c"),
        go.Bar(name="Net",      x=months, y=df_monthly["net"],       marker_color="#3498db"),
    ])
    fig.update_layout(
        **BASE_LAYOUT,
        title="Monthly Income vs Expenses vs Net",
        barmode="group",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor=GRID_COLOR, tickprefix="€"),
        legend=dict(orientation="h", y=1.1),
    )
    return fig


def fig_category_pie() -> go.Figure:
    if df_categories.empty:
        return go.Figure(layout=BASE_LAYOUT)

    fig = go.Figure(go.Pie(
        labels=df_categories["category"],
        values=df_categories["total"].abs(),
        hole=0.4,
        textinfo="label+percent",
        hovertemplate="%{label}<br>€%{value:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        **BASE_LAYOUT,
        title="Expenses by Category (last 3 months)",
        showlegend=True,
        legend=dict(orientation="v"),
    )
    return fig


def recurring_table() -> dash_table.DataTable:
    if df_recurring.empty:
        data, columns = [], []
    else:
        display = df_recurring.copy()
        display["amount"] = display["amount"].apply(lambda x: f"€{x:,.2f}")
        display["annual_cost"] = display["annual_cost"].apply(lambda x: f"€{x:,.2f}")
        data = display.to_dict("records")
        columns = [
            {"name": "Description", "id": "description"},
            {"name": "Amount",      "id": "amount"},
            {"name": "Frequency",   "id": "frequency"},
            {"name": "Annual Cost", "id": "annual_cost"},
        ]

    return dash_table.DataTable(
        data=data,
        columns=columns,
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#333",
            "color": FONT_COLOR,
            "fontWeight": "bold",
            "border": "1px solid #444",
        },
        style_cell={
            "backgroundColor": PLOT_BGCOLOR,
            "color": FONT_COLOR,
            "border": "1px solid #444",
            "padding": "8px 12px",
            "textAlign": "left",
        },
        style_data_conditional=[{
            "if": {"row_index": "odd"},
            "backgroundColor": "#2a2a2a",
        }],
        page_size=15,
    )


def monthly_category_table() -> dash_table.DataTable:
    if df_monthly_cat.empty:
        data, columns = [], []
    else:
        display = df_monthly_cat.copy()
        category_cols = [c for c in display.columns if c != "Month"]
        for col in category_cols:
            display[col] = display[col].apply(lambda x: f"€{x:,.2f}" if x else "—")
        data = display.to_dict("records")
        columns = [{"name": "Month", "id": "Month"}] + [
            {"name": c, "id": c} for c in category_cols
        ]

    return dash_table.DataTable(
        data=data,
        columns=columns,
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#333",
            "color": FONT_COLOR,
            "fontWeight": "bold",
            "border": "1px solid #444",
        },
        style_cell={
            "backgroundColor": PLOT_BGCOLOR,
            "color": FONT_COLOR,
            "border": "1px solid #444",
            "padding": "8px 12px",
            "textAlign": "right",
            "minWidth": "90px",
        },
        style_cell_conditional=[{
            "if": {"column_id": "Month"},
            "textAlign": "left",
            "fontWeight": "bold",
        }],
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#2a2a2a"},
            {"if": {"column_id": "Total"}, "fontWeight": "bold", "color": "#f39c12"},
        ],
        page_size=24,
    )


# ── Layout ────────────────────────────────────────────────────────────────────

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Finance Dashboard",
)
server = app.server  # WSGI entry point for gunicorn
init_basic_auth(server)

app.layout = dbc.Container([
    html.H2("Finance Dashboard", className="my-4"),

    # KPI row
    dbc.Row([
        kpi_card("Avg Monthly Income",   f"€{avg_income:,.2f}",        "#2ecc71"),
        kpi_card("Avg Monthly Expenses", f"€{abs(avg_expenses):,.2f}", "#e74c3c"),
        kpi_card("Avg Monthly Net",      f"€{avg_net:,.2f}",           "#3498db"),
        kpi_card("Savings Rate",         f"{savings_rate:.1f}%",       "#f39c12"),
    ], className="mb-4 g-3"),

    # Monthly bar chart
    dbc.Row(dbc.Col(
        dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_monthly_bar(), config={"displayModeBar": False}))),
    ), className="mb-4"),

    # Category pie + recurring table
    dbc.Row([
        dbc.Col(
            dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_category_pie(), config={"displayModeBar": False}))),
            xs=12, lg=5,
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H6("Recurring Transactions", className="mb-3"),
                recurring_table(),
            ])),
            xs=12, lg=7,
        ),
    ], className="mb-4 g-3"),

    # Expenses by month × category
    dbc.Row(dbc.Col(
        dbc.Card(dbc.CardBody([
            html.H6("Expenses by Month & Category", className="mb-3"),
            monthly_category_table(),
        ])),
    ), className="mb-4"),

    # Deep Dive
    dbc.Row(dbc.Col(
        dbc.Card(dbc.CardBody([
            html.H6("Deep Dive", className="mb-3"),
            dbc.Row([
                dbc.Col(
                    dcc.Dropdown(
                        id="dd-month",
                        options=dd_month_options,
                        value=dd_month_default,
                        clearable=False,
                        style={"color": "#000"},
                    ),
                    xs=12, md=3,
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="dd-category",
                        options=dd_cat_options,
                        value=dd_cat_default,
                        clearable=False,
                        style={"color": "#000"},
                    ),
                    xs=12, md=3,
                ),
            ], className="mb-3 g-2"),
            dash_table.DataTable(
                id="deep-dive-table",
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#333",
                    "color": FONT_COLOR,
                    "fontWeight": "bold",
                    "border": "1px solid #444",
                },
                style_cell={
                    "backgroundColor": PLOT_BGCOLOR,
                    "color": FONT_COLOR,
                    "border": "1px solid #444",
                    "padding": "8px 12px",
                    "textAlign": "left",
                },
                style_cell_conditional=[{
                    "if": {"column_id": "amount"},
                    "textAlign": "right",
                }],
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#2a2a2a"},
                    {"if": {"filter_query": '{date} = "Total"'},
                     "fontWeight": "bold", "color": "#f39c12", "backgroundColor": "#2b2b2b"},
                ],
                page_size=50,
            ),
        ])),
    ), className="mb-4"),

], fluid=True)


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("deep-dive-table", "data"),
    Output("deep-dive-table", "columns"),
    Input("dd-month", "value"),
    Input("dd-category", "value"),
)
def update_deep_dive(month: str, category: str):
    if not month or not category:
        return [], []

    sql = text("""
        SELECT
            date::text      AS date,
            bank,
            description,
            amount
        FROM transactions
        WHERE TO_CHAR(DATE_TRUNC('month', date), 'YYYY-MM') = :month
          AND category = :category
        ORDER BY date DESC
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params={"month": month, "category": category})

    if df.empty:
        return [], []

    total = df["amount"].sum()
    df["amount"] = df["amount"].apply(lambda x: f"€{x:,.2f}")

    totals_row = {"date": "Total", "bank": "", "description": "", "amount": f"€{total:,.2f}"}
    records = df.to_dict("records") + [totals_row]

    columns = [
        {"name": "Date",        "id": "date"},
        {"name": "Bank",        "id": "bank"},
        {"name": "Description", "id": "description"},
        {"name": "Amount",      "id": "amount"},
    ]
    return records, columns


if __name__ == "__main__":
    app.run(debug=True)
