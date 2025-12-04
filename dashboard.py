import io
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
    Generate synthetic OSF Institutions–style usage data.
    Each row ~ "event" (project/file/registration activity with size + visibility).
    """
    today = dt.date.today()
    dates = pd.date_range(end=today, periods=n_days, freq="D")

    institutions = ["Sample University", "Demo College", "Test Institute"]
    departments = ["Psychology", "Biology", "CS", "Economics", "Library"]
    countries = ["US", "UK", "DE", "NL", "ZA", "BR"]
    resource_types = ["project", "registration", "file"]
    visibility = ["public", "private"]
    storage_scale = [10_000, 50_000, 200_000, 1_000_000]  # bytes

    rows = []
    rng = np.random.default_rng(42)

    for date in dates:
        # number of events per day
        n_events = rng.integers(50, 200)
        for _ in range(n_events):
            user_id = f"user_{rng.integers(1, n_users + 1)}"
            project_id = f"proj_{rng.integers(1, n_users * 3)}"
            inst = rng.choice(institutions)
            dept = rng.choice(departments)
            country = rng.choice(countries)
            rtype = rng.choice(resource_types, p=[0.5, 0.2, 0.3])
            vis = rng.choice(visibility, p=[0.6, 0.4])
            size = rng.choice(storage_scale) * abs(rng.normal(1, 0.5))

            has_orcid = rng.random() < 0.35  # 35% adoption

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
    # Expect at least a 'date' or 'event_date' and 'user_id'
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
        # Try to infer; if none, create fake sequential dates
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
    total_projects = (
        df.loc[df.get("resource_type", "") == "project", "project_id"].nunique()
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
        "total_projects": total_projects,
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
    st.markdown("### 📊 OSF Institutions Demo")

    page = st.radio(
        "Sections",
        ["Overview", "Users", "Projects & Activity", "Storage", "Data"],
        index=0,
    )

    st.markdown("---")
    uploaded_file = st.file_uploader(
        "Upload OSF-style data", type=["csv", "json"], help="CSV or JSON with usage events"
    )

    use_demo = st.checkbox("Use built-in demo data", value=(uploaded_file is None))

    st.markdown("---")
    st.caption(
        "This is a demo dashboard inspired by the OSF Institutions member dashboard. "
        "For illustration and training only."
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
# Header
# ---------------------------
st.markdown(
    """
    <div class="osf-header">
      <div>
        <div class="osf-title">OSF Institutions — Demo Dashboard</div>
        <div class="osf-subtitle">
          Simulated institutional usage metrics for demonstration and onboarding.
        </div>
      </div>
      <div>
        <span class="osf-badge">Demo environment</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


metrics = compute_overall_metrics(df)

st.caption(
    f"Data range: up to **{metrics['latest_date']}** · "
    f"Rows: **{len(df):,}**"
)


# ---------------------------
# Overview page
# ---------------------------
if page == "Overview":
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Active users (30d)", format_metric(metrics["dau_30"]))
    col2.metric("Active users (90d)", format_metric(metrics["mau_90"]))
    col3.metric(
        "Total users",
        format_metric(metrics["total_users"]),
    )
    col4.metric(
        "Total projects",
        format_metric(metrics["total_projects"]),
    )

    col5, col6 = st.columns(2)
    col5.metric(
        "Storage used (GB)",
        format_metric(
            metrics["total_storage_gb"], fmt="{:,.2f}"
        ),
    )
    col6.metric(
        "Public content (%)",
        format_metric(
            metrics["public_share"], fmt="{:,.1f}%"
        ),
    )

    st.markdown("### Activity over time")

    by_date = df.groupby("date").agg(
        events=("user_id", "count"),
        users=("user_id", "nunique") if "user_id" in df.columns else ("date", "count"),
    )

    tab1, tab2 = st.tabs(["Events per day", "Unique users per day"])
    with tab1:
        st.line_chart(by_date["events"])
    with tab2:
        if "user_id" in df.columns:
            st.line_chart(by_date["users"])
        else:
            st.info("No user_id column available for unique user counts.")

    st.markdown("### Resource type breakdown")
    if "resource_type" in df.columns:
        rt_counts = df["resource_type"].value_counts()
        st.bar_chart(rt_counts)
    else:
        st.info("No resource_type column found in data.")

    st.markdown("### Visibility breakdown")
    if "visibility" in df.columns:
        vis_counts = df["visibility"].value_counts()
        st.bar_chart(vis_counts)
    else:
        st.info("No visibility column found in data.")


# ---------------------------
# Users page
# ---------------------------
elif page == "Users":
    st.subheader("User adoption and engagement")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total users", format_metric(metrics["total_users"]))
    if metrics["orcid_share"] is not None:
        col2.metric(
            "Users with ORCID (%)",
            format_metric(metrics["orcid_share"], fmt="{:,.1f}%"),
        )
    else:
        col2.metric("Users with ORCID (%)", "—")
    col3.metric(
        "Active users (30d)",
        format_metric(metrics["dau_30"]),
    )

    st.markdown("#### Users by country")
    if "country" in df.columns and "user_id" in df.columns:
        users_by_country = (
            df.groupby("country")["user_id"].nunique().sort_values(ascending=False)
        )
        st.bar_chart(users_by_country)
    else:
        st.info("No country and/or user_id column available.")

    st.markdown("#### Users by department")
    if "department" in df.columns and "user_id" in df.columns:
        users_by_dept = (
            df.groupby("department")["user_id"].nunique().sort_values(ascending=False)
        )
        st.bar_chart(users_by_dept)
    else:
        st.info("No department and/or user_id column available.")

    with st.expander("Sample user-level table"):
        if "user_id" in df.columns:
            user_summary = (
                df.groupby("user_id")
                .agg(
                    events=("date", "count"),
                    first_seen=("date", "min"),
                    last_seen=("date", "max"),
                )
                .sort_values("events", ascending=False)
                .head(50)
            )
            st.dataframe(user_summary)
        else:
            st.info("No user_id column found.")


# ---------------------------
# Projects & Activity page
# ---------------------------
elif page == "Projects & Activity":
    st.subheader("Projects and registrations")

    if "project_id" in df.columns:
        proj_counts = (
            df.groupby("project_id")
            .agg(
                events=("date", "count"),
                first_seen=("date", "min"),
                last_seen=("date", "max"),
            )
            .sort_values("events", ascending=False)
        )

        st.markdown("#### Top projects by activity")
        st.dataframe(proj_counts.head(50))
    else:
        st.info("No project_id column found.")

    st.markdown("#### Project visibility")
    if "project_id" in df.columns and "visibility" in df.columns:
        proj_vis = (
            df.groupby(["project_id", "visibility"])
            .size()
            .unstack(fill_value=0)
        )
        vis_summary = proj_vis.gt(0).sum().sort_values(ascending=False)
        st.bar_chart(vis_summary)
    else:
        st.info("Need both project_id and visibility columns to show this chart.")

    st.markdown("#### Activity heatmap (day-of-week)")
    df["dow"] = pd.to_datetime(df["date"]).dt.day_name()
    activity_dow = df["dow"].value_counts().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    )
    st.bar_chart(activity_dow)


# ---------------------------
# Storage page
# ---------------------------
elif page == "Storage":
    st.subheader("Storage usage")

    if "size_bytes" not in df.columns:
        st.info("No size_bytes column found. Cannot compute storage metrics.")
    else:
        df["size_gb"] = df["size_bytes"] / 1e9

        col1, col2 = st.columns(2)
        col1.metric(
            "Total storage (GB)",
            format_metric(df["size_gb"].sum(), fmt="{:,.2f}"),
        )
        col2.metric(
            "Median object size (MB)",
            format_metric(df["size_bytes"].median() / 1e6, fmt="{:,.2f}"),
        )

        st.markdown("#### Storage over time")
        storage_by_date = df.groupby("date")["size_gb"].sum().cumsum()
        st.line_chart(storage_by_date)

        st.markdown("#### Storage by resource type")
        if "resource_type" in df.columns:
            storage_by_type = (
                df.groupby("resource_type")["size_gb"].sum().sort_values(ascending=False)
            )
            st.bar_chart(storage_by_type)
        else:
            st.info("No resource_type column found.")

        st.markdown("#### Storage by visibility")
        if "visibility" in df.columns:
            storage_by_vis = (
                df.groupby("visibility")["size_gb"].sum().sort_values(ascending=False)
            )
            st.bar_chart(storage_by_vis)
        else:
            st.info("No visibility column found.")


# ---------------------------
# Data page (schema & download)
# ---------------------------
elif page == "Data":
    st.subheader("Data preview & template")

    st.markdown("#### Current data sample")
    st.dataframe(df.head(50))

    st.markdown("#### Expected / useful columns")

    st.markdown(
        """
        The dashboard works best when your CSV/JSON has columns like:

        - `date` (or `event_date`, `timestamp`) – will be normalized to `date`
        - `user_id` – pseudonymous user identifier
        - `project_id` – project or registration ID
        - `institution` – institutional affiliation string
        - `department` – department / unit
        - `country` – country code or label
        - `resource_type` – e.g., `project`, `registration`, `file`
        - `visibility` – `public` or `private`
        - `size_bytes` – size of file / object in bytes
        - `has_orcid` – `True/False` or 1/0 flag
        """
    )

    st.markdown("#### Download demo dataset as CSV")

    demo_df = generate_demo_data(n_days=60, n_users=100)
    csv_buf = io.StringIO()
    demo_df.to_csv(csv_buf, index=False)
    st.download_button(
        "Download demo_data.csv",
        data=csv_buf.getvalue(),
        file_name="osf_institutions_demo_data.csv",
        mime="text/csv",
    )
