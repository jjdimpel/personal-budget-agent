"""
Conversational budget agent powered by Claude.

The agent exposes tools that Claude can call:
  - load_budget           : Load budget from an Excel file
  - load_credit_card      : Ingest a credit card CSV
  - load_venmo            : Ingest a Venmo CSV
  - get_summary           : Get spending vs. budget summary (optional month filter)
  - get_top_transactions  : Get the largest individual transactions
  - get_monthly_trend     : Month-over-month spending data
  - add_category_mapping  : Teach the agent a new keyword → category mapping
  - generate_charts       : Render all charts to the output directory
  - get_status            : Report what data is currently loaded

Usage:
    from budget_agent import BudgetAgent
    agent = BudgetAgent()
    agent.chat("Load my budget from budget.xlsx")
    agent.chat("Load my Chase credit card from chase_jan.csv")
    agent.chat("How am I doing on groceries this month?")
    agent.chat("Show me a spending breakdown chart")
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import anthropic
import pandas as pd
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .budget import BudgetLoader
from .transactions import TransactionParser
from .tracker import BudgetTracker
from .visualizer import BudgetVisualizer


console = Console()


SYSTEM_PROMPT = """You are a helpful personal finance assistant. You help the user track their spending against their budget.

You have access to tools to:
- Load a budget from an Excel file
- Ingest credit card and Venmo transaction CSVs
- Analyze spending vs. budget by category
- Find the largest transactions
- Show monthly spending trends
- Generate interactive charts

When the user asks about their finances, use the appropriate tool(s) to get the data and provide clear, actionable insights.
Always be encouraging but honest about overspending. Format monetary amounts with dollar signs and commas.
When showing summaries, highlight categories that are over budget (in red) and categories with good savings (in green).
If charts are generated, tell the user where they were saved."""


TOOLS: list[dict] = [
    {
        "name": "load_budget",
        "description": "Load the baseline budget from an Excel file. Must be called before analysis tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the Excel budget file (e.g. 'budget.xlsx')",
                }
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "load_credit_card",
        "description": "Ingest a credit card CSV export. Supports Chase, Capital One, and generic formats.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the credit card CSV file",
                },
                "source_label": {
                    "type": "string",
                    "description": "Label for this card (e.g. 'Chase Sapphire', 'Capital One'). Defaults to 'credit_card'.",
                },
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "load_venmo",
        "description": "Ingest a Venmo CSV export.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to the Venmo CSV export file",
                }
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "get_summary",
        "description": "Get a spending vs. budget summary by category. Optionally filter to a specific month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "Filter to this year (e.g. 2024). Omit for all time.",
                },
                "month": {
                    "type": "integer",
                    "description": "Filter to this month number 1-12 (e.g. 1 = January). Omit for all time.",
                },
            },
        },
    },
    {
        "name": "get_top_transactions",
        "description": "Get the largest individual transactions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {
                    "type": "integer",
                    "description": "Number of transactions to return (default 10)",
                },
                "year": {"type": "integer", "description": "Filter to this year"},
                "month": {"type": "integer", "description": "Filter to this month (1-12)"},
            },
        },
    },
    {
        "name": "get_monthly_trend",
        "description": "Get month-over-month spending broken down by category.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_category_mapping",
        "description": "Teach the agent to map certain keywords in transaction descriptions to a budget category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "budget_category": {
                    "type": "string",
                    "description": "The budget category name (must match one in the loaded budget)",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of keywords/merchant names to map to this category",
                },
            },
            "required": ["budget_category", "keywords"],
        },
    },
    {
        "name": "generate_charts",
        "description": "Generate all budget visualization charts as interactive HTML files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Filter charts to this year"},
                "month": {"type": "integer", "description": "Filter charts to this month (1-12)"},
                "output_dir": {
                    "type": "string",
                    "description": "Directory to save charts (default: 'charts')",
                },
            },
        },
    },
    {
        "name": "get_status",
        "description": "Report what budget and transaction data is currently loaded.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


class BudgetAgent:
    """Conversational budget tracking agent backed by Claude."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._model = model
        self._history: list[dict] = []

        # State
        self._budget_loader: Optional[BudgetLoader] = None
        self._budget: dict[str, float] = {}
        self._parser = TransactionParser()
        self._tracker: Optional[BudgetTracker] = None

    # ------------------------------------------------------------------
    # Public chat interface
    # ------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """Send a message and get a response. Handles tool calls automatically."""
        console.print(Panel(user_message, title="[bold blue]You[/bold blue]", border_style="blue"))

        self._history.append({"role": "user", "content": user_message})

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=self._history,
        )

        # Agentic loop: keep going until stop_reason is not tool_use
        while response.stop_reason == "tool_use":
            # Collect assistant message
            assistant_content = response.content
            self._history.append({"role": "assistant", "content": assistant_content})

            # Process each tool call
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    result = self._dispatch_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            self._history.append({"role": "user", "content": tool_results})

            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self._history,
            )

        # Extract final text response
        final_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        self._history.append({"role": "assistant", "content": response.content})

        console.print(Panel(Markdown(final_text), title="[bold green]Budget Agent[/bold green]", border_style="green"))
        return final_text

    def reset(self) -> None:
        """Clear conversation history and loaded data."""
        self._history = []
        self._budget_loader = None
        self._budget = {}
        self._parser.clear()
        self._tracker = None
        console.print("[yellow]Agent reset. All data cleared.[/yellow]")

    # ------------------------------------------------------------------
    # Tool dispatcher
    # ------------------------------------------------------------------

    def _dispatch_tool(self, name: str, inputs: dict) -> str:
        console.print(f"  [dim]→ Tool: {name}({json.dumps(inputs, default=str)})[/dim]")
        try:
            handler = getattr(self, f"_tool_{name}")
            result = handler(**inputs)
            return result
        except Exception as e:
            return f"Error in tool '{name}': {e}"

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _tool_load_budget(self, filepath: str) -> str:
        self._budget_loader = BudgetLoader(filepath)
        self._budget = self._budget_loader.load()
        self._rebuild_tracker()
        cats = "\n".join(f"  - {k}: ${v:,.0f}" for k, v in self._budget.items())
        total = sum(self._budget.values())
        return (
            f"Budget loaded from '{filepath}'.\n"
            f"Total monthly budget: ${total:,.0f}\n"
            f"Categories:\n{cats}"
        )

    def _tool_load_credit_card(self, filepath: str, source_label: str = "credit_card") -> str:
        self._parser.load_credit_card(filepath, source_label)
        df = self._parser.dataframe
        count = len(df[df["source"] == source_label]) if not df.empty else 0
        self._rebuild_tracker()
        date_range = ""
        if not df.empty:
            subset = df[df["source"] == source_label]
            if not subset.empty:
                date_range = f" ({subset['date'].min().date()} to {subset['date'].max().date()})"
        return f"Loaded {count} transactions from '{filepath}' (source: {source_label}){date_range}."

    def _tool_load_venmo(self, filepath: str) -> str:
        self._parser.load_venmo(filepath)
        df = self._parser.dataframe
        count = len(df[df["source"] == "venmo"]) if not df.empty else 0
        self._rebuild_tracker()
        date_range = ""
        if not df.empty:
            subset = df[df["source"] == "venmo"]
            if not subset.empty:
                date_range = f" ({subset['date'].min().date()} to {subset['date'].max().date()})"
        return f"Loaded {count} Venmo transactions from '{filepath}'{date_range}."

    def _tool_get_summary(self, year: Optional[int] = None, month: Optional[int] = None) -> str:
        if not self._tracker:
            return "No data loaded yet. Please load a budget and transactions first."
        summary = self._tracker.summary(year, month)
        total_spent = self._tracker.total_spent(year, month)
        total_budget = self._tracker.total_budget()

        lines = [f"Spending Summary (Total: ${total_spent:,.2f} / ${total_budget:,.2f} budgeted)\n"]
        lines.append(f"{'Category':<22} {'Budget':>10} {'Spent':>10} {'Remaining':>12} {'% Used':>8}")
        lines.append("-" * 66)
        for _, row in summary.iterrows():
            flag = " ⚠️" if row["Remaining"] < 0 else ""
            lines.append(
                f"{row['Category']:<22} ${row['Budget']:>9,.0f} ${row['Spent']:>9,.2f}"
                f" ${row['Remaining']:>11,.2f} {row['Percent Used']:>7.1f}%{flag}"
            )
        return "\n".join(lines)

    def _tool_get_top_transactions(
        self,
        n: int = 10,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> str:
        if not self._tracker:
            return "No data loaded yet."
        top = self._tracker.top_transactions(n, year, month)
        if top.empty:
            return "No transactions found for the specified period."
        lines = [f"Top {n} Transactions:\n"]
        lines.append(f"{'Date':<12} {'Description':<35} {'Amount':>10} {'Category':<20} {'Source'}")
        lines.append("-" * 90)
        for _, row in top.iterrows():
            lines.append(
                f"{str(row['date'].date()):<12} {str(row['description'])[:34]:<35}"
                f" ${row['amount']:>9,.2f} {str(row['budget_category']):<20} {row['source']}"
            )
        return "\n".join(lines)

    def _tool_get_monthly_trend(self) -> str:
        if not self._tracker:
            return "No data loaded yet."
        trend = self._tracker.monthly_trend()
        if trend.empty:
            return "No trend data available."
        summary = trend.groupby("Month")["Spent"].sum().reset_index()
        lines = ["Monthly Spending Totals:\n"]
        for _, row in summary.iterrows():
            lines.append(f"  {row['Month']}: ${row['Spent']:,.2f}")
        return "\n".join(lines)

    def _tool_add_category_mapping(self, budget_category: str, keywords: list[str]) -> str:
        if not self._tracker:
            return "Please load a budget first before adding mappings."
        self._tracker.add_mapping(budget_category, keywords)
        return f"Added {len(keywords)} keyword(s) → '{budget_category}': {', '.join(keywords)}"

    def _tool_generate_charts(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        output_dir: str = "charts",
    ) -> str:
        if not self._tracker:
            return "No data loaded yet. Please load a budget and transactions first."

        viz = BudgetVisualizer(output_dir=output_dir)
        summary = self._tracker.summary(year, month)
        trend = self._tracker.monthly_trend()
        daily = self._tracker.spending_by_day(year, month)
        total_budget = self._tracker.total_budget()

        period = ""
        if year and month:
            import calendar
            period = f"{calendar.month_name[month]} {year}"
        elif year:
            period = str(year)

        viz.budget_vs_spent(summary, save=True)
        viz.spending_pie(summary, save=True)
        viz.monthly_trend(trend, save=True)
        viz.daily_spending(daily, budget=total_budget / 12, save=True)
        viz.percent_used(summary, save=True)
        viz.dashboard(summary, trend, daily, total_budget, period_label=period, save=True)

        charts = [
            "budget_vs_spent.html",
            "spending_pie.html",
            "monthly_trend.html",
            "daily_spending.html",
            "percent_used.html",
            "dashboard.html",
        ]
        chart_list = "\n".join(f"  - {output_dir}/{c}" for c in charts)
        return f"Generated 6 charts in '{output_dir}/':\n{chart_list}\nOpen the HTML files in your browser to view interactive charts."

    def _tool_get_status(self) -> str:
        budget_status = (
            f"Loaded ({len(self._budget)} categories, total ${sum(self._budget.values()):,.0f}/mo)"
            if self._budget
            else "Not loaded"
        )
        df = self._parser.dataframe
        if df.empty:
            tx_status = "No transactions loaded"
        else:
            sources = df["source"].value_counts().to_dict()
            tx_status = f"{len(df)} total transactions — " + ", ".join(f"{s}: {c}" for s, c in sources.items())
            date_range = f"({df['date'].min().date()} to {df['date'].max().date()})"
            tx_status += f" {date_range}"

        return f"Budget: {budget_status}\nTransactions: {tx_status}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rebuild_tracker(self) -> None:
        if self._budget:
            df = self._parser.dataframe
            self._tracker = BudgetTracker(self._budget, df)
