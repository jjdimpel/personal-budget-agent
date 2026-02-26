"""Tests for BudgetLoader."""

import pytest
from pathlib import Path
import pandas as pd

from budget_agent.budget import BudgetLoader

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


@pytest.fixture(scope="session")
def budget_template(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    path = BudgetLoader.create_template(tmp / "budget.xlsx")
    return path


def test_create_template_produces_file(budget_template):
    assert budget_template.exists()


def test_load_returns_dict(budget_template):
    loader = BudgetLoader(budget_template)
    budget = loader.load()
    assert isinstance(budget, dict)
    assert len(budget) > 0


def test_all_values_are_numeric(budget_template):
    loader = BudgetLoader(budget_template)
    budget = loader.load()
    for k, v in budget.items():
        assert isinstance(v, (int, float)), f"{k} value is {type(v)}"


def test_total_budget_positive(budget_template):
    loader = BudgetLoader(budget_template)
    assert loader.total_budget > 0


def test_required_categories_present(budget_template):
    loader = BudgetLoader(budget_template)
    budget = loader.load()
    expected = {"Housing", "Groceries", "Dining Out", "Savings"}
    assert expected.issubset(set(budget.keys()))


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        BudgetLoader("nonexistent.xlsx").load()
