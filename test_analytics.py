
import pandas as pd

from analytics import (
    calculate_revenue,
    calculate_total_profit,
    calculate_average_order_value,
    revenue_by_category,
    top_products_by_revenue,
    revenue_by_region,
    monthly_revenue,
)


df = pd.read_csv("data/sample_sales.csv")

print("Total revenue:", calculate_revenue(df))
print("Total profit:", calculate_total_profit(df))
print("Average order value:", calculate_average_order_value(df))

print("\nRevenue by category:")
print(revenue_by_category(df))

print("\nTop products:")
print(top_products_by_revenue(df))

print("\nRevenue by region:")
print(revenue_by_region(df))

print("\nMonthly revenue:")
print(monthly_revenue(df))