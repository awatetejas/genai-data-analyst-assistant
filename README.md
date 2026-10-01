# InsightAI — GenAI-Powered Data Analyst Assistant

A portfolio project combining data analysis with a natural-language interface. Upload CSV/Excel data, explore KPIs and charts, ask supported questions, and export filtered data and a summary report.

> **Status:** Update this after completing local testing and deploying a working demo.

## Features
- CSV and Excel upload
- Dataset overview, missing-value and duplicate checks
- Sales KPIs when required columns exist: revenue, profit, average order value
- Interactive category, region, and monthly revenue charts
- Date/category/region filters when matching columns exist
- Natural-language questions routed to predefined analyses
- Python calculates results; the LLM explains computed results
- Conversation history and follow-up context
- CSV, Excel, and Markdown report exports

## Tech stack
Python, Pandas, Streamlit, Plotly, OpenRouter API, Requests, python-dotenv, pytest.

## Architecture
```text
CSV/XLSX -> data_loader.py -> DataFrame
                              |-> app.py: UI, filters, charts, exports
                              |-> query_engine.py: supported analysis + validation
                                      -> analytics.py: Python calculations
                                      -> computed result
                                      -> llm_client.py: OpenRouter explanation
                                      -> Streamlit answer
```
The LLM does not execute generated Python or SQL. Calculations use predefined Python functions.

## Project structure
```text
GenAI-Data-Analyst/
├── app.py
├── analytics.py
├── data_loader.py
├── query_engine.py
├── llm_client.py
├── requirements.txt
├── .env                 # local only; never commit
├── .gitignore
├── data/sample_sales.csv
└── test_query_engine.py
```

## Run locally

### 1. Clone the repository
```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd GenAI-Data-Analyst
```

### 2. Create and activate a virtual environment
Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
If activation is blocked, for this terminal session only:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```powershell
python -m pip install -r requirements.txt
```

### 4. Configure the API key
Create a local `.env` file in the project root:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```
Use the exact variable name expected by `llm_client.py`. Never commit `.env` or share your key.

### 5. Run tests and start the app
```powershell
python -m pytest -q
streamlit run app.py
```

## Sample dataset validation
With the included sample sales data, expected baseline values are:

| Metric | Expected value |
|---|---:|
| Total revenue | ₹315,500 |
| Total profit | ₹44,100 |
| Average order value | ₹31,550 |

These baseline values assume all rows are included by the filters.

## Example questions
- What is the total revenue?
- What is the total profit?
- What is the average order value?
- Which category generated the most revenue?
- Which are the top products by revenue?
- Show revenue by region.
- How has revenue changed month by month?
- Summarize this dataset.

Supported questions depend on the analysis labels implemented in the current code.

## Deployment: Streamlit Community Cloud
1. Push the project to GitHub.
2. Verify `.env` and `.venv/` are excluded by `.gitignore`.
3. Create a new app in Streamlit Community Cloud, select your repository and branch, and set `app.py` as the entry point.
4. In the app's Secrets settings, add the API key using the exact variable name expected by `llm_client.py`. For example:
   ```toml
   OPENROUTER_API_KEY = "your_api_key_here"
   ```
5. Deploy and test the public URL using a non-sensitive sample dataset.

Never commit secrets. Review API usage limits/costs and avoid uploading confidential data. When asking a question, data may be processed by the configured LLM provider.

## Known limitations
- Questions are limited to analyses implemented in the query engine.
- Sales KPIs require compatible columns such as `quantity` and `unit_price`.
- Column names and date formats may vary across datasets.
- LLM responses may be wrong; verify conclusions against the displayed computed result.
- Hosting and API use may have limits or costs.

## Screenshots
After testing, add screenshots to `screenshots/` and embed them here:
```markdown
![Overview dashboard](screenshots/overview.png)
```
Suggested screenshots: Overview, AI Assistant, Data Quality, Export.

## Future improvements
- Robust column mapping
- PDF report export
- Anomaly detection and explainable trend alerts
- Caching and performance tests for larger datasets
- Authentication and stronger privacy controls before handling sensitive data

## Author
**Tejas Awate**  
Data Analytics | Business Intelligence | Python | GenAI

Add your LinkedIn, GitHub, and portfolio links here.
