"""
Auto-discover and load budget/transaction files from the data/ directory.

Folder conventions:
    data/budgets/       — place .xlsx budget files here (most recent is loaded)
    data/transactions/  — place .csv transaction files here (all are loaded)

Venmo CSVs are detected by the presence of "venmo" in the filename.
All other CSVs are treated as credit card exports (Chase, Capital One, or generic).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import BudgetAgent

DATA_DIR = Path("data")
BUDGETS_DIR = DATA_DIR / "budgets"
TRANSACTIONS_DIR = DATA_DIR / "transactions"


def find_budget_file() -> Path | None:
    """Return the most recently modified .xlsx in data/budgets/, or None."""
    if not BUDGETS_DIR.exists():
        return None
    files = sorted(BUDGETS_DIR.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def find_transaction_files() -> list[Path]:
    """Return all .csv files in data/transactions/, sorted oldest-first."""
    if not TRANSACTIONS_DIR.exists():
        return []
    return sorted(TRANSACTIONS_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime)


def _is_venmo(path: Path) -> bool:
    return "venmo" in path.stem.lower()


def autoload(agent: "BudgetAgent") -> list[str]:
    """
    Scan data/ folders and load whatever files are found into the agent.

    Returns a list of human-readable status strings (Rich markup supported).
    """
    messages: list[str] = []

    # --- Budget ---
    budget_file = find_budget_file()
    if budget_file:
        try:
            result = agent._tool_load_budget(str(budget_file))
            # First line: "Budget loaded from '...'. Total monthly budget: $X"
            messages.append(f"[green]✓ Budget:[/green] {result.splitlines()[0]}")
        except Exception as e:
            messages.append(f"[red]✗ Budget ({budget_file.name}):[/red] {e}")
    else:
        messages.append(
            f"[yellow]  No budget file found in {BUDGETS_DIR}/[/yellow]  "
            f"(place a .xlsx file there to auto-load it)"
        )

    # --- Transactions ---
    tx_files = find_transaction_files()
    if tx_files:
        for csv_path in tx_files:
            try:
                if _is_venmo(csv_path):
                    result = agent._tool_load_venmo(str(csv_path))
                else:
                    result = agent._tool_load_credit_card(str(csv_path), source_label=csv_path.stem)
                messages.append(f"[green]✓ Transactions:[/green] {result}")
            except Exception as e:
                messages.append(f"[red]✗ Transactions ({csv_path.name}):[/red] {e}")
    else:
        messages.append(
            f"[yellow]  No transaction CSVs found in {TRANSACTIONS_DIR}/[/yellow]  "
            f"(place .csv exports there to auto-load them)"
        )

    return messages
