"""
Budget loader: reads baseline budget from an Excel file.

Expected Excel format:
  Sheet name: "Budget" (or first sheet)
  Columns: Category | Monthly Budget | Notes (optional)

Example:
  Category          | Monthly Budget | Notes
  ------------------+----------------+------------------
  Housing           | 1500           | Rent + utilities
  Groceries         | 400            |
  Dining Out        | 200            |
  Transportation    | 150            |
  Entertainment     | 100            |
  Healthcare        | 75             |
  Clothing          | 100            |
  Savings           | 500            |
  Miscellaneous     | 150            |
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd


REQUIRED_COLUMNS = {"category", "monthly budget"}


class BudgetLoader:
    """Loads and validates a budget from an Excel file."""

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self._df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> dict[str, float]:
        """Return {category: monthly_budget_amount} mapping."""
        self._df = self._read_excel()
        return self._to_dict()

    @property
    def dataframe(self) -> pd.DataFrame:
        if self._df is None:
            self._df = self._read_excel()
        return self._df

    @property
    def total_budget(self) -> float:
        return sum(self.load().values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_excel(self) -> pd.DataFrame:
        if not self.filepath.exists():
            raise FileNotFoundError(f"Budget file not found: {self.filepath}")

        # Try "Budget" sheet first, fall back to first sheet
        xl = pd.ExcelFile(self.filepath)
        sheet = "Budget" if "Budget" in xl.sheet_names else xl.sheet_names[0]
        df = pd.read_excel(self.filepath, sheet_name=sheet)

        # Normalize column names
        df.columns = [self._normalize(c) for c in df.columns]

        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(
                f"Excel sheet '{sheet}' is missing required columns: {missing}. "
                f"Found columns: {list(df.columns)}"
            )

        # Keep only relevant columns, drop blank rows
        df = df[["category", "monthly budget"] + [c for c in df.columns if c not in REQUIRED_COLUMNS]]
        df = df.dropna(subset=["category", "monthly budget"])
        df["category"] = df["category"].astype(str).str.strip()
        df["monthly budget"] = pd.to_numeric(df["monthly budget"], errors="coerce").fillna(0.0)

        return df

    def _to_dict(self) -> dict[str, float]:
        return dict(zip(self._df["category"], self._df["monthly budget"]))

    @staticmethod
    def _normalize(col: str) -> str:
        return re.sub(r"\s+", " ", str(col).strip().lower())

    # ------------------------------------------------------------------
    # Template generation
    # ------------------------------------------------------------------

    @staticmethod
    def create_template(output_path: str | Path = "budget_template.xlsx") -> Path:
        """Write a sample budget Excel file so users know the expected format."""
        output_path = Path(output_path)
        default_categories = [
            ("Housing", 1500, "Rent, mortgage, utilities"),
            ("Groceries", 400, ""),
            ("Dining Out", 200, "Restaurants, takeout, coffee"),
            ("Transportation", 150, "Gas, transit, rideshare"),
            ("Entertainment", 100, "Streaming, events, hobbies"),
            ("Healthcare", 75, "Copays, prescriptions"),
            ("Clothing", 100, ""),
            ("Personal Care", 50, "Haircuts, toiletries"),
            ("Savings", 500, "Emergency fund, investments"),
            ("Subscriptions", 50, "Software, memberships"),
            ("Miscellaneous", 150, ""),
        ]
        df = pd.DataFrame(default_categories, columns=["Category", "Monthly Budget", "Notes"])
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Budget", index=False)
            ws = writer.sheets["Budget"]
            # Set column widths
            for col, width in [("A", 22), ("B", 16), ("C", 30)]:
                ws.column_dimensions[col].width = width
        return output_path
