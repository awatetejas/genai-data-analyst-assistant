"""Safe, predefined analytics operations for the GenAI Data Analyst app."""
from analytics import (
    calculate_average_order_value, calculate_revenue, calculate_total_profit,
    monthly_revenue, revenue_by_category, revenue_by_region, top_products_by_revenue,
)

ANALYSIS_REQUIREMENTS = {
    "total_revenue": {"quantity", "unit_price"},
    "total_profit": {"profit"},
    "average_order_value": {"order_id", "quantity", "unit_price"},
    "revenue_by_category": {"category", "quantity", "unit_price"},
    "top_products": {"product", "quantity", "unit_price"},
    "revenue_by_region": {"region", "quantity", "unit_price", "profit"},
    "monthly_revenue": {"order_date", "quantity", "unit_price"},
    "dataset_summary": set(),
}
ANALYSIS_LABELS = {
    "total_revenue": "Total revenue",
    "total_profit": "Total profit",
    "average_order_value": "Average order value",
    "revenue_by_category": "Revenue by category",
    "top_products": "Top products by revenue",
    "revenue_by_region": "Revenue and profit by region",
    "monthly_revenue": "Monthly revenue",
    "dataset_summary": "Dataset summary",
}


class AnalysisValidationError(ValueError):
    """Raised when the uploaded dataset cannot support an analysis."""


def validate_analysis_columns(analysis, columns):
    if analysis not in ANALYSIS_REQUIREMENTS:
        raise AnalysisValidationError(f"Unsupported analysis: {analysis}")
    missing = sorted(ANALYSIS_REQUIREMENTS[analysis] - set(columns))
    if missing:
        names = ", ".join(f"`{name}`" for name in missing)
        raise AnalysisValidationError(
            f"This question requires these column(s): {names}. "
            "Try another question or upload a dataset containing those columns."
        )


def compute_analysis(analysis, data):
    """Run a fixed Python analysis; never execute model-generated code."""
    validate_analysis_columns(analysis, data.columns)
    if analysis == "total_revenue":
        return {"total_revenue": calculate_revenue(data)}
    if analysis == "total_profit":
        return {"total_profit": calculate_total_profit(data)}
    if analysis == "average_order_value":
        return {"average_order_value": calculate_average_order_value(data)}
    if analysis == "revenue_by_category":
        return revenue_by_category(data).to_dict(orient="records")
    if analysis == "top_products":
        return top_products_by_revenue(data, n=5).to_dict(orient="records")
    if analysis == "revenue_by_region":
        return revenue_by_region(data).to_dict(orient="records")
    if analysis == "monthly_revenue":
        return monthly_revenue(data).to_dict(orient="records")
    if analysis == "dataset_summary":
        numeric = data.select_dtypes(include="number")
        return {
            "rows": int(len(data)),
            "columns": list(data.columns),
            "missing_cells": int(data.isna().sum().sum()),
            "duplicate_rows": int(data.duplicated().sum()),
            "numeric_summary": numeric.describe().round(2).to_dict(),
            "sample_rows": data.head(5).to_dict(orient="records"),
        }
    raise AnalysisValidationError(f"Unsupported analysis: {analysis}")
