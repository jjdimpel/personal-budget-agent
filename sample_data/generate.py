"""
Generate realistic sample data files for testing and demonstration.

Produces:
  - sample_data/budget_template.xlsx   : Sample budget
  - sample_data/chase_sample.csv       : Chase credit card export
  - sample_data/capital_one_sample.csv : Capital One credit card export
  - sample_data/venmo_sample.csv       : Venmo export
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from budget_agent.budget import BudgetLoader

SAMPLE_DIR = Path(__file__).parent


def _random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def generate_chase_csv(filepath: Path = SAMPLE_DIR / "chase_sample.csv") -> Path:
    """Generate a Chase-format credit card CSV."""
    random.seed(42)
    start = datetime(2024, 1, 1)
    end = datetime(2024, 3, 31)

    transactions = [
        # Housing
        ("2024-01-01", "ACH PAYMENT - LANDLORD", "Rent & Landlord", -1500.00),
        ("2024-02-01", "ACH PAYMENT - LANDLORD", "Rent & Landlord", -1500.00),
        ("2024-03-01", "ACH PAYMENT - LANDLORD", "Rent & Landlord", -1500.00),
        ("2024-01-05", "CON EDISON ELECTRIC", "Utilities", -85.00),
        ("2024-02-05", "CON EDISON ELECTRIC", "Utilities", -92.00),
        ("2024-03-05", "CON EDISON ELECTRIC", "Utilities", -78.00),
        # Groceries
        ("2024-01-08", "WHOLE FOODS MARKET", "Groceries", -67.43),
        ("2024-01-15", "TRADER JOES #123", "Groceries", -89.12),
        ("2024-01-22", "WHOLE FOODS MARKET", "Groceries", -54.22),
        ("2024-01-28", "COSTCO WHOLESALE", "Groceries", -143.67),
        ("2024-02-06", "WHOLE FOODS MARKET", "Groceries", -71.88),
        ("2024-02-14", "TRADER JOES #123", "Groceries", -95.40),
        ("2024-02-21", "WALMART GROCERY", "Groceries", -112.33),
        ("2024-02-27", "WHOLE FOODS MARKET", "Groceries", -48.91),
        ("2024-03-07", "WHOLE FOODS MARKET", "Groceries", -63.20),
        ("2024-03-14", "TRADER JOES #123", "Groceries", -77.55),
        ("2024-03-21", "COSTCO WHOLESALE", "Groceries", -168.90),
        ("2024-03-28", "WHOLE FOODS MARKET", "Groceries", -52.10),
        # Dining Out
        ("2024-01-10", "DOORDASH*CHIPOTLE", "Food & Drink", -18.45),
        ("2024-01-14", "STARBUCKS #4521", "Food & Drink", -7.80),
        ("2024-01-17", "LOCAL PIZZA PLACE", "Food & Drink", -32.50),
        ("2024-01-20", "STARBUCKS #4521", "Food & Drink", -6.50),
        ("2024-01-25", "UBEREATS*THAI GARDEN", "Food & Drink", -28.90),
        ("2024-02-07", "DOORDASH*SUSHI PLACE", "Food & Drink", -41.20),
        ("2024-02-11", "STARBUCKS #4521", "Food & Drink", -7.20),
        ("2024-02-16", "LOCAL BURGER BAR", "Food & Drink", -24.75),
        ("2024-02-21", "GRUBHUB*ITALIAN REST", "Food & Drink", -55.80),  # over budget!
        ("2024-02-23", "STARBUCKS #4521", "Food & Drink", -8.10),
        ("2024-03-03", "DOORDASH*CHIPOTLE", "Food & Drink", -19.99),
        ("2024-03-09", "LOCAL SUSHI RESTAURANT", "Food & Drink", -78.40),  # splurge
        ("2024-03-15", "STARBUCKS #4521", "Food & Drink", -6.90),
        ("2024-03-22", "UBEREATS*PIZZA HUT", "Food & Drink", -31.50),
        # Transportation
        ("2024-01-03", "UBER TRIP", "Transportation", -12.50),
        ("2024-01-11", "MTA*METRO CARD", "Transportation", -33.00),
        ("2024-01-18", "LYFT *RIDE", "Transportation", -9.75),
        ("2024-01-24", "UBER TRIP", "Transportation", -15.25),
        ("2024-02-04", "MTA*METRO CARD", "Transportation", -33.00),
        ("2024-02-12", "UBER TRIP", "Transportation", -22.80),
        ("2024-02-19", "LYFT *RIDE", "Transportation", -11.40),
        ("2024-03-02", "MTA*METRO CARD", "Transportation", -33.00),
        ("2024-03-11", "UBER TRIP", "Transportation", -18.60),
        # Entertainment
        ("2024-01-01", "NETFLIX.COM", "Entertainment", -15.99),
        ("2024-01-01", "SPOTIFY USA", "Entertainment", -9.99),
        ("2024-01-20", "AMC THEATERS", "Entertainment", -28.50),
        ("2024-02-01", "NETFLIX.COM", "Entertainment", -15.99),
        ("2024-02-01", "SPOTIFY USA", "Entertainment", -9.99),
        ("2024-02-14", "TICKETMASTER*CONCERT", "Entertainment", -145.00),  # over budget!
        ("2024-03-01", "NETFLIX.COM", "Entertainment", -15.99),
        ("2024-03-01", "SPOTIFY USA", "Entertainment", -9.99),
        ("2024-03-22", "AMC THEATERS", "Entertainment", -24.00),
        # Healthcare
        ("2024-01-12", "CVS PHARMACY #1234", "Health & Wellness", -34.50),
        ("2024-02-15", "DR SMITH MEDICAL COPAY", "Health & Wellness", -30.00),
        ("2024-03-08", "WALGREENS #5678", "Health & Wellness", -22.75),
        # Clothing
        ("2024-01-15", "H&M STORE #42", "Shopping", -67.80),
        ("2024-02-20", "NORDSTROM RACK", "Shopping", -118.40),
        ("2024-03-10", "ZARA USA", "Shopping", -89.95),
        # Subscriptions
        ("2024-01-05", "ADOBE CREATIVE CLOUD", "Subscriptions", -54.99),
        ("2024-02-05", "ADOBE CREATIVE CLOUD", "Subscriptions", -54.99),
        ("2024-03-05", "ADOBE CREATIVE CLOUD", "Subscriptions", -54.99),
        # Savings
        ("2024-01-01", "TRANSFER TO SAVINGS", "Transfer", 500.00),
        ("2024-02-01", "TRANSFER TO SAVINGS", "Transfer", 500.00),
        ("2024-03-01", "TRANSFER TO SAVINGS", "Transfer", 500.00),
    ]

    rows = []
    for txn_date, desc, cat, amount in transactions:
        post_date = datetime.strptime(txn_date, "%Y-%m-%d") + timedelta(days=2)
        rows.append({
            "Transaction Date": txn_date,
            "Post Date": post_date.strftime("%Y-%m-%d"),
            "Description": desc,
            "Category": cat,
            "Type": "Sale",
            "Amount": amount,
            "Memo": "",
        })

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False)
    return filepath


def generate_capital_one_csv(filepath: Path = SAMPLE_DIR / "capital_one_sample.csv") -> Path:
    """Generate a Capital One-format credit card CSV."""
    rows = [
        ("2024-01-06", "2024-01-07", "1234", "AMAZON.COM*ABC123", "Shopping", 42.99, ""),
        ("2024-01-09", "2024-01-10", "1234", "TARGET #1234", "Shopping", 67.50, ""),
        ("2024-01-13", "2024-01-14", "1234", "PLANET FITNESS", "Health & Fitness", 24.99, ""),
        ("2024-01-19", "2024-01-20", "1234", "BEST BUY #567", "Electronics", 129.99, ""),
        ("2024-02-03", "2024-02-04", "1234", "AMAZON.COM*XYZ", "Shopping", 38.75, ""),
        ("2024-02-10", "2024-02-11", "1234", "TARGET #1234", "Shopping", 54.20, ""),
        ("2024-02-13", "2024-02-14", "1234", "PLANET FITNESS", "Health & Fitness", 24.99, ""),
        ("2024-02-18", "2024-02-19", "1234", "ULTA BEAUTY", "Personal Care", 45.60, ""),
        ("2024-03-04", "2024-03-05", "1234", "AMAZON.COM*DEF", "Shopping", 89.99, ""),
        ("2024-03-13", "2024-03-14", "1234", "PLANET FITNESS", "Health & Fitness", 24.99, ""),
        ("2024-03-19", "2024-03-20", "1234", "APPLE.COM/BILL", "Subscriptions", 14.99, ""),
        ("2024-03-25", "2024-03-26", "1234", "AMAZON.COM*GHI", "Shopping", 156.78, ""),
    ]

    df = pd.DataFrame(rows, columns=[
        "Transaction Date", "Posted Date", "Card No.", "Description", "Category", "Debit", "Credit"
    ])
    df.to_csv(filepath, index=False)
    return filepath


def generate_venmo_csv(filepath: Path = SAMPLE_DIR / "venmo_sample.csv") -> Path:
    """Generate a Venmo-format CSV export."""
    # Venmo exports have 3 metadata rows at the top
    metadata = [
        ["Username", "john_doe", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", "", "", "", "", "", "", ""],
    ]
    header = [
        "ID", "Datetime", "Type", "Status", "Note", "From", "To",
        "Amount (total)", "Amount (fee)", "Funding Source", "Destination",
        "Beginning Balance", "Ending Balance", "Statement Period Venmo Fees", "Terminal Digits"
    ]
    transactions = [
        ("3001", "2024-01-08T19:30:00", "Payment", "Complete", "Dinner split", "jane_smith", "john_doe", "- $25.00", "$0.00", "Venmo balance", "", "$100.00", "$75.00", "$0.00", "1234"),
        ("3002", "2024-01-12T12:00:00", "Payment", "Complete", "Groceries reimbursement", "mike_jones", "john_doe", "- $18.50", "$0.00", "Venmo balance", "", "$75.00", "$56.50", "$0.00", "1234"),
        ("3003", "2024-01-20T20:15:00", "Payment", "Complete", "Movie tickets", "john_doe", "sarah_lee", "+ $30.00", "$0.00", "Bank Account", "", "$56.50", "$56.50", "$0.00", "1234"),
        ("3004", "2024-02-03T18:45:00", "Payment", "Complete", "Pizza night", "john_doe", "mike_jones", "+ $22.75", "$0.00", "Bank Account", "", "$56.50", "$56.50", "$0.00", "1234"),
        ("3005", "2024-02-10T13:00:00", "Payment", "Complete", "Uber split", "jane_smith", "john_doe", "- $8.50", "$0.00", "Venmo balance", "", "$56.50", "$48.00", "$0.00", "1234"),
        ("3006", "2024-02-17T21:30:00", "Payment", "Complete", "Concert tickets split", "john_doe", "sarah_lee", "+ $72.50", "$0.00", "Bank Account", "", "$48.00", "$48.00", "$0.00", "1234"),
        ("3007", "2024-02-25T19:00:00", "Payment", "Complete", "Dinner", "john_doe", "alex_w", "+ $45.00", "$0.00", "Bank Account", "", "$48.00", "$48.00", "$0.00", "1234"),
        ("3008", "2024-03-05T12:30:00", "Payment", "Complete", "Lunch split", "mike_jones", "john_doe", "- $15.25", "$0.00", "Venmo balance", "", "$48.00", "$32.75", "$0.00", "1234"),
        ("3009", "2024-03-14T19:45:00", "Payment", "Complete", "Bar tab split", "john_doe", "jane_smith", "+ $38.00", "$0.00", "Bank Account", "", "$32.75", "$32.75", "$0.00", "1234"),
        ("3010", "2024-03-22T20:00:00", "Payment", "Complete", "Group dinner", "john_doe", "sarah_lee", "+ $55.25", "$0.00", "Bank Account", "", "$32.75", "$32.75", "$0.00", "1234"),
        ("3011", "2024-01-15T10:00:00", "Standard Transfer", "Complete", "", "john_doe", "", "- $56.50", "$0.00", "Venmo balance", "Bank Account", "$56.50", "$0.00", "$0.00", "1234"),
    ]

    with open(filepath, "w", encoding="utf-8") as f:
        for row in metadata:
            f.write(",".join(row) + "\n")
        f.write(",".join(header) + "\n")
        for txn in transactions:
            f.write(",".join(txn) + "\n")

    return filepath


def generate_all_samples() -> None:
    from rich.console import Console
    c = Console()

    SAMPLE_DIR.mkdir(exist_ok=True)

    path = BudgetLoader.create_template(SAMPLE_DIR / "budget_template.xlsx")
    c.print(f"[green]✓[/green] Budget template: {path}")

    path = generate_chase_csv()
    c.print(f"[green]✓[/green] Chase CSV: {path}")

    path = generate_capital_one_csv()
    c.print(f"[green]✓[/green] Capital One CSV: {path}")

    path = generate_venmo_csv()
    c.print(f"[green]✓[/green] Venmo CSV: {path}")

    c.print("\n[bold]Sample data ready![/bold] Try running:")
    c.print("  python main.py")
    c.print('\nThen chat with the agent — for example:')
    c.print('  "Load my budget from sample_data/budget_template.xlsx"')
    c.print('  "Load my Chase card from sample_data/chase_sample.csv"')
    c.print('  "Load my Venmo from sample_data/venmo_sample.csv"')
    c.print('  "How am I doing this month?"')
    c.print('  "Generate charts"')


if __name__ == "__main__":
    generate_all_samples()
