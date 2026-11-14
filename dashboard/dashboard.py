from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

# ------------------------------------------------------------------ konfigurasi
st.set_page_config(page_title="Dashboard E-Commerce", page_icon="🛒", layout="wide")
sns.set_theme(style="whitegrid")

BASE_DIR = Path(__file__).parent
HIGHLIGHT, MUTED, ALERT, TEAL = "#1f6fb2", "#c9ced6", "#d1495b", "#2a9d8f"
SEGMENT_COLORS = {
    "Loyal (>= 2 pesanan)": HIGHLIGHT,
    "Recent Big Spender": TEAL,
    "At Risk Big Spender": ALERT,
    "Recent Small Spender": MUTED,
    "Lost / Low Value": MUTED,
}


# ------------------------------------------------------------------ data
@st.cache_data
def load_data():
    df = pd.read_csv(BASE_DIR / "main_data.csv", parse_dates=["order_purchase_timestamp"])
    df["order_date"] = df["order_purchase_timestamp"].dt.normalize()
    df["month"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    return df


def safe_qcut(values, labels):
    """qcut kuartil; bila batas bin tidak unik (data kecil/banyak nilai sama) pakai peringkat."""
    try:
        return pd.qcut(values, 4, labels=labels).astype(int)
    except ValueError:
        return pd.qcut(values.rank(method="first"), 4, labels=labels).astype(int)


def segment(row):
    if row["frequency"] >= 2:
        return "Loyal (>= 2 pesanan)"
    if row["R_score"] >= 3:
        return "Recent Big Spender" if row["M_score"] >= 3 else "Recent Small Spender"
    return "At Risk Big Spender" if row["M_score"] >= 3 else "Lost / Low Value"


def build_rfm(df):
    snapshot = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    rfm = (df.groupby("customer_unique_id")
           .agg(last_purchase=("order_purchase_timestamp", "max"),
                frequency=("order_id", "nunique"),
                monetary=("price", "sum")))
    rfm["recency"] = (snapshot - rfm["last_purchase"]).dt.days
    rfm["R_score"] = safe_qcut(rfm["recency"], [4, 3, 2, 1])
    rfm["M_score"] = safe_qcut(rfm["monetary"], [1, 2, 3, 4])
    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm


def show(fig):
    st.pyplot(fig)
    plt.close(fig)


def style_barh(ax):
    ax.set_ylabel("")
    ax.grid(axis="y", visible=False)


df_all = load_data()

# ------------------------------------------------------------------ sidebar
st.sidebar.header("Filter")
min_date, max_date = df_all["order_date"].min().date(), df_all["order_date"].max().date()
date_range = st.sidebar.date_input("Rentang tanggal pembelian", value=(min_date, max_date),
                                   min_value=min_date, max_value=max_date)
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Pilih tanggal akhir pada filter rentang tanggal untuk melanjutkan.")
    st.stop()

all_states = sorted(df_all["customer_state"].dropna().unique())
states = st.sidebar.multiselect("State pelanggan", all_states, default=all_states)
top_n = st.sidebar.slider("Jumlah kategori teratas/terbawah", 5, 15, 10)
min_orders = st.sidebar.slider("Minimum pesanan per state (untuk perbandingan)", 1, 500, 100, step=10)

mask = ((df_all["order_date"] >= pd.Timestamp(date_range[0]))
        & (df_all["order_date"] <= pd.Timestamp(date_range[1]))
        & (df_all["customer_state"].isin(states)))
df = df_all[mask]
if df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih. Ubah rentang tanggal atau state.")
    st.stop()
orders = df.drop_duplicates("order_id")   # satu baris per pesanan

# ------------------------------------------------------------------ header & KPI
st.title("🛒 Dashboard Analisis E-Commerce")
st.caption("Pesanan berstatus delivered, Januari 2017 - Agustus 2018. Nilai uang dalam Real Brasil (R$). "
           "Gunakan filter di sisi kiri untuk mengubah rentang tanggal dan state.")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total revenue", f"R$ {df['price'].sum():,.0f}")
k2.metric("Jumlah pesanan", f"{orders['order_id'].nunique():,}")
review_mean = orders["review_score"].mean()
k3.metric("Rata-rata review score", "-" if pd.isna(review_mean) else f"{review_mean:.2f}")
k4.metric("Pesanan terlambat", f"{orders['is_late'].mean() * 100:.1f}%")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Kategori Produk", "Tren Bulanan", "Pengiriman per State", "Segmentasi RFM", "Peta Keterlambatan"])

# ------------------------------------------------------------------ tab 1: kategori
with tab1:
    st.subheader("Kategori produk dengan revenue tertinggi dan terendah")
    cat = (df.groupby("product_category_name_english")
           .agg(revenue=("price", "sum"), items_sold=("order_id", "count"))
           .sort_values("revenue", ascending=False))
    n = min(top_n, max(len(cat) // 2, 1))
    top = cat.head(n)["revenue"].sort_values()
    bottom = cat.tail(n)["revenue"].sort_values(ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    axes[0].barh(top.index, top.values, color=[MUTED] * (len(top) - 1) + [HIGHLIGHT])
    axes[0].set_title(f"{n} Kategori Revenue Tertinggi", fontsize=13, loc="left", fontweight="bold")
    axes[0].set_xlim(0, top.max() * 1.25)
    for y, v in enumerate(top.values):
        axes[0].text(v + top.max() * 0.01, y, f"R$ {v:,.0f}", va="center", fontsize=8)
    axes[1].barh(bottom.index, bottom.values, color=[MUTED] * (len(bottom) - 1) + [ALERT])
    axes[1].set_title(f"{n} Kategori Revenue Terendah", fontsize=13, loc="left", fontweight="bold")
    axes[1].set_xlim(0, max(bottom.max(), 1) * 1.3)
    for y, v in enumerate(bottom.values):
        axes[1].text(v + max(bottom.max(), 1) * 0.01, y, f"R$ {v:,.0f}", va="center", fontsize=8)
    for ax in axes:
        ax.set_xlabel("Total revenue (R$)")
        ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        style_barh(ax)
    plt.tight_layout()
    show(fig)

    share = cat.head(n)["revenue"].sum() / cat["revenue"].sum() * 100
    st.caption(f"{n} kategori teratas menyumbang {share:.1f}% dari total revenue pada filter ini.")
    with st.expander("Lihat tabel lengkap revenue per kategori"):
        st.dataframe(cat.reset_index())

# ------------------------------------------------------------------ tab 2: tren
with tab2:
    st.subheader("Tren jumlah pesanan dan total revenue per bulan")
    monthly = (df.groupby("month").agg(orders=("order_id", "nunique"), revenue=("price", "sum")).reset_index())
    fig, axes = plt.subplots(2, 1, figsize=(13, 7.5), sharex=True)
    specs = [(axes[0], "orders", "Jumlah pesanan", HIGHLIGHT, mtick.FuncFormatter(lambda x, _: f"{x:,.0f}")),
             (axes[1], "revenue", "Revenue (R$)", TEAL, mtick.FuncFormatter(lambda x, _: f"{x / 1e3:,.0f} rb"))]
    for ax, col, label, color, fmt in specs:
        ax.plot(monthly["month"], monthly[col], marker="o", color=color, linewidth=2)
        peak = monthly.loc[monthly[col].idxmax()]
        ax.scatter(peak["month"], peak[col], s=120, color=ALERT, zorder=5)
        ax.annotate(f"Puncak: {peak['month']:%b %Y}\n{peak[col]:,.0f}", (peak["month"], peak[col]),
                    xytext=(-25, -2), textcoords="offset points", ha="right", va="center", fontsize=9,
                    color=ALERT, arrowprops=dict(arrowstyle="->", color=ALERT))
        ax.set_ylabel(label)
        ax.set_ylim(0, max(monthly[col].max(), 1) * 1.15)
        ax.yaxis.set_major_formatter(fmt)
    axes[0].set_title("Jumlah Pesanan per Bulan", fontsize=12, loc="left", fontweight="bold")
    axes[1].set_title("Total Revenue per Bulan", fontsize=12, loc="left", fontweight="bold")
    axes[1].set_xlabel("Bulan pembelian")
    plt.tight_layout()
    show(fig)
    st.caption("Titik merah menandai bulan puncak pada rentang yang dipilih.")

# ------------------------------------------------------------------ tab 3: state
with tab3:
    st.subheader("Review score dan keterlambatan pengiriman per state")
    state_df = (orders.groupby("customer_state")
                .agg(orders=("order_id", "count"), avg_review=("review_score", "mean"),
                     late_pct=("is_late", "mean")))
    state_df["late_pct"] *= 100
    rank = state_df[state_df["orders"] >= min_orders]
    rank = rank.dropna(subset=["avg_review"])
    if len(rank) < 2:
        st.info("Kurang dari 2 state memenuhi minimum pesanan. Turunkan nilai 'Minimum pesanan per state'.")
    else:
        avg_all, late_all = orders["review_score"].mean(), orders["is_late"].mean() * 100
        fig, axes = plt.subplots(1, 2, figsize=(15, max(5, len(rank) * 0.3)))
        k = min(3, len(rank))
        rv = rank.sort_values("avg_review", ascending=False)
        thr = rv["avg_review"].nsmallest(k).max()
        axes[0].barh(rv.index, rv["avg_review"], color=[ALERT if v <= thr else MUTED for v in rv["avg_review"]])
        axes[0].axvline(avg_all, color="black", linestyle="--", linewidth=1)
        axes[0].set_title(f"Rata-rata Review Score (rata-rata: {avg_all:.2f})", fontsize=12, loc="left", fontweight="bold")
        axes[0].set_xlabel("Review score (1-5)")
        axes[0].set_xlim(min(3.0, rv["avg_review"].min() - 0.1), 5)
        lt = rank.sort_values("late_pct")
        thr2 = lt["late_pct"].nlargest(k).min()
        axes[1].barh(lt.index, lt["late_pct"], color=[ALERT if v >= thr2 else MUTED for v in lt["late_pct"]])
        axes[1].axvline(late_all, color="black", linestyle="--", linewidth=1)
        axes[1].set_title(f"Pesanan Terlambat (rata-rata: {late_all:.1f}%)", fontsize=12, loc="left", fontweight="bold")
        axes[1].set_xlabel("Pesanan terlambat (%)")
        for ax in axes:
            style_barh(ax)
        plt.tight_layout()
        show(fig)
        st.caption(f"Hanya state dengan minimal {min_orders} pesanan yang diperbandingkan. "
                   "Batang merah menandai 3 state terburuk pada tiap metrik.")

    st.subheader("Dampak tingkat keterlambatan terhadap review")
    bins = [-np.inf, 0, 3, 7, np.inf]
    labels = ["Tepat waktu / lebih cepat", "Terlambat 1-3 hari", "Terlambat 4-7 hari", "Terlambat > 7 hari"]
    grp = orders.assign(delay_group=pd.cut(orders["delay_days"], bins=bins, labels=labels))
    delay = (grp.groupby("delay_group", observed=True)
             .agg(pesanan=("order_id", "count"), avg_review=("review_score", "mean")))
    delay = delay.dropna(subset=["avg_review"])
    if not delay.empty:
        fig, ax = plt.subplots(figsize=(9, 4))
        palette = {labels[0]: HIGHLIGHT, labels[3]: ALERT}
        ax.bar(delay.index.astype(str), delay["avg_review"], color=[palette.get(i, MUTED) for i in delay.index])
        for i, v in enumerate(delay["avg_review"]):
            ax.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=10)
        ax.set_ylim(0, 5)
        ax.set_ylabel("Rata-rata review score")
        ax.grid(axis="x", visible=False)
        plt.xticks(rotation=10)
        plt.tight_layout()
        show(fig)

# ------------------------------------------------------------------ tab 4: RFM
with tab4:
    st.subheader("Segmentasi pelanggan (RFM)")
    st.caption("Recency = hari sejak pembelian terakhir, Frequency = jumlah pesanan, Monetary = total belanja. "
               "Skor dihitung ulang pada data hasil filter.")
    if df["customer_unique_id"].nunique() < 4:
        st.info("Jumlah pelanggan pada filter ini terlalu sedikit untuk segmentasi RFM.")
    else:
        rfm = build_rfm(df)
        summary = (rfm.groupby("segment")
                   .agg(pelanggan=("monetary", "size"), total_revenue=("monetary", "sum"),
                        avg_recency_hari=("recency", "mean"))
                   .sort_values("pelanggan", ascending=False))
        fig, axes = plt.subplots(1, 2, figsize=(15, 4.5))
        colors = [SEGMENT_COLORS[s] for s in summary.index]
        axes[0].barh(summary.index, summary["pelanggan"], color=colors)
        axes[0].set_title("Jumlah Pelanggan per Segmen", fontsize=12, loc="left", fontweight="bold")
        axes[0].set_xlim(0, summary["pelanggan"].max() * 1.15)
        for y, v in enumerate(summary["pelanggan"]):
            axes[0].text(v + summary["pelanggan"].max() * 0.01, y, f"{v:,.0f}", va="center", fontsize=9)
        axes[1].barh(summary.index, summary["total_revenue"], color=colors)
        axes[1].set_title("Total Revenue per Segmen (R$)", fontsize=12, loc="left", fontweight="bold")
        axes[1].set_xlim(0, summary["total_revenue"].max() * 1.25)
        for y, v in enumerate(summary["total_revenue"]):
            axes[1].text(v + summary["total_revenue"].max() * 0.01, y, f"R$ {v / 1e6:.2f} jt", va="center", fontsize=9)
        for ax in axes:
            ax.invert_yaxis()
            style_barh(ax)
        plt.tight_layout()
        show(fig)
        repeat = (rfm["frequency"] >= 2).mean() * 100
        st.caption(f"Pelanggan dengan lebih dari satu pesanan: {repeat:.1f}% dari {len(rfm):,} pelanggan unik.")
        with st.expander("Lihat ringkasan segmen"):
            st.dataframe(summary.round(1).reset_index())

# ------------------------------------------------------------------ tab 5: peta
with tab5:
    st.subheader("Persentase pesanan terlambat per state")
    geo_orders = orders.dropna(subset=["lat", "lng"])
    geo_state = (geo_orders.groupby("customer_state")
                 .agg(lat=("lat", "mean"), lng=("lng", "mean"), orders=("order_id", "count"),
                      late_pct=("is_late", lambda s: s.mean() * 100)))
    if geo_state.empty:
        st.info("Tidak ada data koordinat untuk filter ini.")
    else:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.scatter(geo_orders["lng"], geo_orders["lat"], s=2, color="#e3e6ea", alpha=0.5, zorder=1)
        sc = ax.scatter(geo_state["lng"], geo_state["lat"], s=geo_state["orders"] / 25 + 30,
                        c=geo_state["late_pct"], cmap="YlOrRd", edgecolor="black", linewidth=0.6, zorder=3)
        for st_code, r in geo_state.iterrows():
            ax.annotate(st_code, (r["lng"], r["lat"]), fontsize=8, ha="center", va="center", zorder=4)
        plt.colorbar(sc, ax=ax, shrink=0.7).set_label("Pesanan terlambat (%)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(False)
        plt.tight_layout()
        show(fig)
        st.caption("Ukuran titik = jumlah pesanan; warna = persentase pesanan terlambat. "
                   "Titik berada di rata-rata koordinat pelanggan tiap state.")
