"""Tests for TransactionParser."""

import pytest
from pathlib import Path

from budget_agent.transactions import TransactionParser
from sample_data.generate import generate_chase_csv, generate_capital_one_csv, generate_venmo_csv


@pytest.fixture(scope="session")
def chase_csv(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    return generate_chase_csv(tmp / "chase.csv")


@pytest.fixture(scope="session")
def capital_one_csv(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    return generate_capital_one_csv(tmp / "cap1.csv")


@pytest.fixture(scope="session")
def venmo_csv(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    return generate_venmo_csv(tmp / "venmo.csv")


def test_chase_loads_transactions(chase_csv):
    parser = TransactionParser()
    parser.load_credit_card(chase_csv, "chase")
    df = parser.dataframe
    assert len(df) > 0


def test_chase_schema(chase_csv):
    parser = TransactionParser()
    parser.load_credit_card(chase_csv, "chase")
    df = parser.dataframe
    for col in ["date", "description", "amount", "category", "source"]:
        assert col in df.columns, f"Missing column: {col}"


def test_chase_source_label(chase_csv):
    parser = TransactionParser()
    parser.load_credit_card(chase_csv, "my_chase")
    df = parser.dataframe
    assert (df["source"] == "my_chase").all()


def test_capital_one_loads(capital_one_csv):
    parser = TransactionParser()
    parser.load_credit_card(capital_one_csv, "capital_one")
    df = parser.dataframe
    assert len(df) > 0


def test_venmo_loads(venmo_csv):
    parser = TransactionParser()
    parser.load_venmo(venmo_csv)
    df = parser.dataframe
    assert len(df) > 0


def test_venmo_filters_transfers(venmo_csv):
    parser = TransactionParser()
    parser.load_venmo(venmo_csv)
    df = parser.dataframe
    # Standard transfers should be filtered out
    assert not (df["description"].str.contains("Standard Transfer", case=False)).any()


def test_multi_source_load(chase_csv, venmo_csv):
    parser = TransactionParser()
    parser.load_credit_card(chase_csv, "chase")
    parser.load_venmo(venmo_csv)
    df = parser.dataframe
    sources = set(df["source"].unique())
    assert "chase" in sources
    assert "venmo" in sources


def test_filter_by_month(chase_csv):
    parser = TransactionParser()
    parser.load_credit_card(chase_csv, "chase")
    jan = parser.filter_by_month(2024, 1)
    assert len(jan) > 0
    assert (jan["date"].dt.month == 1).all()
    assert (jan["date"].dt.year == 2024).all()


def test_missing_file_raises():
    parser = TransactionParser()
    with pytest.raises(FileNotFoundError):
        parser.load_credit_card("nonexistent.csv")
