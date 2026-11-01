"""
Product Line Profitability & Margin Performance Analysis - Nassau Candy Distributor
Run:  streamlit run app.py
Data: upload the Nassau Candy CSV in the sidebar (or place it next to app.py as nassau_candy.csv)
"""
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Nassau Candy - Profitability", layout="wide")

# ---------------------------------------------------------------- data
FACTORY_MAP = {
    "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
    "Wonka Bar -Scrumdiddlyumptious": "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's",
    "Laffy Taffy": "Sugar Shack",
    "SweeTARTS": "Sugar Shack",
    "Nerds": "Sugar Shack",
    "Fun Dip": "Sugar Shack",
    "Fizzy Lifting Drinks": "Sugar Shack",
    "Everlasting Gobstopper": "Secret Factory",
    "Hair Toffee": "The Other Factory",
    "Lickable Wallpaper": "Secret Factory",
    "Wonka Gum": "Secret Factory",
    "Kazookles": "The Other Factory",
}


@st.cache_data(show_spinner=False)
def load_and_clean(file) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(file, encoding="latin1") if not hasattr(file, "name") or file.name.endswith(".csv") else pd.read_excel(file)
    df.columns = [c.strip() for c in df.columns]
    log = {"raw_rows": len(df)}

    for c in ["Order Date", "Ship Date"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)

    for c in ["Sales", "Units", "Gross Profit", "Cost"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in ["Division", "Product Name", "Region", "Ship Mode"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    df["Product Name"] = df["Product Name"].str.replace(r"\s+", " ", regex=True)

    # validation rules from the brief
    before = len(df)
    df = df.dropna(subset=["Sales", "Cost", "Gross Profit"])
    log["missing_core_values"] = before - len(df)

    before = len(df)
    df = df[df["Sales"] > 0]
    log["zero_or_negative_sales"] = before - len(df)

    before = len(df)
    df = df[df["Cost"] >= 0]
    log["negative_cost"] = before - len(df)

    # units: impute missing / non-positive with median units of the same product
    bad_units = df["Units"].isna() | (df["Units"] <= 0)
    log["units_imputed"] = int(bad_units.sum())
    med = df.loc[~bad_units].groupby("Product Name")["Units"].median()
    df.loc[bad_units, "Units"] = df.loc[bad_units, "Product Name"].map(med).fillna(1)

    # profit consistency check: Gross Profit should equal Sales - Cost
    mismatch = (df["Gross Profit"] - (df["Sales"] - df["Cost"])).abs() > 0.05
    log["profit_mismatch_rows"] = int(mismatch.sum())
    df.loc[mismatch, "Gross Profit"] = df["Sales"] - df["Cost"]

    before = len(df)
    df = df.drop_duplicates()
    log["duplicates"] = before - len(df)

    df["Factory"] = df["Product Name"].map(FACTORY_MAP)
    df["Margin %"] = df["Gross Profit"] / df["Sales"] * 100
    df["Profit per Unit"] = df["Gross Profit"] / df["Units"]
    log["clean_rows"] = len(df)
    return df.reset_index(drop=True), log


def product_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["Division", "Product Name"], as_index=False).agg(
        Sales=("Sales", "sum"), Cost=("Cost", "sum"),
        Gross_Profit=("Gross Profit", "sum"), Units=("Units", "sum"), Orders=("Order ID", "nunique"),
    )
    g["Gross Margin %"] = g["Gross_Profit"] / g["Sales"] * 100
    g["Profit per Unit"] = g["Gross_Profit"] / g["Units"]
    g["Revenue Contribution %"] = g["Sales"] / g["Sales"].sum() * 100
    g["Profit Contribution %"] = g["Gross_Profit"] / g["Gross_Profit"].sum() * 100
    return g


def margin_volatility(df: pd.DataFrame) -> pd.Series:
    """Std-dev of monthly gross margin (%) per product."""
    if "Order Date" not in df.columns or df["Order Date"].isna().all():
        return pd.Series(dtype=float)
    m = df.assign(Month=df["Order Date"].dt.to_period("M")).groupby(["Product Name", "Month"]).agg(
        s=("Sales", "sum"), p=("Gross Profit", "sum"))
    m["margin"] = m["p"] / m["s"] * 100
    return m.groupby("Product Name")["margin"].std().rename("Margin Volatility")


def pareto(series: pd.Series) -> pd.DataFrame:
    s = series.sort_values(ascending=False)
    out = s.reset_index()
    out.columns = ["Product Name", "Value"]
    out["Cumulative %"] = out["Value"].cumsum() / out["Value"].sum() * 100
    out["Rank"] = np.arange(1, len(out) + 1)
    return out


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Nassau Candy")
upload = st.sidebar.file_uploader("Upload dataset (CSV/XLSX)", type=["csv", "xlsx"])
default_path = "nassau_candy.csv"
src = upload if upload is not None else (default_path if os.path.exists(default_path) else None)

if src is None:
    st.title("Product Line Profitability & Margin Performance")
    st.info("Upload the Nassau Candy dataset in the sidebar to begin.")
    st.stop()

df, log = load_and_clean(src)

st.sidebar.markdown("### Filters")
if df["Order Date"].notna().any():
    dmin, dmax = df["Order Date"].min().date(), df["Order Date"].max().date()
    dr = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
    if len(dr) == 2:
        df = df[(df["Order Date"].dt.date >= dr[0]) & (df["Order Date"].dt.date <= dr[1])]

divs = sorted(df["Division"].unique())
sel_div = st.sidebar.multiselect("Division", divs, default=divs)
df = df[df["Division"].isin(sel_div)]

margin_thr = st.sidebar.slider("Margin threshold (%)", 0, 100, 40)
search = st.sidebar.text_input("Product search")
if search:
    df = df[df["Product Name"].str.contains(search, case=False, na=False)]

if df.empty:
    st.warning("No data for the selected filters.")
    st.stop()

prod = product_table(df)
vol = margin_volatility(df)
prod = prod.merge(vol, left_on="Product Name", right_index=True, how="left")
prod["Margin Risk"] = prod["Gross Margin %"] < margin_thr

# ---------------------------------------------------------------- header + KPIs
st.title("Product Line Profitability & Margin Performance Analysis")
total_sales, total_profit = df["Sales"].sum(), df["Gross Profit"].sum()
k = st.columns(5)
k[0].metric("Total Sales", f"${total_sales:,.0f}")
k[1].metric("Total Gross Profit", f"${total_profit:,.0f}")
k[2].metric("Gross Margin", f"{total_profit / total_sales * 100:.1f}%")
k[3].metric("Profit per Unit", f"${total_profit / df['Units'].sum():.2f}")
k[4].metric("Products below threshold", int(prod["Margin Risk"].sum()))

tabs = st.tabs(["Product Profitability", "Division Performance", "Cost vs Margin", "Profit Concentration", "Data Quality"])

# ---- 1. product profitability
with tabs[0]:
    c1, c2 = st.columns(2)
    metric = c1.radio("Rank by", ["Gross_Profit", "Gross Margin %"], horizontal=True)
    lb = prod.sort_values(metric, ascending=True)
    fig = px.bar(lb, x=metric, y="Product Name", color="Division", orientation="h",
                 title=f"Product leaderboard by {metric.replace('_', ' ')}")
    fig.update_layout(height=550)
    c1.plotly_chart(fig, use_container_width=True)
    fig = px.pie(prod, names="Product Name", values="Gross_Profit", title="Profit contribution by product")
    c2.plotly_chart(fig, use_container_width=True)

    # quadrant classification
    s_med, m_med = prod["Sales"].median(), prod["Gross Margin %"].median()

    def quad(r):
        hs, hm = r["Sales"] >= s_med, r["Gross Margin %"] >= m_med
        return ("High-sales / High-margin" if hs and hm else "High-sales / Low-margin" if hs
                else "Low-sales / High-margin" if hm else "Low-sales / Low-margin")

    prod["Segment"] = prod.apply(quad, axis=1)
    st.subheader("Product segmentation (median split on sales and margin)")
    st.dataframe(prod[["Division", "Product Name", "Sales", "Gross_Profit", "Gross Margin %",
                       "Profit per Unit", "Profit Contribution %", "Segment"]]
                 .sort_values("Gross_Profit", ascending=False).round(2), use_container_width=True)

# ---- 2. division
with tabs[1]:
    d = df.groupby("Division", as_index=False).agg(Sales=("Sales", "sum"), Gross_Profit=("Gross Profit", "sum"))
    d["Gross Margin %"] = d["Gross_Profit"] / d["Sales"] * 100
    d["Revenue Share %"] = d["Sales"] / d["Sales"].sum() * 100
    d["Profit Share %"] = d["Gross_Profit"] / d["Gross_Profit"].sum() * 100
    d["Imbalance (pp)"] = d["Revenue Share %"] - d["Profit Share %"]
    c1, c2 = st.columns(2)
    m = d.melt(id_vars="Division", value_vars=["Sales", "Gross_Profit"], var_name="Measure")
    c1.plotly_chart(px.bar(m, x="Division", y="value", color="Measure", barmode="group",
                           title="Revenue vs profit by division"), use_container_width=True)
    c2.plotly_chart(px.box(df, x="Division", y="Margin %", color="Division",
                           title="Margin distribution by division (order level)"), use_container_width=True)
    st.dataframe(d.round(2), use_container_width=True)
    st.caption("Positive imbalance = division earns a larger share of revenue than of profit (structural margin issue).")

# ---- 3. cost vs margin
with tabs[2]:
    fig = px.scatter(prod, x="Cost", y="Sales", size="Units", color="Gross Margin %", hover_name="Product Name",
                     color_continuous_scale="RdYlGn", title="Cost vs sales (bubble = units)")
    mx = max(prod["Cost"].max(), prod["Sales"].max())
    fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", name="Break-even", line=dict(dash="dash")))
    st.plotly_chart(fig, use_container_width=True)

    cost_ratio_med = (prod["Cost"] / prod["Sales"]).median()
    prod["Cost / Sales"] = prod["Cost"] / prod["Sales"]
    prod["Action"] = np.select(
        [prod["Margin Risk"] & (prod["Profit Contribution %"] < 100 / len(prod) / 2),
         prod["Margin Risk"] & (prod["Cost / Sales"] > cost_ratio_med),
         prod["Margin Risk"]],
        ["Discontinuation review", "Cost renegotiation", "Repricing"], default="OK")
    st.subheader(f"Margin risk flags (margin < {margin_thr}%)")
    st.dataframe(prod[prod["Margin Risk"]][["Product Name", "Division", "Gross Margin %", "Cost / Sales",
                                            "Profit Contribution %", "Margin Volatility", "Action"]]
                 .sort_values("Gross Margin %").round(2), use_container_width=True)

# ---- 4. pareto
with tabs[3]:
    basis = st.radio("Pareto basis", ["Sales", "Gross_Profit"], horizontal=True)
    p = pareto(prod.set_index("Product Name")[basis])
    fig = go.Figure()
    fig.add_bar(x=p["Product Name"], y=p["Value"], name=basis)
    fig.add_scatter(x=p["Product Name"], y=p["Cumulative %"], yaxis="y2", name="Cumulative %", mode="lines+markers")
    fig.add_hline(y=80, line_dash="dot", yref="y2")
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105]), title=f"Pareto - {basis}")
    st.plotly_chart(fig, use_container_width=True)

    def share_for_80(basis_col):
        pp = pareto(prod.set_index("Product Name")[basis_col])
        n = int((pp["Cumulative %"] < 80).sum()) + 1
        return n, n / len(pp) * 100

    n_s, pc_s = share_for_80("Sales")
    n_p, pc_p = share_for_80("Gross_Profit")
    c1, c2, c3 = st.columns(3)
    c1.metric("Products for 80% of revenue", f"{n_s} ({pc_s:.0f}%)")
    c2.metric("Products for 80% of profit", f"{n_p} ({pc_p:.0f}%)")
    top = prod.sort_values("Gross_Profit", ascending=False).iloc[0]
    c3.metric("Top product profit share", f"{top['Profit Contribution %']:.1f}%", top["Product Name"])
    if pc_p < 50:
        st.warning("Profit is concentrated in a minority of products - over-dependency risk.")

    st.subheader("Dependency by factory")
    f = df.dropna(subset=["Factory"]).groupby("Factory", as_index=False).agg(
        Sales=("Sales", "sum"), Gross_Profit=("Gross Profit", "sum"))
    f["Profit Share %"] = f["Gross_Profit"] / f["Gross_Profit"].sum() * 100
    st.plotly_chart(px.bar(f, x="Factory", y="Profit Share %", title="Share of gross profit by factory"),
                    use_container_width=True)

# ---- 5. data quality
with tabs[4]:
    st.json(log)
    st.dataframe(df.head(200), use_container_width=True)
    st.download_button("Download product table (CSV)", prod.to_csv(index=False), "product_profitability.csv")
