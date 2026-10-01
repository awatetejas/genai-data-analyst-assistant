"""Run with: python -m pytest -q"""
import pandas as pd
import pytest
from query_engine import AnalysisValidationError, compute_analysis, validate_analysis_columns


@pytest.fixture
def sales_df():
    return pd.DataFrame({
        "order_id": [1, 2, 3],
        "order_date": ["2026-01-02", "2026-01-10", "2026-02-03"],
        "product": ["Pen", "Book", "Pen"],
        "category": ["Stationery", "Books", "Stationery"],
        "region": ["West", "South", "West"],
        "quantity": [2, 1, 3],
        "unit_price": [10, 100, 10],
        "profit": [5, 30, 8],
    })


def test_total_revenue(sales_df):
    assert compute_analysis("total_revenue", sales_df)["total_revenue"] == 150


def test_total_profit(sales_df):
    assert compute_analysis("total_profit", sales_df)["total_profit"] == 43


def test_average_order_value(sales_df):
    assert compute_analysis("average_order_value", sales_df)["average_order_value"] == 50


def test_top_products(sales_df):
    result = compute_analysis("top_products", sales_df)

    assert isinstance(result, list)
    assert result[0]["product"] == "Book"
    assert result[0]["revenue"] == 100

    assert result[1]["product"] == "Pen"
    assert result[1]["revenue"] == 50


def test_missing_columns_raise_helpful_error():
    with pytest.raises(AnalysisValidationError, match="quantity"):
        validate_analysis_columns("total_revenue", ["product", "unit_price"])


def test_dataset_summary_does_not_need_sales_columns():
    result = compute_analysis("dataset_summary", pd.DataFrame({"name": ["A", "B"], "score": [5, 8]}))
    assert result["rows"] == 2
    assert result["columns"] == ["name", "score"]


def test_unknown_analysis_is_rejected(sales_df):
    with pytest.raises(AnalysisValidationError, match="Unsupported analysis"):
        compute_analysis("run_arbitrary_code", sales_df)
