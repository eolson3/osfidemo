import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st


# =====================================================
# CONFIG & STYLING
# =====================================================

st.set_page_config(
    page_title="OSF Institutions Demo Dashboard",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    body { background-color: #f4f5f7; }
    .main { background-color: #f4f5f7; }
    .block-container { padding-top: 0.5rem; }

    .osf-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1.0rem;
        background: #023c52;
        color: #ffffff;
        border-radius: 8px;
        margin-bottom: 1.0rem;
    }
    .osf-title {
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .osf-subtitle {
        font-size: 0.95rem;
        color: #e3edf2;
    }
    .osf-badge {
        background-color: #0f7ea5;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        font-size: 0.75rem;
        color: #ffffff;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
        color: #e5e7eb;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p {
        color: #e5e7eb;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================
# DATA LOADING
# =====================================================

DATA_DIR = Path(__file__).parent

USERS_CSV = DATA_DIR / "institution-user-metrics_2025-12.csv"
PROJECTS_CSV = DATA_DIR / "2025-12-04_projects-search-results.csv"
REGS_CSV = DATA_DIR / "2025-12-04_registrations-search-results.csv"
PREPRINTS_CSV = DATA_DIR / "2025-12-04_preprints-search-results.csv"


@st.cache_data
def load_users(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # ensure expected columns exist
    expected = {
        "report_yearmonth",
        "account_creation_date",
        "contacts",
        "department",
        "embargoed_registration_count",
        "month_last_active",
        "month_last_login",
        "orcid_id",
        "private_projects",
        "public_file_count",
        "public_projects",
        "public_registration_count",
        "published_preprint_count",
        "storage_byte_count",
        "user_name",
    }
    missing = expected - set(df.columns)
    if missing:
        st.warning(f"Users CSV missing columns: {missing}")
    return df


@st.cache_data
def load_projects(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


@st.cache_data
def load_regs(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


@st.cache_data
def load_preprints(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


try:
    users_raw = load_users(USERS_CSV)
    projects_raw = load_projects(PROJECTS_CSV)
    regs_raw = load_regs(REGS_CSV)
    preprints_raw = load_preprints(PREPRINTS_CSV)
except Exception as e:
    st.error(
        f"Error loading default CSVs: {e}\n\n"
        "Make sure the four OSFI export CSV files are in the same directory as this app."
    )
    st.stop()


# =====================================================
# SIDEBAR: NAV + GLOBAL FILTERS
# =====================================================

with st.sidebar:
    st.markdown("### 📊 OSF Institutions (Demo)")

    page = st.radio(
        "Tabs",
        ["Summary", "Users", "Projects", "Registrations", "Preprints"],
        index=0,
    )

    st.markdown("---")

    st.caption(
        "This demo uses CSV exports from a real OSF Institutions dashboard. "
        "It is not connected to the live OSF API."
    )

    st.markdown("---")
    st.markdown("### Filters (apply across tabs where relevant)")

    # Global search: user_name / title contains
    search_text = st.text_input(
        "Search (user name / title contains)",
        value="",
        help="Case-insensitive search in user_name (Users) or title (Projects/Registrations/Preprints).",
    ).strip()

    # Department (Users)
    dept_options = sorted(
        users_raw["department"].dropna().unique().tolist()
    ) if "department" in users_raw.columns else []
    if dept_options:
        dept_selected = st.multiselect(
            "Department (Users)",
            options=dept_options,
            default=dept_options,
        )
    else:
        dept_selected = []

    # ORCID (Users)
    if "orcid_id" in users_raw.columns:
        orcid_filter = st.selectbox(
            "ORCID (Users)",
            ["All", "Has ORCID", "No ORCID"],
            index=0,
        )
    else:
        orcid_filter = "All"

    # License (Projects/Registrations/Preprints)
    license_values = set()
    for df in (projects_raw, regs_raw, preprints_raw):
        if "rights.name" in df.columns:
            license_values.update(df["rights.name"].dropna().unique().tolist())
    license_options = sorted(license_values)
    if license_options:
        licenses_selected = st.multiselect(
            "License (content tabs)",
            options=license_options,
            default=license_options,
        )
    else:
        licenses_selected = []

    # Storage region (Projects/Registrations)
    region_values = set()
    for df in (projects_raw, regs_raw):
        if "storageRegion.prefLabel" in df.columns:
            region_values.update(df["storageRegion.prefLabel"].dropna().unique().tolist())
    region_options = sorted(region_values)
    if region_options:
        regions_selected = st.multiselect(
            "Storage region (Projects/Regs)",
            options=region_options,
            default=region_options,
        )
    else:
        regions_selected = []


# =====================================================
# APPLY FILTERS TO EACH DATASET
# =====================================================

def apply_user_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Department filter
    if dept_selected:
        out = out[out["department"].isin(dept_selected)]

    # ORCID filter
    if orcid_filter != "All":
        if orcid_filter == "Has ORCID":
            out = out[out["orcid_id"].notna() & (out["orcid_id"].astype(str).str.strip() != "")]
        else:
            out = out[out["orcid_id"].isna() | (out["orcid_id"].astype(str).str.strip() == "")]

    # Search (user_name)
    if search_text:
        out = out[out["user_name"].astype(str).str.contains(search_text, case=False, na=False)]

    return out


def apply_project_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # License
    if licenses_selected and "rights.name" in out.columns:
        out = out[out["rights.name"].isin(licenses_selected) | out["rights.name"].isna()]

    # Storage region
    if regions_selected and "storageRegion.prefLabel" in out.columns:
        out = out[
            out["storageRegion.prefLabel"].isin(regions_selected)
            | out["storageRegion.prefLabel"].isna()
        ]

    # Search (title)
    if search_text and "title" in out.columns:
        out = out[out["title"].astype(str).str.contains(search_text, case=False, na=False)]

    return out


def apply_reg_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # License
    if licenses_selected and "rights.name" in out.columns:
        out = out[out["rights.name"].isin(licenses_selected) | out["rights.name"].isna()]

    # Storage region
    if regions_selected and "storageRegion.prefLabel" in out.columns:
        out = out[
            out["storageRegion.prefLabel"].isin(regions_selected)
            | out["storageRegion.prefLabel"].isna()
        ]

    # Search (title)
    if search_text and "title" in out.columns:
        out = out[out["title"].astype(str).str.contains(search_text, case=False, na=False)]

    return out


def apply_preprint_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # License
    if licenses_selected and "rights.name" in out.columns:
        out = out[out["rights.name"].isin(licenses_selected) | out["rights.name"].isna()]

    # Search (title)
    if search_text and "title" in out.columns:
        out = out[out["title"].astype(str).str.contains(search_text, case=False, na=False)]

    return out


users = apply_user_filters(users_raw)
projects = apply_project_filters(projects_raw)
regs = apply_reg_filters(regs_raw)
preprints = apply_preprint_filters(preprints_raw)


# =====================================================
# SUMMARY METRICS (SNAPSHOT)
# =====================================================

def compute_summary_metrics(users_df, projects_df, regs_df, preprints_df):
    # Users
    total_users = len(users_df)
    has_orcid = (
        users_df["orcid_id"].notna()
        & (users_df["orcid_id"].astype(str).str.strip() != "")
    ).sum() if "orcid_id" in users_df.columns else None

    # Use report_yearmonth + month_last_* to approximate “monthly” metrics
    monthly_logged_in = None
    monthly_active = None
    report_month = None
    if {"report_yearmonth", "month_last_login", "month_last_active"} <= set(users_df.columns):
        if not users_df["report_yearmonth"].isna().all():
            report_month = str(users_df["report_yearmonth"].iloc[0])
            monthly_logged_in = (
                (users_df["month_last_login"] == users_df["report_yearmonth"]).sum()
            )
            monthly_active = (
                (users_df["month_last_active"] == users_df["report_yearmonth"]).sum()
            )

    # Content counts
    total_projects = len(projects_df)
    total_regs = len(regs_df)
    total_preprints = len(preprints_df)

    # Files & storage from user metrics
    total_files = (
        users_df["public_file_count"].sum()
        if "public_file_count" in users_df.columns
        else None
    )
    total_storage_gb = (
        users_df["storage_byte_count"].sum() / 1e9
        if "storage_byte_count" in users_df.columns
        else None
    )

    return {
        "report_month": report_month,
        "total_users": total_users,
        "has_orcid": has_orcid,
        "monthly_logged_in": monthly_logged_in,
        "monthly_active": monthly_active,
        "total_projects": total_projects,
        "total_regs": total_regs,
        "total_preprints": total_preprints,
        "total_files": total_files,
        "total_storage_gb": total_storage_gb,
    }


summary = compute_summary_metrics(users, projects, regs, preprints)


def fmt(value, default="—", fmt_str="{:,}"):
    if value is None:
        return default
    try:
        return fmt_str.format(value)
    except Exception:
        return str(value)


# =====================================================
# HEADER
# =====================================================

report_month_label = f"Report month: {summary['report_month']}" if summary["report_month"] else ""

st.markdown(
    f"""
    <div class="osf-header">
      <div>
        <div class="osf-title">OSF Institutions — Metrics Dashboard (Demo)</div>
        <div class="osf-subtitle">
          Snapshot-style metrics using real CSV exports from an OSF Institutions dashboard.
          {report_month_label}
        </div>
      </div>
      <div>
        <span class="osf-badge">Demo snapshot</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    f"Current filters applied · Users: **{len(users):,}** · "
    f"Projects: **{len(projects):,}** · Registrations: **{len(regs):,}** · "
    f"Preprints: **{len(preprints):,}**"
)


# =====================================================
# SUMMARY TAB
# =====================================================

if page == "Summary":
    st.subheader("Summary (snapshot counts)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total users", fmt(summary["total_users"]))
    c2.metric(
        "Total monthly logged in users",
        fmt(summary["monthly_logged_in"]),
    )
    c3.metric(
        "Total monthly active users",
        fmt(summary["monthly_active"]),
    )
    orcid_pct = (
        (summary["has_orcid"] / summary["total_users"] * 100)
        if summary["has_orcid"] is not None and summary["total_users"]
        else None
    )
    c4.metric(
        "Users with ORCID (%)",
        fmt(orcid_pct, fmt_str="{:,.1f}%"),
    )

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("OSF projects (rows)", fmt(summary["total_projects"]))
    c6.metric("OSF registrations (rows)", fmt(summary["total_regs"]))
    c7.metric("OSF preprints (rows)", fmt(summary["total_preprints"]))
    c8.metric("Total public file count", fmt(summary["total_files"]))

    c9, c10 = st.columns(2)
    c9.metric(
        "Total storage on OSF (GB)",
        fmt(summary["total_storage_gb"], fmt_str="{:,.2f}"),
    )
    # we don't have public/private flag in these CSVs, so skip “Public content %”

    st.markdown("### Visualization snapshots")

    # Users by department
    st.markdown("#### Users by department")
    if "department" in users.columns:
        dept_counts = (
            users["department"].fillna("Unknown").value_counts().sort_values(ascending=False)
        )
        st.bar_chart(dept_counts)
    else:
        st.info("No department column in users CSV.")

    # Projects by storage region
    st.markdown("#### Projects by storage region")
    if "storageRegion.prefLabel" in projects.columns:
        proj_region = (
            projects["storageRegion.prefLabel"]
            .fillna("Unknown")
            .value_counts()
            .sort_values(ascending=False)
        )
        st.bar_chart(proj_region)
    else:
        st.info("No storageRegion.prefLabel column in projects CSV.")

    # Registrations by schema
    st.markdown("#### Registrations by registration schema")
    if "conformsTo.title" in regs.columns:
        schema_counts = (
            regs["conformsTo.title"]
            .fillna("Unknown")
            .value_counts()
            .sort_values(ascending=False)
        )
        st.bar_chart(schema_counts)
    else:
        st.info("No conformsTo.title column in registrations CSV.")

    # Preprints by license
    st.markdown("#### Preprints by license")
    if "rights.name" in preprints.columns:
        license_counts = (
            preprints["rights.name"]
            .fillna("Unknown")
            .value_counts()
            .sort_values(ascending=False)
        )
        st.bar_chart(license_counts)
    else:
        st.info("No rights.name column in preprints CSV.")


# =====================================================
# USERS TAB
# =====================================================

elif page == "Users":
    st.subheader("Users")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total users", fmt(summary["total_users"]))
    c2.metric("Users with ORCID", fmt(summary["has_orcid"]))
    c3.metric("Monthly active users", fmt(summary["monthly_active"]))

    if users.empty:
        st.info("No users match the current filters.")
    else:
        df = users.copy()

        # Storage in GB
        if "storage_byte_count" in df.columns:
            df["Total data stored on OSF (GB)"] = df["storage_byte_count"] / 1e9

        display = df.rename(
            columns={
                "user_name": "Name",
                "department": "Department",
                "orcid_id": "ORCID iD",
                "account_creation_date": "Account created (YYYY-MM)",
                "month_last_login": "Month last login (YYYY-MM)",
                "month_last_active": "Month last active (YYYY-MM)",
                "public_projects": "Public projects",
                "private_projects": "Private projects",
                "public_registration_count": "Public registrations",
                "embargoed_registration_count": "Embargoed registrations",
                "published_preprint_count": "Published preprints",
                "public_file_count": "Public files",
            }
        )

        cols = [
            "Name",
            "Department",
            "ORCID iD",
            "Public projects",
            "Private projects",
            "Public registrations",
            "Embargoed registrations",
            "Published preprints",
            "Public files",
            "Total data stored on OSF (GB)",
            "Account created (YYYY-MM)",
            "Month last login (YYYY-MM)",
            "Month last active (YYYY-MM)",
        ]
        existing = [c for c in cols if c in display.columns]

        st.markdown("#### User metrics (one row per affiliated user)")
        st.dataframe(display[existing].sort_values("Name").reset_index(drop=True))


# =====================================================
# PROJECTS TAB
# =====================================================

elif page == "Projects":
    st.subheader("Projects")

    if projects.empty:
        st.info("No projects match the current filters.")
    else:
        df = projects.copy()

        if "storageByteCount" in df.columns:
            df["Total data stored on OSF (GB)"] = df["storageByteCount"] / 1e9

        display = df.rename(
            columns={
                "title": "Title",
                "@id": "OSF Link",
                "dateCreated": "Created date",
                "dateModified": "Modified date",
                "sameAs": "DOI",
                "storageRegion.prefLabel": "Storage region",
                "creator.name": "Creator(s)",
                "usage.viewCount": "Views (last 30 days)",
                "resourceNature.displayLabel": "Resource type",
                "rights.name": "License",
                "hasOsfAddon.prefLabel": "Add-ons",
                "funder.name": "Funder name",
            }
        )

        cols = [
            "Title",
            "Created date",
            "Modified date",
            "DOI",
            "Storage region",
            "Total data stored on OSF (GB)",
            "Creator(s)",
            "Views (last 30 days)",
            "Resource type",
            "License",
            "Add-ons",
            "Funder name",
            "OSF Link",
        ]
        existing = [c for c in cols if c in display.columns]

        c1, c2 = st.columns(2)
        c1.metric("Projects (rows)", fmt(len(display)))
        if "Total data stored on OSF (GB)" in display.columns:
            c2.metric(
                "Total storage (GB)",
                fmt(display["Total data stored on OSF (GB)"].sum(), fmt_str="{:,.2f}"),
            )

        st.markdown("#### Project metrics (one row per project)")
        st.dataframe(
            display[existing].sort_values("Modified date", ascending=False).reset_index(drop=True)
        )


# =====================================================
# REGISTRATIONS TAB
# =====================================================

elif page == "Registrations":
    st.subheader("Registrations")

    if regs.empty:
        st.info("No registrations match the current filters.")
    else:
        df = regs.copy()

        if "storageByteCount" in df.columns:
            df["Total data stored on OSF (GB)"] = df["storageByteCount"] / 1e9

        display = df.rename(
            columns={
                "title": "Title",
                "@id": "OSF Link",
                "dateCreated": "Created date",
                "dateModified": "Modified date",
                "sameAs": "DOI",
                "storageRegion.prefLabel": "Storage region",
                "creator.name": "Creator(s)",
                "usage.viewCount": "Views (last 30 days)",
                "resourceNature.displayLabel": "Resource type",
                "rights.name": "License",
                "funder.name": "Funder name",
                "conformsTo.title": "Registration schema",
            }
        )

        cols = [
            "Title",
            "Created date",
            "Modified date",
            "DOI",
            "Storage region",
            "Total data stored on OSF (GB)",
            "Creator(s)",
            "Views (last 30 days)",
            "Resource type",
            "License",
            "Funder name",
            "Registration schema",
            "OSF Link",
        ]
        existing = [c for c in cols if c in display.columns]

        c1, c2 = st.columns(2)
        c1.metric("Registrations (rows)", fmt(len(display)))
        if "Total data stored on OSF (GB)" in display.columns:
            c2.metric(
                "Total storage (GB)",
                fmt(display["Total data stored on OSF (GB)"].sum(), fmt_str="{:,.2f}"),
            )

        st.markdown("#### Registration metrics (one row per registration)")
        st.dataframe(
            display[existing].sort_values("Modified date", ascending=False).reset_index(drop=True)
        )


# =====================================================
# PREPRINTS TAB
# =====================================================

elif page == "Preprints":
    st.subheader("Preprints")

    if preprints.empty:
        st.info("No preprints match the current filters.")
    else:
        df = preprints.copy()

        display = df.rename(
            columns={
                "title": "Title",
                "@id": "OSF Link",
                "dateCreated": "Created date",
                "dateModified": "Modified date",
                "sameAs": "DOI",
                "rights.name": "License",
                "creator.name": "Creator(s)",
                "usage.viewCount": "Views (last 30 days)",
                "usage.downloadCount": "Downloads (last 30 days)",
            }
        )

        cols = [
            "Title",
            "Created date",
            "Modified date",
            "DOI",
            "License",
            "Creator(s)",
            "Views (last 30 days)",
            "Downloads (last 30 days)",
            "OSF Link",
        ]
        existing = [c for c in cols if c in display.columns]

        c1, c2 = st.columns(2)
        c1.metric("Preprints (rows)", fmt(len(display)))
        if "Views (last 30 days)" in display.columns:
            c2.metric(
                "Avg. views (30 days)",
                fmt(display["Views (last 30 days)"].mean(), fmt_str="{:,.1f}"),
            )

        st.markdown("#### Preprint metrics (one row per preprint)")
        st.dataframe(
            display[existing].sort_values("Modified date", ascending=False).reset_index(drop=True)
        )
