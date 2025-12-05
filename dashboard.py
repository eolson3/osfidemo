import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# =====================================================
# CONFIG & STYLING
# =====================================================

st.set_page_config(
    page_title="OSF Institutions Demo Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

INSTITUTION_NAME = "Center For Open Science [Test]"
INSTITUTION_LOGO_URL = "https://osf.io/static/img/cos-white.svg"

st.markdown(
    """
    <style>
    body { background-color: #f4f5f7; }
    .main { background-color: #f4f5f7; }
    .block-container {
        padding-top: 1.75rem !important;  /* prevent header from being cut off */
    }

    .osf-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem 1.0rem;
        background: #023c52;
        color: #ffffff;
        border-radius: 0;
        margin: 0 0 0.25rem 0;
        border-bottom: 1px solid #0b4f68;
    }
    .osf-header-left {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .osf-logo {
        height: 40px;
        width: 40px;
        border-radius: 999px;
        background: #ffffff11;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }
    .osf-logo img {
        max-height: 32px;
        max-width: 32px;
    }
    .osf-title {
        font-size: 1.4rem;
        font-weight: 700;
        margin-bottom: 0.15rem;
    }
    .osf-subtitle {
        font-size: 0.9rem;
        color: #e3edf2;
    }
    .osf-badge {
        background-color: #0f7ea5;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        font-size: 0.75rem;
        color: #ffffff;
    }

    /* Customize panel styling */
    .customize-box {
        background-color: #ffffff;
        border: 1px solid #d0d4da;
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        margin-top: 0.25rem;
        max-width: 320px;
        box-shadow: 0 2px 4px rgba(15, 23, 42, 0.08);
    }

    /* Hide sidebar completely */
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    [data-testid="collapsedControl"] {
        display: none !important;
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
    return df


@st.cache_data
def load_projects(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data
def load_regs(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data
def load_preprints(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


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
# HELPERS
# =====================================================


def fmt(value, default="—", fmt_str="{:,}"):
    if value is None:
        return default
    try:
        return fmt_str.format(value)
    except Exception:
        return str(value)


def compute_summary_metrics(users_df, projects_df, regs_df, preprints_df):
    total_users = len(users_df)
    has_orcid = (
        users_df["orcid_id"].notna()
        & (users_df["orcid_id"].astype(str).str.strip() != "")
    ).sum() if "orcid_id" in users_df.columns else None

    monthly_logged_in = None
    monthly_active = None
    report_month = None
    needed_cols = {"report_yearmonth", "month_last_login", "month_last_active"}
    if needed_cols.issubset(users_df.columns):
        if not users_df["report_yearmonth"].isna().all():
            report_month = str(users_df["report_yearmonth"].iloc[0])
            monthly_logged_in = (
                (users_df["month_last_login"] == users_df["report_yearmonth"]).sum()
            )
            monthly_active = (
                (users_df["month_last_active"] == users_df["report_yearmonth"]).sum()
            )

    total_projects = len(projects_df)
    total_regs = len(regs_df)
    total_preprints = len(preprints_df)

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


def donut_chart(labels, values, title: str):
    if not len(values) or sum(values) == 0:
        st.info(f"No data available for **{title}**.")
        return
    fig, ax = plt.subplots()
    wedges, _ = ax.pie(
        values,
        startangle=90,
        wedgeprops=dict(width=0.4),
    )
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.legend(
        wedges,
        [f"{l} ({v:,})" for l, v in zip(labels, values)],
        loc="center left",
        bbox_to_anchor=(1, 0.5),
    )
    st.pyplot(fig)


def bar_chart_from_series(series: pd.Series, title: str, top_n: int = 10):
    series = series.dropna().sort_values(ascending=False).head(top_n)
    if series.empty:
        st.info(f"No data available for **{title}**.")
        return
    st.markdown(f"**{title}**")
    st.bar_chart(series)


def get_page_df(df: pd.DataFrame, page_key: str, page_size: int = 10):
    """Return the slice for the current page, and total row count."""
    total_rows = len(df)
    if total_rows == 0:
        return df, total_rows

    total_pages = max(1, math.ceil(total_rows / page_size))
    page = st.session_state.get(page_key, 1)
    if page < 1 or page > total_pages:
        page = 1
        st.session_state[page_key] = page

    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total_rows


def render_pagination_controls(page_key: str, total_rows: int, page_size: int = 10):
    """Render OSF-style pagination controls under the table."""
    if total_rows <= page_size:
        return

    total_pages = max(1, math.ceil(total_rows / page_size))
    page = st.session_state.get(page_key, 1)
    if page < 1 or page > total_pages:
        page = 1
        st.session_state[page_key] = page

    info_col, first_col, prev_col, next_col, last_col = st.columns([3, 1, 1, 1, 1])

    with info_col:
        st.caption(f"Page {page} of {total_pages} · {total_rows:,} rows")

    with first_col:
        if st.button("≪", key=page_key + "_first") and page != 1:
            st.session_state[page_key] = 1

    with prev_col:
        if st.button("‹", key=page_key + "_prev") and page > 1:
            st.session_state[page_key] = page - 1

    with next_col:
        if st.button("›", key=page_key + "_next") and page < total_pages:
            st.session_state[page_key] = page + 1

    with last_col:
        if st.button("≫", key=page_key + "_last") and page != total_pages:
            st.session_state[page_key] = total_pages


# =====================================================
# HEADER
# =====================================================

global_summary = compute_summary_metrics(
    users_raw, projects_raw, regs_raw, preprints_raw
)
report_month_label = (
    f"Report month: {global_summary['report_month']}"
    if global_summary["report_month"]
    else ""
)

st.markdown(
    f"""
    <div class="osf-header">
      <div class="osf-header-left">
        <div class="osf-logo">
          <img src="{INSTITUTION_LOGO_URL}" alt="Institution logo" />
        </div>
        <div>
          <div class="osf-title">{INSTITUTION_NAME}</div>
          <div class="osf-subtitle">
            Institutions Dashboard (Demo) · {report_month_label}
          </div>
        </div>
      </div>
      <div>
        <span class="osf-badge">Demo snapshot</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =====================================================
# TABS
# =====================================================

(
    tab_summary,
    tab_users,
    tab_projects,
    tab_regs,
    tab_preprints,
) = st.tabs(["Summary", "Users", "Projects", "Registrations", "Preprints"])

# ---------------------- SUMMARY ---------------------- #
with tab_summary:
    st.subheader("Summary")

    summary = compute_summary_metrics(
        users_raw, projects_raw, regs_raw, preprints_raw
    )

    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r2c1, r2c2, r2c3, r2c4 = st.columns(4)

    r1c1.metric("Total Users", fmt(summary["total_users"]))
    r1c2.metric("Total Monthly Logged in Users", fmt(summary["monthly_logged_in"]))
    r1c3.metric("Total Monthly Active Users", fmt(summary["monthly_active"]))
    r1c4.metric("OSF Public and Private Projects", fmt(summary["total_projects"]))

    r2c1.metric(
        "OSF Public and Embargoed Registrations",
        fmt(summary["total_regs"]),
    )
    r2c2.metric("OSF Preprints", fmt(summary["total_preprints"]))
    r2c3.metric("Total Public File Count", fmt(summary["total_files"]))
    r2c4.metric(
        "Total Storage in GB",
        fmt(summary["total_storage_gb"], fmt_str="{:,.1f}"),
    )

    st.markdown("---")

    a1, a2, a3 = st.columns(3)

    with a1:
        st.markdown("#### Total Users by Department")
        if "department" in users_raw.columns:
            dept_counts = (
                users_raw["department"]
                .fillna("Unknown")
                .value_counts()
            )
            labels = dept_counts.index.tolist()
            values = dept_counts.values.tolist()
        else:
            labels, values = [], []
        donut_chart(labels, values, title="Total Users by Department")

    with a2:
        st.markdown("#### Public vs Private Projects")
        proj_labels, proj_values = [], []
        if "visibility" in projects_raw.columns:
            vis_counts = (
                projects_raw["visibility"].fillna("Unknown").value_counts()
            )
            proj_labels = vis_counts.index.tolist()
            proj_values = vis_counts.values.tolist()
        donut_chart(proj_labels, proj_values, title="Public vs Private Projects")

    with a3:
        st.markdown("#### Public vs Embargoed Registrations")
        reg_labels, reg_values = [], []
        if "visibility" in regs_raw.columns:
            reg_vis = (
                regs_raw["visibility"].fillna("Unknown").value_counts()
            )
            reg_labels = reg_vis.index.tolist()
            reg_values = reg_vis.values.tolist()
        donut_chart(reg_labels, reg_values, title="Public vs Embargoed Registrations")

    b1, b2, b3 = st.columns(3)

    with b1:
        labels = []
        values = []
        if summary["total_projects"] is not None:
            labels.append("Projects")
            values.append(summary["total_projects"])
        if summary["total_regs"] is not None:
            labels.append("Registrations")
            values.append(summary["total_regs"])
        if summary["total_preprints"] is not None:
            labels.append("Preprints")
            values.append(summary["total_preprints"])
        if summary["total_files"] is not None:
            labels.append("Files")
            values.append(summary["total_files"])
        st.markdown("#### Total OSF Objects")
        donut_chart(labels, values, title="Total OSF Objects")

    with b2:
        all_licenses = []
        for df_ in (projects_raw, regs_raw, preprints_raw):
            if "rights.name" in df_.columns:
                all_licenses.append(df_["rights.name"])
        if all_licenses:
            license_series = pd.concat(all_licenses, ignore_index=True).value_counts()
        else:
            license_series = pd.Series(dtype=int)
        bar_chart_from_series(license_series, "Top 10 Licenses")

    with b3:
        addons_counts = None
        try:
            addons_csv = DATA_DIR / "summary_addons.csv"
            if addons_csv.exists():
                df_addons = pd.read_csv(addons_csv)
                if {"addon", "count"} <= set(df_addons.columns):
                    addons_counts = (
                        df_addons.set_index("addon")["count"].astype(int)
                    )
        except Exception:
            addons_counts = None

        if addons_counts is None:
            if "hasOsfAddon.prefLabel" in projects_raw.columns:
                addons_counts = (
                    projects_raw["hasOsfAddon.prefLabel"]
                    .dropna()
                    .value_counts()
                )
            else:
                addons_counts = pd.Series(dtype=int)

        bar_chart_from_series(addons_counts, "Top 10 Add-ons")

    c1, _, _ = st.columns([1.2, 1, 1])

    with c1:
        region_series_parts = []
        for df_ in (projects_raw, regs_raw):
            if "storageRegion.prefLabel" in df_.columns:
                region_series_parts.append(df_["storageRegion.prefLabel"])
        if region_series_parts:
            region_counts = (
                pd.concat(region_series_parts, ignore_index=True)
                .dropna()
                .value_counts()
            )
        else:
            region_counts = pd.Series(dtype=int)

        labels = region_counts.index.tolist()
        values = region_counts.values.tolist()

        st.markdown("#### Top Storage Regions")
        donut_chart(labels, values, title="Top Storage Regions")


# ---------------------- USERS ------------------------ #
with tab_users:
    st.subheader("Users")

    if "users_show_customize" not in st.session_state:
        st.session_state["users_show_customize"] = False

    ctop1, ctop2, ctop3 = st.columns([4, 1, 1])
    count_placeholder = ctop1.empty()

    def toggle_users_customize():
        st.session_state["users_show_customize"] = not st.session_state[
            "users_show_customize"
        ]

    with ctop2:
        st.button(
            "Customize",
            key="users_customize_btn",
            on_click=toggle_users_customize,
            use_container_width=True,
        )

    # Filters row
    st.markdown("##### Filters")
    ucol1, ucol2 = st.columns([2, 1])

    with ucol1:
        dept_options = (
            sorted(users_raw["department"].dropna().unique().tolist())
            if "department" in users_raw.columns
            else []
        )
        if dept_options:
            users_depts = st.multiselect(
                "Department",
                options=dept_options,
                default=[],
                key="users_depts",
            )
        else:
            users_depts = []
    with ucol2:
        if "orcid_id" in users_raw.columns:
            users_orcid = st.selectbox(
                "ORCID",
                ["All", "Has ORCID", "No ORCID"],
                index=0,
                key="users_orcid",
            )
        else:
            users_orcid = "All"

    users = users_raw.copy()
    if users_depts:
        users = users[users["department"].isin(users_depts)]
    if users_orcid != "All" and "orcid_id" in users.columns:
        if users_orcid == "Has ORCID":
            users = users[
                users["orcid_id"].notna()
                & (users["orcid_id"].astype(str).str.strip() != "")
            ]
        else:
            users = users[
                users["orcid_id"].isna()
                | (users["orcid_id"].astype(str).str.strip() == "")
            ]

    count_placeholder.markdown(f"**{len(users):,} Total Users**")

    if users.empty:
        st.info("No users match the current filters.")
    else:
        df = users.copy()
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

        all_cols = [
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
        all_existing = [c for c in all_cols if c in display.columns]

        if st.session_state["users_show_customize"]:
            st.markdown('<div class="customize-box">', unsafe_allow_html=True)
            selected_cols = st.multiselect(
                "Show columns",
                options=all_existing,
                default=all_existing,
                key="users_columns",
            )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            selected_cols = all_existing

        display = display[selected_cols]

        # Download button using current filters/columns
        csv_bytes = display.to_csv(index=False).encode("utf-8")
        with ctop3:
            st.download_button(
                "Download CSV",
                key="users_download_btn",
                data=csv_bytes,
                file_name="users_filtered.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.markdown("#### Results")
        page_df, total_rows = get_page_df(display, page_key="users_page", page_size=10)
        st.dataframe(page_df, hide_index=True)
        render_pagination_controls("users_page", total_rows, page_size=10)


# ---------------------- PROJECTS --------------------- #
with tab_projects:
    st.subheader("Projects")

    if "projects_show_filters" not in st.session_state:
        st.session_state["projects_show_filters"] = False
    if "projects_show_customize" not in st.session_state:
        st.session_state["projects_show_customize"] = False

    def toggle_projects_filters():
        st.session_state["projects_show_filters"] = not st.session_state[
            "projects_show_filters"
        ]

    def toggle_projects_customize():
        st.session_state["projects_show_customize"] = not st.session_state[
            "projects_show_customize"
        ]

    top_left_col, top_filters, top_customize, top_download = st.columns([4, 1, 1, 1])
    count_placeholder = top_left_col.empty()

    with top_filters:
        st.button(
            "Filters",
            key="projects_filters_btn",
            on_click=toggle_projects_filters,
            use_container_width=True,
        )
    with top_customize:
        st.button(
            "Customize",
            key="projects_customize_btn",
            on_click=toggle_projects_customize,
            use_container_width=True,
        )

    show_filters = st.session_state["projects_show_filters"]

    if show_filters:
        main_col, filter_col = st.columns([4, 2])
    else:
        main_col = st.container()
        filter_col = None

    creators_selected = []
    licenses_selected = []
    regions_selected = []
    funders_selected = []
    subjects_selected = []
    resource_types_selected = []
    institutions_selected = []
    collections_selected = []

    if filter_col is not None:
        with filter_col:
            st.markdown("#### Filter By")

            # Creator
            if "creator.name" in projects_raw.columns:
                with st.expander("Creator", expanded=False):
                    creator_options = sorted(
                        projects_raw["creator.name"].dropna().unique().tolist()
                    )
                    creators_selected = st.multiselect(
                        "Creator name",
                        options=creator_options,
                        default=[],
                        key="projects_creator_filter",
                    )

            # Date created (year)
            year_selected = None
            if "dateCreated" in projects_raw.columns:
                with st.expander("Date created", expanded=False):
                    years = (
                        pd.to_datetime(projects_raw["dateCreated"], errors="coerce")
                        .dt.year.dropna()
                        .astype(int)
                        .unique()
                        .tolist()
                    )
                    years = sorted(years)
                    options = ["All years"] + [str(y) for y in years]
                    choice = st.selectbox(
                        "Year created",
                        options=options,
                        index=0,
                        key="projects_year_filter",
                    )
                    if choice != "All years":
                        year_selected = int(choice)

            # Funder
            if "funder.name" in projects_raw.columns:
                with st.expander("Funder", expanded=False):
                    funder_options = sorted(
                        projects_raw["funder.name"].dropna().unique().tolist()
                    )
                    funders_selected = st.multiselect(
                        "Funder name",
                        options=funder_options,
                        default=[],
                        key="projects_funder_filter",
                    )

            # Subject
            subj_col = next(
                (c for c in projects_raw.columns if "subject" in c.lower()),
                None,
            )
            if subj_col:
                with st.expander("Subject", expanded=False):
                    subj_options = sorted(
                        projects_raw[subj_col].dropna().unique().tolist()
                    )
                    subjects_selected = st.multiselect(
                        "Subject",
                        options=subj_options,
                        default=[],
                        key="projects_subject_filter",
                    )

            # License
            if "rights.name" in projects_raw.columns:
                with st.expander("License", expanded=False):
                    license_options = sorted(
                        projects_raw["rights.name"].dropna().unique().tolist()
                    )
                    licenses_selected = st.multiselect(
                        "License",
                        options=license_options,
                        default=[],
                        key="projects_license_filter",
                    )

            # Resource type
            if "resourceNature.displayLabel" in projects_raw.columns:
                with st.expander("Resource type", expanded=False):
                    rt_options = sorted(
                        projects_raw["resourceNature.displayLabel"]
                        .dropna()
                        .unique()
                        .tolist()
                    )
                    resource_types_selected = st.multiselect(
                        "Resource type",
                        options=rt_options,
                        default=[],
                        key="projects_resource_type_filter",
                    )

            # Institution
            inst_col_raw = next(
                (
                    c
                    for c in projects_raw.columns
                    if "institution" in c.lower() and "name" in c.lower()
                ),
                None,
            )
            if inst_col_raw:
                with st.expander("Institution", expanded=False):
                    inst_options = sorted(
                        projects_raw[inst_col_raw].dropna().unique().tolist()
                    )
                    institutions_selected = st.multiselect(
                        "Institution",
                        options=inst_options,
                        default=[],
                        key="projects_institution_filter",
                    )

            # Is part of collection
            coll_col_raw = next(
                (c for c in projects_raw.columns if "collection" in c.lower()),
                None,
            )
            if coll_col_raw:
                with st.expander("Is part of collection", expanded=False):
                    coll_options = sorted(
                        projects_raw[coll_col_raw].dropna().unique().tolist()
                    )
                    collections_selected = st.multiselect(
                        "Collection",
                        options=coll_options,
                        default=[],
                        key="projects_collection_filter",
                    )

            # Storage region
            if "storageRegion.prefLabel" in projects_raw.columns:
                with st.expander("Storage region", expanded=False):
                    region_options = sorted(
                        projects_raw["storageRegion.prefLabel"]
                        .dropna()
                        .unique()
                        .tolist()
                    )
                    regions_selected = st.multiselect(
                        "Storage region",
                        options=region_options,
                        default=[],
                        key="projects_region_filter",
                    )

    projects = projects_raw.copy()

    # Apply filters (AND behavior)
    if creators_selected and "creator.name" in projects.columns:
        def has_all_creators(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return all(c in text for c in creators_selected)

        projects = projects[projects["creator.name"].apply(has_all_creators)]

    if "projects_year_filter" in st.session_state and "dateCreated" in projects.columns:
        year_choice = st.session_state.get("projects_year_filter")
        if year_choice and year_choice != "All years":
            year_val = int(year_choice)
            years = pd.to_datetime(projects["dateCreated"], errors="coerce").dt.year
            projects = projects[years == year_val]

    if licenses_selected and "rights.name" in projects.columns:
        projects = projects[projects["rights.name"].isin(licenses_selected)]

    if regions_selected and "storageRegion.prefLabel" in projects.columns:
        projects = projects[projects["storageRegion.prefLabel"].isin(regions_selected)]

    if funders_selected and "funder.name" in projects.columns:
        projects = projects[projects["funder.name"].isin(funders_selected)]

    subj_col_proj = next(
        (c for c in projects.columns if "subject" in c.lower()),
        None,
    )
    if subjects_selected and subj_col_proj in projects.columns:
        projects = projects[projects[subj_col_proj].isin(subjects_selected)]

    if resource_types_selected and "resourceNature.displayLabel" in projects.columns:
        projects = projects[
            projects["resourceNature.displayLabel"].isin(resource_types_selected)
        ]

    inst_col = next(
        (
            c
            for c in projects.columns
            if "institution" in c.lower() and "name" in c.lower()
        ),
        None,
    )
    if institutions_selected and inst_col in projects.columns:
        projects = projects[projects[inst_col].isin(institutions_selected)]

    coll_col = next(
        (c for c in projects.columns if "collection" in c.lower()),
        None,
    )
    if collections_selected and coll_col in projects.columns:
        projects = projects[projects[coll_col].isin(collections_selected)]

    count_placeholder.markdown(f"**{len(projects):,} Total Projects**")

    with main_col:
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

            all_cols = [
                "Title",
                "OSF Link",
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
            ]
            all_existing = [c for c in all_cols if c in display.columns]

            if st.session_state["projects_show_customize"]:
                st.markdown('<div class="customize-box">', unsafe_allow_html=True)
                selected_cols = st.multiselect(
                    "Show columns",
                    options=all_existing,
                    default=all_existing,
                    key="projects_columns",
                )
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                selected_cols = all_existing

            display = display[selected_cols]

            csv_bytes = display.to_csv(index=False).encode("utf-8")
            with top_download:
                st.download_button(
                    "Download CSV",
                    key="projects_download_btn",
                    data=csv_bytes,
                    file_name="projects_filtered.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            st.markdown("#### Results")
            page_df, total_rows = get_page_df(
                display, page_key="projects_page", page_size=10
            )
            st.dataframe(page_df, hide_index=True)
            render_pagination_controls("projects_page", total_rows, page_size=10)


# ---------------------- REGISTRATIONS ---------------- #
with tab_regs:
    st.subheader("Registrations")

    if "regs_show_filters" not in st.session_state:
        st.session_state["regs_show_filters"] = False
    if "regs_show_customize" not in st.session_state:
        st.session_state["regs_show_customize"] = False

    def toggle_regs_filters():
        st.session_state["regs_show_filters"] = not st.session_state[
            "regs_show_filters"
        ]

    def toggle_regs_customize():
        st.session_state["regs_show_customize"] = not st.session_state[
            "regs_show_customize"
        ]

    top_left_col, top_filters, top_customize, top_download = st.columns([4, 1, 1, 1])
    regs_count_placeholder = top_left_col.empty()

    with top_filters:
        st.button(
            "Filters",
            key="regs_filters_btn",
            on_click=toggle_regs_filters,
            use_container_width=True,
        )
    with top_customize:
        st.button(
            "Customize",
            key="regs_customize_btn",
            on_click=toggle_regs_customize,
            use_container_width=True,
        )

    show_filters = st.session_state["regs_show_filters"]

    if show_filters:
        main_col, filter_col = st.columns([4, 2])
    else:
        main_col = st.container()
        filter_col = None

    creators_selected = []
    licenses_selected = []
    regions_selected = []
    schemas_selected = []
    institutions_selected = []

    if filter_col is not None:
        with filter_col:
            st.markdown("#### Filter By")

            if "creator.name" in regs_raw.columns:
                with st.expander("Creator", expanded=False):
                    creator_options = sorted(
                        regs_raw["creator.name"].dropna().unique().tolist()
                    )
                    creators_selected = st.multiselect(
                        "Creator name",
                        options=creator_options,
                        default=[],
                        key="regs_creator_filter",
                    )

            year_selected = None
            if "dateCreated" in regs_raw.columns:
                with st.expander("Date created", expanded=False):
                    years = (
                        pd.to_datetime(regs_raw["dateCreated"], errors="coerce")
                        .dt.year.dropna()
                        .astype(int)
                        .unique()
                        .tolist()
                    )
                    years = sorted(years)
                    options = ["All years"] + [str(y) for y in years]
                    choice = st.selectbox(
                        "Year created",
                        options=options,
                        index=0,
                        key="regs_year_filter",
                    )
                    if choice != "All years":
                        year_selected = int(choice)

            if "rights.name" in regs_raw.columns:
                with st.expander("License", expanded=False):
                    license_options = sorted(
                        regs_raw["rights.name"].dropna().unique().tolist()
                    )
                    licenses_selected = st.multiselect(
                        "License",
                        options=license_options,
                        default=[],
                        key="regs_license_filter",
                    )

            if "storageRegion.prefLabel" in regs_raw.columns:
                with st.expander("Storage region", expanded=False):
                    region_options = sorted(
                        regs_raw["storageRegion.prefLabel"]
                        .dropna()
                        .unique()
                        .tolist()
                    )
                    regions_selected = st.multiselect(
                        "Storage region",
                        options=region_options,
                        default=[],
                        key="regs_region_filter",
                    )

            if "conformsTo.title" in regs_raw.columns:
                with st.expander("Registration schema", expanded=False):
                    schema_options = sorted(
                        regs_raw["conformsTo.title"].dropna().unique().tolist()
                    )
                    schemas_selected = st.multiselect(
                        "Schema",
                        options=schema_options,
                        default=[],
                        key="regs_schema_filter",
                    )

            inst_col_raw = next(
                (
                    c
                    for c in regs_raw.columns
                    if "institution" in c.lower() and "name" in c.lower()
                ),
                None,
            )
            if inst_col_raw:
                with st.expander("Institution", expanded=False):
                    inst_options = sorted(
                        regs_raw[inst_col_raw].dropna().unique().tolist()
                    )
                    institutions_selected = st.multiselect(
                        "Institution",
                        options=inst_options,
                        default=[],
                        key="regs_institution_filter",
                    )

    regs = regs_raw.copy()

    if creators_selected and "creator.name" in regs.columns:
        def has_all_creators(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return all(c in text for c in creators_selected)

        regs = regs[regs["creator.name"].apply(has_all_creators)]

    if "regs_year_filter" in st.session_state and "dateCreated" in regs.columns:
        year_choice = st.session_state.get("regs_year_filter")
        if year_choice and year_choice != "All years":
            year_val = int(year_choice)
            years = pd.to_datetime(regs["dateCreated"], errors="coerce").dt.year
            regs = regs[years == year_val]

    if licenses_selected and "rights.name" in regs.columns:
        regs = regs[regs["rights.name"].isin(licenses_selected)]

    if regions_selected and "storageRegion.prefLabel" in regs.columns:
        regs = regs[regs["storageRegion.prefLabel"].isin(regions_selected)]

    if schemas_selected and "conformsTo.title" in regs.columns:
        regs = regs[regs["conformsTo.title"].isin(schemas_selected)]

    inst_col = next(
        (
            c
            for c in regs.columns
            if "institution" in c.lower() and "name" in c.lower()
        ),
        None,
    )
    if institutions_selected and inst_col in regs.columns:
        regs = regs[regs[inst_col].isin(institutions_selected)]

    regs_count_placeholder.markdown(f"**{len(regs):,} Total Registrations**")

    with main_col:
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

            all_cols = [
                "Title",
                "OSF Link",
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
            ]
            all_existing = [c for c in all_cols if c in display.columns]

            if st.session_state["regs_show_customize"]:
                st.markdown('<div class="customize-box">', unsafe_allow_html=True)
                selected_cols = st.multiselect(
                    "Show columns",
                    options=all_existing,
                    default=all_existing,
                    key="regs_columns",
                )
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                selected_cols = all_existing

            display = display[selected_cols]

            csv_bytes = display.to_csv(index=False).encode("utf-8")
            with top_download:
                st.download_button(
                    "Download CSV",
                    key="regs_download_btn",
                    data=csv_bytes,
                    file_name="registrations_filtered.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            st.markdown("#### Results")
            page_df, total_rows = get_page_df(
                display, page_key="regs_page", page_size=10
            )
            st.dataframe(page_df, hide_index=True)
            render_pagination_controls("regs_page", total_rows, page_size=10)


# ---------------------- PREPRINTS -------------------- #
with tab_preprints:
    st.subheader("Preprints")

    if "preprints_show_filters" not in st.session_state:
        st.session_state["preprints_show_filters"] = False
    if "preprints_show_customize" not in st.session_state:
        st.session_state["preprints_show_customize"] = False

    def toggle_preprints_filters():
        st.session_state["preprints_show_filters"] = not st.session_state[
            "preprints_show_filters"
        ]

    def toggle_preprints_customize():
        st.session_state["preprints_show_customize"] = not st.session_state[
            "preprints_show_customize"
        ]

    top_left_col, top_filters, top_customize, top_download = st.columns([4, 1, 1, 1])
    preprints_count_placeholder = top_left_col.empty()

    with top_filters:
        st.button(
            "Filters",
            key="preprints_filters_btn",
            on_click=toggle_preprints_filters,
            use_container_width=True,
        )
    with top_customize:
        st.button(
            "Customize",
            key="preprints_customize_btn",
            on_click=toggle_preprints_customize,
            use_container_width=True,
        )

    show_filters = st.session_state["preprints_show_filters"]

    if show_filters:
        main_col, filter_col = st.columns([4, 2])
    else:
        main_col = st.container()
        filter_col = None

    creators_selected = []
    subjects_selected = []
    licenses_selected = []

    if filter_col is not None:
        with filter_col:
            st.markdown("#### Filter By")

            if "creator.name" in preprints_raw.columns:
                with st.expander("Creator", expanded=False):
                    creator_options = sorted(
                        preprints_raw["creator.name"].dropna().unique().tolist()
                    )
                    creators_selected = st.multiselect(
                        "Creator name",
                        options=creator_options,
                        default=[],
                        key="preprints_creator_filter",
                    )

            year_selected = None
            if "dateCreated" in preprints_raw.columns:
                with st.expander("Date created", expanded=False):
                    years = (
                        pd.to_datetime(preprints_raw["dateCreated"], errors="coerce")
                        .dt.year.dropna()
                        .astype(int)
                        .unique()
                        .tolist()
                    )
                    years = sorted(years)
                    options = ["All years"] + [str(y) for y in years]
                    choice = st.selectbox(
                        "Year created",
                        options=options,
                        index=0,
                        key="preprints_year_filter",
                    )
                    if choice != "All years":
                        year_selected = int(choice)

            subj_col_raw = next(
                (c for c in preprints_raw.columns if "subject" in c.lower()),
                None,
            )
            if subj_col_raw:
                with st.expander("Subject", expanded=False):
                    subj_options = sorted(
                        preprints_raw[subj_col_raw].dropna().unique().tolist()
                    )
                    subjects_selected = st.multiselect(
                        "Subject",
                        options=subj_options,
                        default=[],
                        key="preprints_subject_filter",
                    )

            if "rights.name" in preprints_raw.columns:
                with st.expander("License", expanded=True):
                    license_options = sorted(
                        preprints_raw["rights.name"].dropna().unique().tolist()
                    )
                    licenses_selected = st.multiselect(
                        "License",
                        options=license_options,
                        default=[],
                        key="preprints_license_filter",
                    )

    preprints = preprints_raw.copy()

    if creators_selected and "creator.name" in preprints.columns:
        def has_all_creators(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return all(c in text for c in creators_selected)

        preprints = preprints[preprints["creator.name"].apply(has_all_creators)]

    if "preprints_year_filter" in st.session_state and "dateCreated" in preprints.columns:
        year_choice = st.session_state.get("preprints_year_filter")
        if year_choice and year_choice != "All years":
            year_val = int(year_choice)
            years = pd.to_datetime(preprints["dateCreated"], errors="coerce").dt.year
            preprints = preprints[years == year_val]

    if licenses_selected and "rights.name" in preprints.columns:
        preprints = preprints[preprints["rights.name"].isin(licenses_selected)]

    subj_col = next(
        (c for c in preprints.columns if "subject" in c.lower()),
        None,
    )
    if subjects_selected and subj_col in preprints.columns:
        preprints = preprints[preprints[subj_col].isin(subjects_selected)]

    preprints_count_placeholder.markdown(f"**{len(preprints):,} Total Preprints**")

    with main_col:
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
                    "creator.name": "Contributor name",
                    "usage.viewCount": "Views (last 30 days)",
                    "usage.downloadCount": "Downloads (last 30 days)",
                }
            )

            all_cols = [
                "Title",
                "OSF Link",
                "Created date",
                "Modified date",
                "DOI",
                "License",
                "Contributor name",
                "Views (last 30 days)",
                "Downloads (last 30 days)",
            ]
            all_existing = [c for c in all_cols if c in display.columns]

            if st.session_state["preprints_show_customize"]:
                st.markdown('<div class="customize-box">', unsafe_allow_html=True)
                selected_cols = st.multiselect(
                    "Show columns",
                    options=all_existing,
                    default=all_existing,
                    key="preprints_columns",
                )
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                selected_cols = all_existing

            display = display[selected_cols]

            csv_bytes = display.to_csv(index=False).encode("utf-8")
            with top_download:
                st.download_button(
                    "Download CSV",
                    key="preprints_download_btn",
                    data=csv_bytes,
                    file_name="preprints_filtered.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            # Only show row count, no average views metric
            st.metric("Preprints (rows)", fmt(len(display)))

            st.markdown("#### Results")
            page_df, total_rows = get_page_df(
                display, page_key="preprints_page", page_size=10
            )
            st.dataframe(page_df, hide_index=True)
            render_pagination_controls("preprints_page", total_rows, page_size=10)
