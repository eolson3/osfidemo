import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st


# ---------------------------
# Page config & basic styling
# ---------------------------
st.set_page_config(
    page_title="OSF Institutions Demo Dashboard",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .osf-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0 1rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .osf-title {
        font-size: 1.8rem;
        font-weight: 700;
    }
    .osf-subtitle {
        font-size: 0.95rem;
        color: #666666;
    }
    .osf-badge {
        background-color: #f5f5f5;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        font-size: 0.75rem;
        color: #555555;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------
# Helper functions
# ---------------------------
def generate_demo_data(n_days: int = 180, n_users: int = 250) -> pd.DataFrame:
    """
    Synthetic OSFI-style data.
    Each row ~ usage event for a project/registration/file/preprint.
    """
    today = dt.date.today()
    dates = pd.date_range(end=today, periods=n_days, freq="D")

    institutions = ["Sample University", "Demo College", "Test Institute"]
    departments = ["Psychology", "Biology", "CS", "Economics", "Library"]
    countries = ["US", "UK", "DE", "NL", "ZA", "BR"]
    resource_types = ["project", "registration", "file", "preprint"]
    visibility = ["public", "private"]
    storage_scale = [10_000, 50_000, 200_000, 1_000_000]  # bytes

    rows = []
    rng = np.random.default_rng(42)

    for date in dates:
        n_events = rng.integers(50, 200)
        for _ in range(n_events):
            user_id = f"user_{rng.integers(1, n_users + 1)}"
            project_id = f"proj_{rng.integers(1, n_users * 3)}"
            inst = rng.choice(institutions)
            dept = rng.choice(departments)
            country = rng.choice(countries)
            rtype = rng.choice(resource_types, p=[0.45, 0.2, 0.2, 0.15])
            vis = rng.choice(visibility, p=[0.6, 0.4])
            size = rng.choice(storage_scale) * abs(rng.normal(1, 0.5))
            has_orcid = rng.random() < 0.35  # 35% ORCID adoption (demo)

            rows.append(
                {
                    "date": date.date(),
                    "user_id": user_id,
                    "project_id": project_id,
                    "institution": inst,
                    "department": dept,
                    "country": country,
                    "resource_type": rtype,
                    "visibility": vis,
                    "size_bytes": max(int(size), 0),
                    "has_orcid": has_orcid,
                }
            )

    df = pd.DataFrame(rows)
    return df


def parse_uploaded_data(uploaded_file) -> pd.DataFrame | None:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.lower().endswith(".json"):
            df = pd.read_json(uploaded_file)
        else:
            st.error("Unsupported file type. Please upload CSV or JSON.")
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

    # Normalize some common column names
    date_cols = [c for c in df.columns if c.lower() in ["date", "event_date", "timestamp"]]
    if date_cols:
        date_col = date_cols[0]
        df[date_col] = pd.to_datetime(df[date_col]).dt.date
        if date_col != "date":
            df.rename(columns={date_col: "date"}, inplace=True)

    if "size" in df.columns and "size_bytes" not in df.columns:
        df.rename(columns={"size": "size_bytes"}, inplace=True)

    return df


def ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    if "date" not in df.columns:
        df = df.copy()
        df["date"] = pd.date_range(
            end=dt.date.today(), periods=len(df), freq="D"
        ).date
    return df


def compute_overall_metrics(df: pd.DataFrame) -> dict:
    df = ensure_date_column(df)
    today = df["date"].max()
    last_30 = today - dt.timedelta(days=30)
    last_90 = today - dt.timedelta(days=90)

    dau_30 = (
        df.loc[df["date"] >= last_30, "user_id"].nunique()
        if "user_id" in df.columns
        else None
    )
    mau_90 = (
        df.loc[df["date"] >= last_90, "user_id"].nunique()
        if "user_id" in df.columns
        else None
    )

    total_users = df["user_id"].nunique() if "user_id" in df.columns else None

    total_affiliated_projects = (
        df.loc[df.get("resource_type", "") == "project", "project_id"].nunique()
        if "project_id" in df.columns and "resource_type" in df.columns
        else None
    )
    total_registrations = (
        df.loc[df.get("resource_type", "") == "registration", "project_id"].nunique()
        if "project_id" in df.columns and "resource_type" in df.columns
        else None
    )
    total_preprints = (
        df.loc[df.get("resource_type", "") == "preprint", "project_id"].nunique()
        if "project_id" in df.columns and "resource_type" in df.columns
        else None
    )

    total_storage_gb = (
        df["size_bytes"].sum() / 1e9 if "size_bytes" in df.columns else None
    )

    public_share = None
    if "visibility" in df.columns:
        vis_counts = df["visibility"].value_counts(normalize=True)
        public_share = float(vis_counts.get("public", 0.0)) * 100

    orcid_share = None
    if "has_orcid" in df.columns:
        orcid_share = float(df["has_orcid"].mean()) * 100

    return {
        "dau_30": dau_30,
        "mau_90": mau_90,
        "total_users": total_users,
        "total_affiliated_projects": total_affiliated_projects,
        "total_registrations": total_registrations,
        "total_preprints": total_preprints,
        "total_storage_gb": total_storage_gb,
        "public_share": public_share,
        "orcid_share": orcid_share,
        "latest_date": today,
    }


def format_metric(value, default="—", fmt="{:,}"):
    if value is None:
        return default
    try:
        return fmt.format(value)
    except Exception:
        return str(value)


# ---------------------------
# Sidebar: navigation + upload
# ---------------------------
with st.sidebar:
    st.markdown("### 📊 OSF Institutions (Demo)")

    # Tabs aligned with OSFI Metrics Dashboard, minus messaging/data
    page = st.radio(
        "Tabs",
        [
            "Summary",
            "Users",
            "Projects",
            "Registrations",
            "Preprints",
        ],
        index=0,
    )

    st.markdown("---")
    uploaded_file = st.file_uploader(
        "Upload OSF-style data", type=["csv", "json"], help="CSV or JSON with usage events"
    )

    use_demo = st.checkbox("Use built-in demo data", value=(uploaded_file is None))

    st.markdown("---")
    st.caption(
        "This is a demo inspired by the OSF Institutions Metrics Dashboard. "
        "It is not connected to the live OSF."
    )


# ---------------------------
# Load data
# ---------------------------
if uploaded_file is not None and not use_demo:
    df = parse_uploaded_data(uploaded_file)
    if df is None:
        st.stop()
else:
    df = generate_demo_data()

df = ensure_date_column(df)

# ---------------------------
# Global filters (similar to OSFI dashboard filters)
# ---------------------------
with st.sidebar:
    st.markdown("### Filters")

    min_date, max_date = df["date"].min(), df["date"].max()
    date_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, (tuple, list)):
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    # Content type filter
    if "resource_type" in df.columns:
        all_types = sorted(df["resource_type"].unique().tolist())
        selected_types = st.multiselect(
            "Content types",
            options=all_types,
            default=all_types,
        )
    else:
        selected_types = None

    # Visibility filter
    if "visibility" in df.columns:
        all_vis = sorted(df["visibility"].unique().tolist())
        selected_vis = st.multiselect(
            "Visibility",
            options=all_vis,
            default=all_vis,
        )
    else:
        selected_vis = None

# Apply filters
df_filtered = df.copy()
df_filtered = df_filtered[
    (df_filtered["date"] >= start_date) & (df_filtered["date"] <= end_date)
]

if selected_types is not None and len(selected_types) > 0:
    df_filtered = df_filtered[df_filtered["resource_type"].isin(selected_types)]

if selected_vis is not None and len(selected_vis) > 0:
    df_filtered = df_filtered[df_filtered["visibility"].isin(selected_vis)]


# ---------------------------
# Header
# ---------------------------
st.markdown(
    """
    <div class="osf-header">
      <div>
        <div class="osf-title">OSF Institutions — Metrics Dashboard (Demo)</div>
        <div class="osf-subtitle">
          Simulated institutional usage metrics to mirror the OSFI Metrics Dashboard structure.
        </div>
      </div>
      <div>
        <span class="osf-badge">Demo environment</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metrics = compute_overall_metrics(df_filtered)

st.caption(
    f"Filtered date range: **{start_date} → {end_date}** · "
    f"Rows in current view: **{len(df_filtered):,}**"
)


# ---------------------------
# SUMMARY TAB
# ---------------------------
if page == "Summary":
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active users (30d)", format_metric(metrics["dau_30"]))
    col2.metric("Active users (90d)", format_metric(metrics["mau_90"]))
    col3.metric("Total affiliated users", format_metric(metrics["total_users"]))
    col4.metric(
        "Users with ORCID (%)",
        format_metric(metrics["orcid_share"], fmt="{:,.1f}%"),
    )

    col5, col6, col7 = st.columns(3)
    col5.metric(
        "Affiliated projects",
        format_metric(metrics["total_affiliated_projects"]),
    )
    col6.metric(
        "Registrations",
        format_metric(metrics["total_registrations"]),
    )
    col7.metric(
        "Preprints",
        format_metric(metrics["total_preprints"]),
    )

    col8, col9 = st.columns(2)
    col8.metric(
        "Storage used (GB)",
        format_metric(metrics["total_storage_gb"], fmt="{:,.2f}"),
    )
    col9.metric(
        "Public content (%)",
        format_metric(metrics["public_share"], fmt="{:,.1f}%"),
    )

    st.markdown("### Activity over time")
    by_date = df_filtered.groupby("date").agg(
        events=("user_id", "count"),
        users=("user_id", "nunique") if "user_id" in df_filtered.columns else ("date", "count"),
    )

    tab1, tab2 = st.tabs(["Events per day", "Unique users per day"])
    with tab1:
        st.line_chart(by_date["events"])
    with tab2:
        if "user_id" in df_filtered.columns:
            st.line_chart(by_date["users"])
        else:
            st.info("No user_id column available for unique user counts.")

    st.markdown("### Content mix (by type)")
    if "resource_type" in df_filtered.columns:
        rt_counts = df_filtered["resource_type"].value_counts()
        st.bar_chart(rt_counts)
    else:
        st.info("No resource_type column found in data.")

    st.markdown("### Visibility breakdown")
    if "visibility" in df_filtered.columns:
        vis_counts = df_filtered["visibility"].value_counts()
        st.bar_chart(vis_counts)
    else:
        st.info("No visibility column found in data.")


# ---------------------------
# USERS TAB
# ---------------------------
elif page == "Users":
    st.subheader("Users")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total affiliated users", format_metric(metrics["total_users"]))
    col2.metric(
        "Users with ORCID (%)",
        format_metric(metrics["orcid_share"], fmt="{:,.1f}%"),
    )
    col3.metric(
        "Active users (30d)",
        format_metric(metrics["dau_30"]),
    )

    st.markdown("#### Users by department")
    if "department" in df_filtered.columns and "user_id" in df_filtered.columns:
        users_by_dept = (
            df_filtered.groupby("department")["user_id"]
            .nunique()
            .sort_values(ascending=False)
        )
        st.bar_chart(users_by_dept)
    else:
        st.info("No department and/or user_id column available.")

    st.markdown("#### Users by country")
    if "country" in df_filtered.columns and "user_id" in df_filtered.columns:
        users_by_country = (
            df_filtered.groupby("country")["user_id"]
            .nunique()
            .sort_values(ascending=False)
        )
        st.bar_chart(users_by_country)
    else:
        st.info("No country and/or user_id column available.")

    st.markdown("#### User table (sample)")
    if "user_id" in df_filtered.columns:
        user_summary = (
            df_filtered.groupby("user_id")
            .agg(
                events=("date", "count"),
                first_seen=("date", "min"),
                last_seen=("date", "max"),
                projects=("project_id", "nunique"),
            )
            .sort_values("events", ascending=False)
            .head(200)
        )
        st.dataframe(user_summary)
    else:
        st.info("No user_id column found.")


# ---------------------------
# PROJECTS TAB
# ---------------------------
elif page == "Projects":
    st.subheader("Projects")

    if "resource_type" not in df_filtered.columns or "project_id" not in df_filtered.columns:
        st.info("Need resource_type and project_id columns to show project metrics.")
    else:
        proj_df = df_filtered[df_filtered["resource_type"] == "project"].copy()

        col1, col2 = st.columns(2)
        col1.metric(
            "Affiliated projects",
            format_metric(
                proj_df["project_id"].nunique() if not proj_df.empty else 0
            ),
        )
        if "visibility" in proj_df.columns:
            proj_vis = (
                proj_df.groupby("project_id")["visibility"]
                .agg(lambda x: (x == "public").any())
                .value_counts(normalize=True)
            )
            public_pct = float(proj_vis.get(True, 0.0) * 100)
        else:
            public_pct = None
        col2.metric(
            "Projects with public content (%)",
            format_metric(public_pct, fmt="{:,.1f}%"),
        )

        st.markdown("#### New projects over time")
        proj_first_seen = (
            proj_df.groupby("project_id")["date"].min().value_counts().sort_index()
        )
        st.line_chart(proj_first_seen)

        st.markdown("#### Project visibility")
        if "visibility" in proj_df.columns:
            vis_counts = proj_df["visibility"].value_counts()
            st.bar_chart(vis_counts)
        else:
            st.info("No visibility column found in project data.")

        st.markdown("#### Project table (sample)")
        proj_summary = (
            proj_df.groupby("project_id")
            .agg(
                events=("date", "count"),
                first_seen=("date", "min"),
                last_seen=("date", "max"),
                total_size_bytes=("size_bytes", "sum") if "size_bytes" in proj_df.columns else ("date", "count"),
            )
            .sort_values("events", ascending=False)
            .head(200)
        )
        if "total_size_bytes" in proj_summary.columns:
            proj_summary["total_size_gb"] = proj_summary["total_size_bytes"] / 1e9
        st.dataframe(proj_summary)


# ---------------------------
# REGISTRATIONS TAB
# ---------------------------
elif page == "Registrations":
    st.subheader("Registrations")

    if "resource_type" not in df_filtered.columns or "project_id" not in df_filtered.columns:
        st.info("Need resource_type and project_id columns to show registration metrics.")
    else:
        reg_df = df_filtered[df_filtered["resource_type"] == "registration"].copy()

        col1, col2 = st.columns(2)
        col1.metric(
            "Registrations",
            format_metric(
                reg_df["project_id"].nunique() if not reg_df.empty else 0
            ),
        )
        if "visibility" in reg_df.columns:
            reg_vis = reg_df["visibility"].value_counts(normalize=True)
            public_pct = float(reg_vis.get("public", 0.0) * 100)
        else:
            public_pct = None
        col2.metric(
            "Public registrations (%)",
            format_metric(public_pct, fmt="{:,.1f}%"),
        )

        st.markdown("#### Registrations over time")
        if not reg_df.empty:
            reg_first_seen = (
                reg_df.groupby("project_id")["date"].min().value_counts().sort_index()
            )
            st.line_chart(reg_first_seen)
        else:
            st.info("No registrations in current filtered view.")

        st.markdown("#### Registration table (sample)")
        reg_summary = (
            reg_df.groupby("project_id")
            .agg(
                events=("date", "count"),
                first_seen=("date", "min"),
                last_seen=("date", "max"),
            )
            .sort_values("events", ascending=False)
            .head(200)
        )
        st.dataframe(reg_summary)


# ---------------------------
# PREPRINTS TAB
# ---------------------------
elif page == "Preprints":
    st.subheader("Preprints")

    if "resource_type" not in df_filtered.columns or "project_id" not in df_filtered.columns:
        st.info("Need resource_type and project_id columns to show preprint metrics.")
    else:
        pp_df = df_filtered[df_filtered["resource_type"] == "preprint"].copy()

        col1, col2 = st.columns(2)
        col1.metric(
            "Preprints",
            format_metric(
                pp_df["project_id"].nunique() if not pp_df.empty else 0
            ),
        )
        if "visibility" in pp_df.columns:
            pp_vis = pp_df["visibility"].value_counts(normalize=True)
            public_pct = float(pp_vis.get("public", 0.0) * 100)
        else:
            public_pct = None
        col2.metric(
            "Public preprints (%)",
            format_metric(public_pct, fmt="{:,.1f}%"),
        )

        st.markdown("#### Preprints over time")
        if not pp_df.empty:
            pp_first_seen = (
                pp_df.groupby("project_id")["date"].min().value_counts().sort_index()
            )
            st.line_chart(pp_first_seen)
        else:
            st.info("No preprints in current filtered view.")

        st.markdown("#### Preprint table (sample)")
        pp_summary = (
            pp_df.groupby("project_id")
            .agg(
                events=("date", "count"),
                first_seen=("date", "min"),
                last_seen=("date", "max"),
            )
            .sort_values("events", ascending=False)
            .head(200)
        )
        st.dataframe(pp_summary)
