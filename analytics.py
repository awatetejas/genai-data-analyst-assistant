
import pandas as pd


def calculate_revenue(df):
    """Calculate total revenue from quantity and unit price."""
    required = {"quantity", "unit_price"}

    if not required.issubset(df.columns):
        raise ValueError(
            f"Missing required columns: {required - set(df.columns)}"
        )

    revenue = df["quantity"] * df["unit_price"]
    return float(revenue.sum())


def calculate_total_profit(df):
    """Calculate total profit."""
    if "profit" not in df.columns:
        raise ValueError("Dataset must contain a profit column.")

    return float(df["profit"].sum())


def calculate_average_order_value(df):
    """Calculate average revenue per order."""
    if "order_id" not in df.columns:
        raise ValueError("Dataset must contain an order_id column.")

    order_revenue = (
        df.assign(revenue=df["quantity"] * df["unit_price"])
        .groupby("order_id")["revenue"]
        .sum()
    )

    if order_revenue.empty:
        return 0.0

    return float(order_revenue.mean())


def revenue_by_category(df):
    """Calculate revenue for each product category."""
    required = {"category", "quantity", "unit_price"}

    if not required.issubset(df.columns):
        raise ValueError("Required columns are missing.")

    data = df.assign(
        revenue=df["quantity"] * df["unit_price"]
    )

    return (
        data.groupby("category", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
    )


def top_products_by_revenue(df, n=5):
    """Return the top n products by revenue."""
    data = df.assign(
        revenue=df["quantity"] * df["unit_price"]
    )

    result = (
        data.groupby("product", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
    )

    return result.head(n)


def revenue_by_region(df):
    """Calculate revenue and profit by region."""
    data = df.assign(
        revenue=df["quantity"] * df["unit_price"]
    )

    return (
        data.groupby("region", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
        )
        .sort_values("revenue", ascending=False)
    )


def monthly_revenue(df):
    """Calculate monthly revenue from order dates."""
    required = {"order_date", "quantity", "unit_price"}

    if not required.issubset(df.columns):
        raise ValueError("Required columns are missing.")

    data = df.copy()
    data["order_date"] = pd.to_datetime(
        data["order_date"], errors="coerce"
    )
    data = data.dropna(subset=["order_date"])

    data["revenue"] = data["quantity"] * data["unit_price"]

    return (
        data.groupby(data["order_date"].dt.to_period("M"))["revenue"]
        .sum()
        .rename_axis("month")
        .reset_index()
        .assign(month=lambda x: x["month"].astype(str))
    )