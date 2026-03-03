#!/usr/bin/env python3
"""
Personal Budget Agent — entry point.

Usage:
    python main.py                          # interactive chat
    python main.py --generate-template      # write sample budget Excel
    python main.py --generate-sample-data   # write sample CSV data files
"""

import argparse
import sys

from budget_agent.budget import BudgetLoader
from budget_agent.agent import BudgetAgent, console
from budget_agent.autoloader import autoload, BUDGETS_DIR, TRANSACTIONS_DIR
from sample_data.generate import generate_all_samples


def interactive_chat(agent: BudgetAgent, data_loaded: bool = False) -> None:
    console.print("\n[bold cyan]Personal Budget Agent[/bold cyan]")
    console.print("Type [bold]'quit'[/bold] or [bold]'exit'[/bold] to stop. Type [bold]'reset'[/bold] to clear data.\n")
    if data_loaded:
        console.print("Try asking:")
        console.print("  • How am I doing this month?")
        console.print("  • What are my top 5 biggest expenses?")
        console.print("  • Show me a spending breakdown chart\n")
    else:
        console.print(f"Drop your files into the data folders, then restart — or load manually:")
        console.print(f"  • Budget (.xlsx)  →  [bold]{BUDGETS_DIR}/[/bold]")
        console.print(f"  • Transactions (.csv)  →  [bold]{TRANSACTIONS_DIR}/[/bold]")
        console.print("  • Or: Load my budget from budget.xlsx")
        console.print("  • Or: Load my Chase CSV from chase.csv\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Goodbye![/yellow]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            console.print("[yellow]Goodbye![/yellow]")
            break
        if user_input.lower() == "reset":
            agent.reset()
            continue

        agent.chat(user_input)


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal Budget Agent")
    parser.add_argument(
        "--generate-template",
        action="store_true",
        help="Generate a sample budget Excel template and exit",
    )
    parser.add_argument(
        "--generate-sample-data",
        action="store_true",
        help="Generate sample CSV data files and exit",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="Claude model to use (default: claude-sonnet-4-6)",
    )
    args = parser.parse_args()

    if args.generate_template:
        path = BudgetLoader.create_template("sample_data/budget_template.xlsx")
        console.print(f"[green]Budget template written to: {path}[/green]")
        sys.exit(0)

    if args.generate_sample_data:
        generate_all_samples()
        sys.exit(0)

    agent = BudgetAgent(model=args.model)

    console.print("\n[bold]Scanning for data files...[/bold]")
    load_messages = autoload(agent)
    for msg in load_messages:
        console.print(f"  {msg}")
    data_loaded = agent._budget or not agent._parser.dataframe.empty

    interactive_chat(agent, data_loaded=data_loaded)


if __name__ == "__main__":
    main()
