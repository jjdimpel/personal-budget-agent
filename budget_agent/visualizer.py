"""
Visualizer: generates interactive Plotly charts for budget analysis.

Charts available:
  - budget_vs_spent_bar   : Grouped bar — budget vs. actual per category
  - spending_pie          : Pie chart of spending breakdown
  - monthly_trend_line    : Line chart of category spending over months
  - daily_spending_bar    : Bar chart of daily spending for a month
  - budget_gauge          : Overall budget utilization gauge
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


_COLORS = px.colors.qualitative.Set3
_OVER_BUDGET_COLOR = "#e74c3c"
_UNDER_BUDGET_COLOR = "#2ecc71"
_BUDGET_LINE_COLOR = "#3498db"


class BudgetVisualizer:
    """Generate interactive Plotly visualizations from tracker data."""

    def __init__(self, output_dir: str | Path = "charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Budget vs. Spent bar chart
    # ------------------------------------------------------------------

    def budget_vs_spent(
        self,
        summary_df: pd.DataFrame,
        title: str = "Budget vs. Actual Spending by Category",
        save: bool = True,
    ) -> go.Figure:
        """Grouped bar chart comparing budget to actual spending per category."""
        df = summary_df.sort_values("Spent", ascending=False)

        colors = [
            _OVER_BUDGET_COLOR if row["Remaining"] < 0 else _UNDER_BUDGET_COLOR
            for _, row in df.iterrows()
        ]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Budget",
            x=df["Category"],
            y=df["Budget"],
            marker_color=_BUDGET_LINE_COLOR,
            opacity=0.6,
        ))
        fig.add_trace(go.Bar(
            name="Spent",
            x=df["Category"],
            y=df["Spent"],
            marker_color=colors,
            text=[f"${v:,.0f}" for v in df["Spent"]],
            textposition="outside",
        ))

        fig.update_layout(
            title=title,
            barmode="group",
            xaxis_title="Category",
            yaxis_title="Amount ($)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template="plotly_white",
            height=500,
        )

        if save:
            self._save(fig, "budget_vs_spent.html")
        return fig

    # ------------------------------------------------------------------
    # Spending pie chart
    # ------------------------------------------------------------------

    def spending_pie(
        self,
        summary_df: pd.DataFrame,
        title: str = "Spending Breakdown by Category",
        save: bool = True,
    ) -> go.Figure:
        df = summary_df[summary_df["Spent"] > 0]

        fig = px.pie(
            df,
            names="Category",
            values="Spent",
            title=title,
            color_discrete_sequence=_COLORS,
            hole=0.3,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(template="plotly_white", height=500)

        if save:
            self._save(fig, "spending_pie.html")
        return fig

    # ------------------------------------------------------------------
    # Monthly trend line chart
    # ------------------------------------------------------------------

    def monthly_trend(
        self,
        trend_df: pd.DataFrame,
        title: str = "Monthly Spending Trend by Category",
        save: bool = True,
    ) -> go.Figure:
        if trend_df.empty:
            return go.Figure()

        fig = px.line(
            trend_df,
            x="Month",
            y="Spent",
            color="Category",
            markers=True,
            title=title,
            color_discrete_sequence=_COLORS,
        )
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Amount Spent ($)",
            template="plotly_white",
            height=500,
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01),
        )

        if save:
            self._save(fig, "monthly_trend.html")
        return fig

    # ------------------------------------------------------------------
    # Daily spending bar
    # ------------------------------------------------------------------

    def daily_spending(
        self,
        daily_df: pd.DataFrame,
        budget: Optional[float] = None,
        title: str = "Daily Spending",
        save: bool = True,
    ) -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily_df["Date"].astype(str),
            y=daily_df["Spent"],
            name="Daily Spending",
            marker_color=_BUDGET_LINE_COLOR,
        ))

        if budget is not None:
            daily_budget = budget / 30
            fig.add_hline(
                y=daily_budget,
                line_dash="dash",
                line_color=_OVER_BUDGET_COLOR,
                annotation_text=f"Daily target (${daily_budget:,.0f})",
            )

        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Amount Spent ($)",
            template="plotly_white",
            height=400,
        )

        if save:
            self._save(fig, "daily_spending.html")
        return fig

    # ------------------------------------------------------------------
    # Percent-used horizontal bar
    # ------------------------------------------------------------------

    def percent_used(
        self,
        summary_df: pd.DataFrame,
        title: str = "Budget Utilization (%)",
        save: bool = True,
    ) -> go.Figure:
        df = summary_df[summary_df["Budget"] > 0].sort_values("Percent Used", ascending=True)

        colors = [
            _OVER_BUDGET_COLOR if pct > 100 else (_BUDGET_LINE_COLOR if pct > 80 else _UNDER_BUDGET_COLOR)
            for pct in df["Percent Used"]
        ]

        fig = go.Figure(go.Bar(
            x=df["Percent Used"],
            y=df["Category"],
            orientation="h",
            marker_color=colors,
            text=[f"{p:.0f}%" for p in df["Percent Used"]],
            textposition="outside",
        ))

        fig.add_vline(x=100, line_dash="dash", line_color="black", annotation_text="100%")
        fig.update_layout(
            title=title,
            xaxis_title="% of Budget Used",
            template="plotly_white",
            height=max(400, len(df) * 35),
        )

        if save:
            self._save(fig, "percent_used.html")
        return fig

    # ------------------------------------------------------------------
    # Dashboard: all charts in one HTML
    # ------------------------------------------------------------------

    def dashboard(
        self,
        summary_df: pd.DataFrame,
        trend_df: Optional[pd.DataFrame] = None,
        daily_df: Optional[pd.DataFrame] = None,
        total_budget: Optional[float] = None,
        period_label: str = "",
        save: bool = True,
    ) -> go.Figure:
        """Combine key charts into a single dashboard figure."""
        rows = 2 + (1 if trend_df is not None and not trend_df.empty else 0)
        row_heights = [0.4, 0.3] + ([0.3] if rows == 3 else [])

        fig = make_subplots(
            rows=rows,
            cols=2,
            subplot_titles=(
                "Budget vs. Spent",
                "Spending Breakdown",
                "Budget Utilization",
                "Top Spending Categories",
                *(["Monthly Trend", "Daily Spending"] if rows == 3 else []),
            ),
            row_heights=row_heights,
            vertical_spacing=0.12,
            horizontal_spacing=0.08,
        )

        # Row 1 col 1: budget vs spent bars
        df_sorted = summary_df.sort_values("Spent", ascending=False)
        fig.add_trace(go.Bar(name="Budget", x=df_sorted["Category"], y=df_sorted["Budget"],
                             marker_color=_BUDGET_LINE_COLOR, opacity=0.6, showlegend=False),
                      row=1, col=1)
        fig.add_trace(go.Bar(name="Spent", x=df_sorted["Category"], y=df_sorted["Spent"],
                             marker_color=[_OVER_BUDGET_COLOR if r < 0 else _UNDER_BUDGET_COLOR
                                           for r in df_sorted["Remaining"]],
                             showlegend=False),
                      row=1, col=1)

        # Row 1 col 2: pie
        df_pie = summary_df[summary_df["Spent"] > 0]
        fig.add_trace(go.Pie(labels=df_pie["Category"], values=df_pie["Spent"],
                             hole=0.3, showlegend=False,
                             textinfo="percent+label"),
                      row=1, col=2)

        # Row 2 col 1: percent used
        df_pct = summary_df[summary_df["Budget"] > 0].sort_values("Percent Used", ascending=True)
        colors_pct = [_OVER_BUDGET_COLOR if p > 100 else (_BUDGET_LINE_COLOR if p > 80 else _UNDER_BUDGET_COLOR)
                      for p in df_pct["Percent Used"]]
        fig.add_trace(go.Bar(x=df_pct["Percent Used"], y=df_pct["Category"],
                             orientation="h", marker_color=colors_pct, showlegend=False,
                             text=[f"{p:.0f}%" for p in df_pct["Percent Used"]],
                             textposition="outside"),
                      row=2, col=1)

        # Row 2 col 2: top categories table
        top = summary_df.nlargest(8, "Spent")[["Category", "Spent", "Budget", "Remaining"]]
        fig.add_trace(go.Table(
            header=dict(values=["Category", "Spent", "Budget", "Remaining"],
                        fill_color="#3498db", font_color="white", align="left"),
            cells=dict(
                values=[top["Category"],
                        [f"${v:,.0f}" for v in top["Spent"]],
                        [f"${v:,.0f}" for v in top["Budget"]],
                        [f"${v:,.0f}" for v in top["Remaining"]]],
                fill_color=[["white", "#f2f2f2"] * (len(top) // 2 + 1)],
                align="left",
            ),
        ), row=2, col=2)

        title = "Personal Budget Dashboard"
        if period_label:
            title += f" — {period_label}"

        fig.update_layout(
            title_text=title,
            barmode="group",
            height=800 + (300 if rows == 3 else 0),
            template="plotly_white",
        )

        if save:
            self._save(fig, "dashboard.html")
        return fig

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _save(self, fig: go.Figure, filename: str) -> Path:
        path = self.output_dir / filename
        fig.write_html(str(path))
        return path
