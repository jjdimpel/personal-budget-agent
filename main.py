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
from sample_data.generate import generate_all_samples


def interactive_chat(agent: BudgetAgent) -> None:
    console.print("\n[bold cyan]Personal Budget Agent[/bold cyan]")
    console.print("Type [bold]'quit'[/bold] or [bold]'exit'[/bold] to stop. Type [bold]'reset'[/bold] to clear data.\n")
    console.print("Example commands:")
    console.print("  • Load my budget from budget.xlsx")
    console.print("  • Load my Chase credit card from sample_data/chase_sample.csv")
    console.print("  • Load my Venmo from sample_data/venmo_sample.csv")
    console.print("  • How am I doing this month?")
    console.print("  • What are my top 5 biggest expenses?")
    console.print("  • Generate charts\n")

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
    interactive_chat(agent)


if __name__ == "__main__":
    main()
