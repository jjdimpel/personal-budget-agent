"""Tests for BudgetTracker."""

import pytest
import pandas as pd
from pathlib import Path

from budget_agent.budget import BudgetLoader
from budget_agent.transactions import TransactionParser
from budget_agent.tracker import BudgetTracker
from sample_data.generate import generate_chase_csv, generate_capital_one_csv


@pytest.fixture(scope="session")
def budget(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    path = BudgetLoader.create_template(tmp / "budget.xlsx")
    return BudgetLoader(path).load()


@pytest.fixture(scope="session")
def transactions(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    chase = generate_chase_csv(tmp / "chase.csv")
    cap1 = generate_capital_one_csv(tmp / "cap1.csv")
    parser = TransactionParser()
    parser.load_credit_card(chase, "chase")
    parser.load_credit_card(cap1, "capital_one")
    return parser.dataframe


@pytest.fixture(scope="session")
def tracker(budget, transactions):
    return BudgetTracker(budget, transactions)


def test_summary_returns_dataframe(tracker):
    summary = tracker.summary()
    assert isinstance(summary, pd.DataFrame)
    for col in ["Category", "Budget", "Spent", "Remaining", "Percent Used"]:
        assert col in summary.columns


def test_summary_month_filter(tracker):
    jan = tracker.summary(year=2024, month=1)
    assert len(jan) > 0


def test_total_spent_positive(tracker):
    total = tracker.total_spent()
    assert total > 0


def test_over_budget_categories(tracker):
    over = tracker.over_budget_categories()
    assert isinstance(over, pd.DataFrame)
    # All returned rows should have negative Remaining
    assert (over["Remaining"] < 0).all()


def test_top_transactions_count(tracker):
    top = tracker.top_transactions(n=5)
    assert len(top) <= 5


def test_monthly_trend_structure(tracker):
    trend = tracker.monthly_trend()
    assert isinstance(trend, pd.DataFrame)
    if not trend.empty:
        for col in ["Month", "Category", "Spent"]:
            assert col in trend.columns


def test_category_mapping(budget, transactions):
    tracker = BudgetTracker(budget, transactions)
    tracker.add_mapping("Dining Out", ["ubereats", "grubhub"])
    summary = tracker.summary()
    assert len(summary) > 0


def test_empty_transactions(budget):
    empty_df = pd.DataFrame(columns=["date", "description", "amount", "category", "source"])
    tracker = BudgetTracker(budget, empty_df)
    summary = tracker.summary()
    assert (summary["Spent"] == 0).all()
