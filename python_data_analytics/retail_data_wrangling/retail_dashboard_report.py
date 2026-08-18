from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "online_retail_II.xlsx"
OUTPUT_PATH = ROOT / "retail_dashboard.pdf"


def load_data():
    df_2009 = pd.read_excel(DATA_PATH, sheet_name="Year 2009-2010")
    df_2010 = pd.read_excel(DATA_PATH, sheet_name="Year 2010-2011")

    for frame in (df_2009, df_2010):
        frame.columns = [
            "invoice_no",
            "stock_code",
            "description",
            "quantity",
            "invoice_date",
            "unit_price",
            "customer_id",
            "country",
        ]
        frame["invoice_date"] = pd.to_datetime(frame["invoice_date"], errors="coerce")
        frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
        frame["unit_price"] = pd.to_numeric(frame["unit_price"], errors="coerce")
        frame["customer_id"] = pd.to_numeric(frame["customer_id"], errors="coerce")

    df = pd.concat([df_2009, df_2010], ignore_index=True)
    df["amount"] = df["quantity"] * df["unit_price"]
    df["yyyymm"] = (df["invoice_date"].dt.year * 100 + df["invoice_date"].dt.month).astype(int)
    df["is_canceled"] = df["invoice_no"].astype(str).str.startswith("C")
    return df


def summarize_invoice_distribution(df):
    invoice_df = df.groupby("invoice_no")["amount"].sum().reset_index()
    invoice_df.columns = ["invoice_no", "invoice_amount"]
    return invoice_df


def build_monthly_orders(df):
    total = df.groupby("yyyymm")["invoice_no"].nunique().reset_index()
    total.columns = ["yyyymm", "total_orders"]

    canceled = (
        df[df["is_canceled"]]
        .groupby("yyyymm")["invoice_no"]
        .nunique()
        .reset_index()
    )
    canceled.columns = ["yyyymm", "canceled_orders"]

    monthly_orders = total.merge(canceled, on="yyyymm", how="left").fillna(0)
    monthly_orders["placed_orders"] = (
        monthly_orders["total_orders"] - 2 * monthly_orders["canceled_orders"]
    )
    return monthly_orders


def build_monthly_sales(df):
    monthly_sales = df.groupby("yyyymm")["amount"].sum().reset_index()
    monthly_sales.columns = ["yyyymm", "sales_amount"]
    monthly_sales["growth_pct"] = monthly_sales["sales_amount"].pct_change() * 100
    return monthly_sales


def build_monthly_users(df):
    monthly_users = (
        df.dropna(subset=["customer_id"])
        .groupby("yyyymm")["customer_id"]
        .nunique()
        .reset_index()
    )
    monthly_users.columns = ["yyyymm", "active_users"]
    return monthly_users


def build_new_vs_existing(df):
    clean_df = df.dropna(subset=["customer_id"]).copy()
    first_purchase = clean_df.groupby("customer_id")["yyyymm"].min().reset_index()
    first_purchase.columns = ["customer_id", "first_yyyymm"]
    merged = clean_df.merge(first_purchase, on="customer_id")
    merged["user_type"] = merged.apply(
        lambda x: "new" if x["yyyymm"] == x["first_yyyymm"] else "existing",
        axis=1,
    )
    user_monthly = (
        merged.groupby(["yyyymm", "user_type"])["customer_id"]
        .nunique()
        .unstack(fill_value=0)
        .reset_index()
    )
    return user_monthly


def build_rfm(df):
    clean_df = df.dropna(subset=["customer_id"]).copy()
    snapshot_date = clean_df["invoice_date"].max() + pd.Timedelta(days=1)
    rfm = (
        clean_df.groupby("customer_id")
        .agg(
            recency=("invoice_date", lambda x: (snapshot_date - x.max()).days),
            frequency=("invoice_no", "nunique"),
            monetary=("amount", "sum"),
        )
        .reset_index()
    )

    rfm["r_score"] = pd.qcut(rfm["recency"], q=5, labels=[5, 4, 3, 2, 1])
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5])
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5])
    rfm["rfm_score"] = rfm["r_score"].astype(str) + rfm["f_score"].astype(str)

    seg_map = {
        r"[1-2][1-2]": "Hibernating",
        r"[1-2][3-4]": "At Risk",
        r"[1-2]5": "Can't Lose",
        r"3[1-2]": "About to Sleep",
        r"33": "Need Attention",
        r"[3-4][4-5]": "Loyal Customers",
        r"41": "Promising",
        r"51": "New Customers",
        r"[4-5][2-3]": "Potential Loyalists",
        r"5[4-5]": "Champions",
    }
    rfm["segment"] = rfm["rfm_score"].replace(seg_map, regex=True)
    return rfm


def add_kpi_cards(fig, ax, metrics):
    ax.axis("off")
    y = 0.8
    x_positions = [0.06, 0.30, 0.54, 0.78]

    for (label, value), x in zip(metrics.items(), x_positions):
        ax.text(
            x,
            y,
            f"{label}\n{value}",
            ha="center",
            va="center",
            fontsize=12,
            bbox=dict(boxstyle="round,pad=0.8", facecolor="#EEF6FF", edgecolor="#7AA7D9"),
        )


def render_dashboard(pdf):
    df = load_data()
    invoice_df = summarize_invoice_distribution(df)
    monthly_orders = build_monthly_orders(df)
    monthly_sales = build_monthly_sales(df)
    monthly_users = build_monthly_users(df)
    user_monthly = build_new_vs_existing(df)
    rfm = build_rfm(df)

    # Cover page
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("#F8FAFC")
    fig.text(0.5, 0.82, "Retail Intelligence Dashboard", ha="center", va="center", fontsize=24, weight="bold")
    fig.text(0.5, 0.70, "London Gift Shop Analytics Overview", ha="center", va="center", fontsize=16, color="#475569")
    fig.text(0.5, 0.60, "Customer value, sales trends, and retention signals", ha="center", va="center", fontsize=12, color="#64748B")

    metrics = {
        "Total Revenue": f"£{df['amount'].sum():,.0f}",
        "Orders": f"{df['invoice_no'].nunique():,}",
        "Customers": f"{df['customer_id'].nunique():,}",
        "Avg. Order": f"£{df.groupby('invoice_no')['amount'].sum().mean():,.0f}",
    }
    add_kpi_cards(fig, fig.add_axes([0.05, 0.2, 0.9, 0.18]), metrics)
    pdf.savefig(fig)
    plt.close(fig)

    # Invoice distribution
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    invoice_df["invoice_amount"].plot(kind="hist", bins=60, ax=axes[0], color="#4F46E5", edgecolor="white")
    axes[0].set_title("Invoice Amount Distribution")
    axes[0].set_xlabel("Invoice Amount")
    axes[0].set_ylabel("Frequency")

    invoice_df["invoice_amount"].plot(kind="box", ax=axes[1], color="#14B8A6")
    axes[1].set_title("Invoice Amount Boxplot")
    axes[1].set_ylabel("Invoice Amount")
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # Monthly placed vs canceled orders
    fig, ax = plt.subplots(figsize=(14, 6))
    x = range(len(monthly_orders))
    ax.bar(x, monthly_orders["placed_orders"], label="Placed Orders", color="#2563EB", alpha=0.8)
    ax.bar(x, monthly_orders["canceled_orders"], label="Canceled Orders", color="#EF4444", alpha=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(monthly_orders["yyyymm"], rotation=45)
    ax.set_title("Monthly Placed and Canceled Orders")
    ax.set_xlabel("Year-Month")
    ax.set_ylabel("Order Count")
    ax.legend()
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # Monthly sales and growth
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    monthly_sales.plot(x="yyyymm", y="sales_amount", kind="bar", ax=ax1, color="#10B981")
    ax1.set_title("Monthly Sales")
    ax1.set_xlabel("Year-Month")
    ax1.set_ylabel("Sales Amount")
    ax1.tick_params(axis="x", rotation=45)

    colors = ["#16A34A" if v >= 0 else "#DC2626" for v in monthly_sales["growth_pct"].fillna(0)]
    ax2.bar(monthly_sales["yyyymm"], monthly_sales["growth_pct"].fillna(0), color=colors)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_title("Monthly Sales Growth (%)")
    ax2.set_xlabel("Year-Month")
    ax2.set_ylabel("Growth %")
    ax2.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # Active users and new vs existing
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    monthly_users.plot(x="yyyymm", y="active_users", kind="bar", ax=ax1, color="#F59E0B")
    ax1.set_title("Monthly Active Users")
    ax1.set_xlabel("Year-Month")
    ax1.set_ylabel("Unique Customers")
    ax1.tick_params(axis="x", rotation=45)

    x = np.arange(len(user_monthly))
    width = 0.35
    ax2.bar(x, user_monthly.get("existing", 0), width=width, label="Existing Users", color="#3B82F6")
    ax2.bar(x + width, user_monthly.get("new", 0), width=width, label="New Users", color="#F97316")
    ax2.set_xticks(x + width / 2)
    ax2.set_xticklabels(user_monthly["yyyymm"], rotation=45)
    ax2.set_title("New vs Existing Users")
    ax2.set_xlabel("Year-Month")
    ax2.set_ylabel("Users")
    ax2.legend()
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # RFM segmentation
    seg_counts = rfm["segment"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(12, 6))
    seg_counts.plot(kind="bar", ax=ax, color="#22C55E")
    ax.set_title("Customer Segments (RFM)")
    ax.set_xlabel("Segment")
    ax.set_ylabel("Number of Customers")
    plt.xticks(rotation=45)
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # Summary insight page
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("#F8FAFC")
    fig.text(0.5, 0.9, "Executive Summary", ha="center", va="center", fontsize=22, weight="bold")
    key_insights = [
        f"• Total revenue generated: £{df['amount'].sum():,.0f}",
        f"• Total unique customers: {df['customer_id'].nunique():,}",
        f"• Peak sales month: {monthly_sales.loc[monthly_sales['sales_amount'].idxmax(), 'yyyymm']}",
        f"• Highest-value segment: {rfm['segment'].value_counts().idxmax()}",
        f"• Avg. invoice value: £{df.groupby('invoice_no')['amount'].sum().mean():,.0f}",
    ]
    for i, line in enumerate(key_insights):
        fig.text(0.12, 0.78 - i * 0.10, line, ha="left", va="center", fontsize=13)
    fig.text(0.12, 0.20, "Recommended next steps: strengthen retention for at-risk segments, amplify high-performing months, and monitor cancellation spikes for operational improvement.", fontsize=12, color="#334155")
    pdf.savefig(fig)
    plt.close(fig)


if __name__ == "__main__":
    with PdfPages(OUTPUT_PATH) as pdf:
        render_dashboard(pdf)
    print(f"Dashboard saved to: {OUTPUT_PATH}")
