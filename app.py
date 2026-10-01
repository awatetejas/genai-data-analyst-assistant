from __future__ import annotations

from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from data_loader import load_dataset
from llm_client import LLMError, classify_question, explain_result
from query_engine import ANALYSIS_LABELS, AnalysisValidationError, compute_analysis

st.set_page_config(
    page_title="InsightAI | Data Analyst Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Theme and helpers ----------
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
      [data-testid="stMetric"] {
        background: #242424;
        border: 1px solid rgba(251,101,133,.28);
        padding: 16px 18px;
        border-radius: 12px;
      }
      [data-testid="stMetricLabel"] {color: #c9c9c9;}
      [data-testid="stMetricValue"] {color: #fcfcfc;}
      .hero {
        padding: 1.1rem 1.3rem;
        background: linear-gradient(120deg, #242424 0%, #1b1b1b 100%);
        border: 1px solid rgba(251,101,133,.35);
        border-radius: 16px;
        margin-bottom: 1rem;
      }
      .hero h1 {color: #fcfcfc;}
      .muted {color: #c9c9c9; opacity: .9; font-size: .92rem;}
      div[data-testid="stSidebar"] {border-right: 1px solid rgba(251,101,133,.18);}
    </style>
    """,
    unsafe_allow_html=True,
)

CURRENCY_COLUMNS = {"unit_price", "revenue", "profit", "total_revenue", "total_profit", "average_order_value"}

def money(value: float | int | str | None) -> str:
    try:
        return f"₹{float(value):,.0f}" if value is not None else "—"
    except (TypeError, ValueError):
        return "—"

def has_sales_schema(data: pd.DataFrame) -> bool:
    return {"quantity", "unit_price"}.issubset(data.columns)

def revenue_series(data: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(data["quantity"], errors="coerce").fillna(0) * pd.to_numeric(
        data["unit_price"], errors="coerce"
    ).fillna(0)

def safe_csv(data: pd.DataFrame) -> bytes:
    return data.to_csv(index=False).encode("utf-8-sig")

def safe_excel(data: pd.DataFrame) -> bytes | None:
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            data.to_excel(writer, index=False, sheet_name="Filtered Data")
        return output.getvalue()
    except Exception:
        return None

def make_report(data: pd.DataFrame, filename: str) -> str:
    lines = [
        "# InsightAI — Dataset Report",
        "",
        f"- **Source file:** {filename}",
        f"- **Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        f"- **Rows in current view:** {len(data):,}",
        f"- **Columns:** {len(data.columns):,}",
        f"- **Missing cells:** {int(data.isna().sum().sum()):,}",
        f"- **Duplicate rows:** {int(data.duplicated().sum()):,}",
        "",
    ]
    if has_sales_schema(data):
        revenue = revenue_series(data).sum()
        lines.extend(["## Business KPIs", "", f"- **Total revenue:** {money(revenue)}"])
        if "profit" in data.columns:
            lines.append(f"- **Total profit:** {money(pd.to_numeric(data['profit'], errors='coerce').fillna(0).sum())}")
        if "order_id" in data.columns:
            order_revenue = pd.DataFrame({"order_id": data["order_id"], "revenue": revenue_series(data)}).groupby("order_id")["revenue"].sum()
            lines.append(f"- **Average order value:** {money(order_revenue.mean() if not order_revenue.empty else 0)}")
    lines.extend(["", "## Data preview", "", str(data.head(10).to_markdown(index=False)), ""])
    return "\n".join(lines)

# ---------- Header ----------
st.markdown(
    """
    <div class="hero">
      <div style="font-size: .85rem; letter-spacing: .08em; text-transform: uppercase; opacity: .7;">
        GenAI · Analytics · Decision Support
      </div>
      <h1 style="margin: .25rem 0;">InsightAI Data Analyst</h1>
      <div class="muted">Explore your data, monitor business metrics, and ask questions in natural language.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Workspace")
    uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    st.divider()
    st.caption("Supported: CSV, XLSX, XLS")

if uploaded_file is None:
    st.info("Upload a dataset from the sidebar to open your analytics workspace.")
    st.markdown("### What you can do")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**📈 Explore**\n\nReview KPIs and interactive charts.")
    c2.markdown("**🧠 Ask questions**\n\nUse plain English to request supported analyses.")
    c3.markdown("**📤 Export**\n\nDownload the filtered dataset and a summary report.")
    st.stop()

try:
    raw_df = load_dataset(uploaded_file)
except Exception as exc:
    st.error(f"Could not load this file. Check that it is a valid CSV or Excel workbook. Details: {exc}")
    st.stop()

if raw_df is None or raw_df.empty:
    st.warning("This file contains no data rows.")
    st.stop()

# Keep chat separate for different uploads, including files with same name but different content.
file_signature = f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}:{len(raw_df)}:{','.join(map(str, raw_df.columns))}"
if st.session_state.get("dataset_signature") != file_signature:
    st.session_state["dataset_signature"] = file_signature
    st.session_state["chat_history"] = []

# ---------- Sidebar filters ----------
filtered_df = raw_df.copy()
with st.sidebar:
    st.subheader("Filters")
    if "order_date" in filtered_df.columns:
        parsed_dates = pd.to_datetime(filtered_df["order_date"], errors="coerce")
        valid_dates = parsed_dates.dropna()
        if not valid_dates.empty:
            start_default = valid_dates.min().date()
            end_default = valid_dates.max().date()
            date_range = st.date_input(
                "Date range",
                value=(start_default, end_default),
                min_value=start_default,
                max_value=end_default,
            )
            if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = filtered_df.loc[
                    parsed_dates.dt.date.between(start_date, end_date, inclusive="both")
                ].copy()
    for col in ("category", "region"):
        if col in filtered_df.columns:
            options = sorted(filtered_df[col].dropna().astype(str).unique().tolist())
            selected = st.multiselect(f"{col.title()}", options, default=options)
            if selected:
                filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected)].copy()
            elif options:
                filtered_df = filtered_df.iloc[0:0].copy()
    if st.button("Reset filters", use_container_width=True):
        st.rerun()

st.caption(f"Source: **{uploaded_file.name}** · Showing **{len(filtered_df):,} of {len(raw_df):,} rows**")

# ---------- Overview metrics ----------
tab_overview, tab_explore, tab_assistant, tab_quality, tab_export = st.tabs(
    ["Overview", "Explore", "AI Assistant", "Data Quality", "Export"]
)

with tab_overview:
    st.subheader("At a glance")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Rows in view", f"{len(filtered_df):,}", delta=f"{len(filtered_df) - len(raw_df):,} vs source")
    metric_cols[1].metric("Columns", f"{len(filtered_df.columns):,}")
    metric_cols[2].metric("Missing cells", f"{int(filtered_df.isna().sum().sum()):,}")
    metric_cols[3].metric("Duplicate rows", f"{int(filtered_df.duplicated().sum()):,}")

    if filtered_df.empty:
        st.warning("No rows match the current filters. Adjust the filters in the sidebar.")
    elif has_sales_schema(filtered_df):
        revenue = revenue_series(filtered_df)
        kpis = st.columns(3)
        kpis[0].metric("Total Revenue", money(revenue.sum()))
        if "profit" in filtered_df.columns:
            profit = pd.to_numeric(filtered_df["profit"], errors="coerce").fillna(0).sum()
            kpis[1].metric("Total Profit", money(profit))
        else:
            kpis[1].metric("Total Profit", "N/A", help="A `profit` column is required.")
        if "order_id" in filtered_df.columns:
            order_values = pd.DataFrame({"order_id": filtered_df["order_id"], "revenue": revenue}).groupby("order_id")["revenue"].sum()
            aov = order_values.mean() if not order_values.empty else 0
            kpis[2].metric("Average Order Value", money(aov))
        else:
            kpis[2].metric("Average Order Value", "N/A", help="An `order_id` column is required.")

        chart_cols = st.columns(2)
        if "category" in filtered_df.columns:
            category_data = pd.DataFrame({
                "category": filtered_df["category"].astype(str),
                "revenue": revenue,
            }).groupby("category", as_index=False)["revenue"].sum()
            category_data = category_data.iloc[category_data["revenue"].to_numpy().argsort()].reset_index(drop=True)
            fig = px.bar(category_data, x="revenue", y="category", orientation="h",
                         title="Revenue by Category", text="revenue", template="plotly_dark")
            fig.update_traces(texttemplate="₹%{x:,.0f}", textposition="outside", cliponaxis=False)
            fig.update_layout(xaxis_title="Revenue (₹)", yaxis_title="", margin=dict(l=10, r=35, t=55, b=10))
            chart_cols[0].plotly_chart(fig, use_container_width=True)
        if "region" in filtered_df.columns:
            region_data = pd.DataFrame({
                "region": filtered_df["region"].astype(str),
                "revenue": revenue,
            }).groupby("region", as_index=False)["revenue"].sum()
            category_data = category_data.iloc[category_data["revenue"].to_numpy().argsort()].reset_index(drop=True)
            fig = px.pie(region_data, names="region", values="revenue", title="Revenue Share by Region",
                         hole=.45, template="plotly_dark")
            fig.update_layout(margin=dict(l=10, r=10, t=55, b=10))
            chart_cols[1].plotly_chart(fig, use_container_width=True)
        if "order_date" in filtered_df.columns:
            trend = pd.DataFrame({
                "date": pd.to_datetime(filtered_df["order_date"], errors="coerce"),
                "revenue": revenue,
            }).dropna(subset=["date"])
            if not trend.empty:
                trend["month"] = trend["date"].dt.to_period("M").astype(str)
                trend = trend.groupby("month", as_index=False)["revenue"].sum()
                fig = px.line(trend, x="month", y="revenue", markers=True, title="Monthly Revenue Trend",
                              template="plotly_dark")
                fig.update_traces(hovertemplate="%{x}<br>Revenue: ₹%{y:,.0f}<extra></extra>")
                fig.update_layout(xaxis_title="", yaxis_title="Revenue (₹)", margin=dict(l=10, r=10, t=55, b=10))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("This dataset does not contain the `quantity` and `unit_price` columns needed for sales KPIs. Use Explore and AI Assistant for supported dataset summaries.")

with tab_explore:
    st.subheader("Explore records")
    st.caption("Sort, inspect, and search the rows currently included by your filters.")
    search_text = st.text_input("Search across displayed values", placeholder="Type a product, region, ID, or keyword…")
    explore_df = filtered_df
    if search_text.strip():
        mask = explore_df.astype(str).apply(lambda column: column.str.contains(search_text, case=False, na=False)).any(axis=1)
        explore_df = explore_df[mask]
    st.dataframe(explore_df, use_container_width=True, hide_index=True)
    st.caption(f"{len(explore_df):,} row(s) displayed.")

with tab_assistant:
    st.subheader("Ask your dataset")
    st.caption("Examples: “What is total revenue?”, “Which product generated the most revenue?”, “Show monthly revenue trends.”")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("result") is not None and message["role"] == "assistant":
                with st.expander("View Python-computed result"):
                    st.json(message["result"])

    question = st.chat_input("Ask a question about the filtered data…", key="assistant_chat_input")
    if question:
        history_before_question = list(st.session_state.chat_history)
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your question…"):
                try:
                    analysis = classify_question(question, filtered_df.columns, history_before_question)
                    if analysis == "unsupported":
                        answer = (
                            "I can answer supported questions about total revenue, total profit, average order value, "
                            "revenue by category, top products, revenue by region, monthly revenue, and dataset summary. "
                            "Try rephrasing your question around one of these analyses."
                        )
                        st.info(answer)
                        result = None
                    else:
                        result = compute_analysis(analysis, filtered_df)
                        answer = explain_result(
                            question, ANALYSIS_LABELS[analysis], result, history_before_question
                        )
                        st.markdown(answer)
                        with st.expander("View Python-computed result"):
                            st.json(result)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": answer, "result": result}
                    )
                except (AnalysisValidationError, LLMError) as exc:
                    answer = str(exc)
                    st.warning(answer)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": answer, "result": None}
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    answer = f"I couldn't complete that analysis. Check the available columns and values. Details: {exc}"
                    st.warning(answer)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": answer, "result": None}
                    )
        st.rerun()
    if st.session_state.chat_history and st.button("Clear conversation", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()

with tab_quality:
    st.subheader("Data quality")
    quality = pd.DataFrame({
        "Column": filtered_df.columns.astype(str),
        "Data type": [str(dtype) for dtype in filtered_df.dtypes],
        "Missing": [int(value) for value in filtered_df.isna().sum().values],
        "Missing (%)": [
            round(float(filtered_df[col].isna().mean() * 100), 2) if len(filtered_df) else 0
            for col in filtered_df.columns
        ],
        "Unique values": [int(filtered_df[col].nunique(dropna=True)) for col in filtered_df.columns],
    })
    st.dataframe(quality, use_container_width=True, hide_index=True)
    left, right = st.columns(2)
    with left:
        st.metric("Rows with any missing value", f"{int(filtered_df.isna().any(axis=1).sum()):,}")
    with right:
        st.metric("Exact duplicate rows", f"{int(filtered_df.duplicated().sum()):,}")
    missing_by_column = filtered_df.isna().sum().rename_axis("Column").reset_index(name="Missing values")
    missing_by_column = missing_by_column[missing_by_column["Missing values"] > 0].sort_values(by="Missing values")
    if not missing_by_column.empty:
        fig = px.bar(missing_by_column, x="Missing values", y="Column", orientation="h",
                     title="Missing values by column", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No missing values found in the current view.")

with tab_export:
    st.subheader("Export your work")
    st.caption("Exports use the rows currently selected by your sidebar filters.")
    st.download_button(
        "Download filtered data (CSV)",
        data=safe_csv(filtered_df),
        file_name="filtered_dataset.csv",
        mime="text/csv",
        use_container_width=True,
    )
    excel_bytes = safe_excel(filtered_df)
    if excel_bytes is not None:
        st.download_button(
            "Download filtered data (Excel)",
            data=excel_bytes,
            file_name="filtered_dataset.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.info("Excel export is unavailable. Install `openpyxl` to enable it.")
    report_text = make_report(filtered_df, uploaded_file.name)
    st.download_button(
        "Download summary report (Markdown)",
        data=report_text.encode("utf-8"),
        file_name="insightai_summary_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.markdown("#### Report preview")
    st.markdown(report_text)