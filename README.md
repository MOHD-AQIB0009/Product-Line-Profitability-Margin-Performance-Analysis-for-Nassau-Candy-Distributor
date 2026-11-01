# Product Line Profitability & Margin Performance Analysis - Nassau Candy Distributor

A Streamlit dashboard that analyses which Nassau Candy products and divisions truly drive profit, which ones are margin risks, and how concentrated profit is across the product portfolio.

Built as part of the Unified Mentor Machine Learning internship (Project ID 25318).

## Problem

Sales volume alone is misleading. Some products sell in high volume but earn little profit, or carry disproportionate manufacturing cost. This project gives visibility into:

- Which product lines deliver the highest gross margin
- Whether high-sales products are actually profitable
- How profitability varies across divisions
- Which products represent margin risk

## Features

| Tab | What it shows |
|---|---|
| Product Profitability | Product leaderboard (by gross profit or margin), profit contribution chart, high/low sales vs margin segmentation |
| Division Performance | Revenue vs profit by division, margin distribution, revenue-profit share imbalance |
| Cost vs Margin | Cost-sales scatter with break-even line, margin risk flags, suggested action (repricing, cost renegotiation, discontinuation review) |
| Profit Concentration | Pareto charts (sales and profit), products needed for 80% of revenue/profit, factory dependency |
| Data Quality | Cleaning log and cleaned data preview, product table download |

**Sidebar controls:** date range, division filter, margin threshold slider, product search.

## KPIs

| KPI | Formula |
|---|---|
| Gross Margin (%) | Gross Profit / Sales |
| Profit per Unit | Gross Profit / Units |
| Revenue Contribution | Product sales / total sales |
| Profit Contribution | Product profit / total profit |
| Margin Volatility | Standard deviation of monthly gross margin (%) per product |

## Data cleaning rules

1. Drop rows with missing Sales, Cost or Gross Profit
2. Remove zero or negative sales and negative cost records
3. Impute missing or non-positive Units with the product's median units
4. Recompute Gross Profit as Sales - Cost where it disagrees (tolerance 0.05)
5. Standardize product and division labels (trim whitespace)
6. Remove duplicate rows

Every step's row count is shown in the Data Quality tab.

## Project structure

```
nassau_profitability/
|-- app.py                     # Streamlit dashboard
|-- requirements.txt           # Python dependencies
|-- make_sample.py             # Generates a synthetic test CSV
|-- nassau_candy_SAMPLE.csv    # Synthetic data for testing only
`-- README.md
```

## Setup and run

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

Note: use `streamlit run`, not `python app.py`. The app opens at http://localhost:8501.

Then either:
- upload the Nassau Candy dataset (CSV or XLSX) using the sidebar, or
- save it as `nassau_candy.csv` next to `app.py` and it loads automatically.

## Expected dataset columns

Row ID, Order ID, Order Date, Ship Date, Ship Mode, Customer ID, Country/Region, City, State/Province, Postal Code, Division, Region, Product ID, Product Name, Sales, Units, Gross Profit, Cost

Dates are parsed day-first (dd-mm-yyyy). If your file uses month-first dates, change `dayfirst=True` in `load_and_clean`.

## Sample data warning

`nassau_candy_SAMPLE.csv` is randomly generated for testing the dashboard only. It is not real Nassau Candy data. Do not draw conclusions or write reports from it.

## Tech stack

Python, Streamlit, pandas, NumPy, Plotly

## Author

Mohd Aqib - https://github.com/MOHD-AQIB0009
