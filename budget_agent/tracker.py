"""
Budget tracker: compares actual spending to budgeted amounts by category.

Category mapping
----------------
Transaction categories from credit cards / Venmo don't always match the
categories in the user's budget. A keyword-based mapper bridges the gap.
Users can extend the mapping via add_mapping().
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional
import calendar

import pandas as pd


# Default keyword → budget-category mappings
DEFAULT_KEYWORD_MAP: dict[str, list[str]] = {
    "Housing": ["rent", "mortgage", "electric", "gas bill", "water bill", "utility", "internet", "at&t", "verizon", "comcast"],
    "Groceries": ["grocery", "groceries", "whole foods", "trader joe", "safeway", "kroger", "aldi", "costco", "walmart", "target food", "supermarket"],
    "Dining Out": ["restaurant", "dining", "doordash", "grubhub", "ubereats", "uber eats", "seamless", "mcdonald", "starbucks", "chipotle", "taco bell", "pizza", "sushi", "cafe", "coffee", "diner"],
    "Transportation": ["uber", "lyft", "transit", "subway", "metro", "bus", "gas station", "shell", "chevron", "bp", "exxon", "parking", "toll", "amtrak"],
    "Entertainment": ["netflix", "spotify", "hulu", "disney", "hbo", "amazon prime", "movie", "theater", "concert", "ticketmaster", "eventbrite", "gym", "planet fitness"],
    "Healthcare": ["pharmacy", "cvs", "walgreens", "rite aid", "doctor", "dental", "vision", "hospital", "urgent care", "copay"],
    "Clothing": ["h&m", "zara", "gap", "old navy", "nordstrom", "macy", "forever 21", "tj maxx", "clothing", "shoes", "nike", "adidas"],
    "Personal Care": ["haircut", "salon", "spa", "nail", "barber", "ulta", "sephora"],
    "Subscriptions": ["subscription", "apple", "google", "microsoft", "adobe", "dropbox", "icloud"],
    "Savings": ["transfer", "savings", "investment", "brokerage"],
}


class BudgetTracker:
    """
    Tracks spending against budget categories for a given time period.
    """

    def __init__(
        self,
        budget: dict[str, float],
        transactions: pd.DataFrame,
        keyword_map: Optional[dict[str, list[str]]] = None,
    ):
        self.budget = budget  # {category: monthly_budget}
        self.transactions = transactions.copy()
        self._keyword_map = {**DEFAULT_KEYWORD_MAP, **(keyword_map or {})}

        # Normalise category column
        if not self.transactions.empty:
            self.transactions["budget_category"] = self.transactions.apply(
                self._map_category, axis=1
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_mapping(self, budget_category: str, keywords: list[str]) -> None:
        """Add or extend keyword-based mapping for a budget category."""
        existing = self._keyword_map.get(budget_category, [])
        self._keyword_map[budget_category] = list(set(existing + keywords))
        # Re-map categories
        if not self.transactions.empty:
            self.transactions["budget_category"] = self.transactions.apply(
                self._map_category, axis=1
            )

    def summary(self, year: Optional[int] = None, month: Optional[int] = None) -> pd.DataFrame:
        """
        Return a DataFrame with columns:
          Category | Budget | Spent | Remaining | Percent Used
        filtered to the given year/month (or all time if not specified).
        """
        df = self._filter(year, month)
        if df.empty or "budget_category" not in df.columns:
            spent_by_cat = {}
        else:
            spent_by_cat = df.groupby("budget_category")["amount"].sum().to_dict()

        rows = []
        all_categories = set(self.budget.keys()) | set(spent_by_cat.keys())
        for cat in sorted(all_categories):
            budgeted = self.budget.get(cat, 0.0)
            spent = spent_by_cat.get(cat, 0.0)
            remaining = budgeted - spent
            pct = (spent / budgeted * 100) if budgeted > 0 else float("inf")
            rows.append({
                "Category": cat,
                "Budget": budgeted,
                "Spent": round(spent, 2),
                "Remaining": round(remaining, 2),
                "Percent Used": round(pct, 1),
            })

        return pd.DataFrame(rows)

    def over_budget_categories(self, year: Optional[int] = None, month: Optional[int] = None) -> pd.DataFrame:
        df = self.summary(year, month)
        return df[df["Remaining"] < 0].reset_index(drop=True)

    def total_spent(self, year: Optional[int] = None, month: Optional[int] = None) -> float:
        df = self._filter(year, month)
        return round(df["amount"].sum(), 2)

    def total_budget(self) -> float:
        return sum(self.budget.values())

    def monthly_trend(self) -> pd.DataFrame:
        """Return month-by-month spending totals for all categories."""
        if self.transactions.empty:
            return pd.DataFrame()
        df = self.transactions.copy()
        df["year_month"] = df["date"].dt.to_period("M")
        trend = df.groupby(["year_month", "budget_category"])["amount"].sum().reset_index()
        trend.columns = ["Month", "Category", "Spent"]
        trend["Month"] = trend["Month"].astype(str)
        return trend

    def top_transactions(
        self,
        n: int = 10,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> pd.DataFrame:
        df = self._filter(year, month)
        return (
            df.sort_values("amount", ascending=False)
            .head(n)[["date", "description", "amount", "budget_category", "source"]]
            .reset_index(drop=True)
        )

    def spending_by_day(self, year: Optional[int] = None, month: Optional[int] = None) -> pd.DataFrame:
        df = self._filter(year, month)
        daily = df.groupby(df["date"].dt.date)["amount"].sum().reset_index()
        daily.columns = ["Date", "Spent"]
        return daily

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _filter(self, year: Optional[int], month: Optional[int]) -> pd.DataFrame:
        df = self.transactions
        if df.empty:
            return df
        if year is not None:
            df = df[df["date"].dt.year == year]
        if month is not None:
            df = df[df["date"].dt.month == month]
        return df

    def _map_category(self, row: pd.Series) -> str:
        """Map a transaction to a budget category using keywords."""
        source_cat = str(row.get("category", "")).lower()
        description = str(row.get("description", "")).lower()
        text = f"{source_cat} {description}"

        for budget_cat, keywords in self._keyword_map.items():
            if any(kw in text for kw in keywords):
                return budget_cat

        # Try to match source category directly to a budget category (case-insensitive)
        for budget_cat in self.budget:
            if budget_cat.lower() in text or source_cat in budget_cat.lower():
                return budget_cat

        return "Miscellaneous"
