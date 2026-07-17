"""Dashboard Streamlit interaktif untuk Brazilian E-Commerce Public Dataset.

Jalankan aplikasi dari folder yang berisi file ini dengan perintah:

    streamlit run app_2.py

Dependensi utama:

    pip install streamlit pandas numpy plotly folium streamlit-folium

Aplikasi otomatis mencari sembilan CSV Olist di folder yang sama, folder
``data/``, atau ``project_sources/``. Nama dengan prefiks seperti
``01-customers_dataset.csv`` juga dikenali. Jika ada file yang tidak ditemukan,
file tersebut dapat diunggah melalui panel sumber data di sidebar.
"""

from __future__ import annotations

import hashlib
import html
import io
import re
from pathlib import Path
from typing import Any

try:
    import folium
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import streamlit as st
    from folium.plugins import Fullscreen, HeatMap, MiniMap
    from streamlit_folium import st_folium
except ImportError as exc:  # Pesan lebih ramah ketika dependensi belum tersedia.
    raise RuntimeError(
        "Dependensi dashboard belum lengkap. Jalankan: "
        "pip install streamlit pandas numpy plotly folium streamlit-folium"
    ) from exc


# -----------------------------------------------------------------------------
# Konfigurasi halaman dan tema visual
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Olist Commerce Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = {
    "navy": "#0B1739",
    "blue": "#2563EB",
    "cyan": "#06B6D4",
    "violet": "#7C3AED",
    "emerald": "#10B981",
    "amber": "#F59E0B",
    "rose": "#F43F5E",
    "muted": "#64748B",
    "grid": "#E8EEF7",
}

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stApp {
            background:
                radial-gradient(circle at 85% -10%, rgba(37,99,235,.10), transparent 28%),
                radial-gradient(circle at 5% 15%, rgba(6,182,212,.07), transparent 24%),
                #F7F9FC;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #07132F 0%, #0B1739 52%, #102553 100%);
            border-right: 1px solid rgba(255,255,255,.08);
        }
        [data-testid="stSidebar"] * { color: #F8FAFC; }
        [data-testid="stSidebar"] .stMultiSelect span,
        [data-testid="stSidebar"] .stDateInput input,
        [data-testid="stSidebar"] .stSelectbox div,
        [data-testid="stSidebar"] .stFileUploader small { color: #0F172A !important; }
        [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.15); }
        .block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1540px; }
        .hero {
            padding: 1.45rem 1.65rem;
            border-radius: 22px;
            background: linear-gradient(120deg, #0B1739 0%, #173A7A 58%, #2563EB 100%);
            color: white;
            box-shadow: 0 18px 50px rgba(11,23,57,.16);
            margin-bottom: 1.1rem;
            position: relative;
            overflow: hidden;
        }
        .hero:after {
            content: '';
            position: absolute;
            width: 240px; height: 240px; right: -70px; top: -110px;
            border: 40px solid rgba(255,255,255,.07); border-radius: 50%;
        }
        .hero-kicker { font-size: .74rem; font-weight: 700; letter-spacing: .16em; opacity: .72; }
        .hero-title { font-size: clamp(1.65rem, 3vw, 2.45rem); font-weight: 800; line-height: 1.12; margin: .35rem 0; }
        .hero-subtitle { font-size: .94rem; color: #DCE8FF; max-width: 880px; }
        .metric-card {
            background: rgba(255,255,255,.94);
            border: 1px solid #E7ECF4;
            border-radius: 17px;
            padding: 1.05rem 1.1rem;
            min-height: 126px;
            box-shadow: 0 7px 25px rgba(15,23,42,.055);
            position: relative;
            overflow: hidden;
        }
        .metric-card:before {
            content: ''; position: absolute; left: 0; top: 0; bottom: 0;
            width: 4px; background: var(--accent);
        }
        .metric-title { color: #64748B; font-size: .74rem; font-weight: 700; letter-spacing: .055em; text-transform: uppercase; }
        .metric-value { color: #0F172A; font-size: 1.72rem; font-weight: 800; margin: .38rem 0 .2rem; white-space: nowrap; }
        .metric-note { color: #64748B; font-size: .75rem; }
        .section-title { color: #0B1739; font-size: 1.12rem; font-weight: 800; margin: .3rem 0 .1rem; }
        .section-note { color: #64748B; font-size: .82rem; margin-bottom: .7rem; }
        .insight-box {
            background: linear-gradient(100deg, rgba(37,99,235,.08), rgba(6,182,212,.06));
            border: 1px solid rgba(37,99,235,.14);
            border-left: 4px solid #2563EB;
            border-radius: 14px;
            padding: .9rem 1.05rem;
            color: #334155;
            font-size: .86rem;
            margin: .45rem 0 .9rem;
        }
        .chart-shell {
            background: #FFFFFF; border: 1px solid #D7E0EE; border-radius: 18px;
            padding: .35rem .6rem; box-shadow: 0 7px 25px rgba(15,23,42,.045);
        }
        div[data-testid="stTabs"] button { font-weight: 700; }
        div[data-testid="stDataFrame"] { border: 1px solid #E7ECF4; border-radius: 14px; overflow: hidden; }
        .stDownloadButton button {
            border-radius: 10px; border: 1px solid #2563EB; color: #2563EB;
            font-weight: 700; background: white;
        }
        footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Penemuan dan pembacaan sumber data
# -----------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent

REQUIRED_FILES = {
    "customers": "customers_dataset.csv",
    "sellers": "sellers_dataset.csv",
    "payments": "order_payments_dataset.csv",
    "translation": "product_category_name_translation.csv",
    "products": "products_dataset.csv",
    "geolocation": "geolocation_dataset.csv",
    "reviews": "order_reviews_dataset.csv",
    "items": "order_items_dataset.csv",
    "orders": "orders_dataset.csv",
}


def normalize_filename(name: str) -> str:
    """Menghapus prefiks angka agar file ``01-...`` tetap dikenali."""
    return re.sub(r"^\d+[-_]", "", Path(name).name.lower())


def discover_local_sources() -> dict[str, Path]:
    """Mencari setiap CSV pada beberapa lokasi yang lazim digunakan."""
    candidate_dirs = [
        APP_DIR,
        APP_DIR / "data",
        APP_DIR / "project_sources",
        Path.cwd(),
        Path.cwd() / "data",
        Path.cwd() / "project_sources",
    ]
    found: dict[str, Path] = {}
    seen_dirs: set[Path] = set()
    for directory in candidate_dirs:
        resolved = directory.resolve()
        if resolved in seen_dirs or not directory.exists():
            continue
        seen_dirs.add(resolved)
        available = {
            normalize_filename(path.name): path
            for path in directory.glob("*.csv")
            if path.is_file()
        }
        for key, canonical_name in REQUIRED_FILES.items():
            if key not in found and canonical_name in available:
                found[key] = available[canonical_name]
    return found


@st.cache_data(show_spinner=False)
def read_csv_path(path: str, modified_ns: int) -> pd.DataFrame:
    """Membaca CSV lokal; waktu modifikasi menjadi bagian kunci cache."""
    del modified_ns
    return pd.read_csv(path, low_memory=False)


@st.cache_data(show_spinner=False)
def read_csv_bytes(file_name: str, payload: bytes) -> pd.DataFrame:
    """Membaca CSV unggahan tanpa menyimpan berkas sementara."""
    del file_name
    return pd.read_csv(io.BytesIO(payload), low_memory=False)


def load_sources(
    local_sources: dict[str, Path], uploaded_files: list[Any]
) -> tuple[dict[str, pd.DataFrame], tuple[str, ...], list[str]]:
    """Menggabungkan sumber lokal dan unggahan menjadi kumpulan DataFrame."""
    uploaded_lookup = {
        normalize_filename(upload.name): upload for upload in (uploaded_files or [])
    }
    datasets: dict[str, pd.DataFrame] = {}
    fingerprints: list[str] = []
    missing: list[str] = []

    for key, canonical_name in REQUIRED_FILES.items():
        if key in local_sources:
            path = local_sources[key]
            stat = path.stat()
            datasets[key] = read_csv_path(str(path), stat.st_mtime_ns)
            fingerprints.append(f"{key}:{path}:{stat.st_size}:{stat.st_mtime_ns}")
        elif canonical_name in uploaded_lookup:
            upload = uploaded_lookup[canonical_name]
            payload = upload.getvalue()
            digest = hashlib.sha256(payload).hexdigest()
            datasets[key] = read_csv_bytes(upload.name, payload)
            fingerprints.append(f"{key}:{upload.name}:{digest}")
        else:
            missing.append(canonical_name)
    return datasets, tuple(fingerprints), missing


def validate_columns(datasets: dict[str, pd.DataFrame]) -> list[str]:
    """Memastikan kolom kunci tersedia sebelum proses penggabungan data."""
    required_columns = {
        "customers": {"customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"},
        "sellers": {"seller_id", "seller_state"},
        "payments": {"order_id", "payment_type", "payment_value"},
        "translation": {"product_category_name", "product_category_name_english"},
        "products": {"product_id", "product_category_name"},
        "geolocation": {"geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"},
        "reviews": {"order_id", "review_score"},
        "items": {"order_id", "product_id", "seller_id", "price", "freight_value"},
        "orders": {"order_id", "customer_id", "order_status", "order_purchase_timestamp"},
    }
    errors: list[str] = []
    for key, expected in required_columns.items():
        missing = expected.difference(datasets[key].columns)
        if missing:
            errors.append(f"{REQUIRED_FILES[key]}: {', '.join(sorted(missing))}")
    return errors


# -----------------------------------------------------------------------------
# Pembuatan data mart
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner="Menyiapkan data mart dan koordinat peta …")
def build_data_model(
    fingerprint: tuple[str, ...], _datasets: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    """Membangun tabel analitik level item, order, pembayaran, dan kualitas data."""
    del fingerprint
    data = {name: frame.copy() for name, frame in _datasets.items()}

    # Satu kode pos memiliki banyak titik; median mengurangi pengaruh outlier.
    geo = data["geolocation"].dropna(
        subset=["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"]
    )
    geo_zip = (
        geo.groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(customer_lat=("geolocation_lat", "median"), customer_lng=("geolocation_lng", "median"))
    )

    customers = data["customers"].merge(
        geo_zip,
        left_on="customer_zip_code_prefix",
        right_on="geolocation_zip_code_prefix",
        how="left",
    )
    customers = customers.drop(columns=["geolocation_zip_code_prefix"], errors="ignore")

    orders = data["orders"].copy()
    date_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for column in date_columns:
        if column in orders.columns:
            orders[column] = pd.to_datetime(orders[column], errors="coerce")

    orders = orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
    orders["purchase_date"] = orders["order_purchase_timestamp"].dt.normalize()
    orders["delivery_days"] = (
        orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
    ).dt.total_seconds() / 86_400
    orders["delivery_delay_days"] = (
        orders["order_delivered_customer_date"] - orders["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86_400
    orders["is_on_time"] = np.where(
        orders["order_delivered_customer_date"].notna(),
        orders["order_delivered_customer_date"] <= orders["order_estimated_delivery_date"],
        np.nan,
    )

    review_order = (
        data["reviews"].groupby("order_id", as_index=False)
        .agg(review_score=("review_score", "mean"), review_count=("review_score", "size"))
    )
    orders = orders.merge(review_order, on="order_id", how="left", validate="one_to_one")

    lifetime = (
        orders.groupby("customer_unique_id")["order_id"]
        .nunique()
        .rename("customer_lifetime_orders")
    )
    orders = orders.merge(lifetime, on="customer_unique_id", how="left")
    orders["customer_segment"] = np.where(
        orders["customer_lifetime_orders"].gt(1), "Repeat customer", "One-time customer"
    )

    products = data["products"].merge(
        data["translation"], on="product_category_name", how="left", validate="many_to_one"
    )
    products["category"] = products["product_category_name_english"].fillna(
        products["product_category_name"]
    )
    products["category"] = (
        products["category"].fillna("unknown").str.replace("_", " ", regex=False).str.title()
    )

    seller_columns = [column for column in ["seller_id", "seller_city", "seller_state"] if column in data["sellers"].columns]
    item_columns = ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"]
    item_columns = [column for column in item_columns if column in data["items"].columns]
    product_columns = ["product_id", "category"]
    fact = (
        data["items"][item_columns]
        .merge(products[product_columns], on="product_id", how="left", validate="many_to_one")
        .merge(data["sellers"][seller_columns], on="seller_id", how="left", validate="many_to_one")
        .merge(orders, on="order_id", how="left", validate="many_to_one")
    )
    fact["category"] = fact["category"].fillna("Unknown")
    fact["seller_state"] = fact["seller_state"].fillna("Unknown")
    fact["price"] = pd.to_numeric(fact["price"], errors="coerce").fillna(0)
    fact["freight_value"] = pd.to_numeric(fact["freight_value"], errors="coerce").fillna(0)
    fact["gmv"] = fact["price"] + fact["freight_value"]

    payments = data["payments"].copy()
    payments["payment_value"] = pd.to_numeric(payments["payment_value"], errors="coerce").fillna(0)
    payments["payment_label"] = (
        payments["payment_type"].fillna("unknown").str.replace("_", " ", regex=False).str.title()
    )

    quality_rows = []
    for name, frame in data.items():
        quality_rows.append(
            {
                "Dataset": REQUIRED_FILES[name],
                "Baris": len(frame),
                "Kolom": len(frame.columns),
                "Sel kosong": int(frame.isna().sum().sum()),
                "Baris duplikat": int(frame.duplicated().sum()),
            }
        )
    quality = pd.DataFrame(quality_rows)

    return {
        "fact": fact,
        "orders": orders,
        "payments": payments,
        "quality": quality,
    }


# -----------------------------------------------------------------------------
# Fungsi presentasi dan visualisasi
# -----------------------------------------------------------------------------
def format_currency(value: float) -> str:
    """Format ringkas Real Brasil dengan istilah Indonesia."""
    if abs(value) >= 1_000_000:
        return f"R$ {value / 1_000_000:,.2f} jt".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(value) >= 1_000:
        return f"R$ {value / 1_000:,.1f} rb".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_integer(value: float | int) -> str:
    return f"{int(value):,}".replace(",", ".")


def percent_delta(current: float, previous: float) -> str:
    if not np.isfinite(previous) or previous == 0:
        return "Periode pembanding tidak tersedia"
    delta = (current - previous) / abs(previous) * 100
    arrow = "▲" if delta >= 0 else "▼"
    return f"{arrow} {abs(delta):.1f}% vs periode sebelumnya"


def metric_card(title: str, value: str, note: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="--accent:{accent}">
            <div class="metric-title">{html.escape(title)}</div>
            <div class="metric-value">{html.escape(value)}</div>
            <div class="metric-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(title: str, note: str = "") -> None:
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="section-note">{html.escape(note)}</div>', unsafe_allow_html=True)


def style_figure(fig: go.Figure, height: int = 380) -> go.Figure:
    """Menerapkan gaya visual kontras tinggi agar grafik terbaca pada background dashboard."""
    fig.update_layout(
        height=height,
        margin=dict(l=25, r=25, t=55, b=30),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Inter, sans-serif",
            color="#1E293B",
            size=12
        ),
        title_font=dict(size=16, color="#0B1739"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#334155")
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_color="#0F172A"
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        linecolor="#CBD5E1",
        tickfont=dict(color="#475569"),
        title_font=dict(color="#334155")
    )

    fig.update_yaxes(
        gridcolor="#E2E8F0",
        zeroline=False,
        tickfont=dict(color="#475569"),
        title_font=dict(color="#334155")
    )

    return fig



def apply_filters(
    fact: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    customer_states: list[str],
    categories: list[str],
    statuses: list[str],
    seller_states: list[str],
) -> pd.DataFrame:
    """Menerapkan seluruh filter pada tabel fakta level item."""
    mask = fact["order_purchase_timestamp"].ge(start_date) & fact["order_purchase_timestamp"].lt(
        end_date + pd.Timedelta(days=1)
    )
    if customer_states:
        mask &= fact["customer_state"].isin(customer_states)
    if categories:
        mask &= fact["category"].isin(categories)
    if statuses:
        mask &= fact["order_status"].isin(statuses)
    if seller_states:
        mask &= fact["seller_state"].isin(seller_states)
    return fact.loc[mask].copy()


def make_customer_map(points: pd.DataFrame, mode: str) -> folium.Map:
    """Membuat peta bubble atau heatmap yang dapat di-zoom dan digeser."""
    center = [points["customer_lat"].median(), points["customer_lng"].median()]
    customer_map = folium.Map(
        location=center,
        zoom_start=4,
        tiles="CartoDB positron",
        control_scale=True,
        prefer_canvas=True,
    )
    Fullscreen(position="topright").add_to(customer_map)
    MiniMap(toggle_display=True, tile_layer="CartoDB positron").add_to(customer_map)

    if mode == "Heatmap":
        heat_data = points[["customer_lat", "customer_lng", "customers"]].values.tolist()
        HeatMap(
            heat_data,
            radius=18,
            blur=14,
            min_opacity=0.28,
            gradient={0.2: "#67E8F9", 0.5: "#2563EB", 0.8: "#7C3AED", 1: "#F43F5E"},
        ).add_to(customer_map)
    else:
        maximum = max(float(points["customers"].max()), 1.0)
        for row in points.itertuples(index=False):
            radius = 4 + 18 * np.sqrt(float(row.customers) / maximum)
            tooltip = (
                f"<b>{html.escape(str(row.customer_city).title())}, {html.escape(str(row.customer_state))}</b><br>"
                f"Customer: {format_integer(row.customers)}<br>"
                f"Pesanan: {format_integer(row.orders)}<br>"
                f"GMV: {format_currency(row.gmv)}"
            )
            folium.CircleMarker(
                location=[row.customer_lat, row.customer_lng],
                radius=radius,
                tooltip=folium.Tooltip(tooltip, sticky=True),
                color="#FFFFFF",
                weight=1.2,
                fill=True,
                fill_color=COLORS["blue"],
                fill_opacity=0.68,
            ).add_to(customer_map)

    bounds = points[["customer_lat", "customer_lng"]].agg(["min", "max"])
    customer_map.fit_bounds(
        [
            [bounds.loc["min", "customer_lat"], bounds.loc["min", "customer_lng"]],
            [bounds.loc["max", "customer_lat"], bounds.loc["max", "customer_lng"]],
        ],
        padding=(20, 20),
    )
    return customer_map


def create_order_export(filtered: pd.DataFrame) -> bytes:
    """Meringkas hasil filter menjadi satu baris per pesanan untuk diunduh."""
    if filtered.empty:
        return b""
    dimensions = [
        "order_id",
        "order_purchase_timestamp",
        "order_status",
        "customer_unique_id",
        "customer_city",
        "customer_state",
        "review_score",
        "delivery_days",
        "is_on_time",
    ]
    dimensions = [column for column in dimensions if column in filtered.columns]
    export = (
        filtered.groupby(dimensions, dropna=False, as_index=False)
        .agg(
            item_count=("order_item_id", "count"),
            product_revenue=("price", "sum"),
            freight_value=("freight_value", "sum"),
            gmv=("gmv", "sum"),
            categories=("category", lambda values: " | ".join(sorted(set(values)))),
        )
        .sort_values("order_purchase_timestamp", ascending=False)
    )
    return export.to_csv(index=False).encode("utf-8-sig")


# -----------------------------------------------------------------------------
# Aplikasi utama
# -----------------------------------------------------------------------------
def main() -> None:
    local_sources = discover_local_sources()

    with st.sidebar:
        st.markdown("## OLIST / BI")
        st.caption("E-commerce performance cockpit")
        with st.expander("Sumber data", expanded=len(local_sources) < len(REQUIRED_FILES)):
            st.caption(
                f"{len(local_sources)}/{len(REQUIRED_FILES)} dataset ditemukan otomatis. "
                "Unggah hanya file yang masih belum ditemukan."
            )
            uploaded_files = st.file_uploader(
                "Tambahkan CSV",
                type=["csv"],
                accept_multiple_files=True,
                label_visibility="collapsed",
            )

    datasets, fingerprint, missing = load_sources(local_sources, uploaded_files or [])
    if missing:
        st.error("Dashboard belum dapat dimuat karena sumber data belum lengkap.")
        st.write("File yang belum ditemukan:")
        for name in missing:
            st.write(f"- `{name}`")
        st.info(
            "Letakkan file di folder yang sama dengan app_2.py, folder data/, "
            "folder project_sources/, atau unggah melalui sidebar."
        )
        st.stop()

    column_errors = validate_columns(datasets)
    if column_errors:
        st.error("Terdapat kolom wajib yang tidak ditemukan:")
        for error in column_errors:
            st.write(f"- {error}")
        st.stop()

    model = build_data_model(fingerprint, datasets)
    fact = model["fact"]
    payments = model["payments"]

    valid_dates = fact["order_purchase_timestamp"].dropna()
    data_min = valid_dates.min().date()
    data_max = valid_dates.max().date()

    # Filter berada di sidebar agar ruang utama tetap fokus pada insight.
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Filter analisis")
        selected_dates = st.date_input(
            "Periode transaksi",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max,
        )
        if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
        else:
            start_date = end_date = selected_dates

        state_options = sorted(fact["customer_state"].dropna().astype(str).unique())
        category_options = sorted(fact["category"].dropna().astype(str).unique())
        status_options = sorted(fact["order_status"].dropna().astype(str).unique())
        seller_state_options = sorted(fact["seller_state"].dropna().astype(str).unique())

        customer_states = st.multiselect(
            "State customer", state_options, placeholder="Semua state"
        )
        categories = st.multiselect(
            "Kategori produk", category_options, placeholder="Semua kategori"
        )
        default_status = ["delivered"] if "delivered" in status_options else []
        statuses = st.multiselect(
            "Status pesanan", status_options, default=default_status, placeholder="Semua status"
        )
        seller_states = st.multiselect(
            "State seller", seller_state_options, placeholder="Semua state seller"
        )

        st.markdown("---")
        st.caption(
            f"Rentang data: {data_min.strftime('%d %b %Y')} — "
            f"{data_max.strftime('%d %b %Y')}"
        )

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    filtered = apply_filters(
        fact, start_ts, end_ts, customer_states, categories, statuses, seller_states
    )

    if filtered.empty:
        st.warning("Tidak ada data yang cocok dengan kombinasi filter saat ini.")
        st.stop()

    order_view = filtered.drop_duplicates("order_id").copy()
    span_days = max((end_ts - start_ts).days + 1, 1)
    previous_end = start_ts - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=span_days - 1)
    previous = apply_filters(
        fact,
        previous_start,
        previous_end,
        customer_states,
        categories,
        statuses,
        seller_states,
    )
    previous_orders = previous["order_id"].nunique()

    current_revenue = float(filtered["gmv"].sum())
    current_orders = int(filtered["order_id"].nunique())
    current_customers = int(filtered["customer_unique_id"].nunique())
    current_aov = current_revenue / current_orders if current_orders else 0
    current_rating = float(order_view["review_score"].mean())
    previous_revenue = float(previous["gmv"].sum())
    previous_customers = int(previous["customer_unique_id"].nunique()) if not previous.empty else 0
    previous_aov = previous_revenue / previous_orders if previous_orders else np.nan

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-kicker">COMMERCE INTELLIGENCE • BRAZIL</div>
            <div class="hero-title">Olist Executive Dashboard</div>
            <div class="hero-subtitle">
                Pantau pertumbuhan, konsentrasi customer, performa produk, dan kualitas layanan
                dalam satu dashboard interaktif. Tampilan aktif mencakup
                <b>{html.escape(pd.Timestamp(start_date).strftime('%d %b %Y'))}</b> hingga
                <b>{html.escape(pd.Timestamp(end_date).strftime('%d %b %Y'))}</b>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_columns = st.columns(5, gap="small")
    with metric_columns[0]:
        metric_card(
            "GMV",
            format_currency(current_revenue),
            percent_delta(current_revenue, previous_revenue),
            COLORS["blue"],
        )
    with metric_columns[1]:
        metric_card(
            "Pesanan",
            format_integer(current_orders),
            percent_delta(current_orders, previous_orders),
            COLORS["cyan"],
        )
    with metric_columns[2]:
        metric_card(
            "Customer unik",
            format_integer(current_customers),
            percent_delta(current_customers, previous_customers),
            COLORS["violet"],
        )
    with metric_columns[3]:
        metric_card(
            "Average order value",
            format_currency(current_aov),
            percent_delta(current_aov, previous_aov),
            COLORS["emerald"],
        )
    with metric_columns[4]:
        rating_text = f"{current_rating:.2f} / 5" if np.isfinite(current_rating) else "N/A"
        reviewed_share = order_view["review_score"].notna().mean() * 100
        metric_card(
            "Rating rata-rata",
            rating_text,
            f"Cakupan ulasan {reviewed_share:.1f}% pesanan",
            COLORS["amber"],
        )

    tabs = st.tabs(["Ringkasan", "Customer & Peta", "Produk & Seller", "Layanan & Pembayaran"])

    # ------------------------------------------------------------------ Ringkasan
    with tabs[0]:
        top_category = filtered.groupby("category")["gmv"].sum().idxmax()
        top_state = filtered.groupby("customer_state")["gmv"].sum().idxmax()
        delivered = order_view.dropna(subset=["is_on_time"])
        on_time_rate = delivered["is_on_time"].mean() * 100 if not delivered.empty else np.nan
        insight = (
            f"Kategori dengan GMV tertinggi adalah {top_category}, sedangkan customer dari {top_state} "
            f"memberikan kontribusi wilayah terbesar. "
            + (f"Sebanyak {on_time_rate:.1f}% pesanan terkirim tepat waktu." if np.isfinite(on_time_rate) else "Data ketepatan waktu belum tersedia pada filter ini.")
        )
        st.markdown(f'<div class="insight-box"><b>Insight otomatis:</b> {html.escape(insight)}</div>', unsafe_allow_html=True)

        left, right = st.columns([1.65, 1], gap="large")
        with left:
            section_heading("Tren GMV dan pesanan", "Granularitas menyesuaikan panjang periode yang dipilih.")
            if span_days > 180:
                period = filtered["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
                period_label = "Bulan"
            elif span_days > 60:
                period = filtered["order_purchase_timestamp"].dt.to_period("W").dt.start_time
                period_label = "Minggu"
            else:
                period = filtered["order_purchase_timestamp"].dt.normalize()
                period_label = "Tanggal"
            trend = (
                filtered.assign(period=period)
                .groupby("period", as_index=False)
                .agg(GMV=("gmv", "sum"), Pesanan=("order_id", "nunique"))
            )
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend["period"], y=trend["GMV"], name="GMV", mode="lines", line=dict(color=COLORS["blue"], width=3), fill="tozeroy", fillcolor="rgba(37,99,235,0.16)", hovertemplate="%{x|%d %b %Y}<br>GMV R$ %{y:,.2f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=trend["period"], y=trend["Pesanan"], name="Pesanan", mode="lines+markers", yaxis="y2", line=dict(color=COLORS["cyan"], width=2), marker=dict(size=5), hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} pesanan<extra></extra>"))
            fig.update_layout(yaxis=dict(title="GMV (R$)"), yaxis2=dict(title="Pesanan", overlaying="y", side="right", showgrid=False), xaxis_title=period_label)
            st.plotly_chart(style_figure(fig, 390), use_container_width=True, config={"displayModeBar": False})

        with right:
            section_heading("Komposisi status", "Jumlah pesanan unik menurut status terakhir.")
            status_summary = order_view["order_status"].value_counts().rename_axis("Status").reset_index(name="Pesanan")
            fig = px.pie(status_summary, names="Status", values="Pesanan", hole=.67, color_discrete_sequence=[COLORS["blue"], COLORS["cyan"], COLORS["violet"], COLORS["amber"], COLORS["rose"], COLORS["emerald"]])
            fig.update_traces(textposition="outside", textinfo="percent+label", marker=dict(line=dict(color="white", width=3)), hovertemplate="%{label}<br>%{value:,.0f} pesanan<br>%{percent}<extra></extra>")
            fig.add_annotation(text=f"<b>{format_integer(current_orders)}</b><br><span style='font-size:11px'>pesanan</span>", x=.5, y=.5, showarrow=False, font=dict(color=COLORS["navy"], size=18))
            st.plotly_chart(style_figure(fig, 390), use_container_width=True, config={"displayModeBar": False})

        left, right = st.columns(2, gap="large")
        with left:
            section_heading("Kategori penyumbang GMV", "Sepuluh kategori dengan nilai produk dan freight tertinggi.")
            category_revenue = filtered.groupby("category", as_index=False)["gmv"].sum().nlargest(10, "gmv").sort_values("gmv")
            fig = px.bar(category_revenue, x="gmv", y="category", orientation="h", color="gmv", color_continuous_scale=["#93C5FD", "#1D4ED8"], labels={"gmv": "GMV (R$)", "category": ""})
            fig.update_layout(coloraxis_showscale=False)
            fig.update_traces(hovertemplate="%{y}<br>GMV R$ %{x:,.2f}<extra></extra>")
            st.plotly_chart(style_figure(fig, 400), use_container_width=True, config={"displayModeBar": False})
        with right:
            section_heading("Kontribusi state customer", "Sepuluh state dengan GMV tertinggi.")
            state_revenue = filtered.groupby("customer_state", as_index=False).agg(GMV=("gmv", "sum"), Pesanan=("order_id", "nunique")).nlargest(10, "GMV")
            fig = px.bar(state_revenue, x="customer_state", y="GMV", color="Pesanan", color_continuous_scale=["#67E8F9", "#0891B2"], labels={"customer_state": "State", "GMV": "GMV (R$)"})
            fig.update_layout(coloraxis_colorbar=dict(title="Pesanan"))
            fig.update_traces(hovertemplate="State %{x}<br>GMV R$ %{y:,.2f}<br>Pesanan %{marker.color:,.0f}<extra></extra>")
            st.plotly_chart(style_figure(fig, 400), use_container_width=True, config={"displayModeBar": False})

    # ----------------------------------------------------------- Customer dan Peta
    with tabs[1]:
        map_orders = order_view.dropna(subset=["customer_lat", "customer_lng"]).copy()
        map_points = (
            map_orders.groupby(["customer_state", "customer_city", "customer_lat", "customer_lng"], as_index=False)
            .agg(customers=("customer_unique_id", "nunique"), orders=("order_id", "nunique"))
        )
        order_gmv = filtered.groupby("order_id", as_index=False)["gmv"].sum()
        map_gmv = map_orders[["order_id", "customer_state", "customer_city", "customer_lat", "customer_lng"]].merge(order_gmv, on="order_id", how="left")
        map_gmv = map_gmv.groupby(["customer_state", "customer_city", "customer_lat", "customer_lng"], as_index=False)["gmv"].sum()
        map_points = map_points.merge(map_gmv, on=["customer_state", "customer_city", "customer_lat", "customer_lng"], how="left")

        control_1, control_2, spacer = st.columns([1, 1.2, 3.4])
        with control_1:
            map_mode = st.selectbox("Mode peta", ["Bubble", "Heatmap"], key="map_mode")
        with control_2:
            max_points = st.slider(
                "Jumlah lokasi",
                50,
                min(800, len(map_points)),
                min(300, len(map_points)),
                1,
                key="map_points",
            ) if len(map_points) >= 50 else len(map_points)

        section_heading("Sebaran customer interaktif", "Peta Folium dapat digeser, diperbesar, diperkecil, dan ditampilkan layar penuh.")
        if map_points.empty:
            st.info("Koordinat customer tidak tersedia untuk kombinasi filter ini.")
        else:
            plotted = map_points.nlargest(int(max_points), "customers")
            customer_map = make_customer_map(plotted, map_mode)
            st_folium(customer_map, height=545, use_container_width=True, returned_objects=[])
            map_coverage = map_orders["customer_unique_id"].nunique() / max(current_customers, 1) * 100
            st.caption(f"Cakupan koordinat: {map_coverage:.1f}% customer pada hasil filter • Menampilkan {format_integer(len(plotted))} lokasi teratas.")

        left, right = st.columns([1.25, 1], gap="large")
        with left:
            section_heading("Profil wilayah", "GMV, pesanan, dan customer unik pada setiap state.")
            state_profile = (
                filtered.groupby("customer_state", as_index=False)
                .agg(GMV=("gmv", "sum"), Pesanan=("order_id", "nunique"), Customer=("customer_unique_id", "nunique"))
                .sort_values("GMV", ascending=False)
            )
            state_profile["AOV"] = state_profile["GMV"] / state_profile["Pesanan"]
            display_state = state_profile.copy()
            display_state["GMV"] = display_state["GMV"].map(format_currency)
            display_state["AOV"] = display_state["AOV"].map(format_currency)
            st.dataframe(display_state, use_container_width=True, hide_index=True, height=380)
        with right:
            section_heading("Retensi customer", "Segmentasi berdasarkan seluruh riwayat customer, bukan hanya periode filter.")
            customer_segments = (
                order_view.drop_duplicates("customer_unique_id")["customer_segment"]
                .value_counts()
                .rename_axis("Segmen")
                .reset_index(name="Customer")
            )
            fig = px.pie(customer_segments, names="Segmen", values="Customer", hole=.62, color="Segmen", color_discrete_map={"One-time customer": COLORS["blue"], "Repeat customer": COLORS["emerald"]})
            fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="white", width=3)), hovertemplate="%{label}<br>%{value:,.0f} customer<br>%{percent}<extra></extra>")
            st.plotly_chart(style_figure(fig, 370), use_container_width=True, config={"displayModeBar": False})

    # -------------------------------------------------------------- Produk/Seller
    with tabs[2]:
        category_profile = (
            filtered.groupby("category", as_index=False)
            .agg(GMV=("gmv", "sum"), Unit=("order_item_id", "count"), Pesanan=("order_id", "nunique"), Customer=("customer_unique_id", "nunique"), Rating=("review_score", "mean"))
        )
        category_profile["GMV per Unit"] = category_profile["GMV"] / category_profile["Unit"]

        left, right = st.columns([1.35, 1], gap="large")
        with left:
            section_heading("Matriks portofolio kategori", "Ukuran bubble menunjukkan jumlah pesanan; warna menunjukkan rating.")
            fig = px.scatter(category_profile, x="Unit", y="GMV", size="Pesanan", color="Rating", hover_name="category", color_continuous_scale=[COLORS["rose"], COLORS["amber"], COLORS["emerald"]], size_max=52, labels={"Unit": "Unit terjual", "GMV": "GMV (R$)"})
            fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Unit %{x:,.0f}<br>GMV R$ %{y:,.2f}<br>Rating %{marker.color:.2f}<extra></extra>")
            st.plotly_chart(style_figure(fig, 450), use_container_width=True, config={"displayModeBar": False})
        with right:
            section_heading("Kategori bernilai tinggi", "Peringkat berdasarkan GMV rata-rata per unit.")
            high_value = category_profile[category_profile["Unit"].ge(10)].nlargest(12, "GMV per Unit").sort_values("GMV per Unit")
            fig = px.bar(high_value, x="GMV per Unit", y="category", orientation="h", color="Rating", color_continuous_scale=["#FDE68A", COLORS["emerald"]], labels={"category": "", "GMV per Unit": "GMV per unit (R$)"})
            fig.update_traces(hovertemplate="%{y}<br>GMV/unit R$ %{x:,.2f}<extra></extra>")
            st.plotly_chart(style_figure(fig, 450), use_container_width=True, config={"displayModeBar": False})

        left, right = st.columns(2, gap="large")
        with left:
            section_heading("Produk terlaris", "Produk diperingkat berdasarkan total GMV pada hasil filter.")
            product_profile = (
                filtered.groupby(["product_id", "category"], as_index=False)
                .agg(GMV=("gmv", "sum"), Unit=("order_item_id", "count"), Rating=("review_score", "mean"))
                .nlargest(12, "GMV")
                .sort_values("GMV")
            )
            product_profile["Produk"] = product_profile["product_id"].str[:8] + "…"
            fig = px.bar(product_profile, x="GMV", y="Produk", orientation="h", color="category", labels={"GMV": "GMV (R$)"})
            fig.update_layout(showlegend=False)
            fig.update_traces(customdata=product_profile[["category", "Unit", "Rating"]], hovertemplate="Produk %{y}<br>%{customdata[0]}<br>GMV R$ %{x:,.2f}<br>Unit %{customdata[1]:,.0f}<br>Rating %{customdata[2]:.2f}<extra></extra>")
            st.plotly_chart(style_figure(fig, 440), use_container_width=True, config={"displayModeBar": False})
        with right:
            section_heading("Kekuatan seller per state", "Perbandingan seller aktif, GMV, dan jumlah pesanan.")
            seller_profile = (
                filtered.groupby("seller_state", as_index=False)
                .agg(GMV=("gmv", "sum"), Seller=("seller_id", "nunique"), Pesanan=("order_id", "nunique"))
                .nlargest(12, "GMV")
            )
            fig = px.bar(seller_profile, x="seller_state", y="GMV", color="Seller", color_continuous_scale=["#C4B5FD", "#6D28D9"], labels={"seller_state": "State seller", "GMV": "GMV (R$)"})
            fig.update_traces(customdata=seller_profile[["Seller", "Pesanan"]], hovertemplate="State %{x}<br>GMV R$ %{y:,.2f}<br>Seller %{customdata[0]:,.0f}<br>Pesanan %{customdata[1]:,.0f}<extra></extra>")
            st.plotly_chart(style_figure(fig, 440), use_container_width=True, config={"displayModeBar": False})

    # ---------------------------------------------------- Layanan dan pembayaran
    with tabs[3]:
        reviewed = order_view.dropna(subset=["review_score"]).copy()
        delivered_orders = order_view.dropna(subset=["delivery_days"]).copy()
        valid_delivery = delivered_orders[delivered_orders["delivery_days"].between(0, 90)]

        left, middle, right = st.columns(3, gap="small")
        average_delivery = delivered_orders["delivery_days"].mean()
        late_rate = (delivered_orders["delivery_delay_days"] > 0).mean() * 100 if not delivered_orders.empty else np.nan
        negative_review = (reviewed["review_score"] <= 2).mean() * 100 if not reviewed.empty else np.nan
        with left:
            metric_card("Waktu kirim rata-rata", f"{average_delivery:.1f} hari" if np.isfinite(average_delivery) else "N/A", "Dari pembelian hingga diterima", COLORS["cyan"])
        with middle:
            metric_card("Keterlambatan", f"{late_rate:.1f}%" if np.isfinite(late_rate) else "N/A", "Diterima setelah estimasi", COLORS["rose"])
        with right:
            metric_card("Ulasan negatif", f"{negative_review:.1f}%" if np.isfinite(negative_review) else "N/A", "Rating 1 atau 2", COLORS["amber"])

        left, right = st.columns(2, gap="large")
        with left:
            section_heading("Distribusi rating", "Jumlah pesanan pada setiap skor ulasan.")
            rating_dist = reviewed.assign(Rating=reviewed["review_score"].round().astype(int)).groupby("Rating", as_index=False).size().rename(columns={"size": "Pesanan"})
            complete_rating = pd.DataFrame({"Rating": [1, 2, 3, 4, 5]}).merge(rating_dist, on="Rating", how="left").fillna(0)
            fig = px.bar(complete_rating, x="Rating", y="Pesanan", color="Rating", color_continuous_scale=[COLORS["rose"], COLORS["amber"], COLORS["emerald"]])
            fig.update_layout(coloraxis_showscale=False)
            fig.update_traces(hovertemplate="Rating %{x}<br>%{y:,.0f} pesanan<extra></extra>")
            st.plotly_chart(style_figure(fig, 390), use_container_width=True, config={"displayModeBar": False})
        with right:
            section_heading("Distribusi waktu pengiriman", "Outlier di atas 90 hari dikeluarkan dari grafik, tetapi tetap masuk KPI.")
            fig = px.histogram(valid_delivery, x="delivery_days", nbins=36, color_discrete_sequence=[COLORS["blue"]], labels={"delivery_days": "Waktu pengiriman (hari)", "count": "Pesanan"})
            if np.isfinite(average_delivery):
                fig.add_vline(x=average_delivery, line_dash="dash", line_color=COLORS["rose"], annotation_text=f"Rata-rata {average_delivery:.1f} hari", annotation_position="top right")
            fig.update_traces(hovertemplate="Waktu %{x:.1f} hari<br>%{y:,.0f} pesanan<extra></extra>")
            st.plotly_chart(style_figure(fig, 390), use_container_width=True, config={"displayModeBar": False})

        selected_order_ids = set(order_view["order_id"])
        filtered_payments = payments[payments["order_id"].isin(selected_order_ids)]
        payment_profile = (
            filtered_payments.groupby("payment_label", as_index=False)
            .agg(Nilai=("payment_value", "sum"), Pesanan=("order_id", "nunique"), Transaksi=("payment_value", "size"))
            .sort_values("Nilai", ascending=False)
        )
        left, right = st.columns([1.25, 1], gap="large")
        with left:
            section_heading("Nilai pembayaran menurut metode", "Nilai pembayaran dihitung pada level pesanan yang masuk hasil filter.")
            fig = px.bar(payment_profile.sort_values("Nilai"), x="Nilai", y="payment_label", orientation="h", color="Nilai", color_continuous_scale=["#60A5FA", "#1E40AF"], labels={"payment_label": "", "Nilai": "Nilai pembayaran (R$)"})
            fig.update_layout(coloraxis_showscale=False)
            fig.update_traces(customdata=payment_profile.sort_values("Nilai")[["Pesanan", "Transaksi"]], hovertemplate="%{y}<br>Nilai R$ %{x:,.2f}<br>Pesanan %{customdata[0]:,.0f}<br>Transaksi %{customdata[1]:,.0f}<extra></extra>")
            st.plotly_chart(style_figure(fig, 400), use_container_width=True, config={"displayModeBar": False})
        with right:
            section_heading("Porsi metode pembayaran", "Proporsi berdasarkan nilai pembayaran, bukan jumlah transaksi.")
            fig = px.pie(payment_profile, names="payment_label", values="Nilai", hole=.62, color_discrete_sequence=[COLORS["blue"], COLORS["cyan"], COLORS["violet"], COLORS["amber"], COLORS["emerald"]])
            fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="white", width=3)), hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>")
            st.plotly_chart(style_figure(fig, 400), use_container_width=True, config={"displayModeBar": False})
        if categories:
            st.caption("Catatan: ketika kategori produk difilter, nilai pembayaran mencakup seluruh nilai pesanan yang memiliki kategori tersebut.")

    st.markdown("---")
    footer_left, footer_middle, footer_right = st.columns([1.6, 1, 1])
    with footer_left:
        st.caption(
            f"Menampilkan {format_integer(len(filtered))} item dari "
            f"{format_integer(current_orders)} pesanan • GMV = harga produk + freight"
        )
    with footer_middle:
        with st.expander("Kualitas data"):
            st.dataframe(model["quality"], hide_index=True, use_container_width=True)
    with footer_right:
        st.download_button(
            "Unduh hasil filter (.csv)",
            data=create_order_export(filtered),
            file_name=f"olist_filtered_{start_date}_{end_date}.csv",
            mime="text/csv",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
