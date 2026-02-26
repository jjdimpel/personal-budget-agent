"""
Transaction parser: ingests credit card CSV exports and Venmo CSV exports.

Supported formats
-----------------
Credit card:
  Chase:
    Columns: Transaction Date, Post Date, Description, Category, Type, Amount, Memo
  Capital One:
    Columns: Transaction Date, Posted Date, Card No., Description, Category, Debit, Credit
  Generic fallback:
    Expects at least: date, description, amount columns (auto-detected)

Venmo:
  Standard export columns include:
    ID, Datetime, Type, Status, Note, From, To,
    Amount (total), Amount (fee), Funding Source, Destination,
    Beginning Balance, Ending Balance, Statement Period Venmo Fees, Terminal Digits

All transactions are normalised to a common schema:
  date        : datetime
  description : str
  amount      : float  (positive = expense, negative = income/refund)
  category    : str    (from source data, or "Uncategorized")
  source      : str    ("credit_card" | "venmo")
  raw         : dict   (original row for debugging)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd
from dateutil import parser as date_parser


NORMALIZED_SCHEMA = ["date", "description", "amount", "category", "source"]


class TransactionParser:
    """Parse and normalise transaction exports from various sources."""

    def __init__(self):
        self._transactions: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_credit_card(self, filepath: str | Path, source_label: str = "credit_card") -> "TransactionParser":
        """Load a credit-card CSV export. Returns self for chaining."""
        df = self._read_csv(filepath)
        normalized = self._parse_credit_card(df, source_label)
        self._transactions.extend(normalized)
        return self

    def load_venmo(self, filepath: str | Path) -> "TransactionParser":
        """Load a Venmo CSV export. Returns self for chaining."""
        df = self._read_csv(filepath, skip_venmo_header=True)
        normalized = self._parse_venmo(df)
        self._transactions.extend(normalized)
        return self

    @property
    def dataframe(self) -> pd.DataFrame:
        """All loaded transactions as a DataFrame."""
        if not self._transactions:
            return pd.DataFrame(columns=NORMALIZED_SCHEMA)
        df = pd.DataFrame(self._transactions)[NORMALIZED_SCHEMA]
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def filter_by_month(self, year: int, month: int) -> pd.DataFrame:
        df = self.dataframe
        return df[(df["date"].dt.year == year) & (df["date"].dt.month == month)]

    def clear(self) -> "TransactionParser":
        self._transactions = []
        return self

    # ------------------------------------------------------------------
    # Credit-card parsers
    # ------------------------------------------------------------------

    def _parse_credit_card(self, df: pd.DataFrame, source_label: str) -> list[dict]:
        cols = {self._norm(c): c for c in df.columns}

        # --- Chase format ---
        if "transaction date" in cols and "description" in cols and "amount" in cols:
            return self._parse_chase(df, cols, source_label)

        # --- Capital One format ---
        if "transaction date" in cols and "debit" in cols and "credit" in cols:
            return self._parse_capital_one(df, cols, source_label)

        # --- Generic fallback ---
        return self._parse_generic_cc(df, cols, source_label)

    def _parse_chase(self, df: pd.DataFrame, cols: dict, source: str) -> list[dict]:
        rows = []
        for _, row in df.iterrows():
            date = self._parse_date(row[cols.get("transaction date", cols.get("date", ""))])
            if date is None:
                continue
            amount = self._to_float(row[cols["amount"]])
            # Chase: negative = expense, positive = credit/refund
            rows.append({
                "date": date,
                "description": str(row.get(cols.get("description", ""), "")).strip(),
                "amount": -amount,  # flip so positive = expense
                "category": str(row.get(cols.get("category", ""), "Uncategorized")).strip() or "Uncategorized",
                "source": source,
            })
        return rows

    def _parse_capital_one(self, df: pd.DataFrame, cols: dict, source: str) -> list[dict]:
        rows = []
        for _, row in df.iterrows():
            date = self._parse_date(row[cols["transaction date"]])
            if date is None:
                continue
            debit = self._to_float(row.get(cols.get("debit", ""), None))
            credit = self._to_float(row.get(cols.get("credit", ""), None))
            amount = debit if debit else -credit  # debit = expense, credit = refund
            rows.append({
                "date": date,
                "description": str(row.get(cols.get("description", ""), "")).strip(),
                "amount": amount,
                "category": str(row.get(cols.get("category", ""), "Uncategorized")).strip() or "Uncategorized",
                "source": source,
            })
        return rows

    def _parse_generic_cc(self, df: pd.DataFrame, cols: dict, source: str) -> list[dict]:
        """Best-effort parser for unknown credit card formats."""
        date_col = next((v for k, v in cols.items() if "date" in k), None)
        desc_col = next((v for k, v in cols.items() if "desc" in k or "name" in k or "merchant" in k), None)
        amount_col = next((v for k, v in cols.items() if "amount" in k or "charge" in k or "debit" in k), None)
        cat_col = next((v for k, v in cols.items() if "cat" in k or "type" in k), None)

        if not (date_col and amount_col):
            raise ValueError(
                "Cannot auto-detect credit card CSV format. "
                "Expected columns for date and amount. "
                f"Found: {list(df.columns)}"
            )

        rows = []
        for _, row in df.iterrows():
            date = self._parse_date(row[date_col])
            if date is None:
                continue
            rows.append({
                "date": date,
                "description": str(row[desc_col]).strip() if desc_col else "",
                "amount": abs(self._to_float(row[amount_col])),
                "category": str(row[cat_col]).strip() if cat_col else "Uncategorized",
                "source": source,
            })
        return rows

    # ------------------------------------------------------------------
    # Venmo parser
    # ------------------------------------------------------------------

    def _parse_venmo(self, df: pd.DataFrame) -> list[dict]:
        cols = {self._norm(c): c for c in df.columns}
        rows = []
        for _, row in df.iterrows():
            datetime_col = cols.get("datetime", cols.get("date", None))
            if datetime_col is None:
                continue
            date = self._parse_date(row[datetime_col])
            if date is None:
                continue

            # Amount total can be "+ $12.34" or "- $12.34"
            raw_amount = str(row.get(cols.get("amount (total)", cols.get("amount", "")), "0"))
            amount = self._parse_venmo_amount(raw_amount)

            note = str(row.get(cols.get("note", ""), "")).strip()
            txn_type = str(row.get(cols.get("type", ""), "Payment")).strip()
            from_user = str(row.get(cols.get("from", ""), "")).strip()
            to_user = str(row.get(cols.get("to", ""), "")).strip()
            description = note or f"{txn_type}: {from_user} -> {to_user}"

            # Only include completed payments; skip transfers/top-ups
            status = str(row.get(cols.get("status", ""), "Complete")).strip()
            if status.lower() not in ("complete", "completed", ""):
                continue
            if txn_type.lower() in ("standard transfer", "instant transfer", "top up"):
                continue

            rows.append({
                "date": date,
                "description": description,
                "amount": amount,
                "category": "Venmo",
                "source": "venmo",
            })
        return rows

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _read_csv(self, filepath: str | Path, skip_venmo_header: bool = False) -> pd.DataFrame:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Transaction file not found: {filepath}")

        if skip_venmo_header:
            # Venmo exports have several metadata rows at the top before the real header
            with open(filepath, encoding="utf-8-sig") as f:
                lines = f.readlines()
            # Find the row that looks like the real header
            header_idx = 0
            for i, line in enumerate(lines):
                if "Datetime" in line or "datetime" in line or "ID" in line:
                    header_idx = i
                    break
            return pd.read_csv(filepath, skiprows=header_idx, encoding="utf-8-sig")

        return pd.read_csv(filepath, encoding="utf-8-sig")

    @staticmethod
    def _norm(col: str) -> str:
        return re.sub(r"\s+", " ", str(col).strip().lower())

    @staticmethod
    def _parse_date(val) -> Optional[pd.Timestamp]:
        if pd.isna(val) or str(val).strip() in ("", "nan"):
            return None
        try:
            return pd.Timestamp(date_parser.parse(str(val)))
        except Exception:
            return None

    @staticmethod
    def _to_float(val) -> float:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return 0.0
        cleaned = re.sub(r"[^\d.\-]", "", str(val))
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_venmo_amount(raw: str) -> float:
        """Parse Venmo amount strings like '+ $12.34' or '- $12.34'."""
        raw = raw.strip()
        negative = raw.startswith("-")
        cleaned = re.sub(r"[^\d.]", "", raw)
        try:
            val = float(cleaned)
            return val if negative else val  # positive = received money (income), keep sign info
        except ValueError:
            return 0.0
