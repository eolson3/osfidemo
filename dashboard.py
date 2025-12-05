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

DATA_DIR = Path(__file__).parent
DATA_FILE = DATA_DIR / "osfi_dashboard_data_with_branding.csv"

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

    /* Compact customize dropdown-style box */
    .customize-box {
        background-color: #ffffff;
        border: 1px solid #d0d4da;
        border-radius: 8px;
        padding: 0.4rem 0.5rem 0.25rem 0.5rem;
        margin-top: 0.35rem;
        max-width: 260px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15);
    }
    .customize-box .stTextInput>div>div>input {
        font-size: 0.8rem;
        padding-top: 0.15rem;
        padding-bottom: 0.15rem;
    }
    .customize-box label {
        font-size: 0.85rem;
        padding: 0.1rem 0;
    }

    /* Hide sidebar completely */
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Hide AG Grid header menu & context menu so only sort-by-click remains */
    .ag-header-cell-menu-button,
    .ag-menu {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================
# DATA LOADING
# =====================================================

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


try:
    data = load_data(DATA_FILE)
except Exception as e:
    st.error(
        f"Error loading unified CSV: {e}\n\n"
        "Make sure osfi_dashboard_data_with_branding.csv is in the same directory as this app."
    )
    st.stop()

# Branding (same on every row; just grab first non-empty)
branding_name = (
    data.get("branding_institution_name", pd.Series([], dtype=str))
    .dropna()
    .astype(str)
)
branding_logo = (
    data.get("branding_institution_logo_url", pd.Series([], dtype=str))
    .dropna()
    .astype(str)
)

INSTITUTION_NAME = branding_name.iloc[0] if len(branding_name) else "OSF Institution [Demo]"
INSTITUTION_LOGO_URL = (
    branding_logo.iloc[0]
    if len(branding_logo)
    else "https://osf.io/static/img/cos-white.svg"
)

# Split by object_type
users_raw = data[data["object_type"] == "user"].copy()
projects_raw = data[data["object_type"] == "project"].copy()
regs_raw = data[data["object_type"] == "registration"].copy()
preprints_raw = data[data["object_type"] == "preprint"].copy()

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


def compute_summary_metrics(all_df, users_df, projects_df, regs_df, preprints_df):
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

    total_files = None
    if "public_file_count" in users_df.columns:
        total_files = pd.to_numeric(
            users_df["public_file_count"], errors="coerce"
        ).fillna(0).sum()

    total_storage_gb = None
    if "storage_bytes" in all_df.columns:
        total_storage_gb = (
            pd.to_numeric(all_df["storage_bytes"], errors="coerce")
            .fillna(0)
            .sum() / 1e9
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


def prepare_link_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "DOI" in df.columns:
        def to_doi_url(x):
            if isinstance(x, str):
                s = x.strip()
                if not s or s == "-":
                    return ""
                if s.startswith("http"):
                    return s
                return "https://doi.org/" + s
            return ""
        df["DOI"] = df["DOI"].apply(to_doi_url)
    return df


def build_link_column_config(df: pd.DataFrame):
    cfg = {}
    for col in df.columns:
        lower = col.lower()
        if col in ("OSF Link", "DOI") or "url" in lower or "link" in lower:
            cfg[col] = st.column_config.LinkColumn(col)
    return cfg


def customize_columns_box(all_existing, prefix: str):
    state_key = f"{prefix}_cols_state"
    if state_key not in st.session_state:
        st.session_state[state_key] = {c: True for c in all_existing}
    state = st.session_state[state_key]

    st.markdown('<div class="customize-box">', unsafe_allow_html=True)
    search = st.text_input("Show columns", key=f"{prefix}_col_search")
    search_lower = search.lower().strip()
    filtered = [c for c in all_existing if search_lower in c.lower()]

    for col in filtered:
        checked = st.checkbox(
            col,
            value=state.get(col, True),
            key=f"{prefix}_col_{col}",
        )
        state[col] = checked

    st.markdown("</div>", unsafe_allow_html=True)
    st.session_state[state_key] = state


def get_saved_columns(all_existing, prefix: str):
    state_key = f"{prefix}_cols_state"
    if state_key not in st.session_state:
        return all_existing
    state = st.session_state[state_key]
    selected_cols = [c for c in all_existing if state.get(c, True)]
    return selected_cols or all_existing


# =====================================================
# HEADER
# =====================================================

global_summary = compute_summary_metrics(
    data, users_raw, projects_raw, regs_raw, preprints_raw
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

    summary = global_summary

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

    # Users by department
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

    # Public vs Private projects
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

    # Public vs Embargoed regs
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
        # Licenses from projects + regs + preprints
        all_licenses = []
        for df_ in (projects_raw, regs_raw, preprints_raw):
            if "license_name" in df_.columns:
                all_licenses.append(df_["license_name"])
        if all_licenses:
            license_series = pd.concat(all_licenses, ignore_index=True).value_counts()
        else:
            license_series = pd.Series(dtype=int)
        bar_chart_from_series(license_series, "Top 10 Licenses")

    with b3:
        # Add-ons from projects (addon_names, possibly | separated)
        if "addon_names" in projects_raw.columns:
            addons_series = projects_raw["addon_names"].dropna().astype(str)
            # Split pipe-separated lists into individual values
            exploded = addons_series.str.split("|").explode().str.strip()
            addons_counts = exploded[exploded != ""].value_counts()
        else:
            addons_counts = pd.Series(dtype=int)

        bar_chart_from_series(addons_counts, "Top 10 Add-ons")

    c1, _, _ = st.columns([1.2, 1, 1])

    with c1:
        region_series_parts = []
        for df_ in (projects_raw, regs_raw):
            if "storage_region" in df_.columns:
                region_series_parts.append(df_["storage_region"])
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

    # Top row: count + customize + download
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
        if "storage_bytes" in df.columns:
            df["Total data stored on OSF (GB)"] = (
                pd.to_numeric(df["storage_bytes"], errors="coerce")
                .fillna(0) / 1e9
            )

        display = df.rename(
            columns={
                "name_or_title": "Name",
                "department": "Department",
                "orcid_id": "ORCID iD",
                "report_yearmonth": "Report month (YYYY-MM)",
                "month_last_login": "Month last login (YYYY-MM)",
                "month_last_active": "Month last active (YYYY-MM)",
                "public_projects": "Public projects",
                "private_projects": "Private projects",
                "public_registrations": "Public registrations",
                "embargoed_registrations": "Embargoed registrations",
                "published_preprints": "Published preprints",
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
            "Report month (YYYY-MM)",
            "Month last login (YYYY-MM)",
            "Month last active (YYYY-MM)",
        ]
        all_existing = [c for c in all_cols if c in display.columns]

        if st.session_state["users_show_customize"]:
            with ctop2:
                customize_columns_box(all_existing, "users")

        selected_cols = get_saved_columns(all_existing, "users")
        display = display[selected_cols]

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
        display_links = prepare_link_columns(display)
        page_df, total_rows = get_page_df(
            display_links, page_key="users_page", page_size=10
        )
        col_cfg = build_link_column_config(page_df)
        st.dataframe(page_df, hide_index=True, column_config=col_cfg)
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
            if "creator_names" in projects_raw.columns:
                with st.expander("Creator", expanded=False):
                    creator_options = sorted(
                        projects_raw["creator_names"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    creators_selected = st.multiselect(
                        "Creator name",
                        options=creator_options,
                        default=[],
                        key="projects_creator_filter",
                    )

            # Date created (year)
            if "created_date" in projects_raw.columns:
                with st.expander("Date created", expanded=False):
                    years = (
                        pd.to_datetime(projects_raw["created_date"], errors="coerce")
                        .dt.year.dropna()
                        .astype(int)
                        .unique()
                        .tolist()
                    )
                    years = sorted(years)
                    options = ["All years"] + [str(y) for y in years]
                    _ = st.selectbox(
                        "Year created",
                        options=options,
                        index=0,
                        key="projects_year_filter",
                    )

            # Funder
            if "funder_names" in projects_raw.columns:
                with st.expander("Funder", expanded=False):
                    funder_options = sorted(
                        projects_raw["funder_names"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    funders_selected = st.multiselect(
                        "Funder name",
                        options=funder_options,
                        default=[],
                        key="projects_funder_filter",
                    )

            # Subject
            if "subject_terms" in projects_raw.columns:
                with st.expander("Subject", expanded=False):
                    subj_options = sorted(
                        projects_raw["subject_terms"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    subjects_selected = st.multiselect(
                        "Subject",
                        options=subj_options,
                        default=[],
                        key="projects_subject_filter",
                    )

            # License
            if "license_name" in projects_raw.columns:
                with st.expander("License", expanded=False):
                    license_options = sorted(
                        projects_raw["license_name"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    licenses_selected = st.multiselect(
                        "License",
                        options=license_options,
                        default=[],
                        key="projects_license_filter",
                    )

            # Resource type
            if "resource_type" in projects_raw.columns:
                with st.expander("Resource type", expanded=False):
                    rt_options = sorted(
                        projects_raw["resource_type"]
                        .dropna()
                        .astype(str)
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
            if "institution_name" in projects_raw.columns:
                with st.expander("Institution", expanded=False):
                    inst_options = sorted(
                        projects_raw["institution_name"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    institutions_selected = st.multiselect(
                        "Institution",
                        options=inst_options,
                        default=[],
                        key="projects_institution_filter",
                    )

            # Is part of collection
            if "collection_name" in projects_raw.columns:
                with st.expander("Is part of collection", expanded=False):
                    coll_options = sorted(
                        projects_raw["collection_name"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    collections_selected = st.multiselect(
                        "Collection",
                        options=coll_options,
                        default=[],
                        key="projects_collection_filter",
                    )

            # Storage region
            if "storage_region" in projects_raw.columns:
                with st.expander("Storage region", expanded=False):
                    region_options = sorted(
                        projects_raw["storage_region"]
                        .dropna()
                        .astype(str)
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

    # AND behavior for creators
    if creators_selected and "creator_names" in projects.columns:
        def has_all_creators(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return all(c in text for c in creators_selected)

        projects = projects[projects["creator_names"].apply(has_all_creators)]

    if "projects_year_filter" in st.session_state and "created_date" in projects.columns:
        year_choice = st.session_state.get("projects_year_filter")
        if year_choice and year_choice != "All years":
            year_val = int(year_choice)
            years = pd.to_datetime(projects["created_date"], errors="coerce").dt.year
            projects = projects[years == year_val]

    if licenses_selected and "license_name" in projects.columns:
        projects = projects[projects["license_name"].isin(licenses_selected)]

    if regions_selected and "storage_region" in projects.columns:
        projects = projects[projects["storage_region"].isin(regions_selected)]

    if funders_selected and "funder_names" in projects.columns:
        projects = projects[projects["funder_names"].isin(funders_selected)]

    if subjects_selected and "subject_terms" in projects.columns:
        projects = projects[projects["subject_terms"].isin(subjects_selected)]

    if resource_types_selected and "resource_type" in projects.columns:
        projects = projects[projects["resource_type"].isin(resource_types_selected)]

    if institutions_selected and "institution_name" in projects.columns:
        projects = projects[projects["institution_name"].isin(institutions_selected)]

    if collections_selected and "collection_name" in projects.columns:
        projects = projects[projects["collection_name"].isin(collections_selected)]

    count_placeholder.markdown(f"**{len(projects):,} Total Projects**")

    with main_col:
        if projects.empty:
            st.info("No projects match the current filters.")
        else:
            df = projects.copy()
            if "storage_bytes" in df.columns:
                df["Total data stored on OSF (GB)"] = (
                    pd.to_numeric(df["storage_bytes"], errors="coerce")
                    .fillna(0) / 1e9
                )

            display = df.rename(
                columns={
                    "name_or_title": "Title",
                    "osf_link": "OSF Link",
                    "created_date": "Created date",
                    "modified_date": "Modified date",
                    "doi": "DOI",
                    "storage_region": "Storage region",
                    "creator_names": "Creator(s)",
                    "view_count_30d": "Views (last 30 days)",
                    "resource_type": "Resource type",
                    "license_name": "License",
                    "addon_names": "Add-ons",
                    "funder_names": "Funder name",
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
                with top_customize:
                    customize_columns_box(all_existing, "projects")

            selected_cols = get_saved_columns(all_existing, "projects")
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
            display_links = prepare_link_columns(display)
            page_df, total_rows = get_page_df(
                display_links, page_key="projects_page", page_size=10
            )
            col_cfg = build_link_column_config(page_df)
            st.dataframe(page_df, hide_index=True, column_config=col_cfg)
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

            if "creator_names" in regs_raw.columns:
                with st.expander("Creator", expanded=False):
                    creator_options = sorted(
                        regs_raw["creator_names"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    creators_selected = st.multiselect(
                        "Creator name",
                        options=creator_options,
                        default=[],
                        key="regs_creator_filter",
                    )

            if "created_date" in regs_raw.columns:
                with st.expander("Date created", expanded=False):
                    years = (
                        pd.to_datetime(regs_raw["created_date"], errors="coerce")
                        .dt.year.dropna()
                        .astype(int)
                        .unique()
                        .tolist()
                    )
                    years = sorted(years)
                    options = ["All years"] + [str(y) for y in years]
                    _ = st.selectbox(
                        "Year created",
                        options=options,
                        index=0,
                        key="regs_year_filter",
                    )

            if "license_name" in regs_raw.columns:
                with st.expander("License", expanded=False):
                    license_options = sorted(
                        regs_raw["license_name"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    licenses_selected = st.multiselect(
                        "License",
                        options=license_options,
                        default=[],
                        key="regs_license_filter",
                    )

            if "storage_region" in regs_raw.columns:
                with st.expander("Storage region", expanded=False):
                    region_options = sorted(
                        regs_raw["storage_region"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    regions_selected = st.multiselect(
                        "Storage region",
                        options=region_options,
                        default=[],
                        key="regs_region_filter",
                    )

            if "registration_schema_title" in regs_raw.columns:
                with st.expander("Registration schema", expanded=False):
                    schema_options = sorted(
                        regs_raw["registration_schema_title"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    schemas_selected = st.multiselect(
                        "Schema",
                        options=schema_options,
                        default=[],
                        key="regs_schema_filter",
                    )

            if "institution_name" in regs_raw.columns:
                with st.expander("Institution", expanded=False):
                    inst_options = sorted(
                        regs_raw["institution_name"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    institutions_selected = st.multiselect(
                        "Institution",
                        options=inst_options,
                        default=[],
                        key="regs_institution_filter",
                    )

    regs = regs_raw.copy()

    if creators_selected and "creator_names" in regs.columns:
        def has_all_creators(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return all(c in text for c in creators_selected)

        regs = regs[regs["creator_names"].apply(has_all_creators)]

    if "regs_year_filter" in st.session_state and "created_date" in regs.columns:
        year_choice = st.session_state.get("regs_year_filter")
        if year_choice and year_choice != "All years":
            year_val = int(year_choice)
            years = pd.to_datetime(regs["created_date"], errors="coerce").dt.year
            regs = regs[years == year_val]

    if licenses_selected and "license_name" in regs.columns:
        regs = regs[regs["license_name"].isin(licenses_selected)]

    if regions_selected and "storage_region" in regs.columns:
        regs = regs[regs["storage_region"].isin(regions_selected)]

    if schemas_selected and "registration_schema_title" in regs.columns:
        regs = regs[regs["registration_schema_title"].isin(schemas_selected)]

    if institutions_selected and "institution_name" in regs.columns:
        regs = regs[regs["institution_name"].isin(institutions_selected)]

    regs_count_placeholder.markdown(f"**{len(regs):,} Total Registrations**")

    with main_col:
        if regs.empty:
            st.info("No registrations match the current filters.")
        else:
            df = regs.copy()
            if "storage_bytes" in df.columns:
                df["Total data stored on OSF (GB)"] = (
                    pd.to_numeric(df["storage_bytes"], errors="coerce")
                    .fillna(0) / 1e9
                )

            display = df.rename(
                columns={
                    "name_or_title": "Title",
                    "osf_link": "OSF Link",
                    "created_date": "Created date",
                    "modified_date": "Modified date",
                    "doi": "DOI",
                    "storage_region": "Storage region",
                    "creator_names": "Creator(s)",
                    "view_count_30d": "Views (last 30 days)",
                    "resource_type": "Resource type",
                    "license_name": "License",
                    "funder_names": "Funder name",
                    "registration_schema_title": "Registration schema",
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
                with top_customize:
                    customize_columns_box(all_existing, "regs")

            selected_cols = get_saved_columns(all_existing, "regs")
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
            display_links = prepare_link_columns(display)
            page_df, total_rows = get_page_df(
                display_links, page_key="regs_page", page_size=10
            )
            col_cfg = build_link_column_config(page_df)
            st.dataframe(page_df, hide_index=True, column_config=col_cfg)
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

            if "creator_names" in preprints_raw.columns:
                with st.expander("Creator", expanded=False):
                    creator_options = sorted(
                        preprints_raw["creator_names"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    creators_selected = st.multiselect(
                        "Creator name",
                        options=creator_options,
                        default=[],
                        key="preprints_creator_filter",
                    )

            if "created_date" in preprints_raw.columns:
                with st.expander("Date created", expanded=False):
                    years = (
                        pd.to_datetime(preprints_raw["created_date"], errors="coerce")
                        .dt.year.dropna()
                        .astype(int)
                        .unique()
                        .tolist()
                    )
                    years = sorted(years)
                    options = ["All years"] + [str(y) for y in years]
                    _ = st.selectbox(
                        "Year created",
                        options=options,
                        index=0,
                        key="preprints_year_filter",
                    )

            if "subject_terms" in preprints_raw.columns:
                with st.expander("Subject", expanded=False):
                    subj_options = sorted(
                        preprints_raw["subject_terms"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    subjects_selected = st.multiselect(
                        "Subject",
                        options=subj_options,
                        default=[],
                        key="preprints_subject_filter",
                    )

            if "license_name" in preprints_raw.columns:
                with st.expander("License", expanded=True):
                    license_options = sorted(
                        preprints_raw["license_name"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    licenses_selected = st.multiselect(
                        "License",
                        options=license_options,
                        default=[],
                        key="preprints_license_filter",
                    )

    preprints = preprints_raw.copy()

    if creators_selected and "creator_names" in preprints.columns:
        def has_all_creators(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return all(c in text for c in creators_selected)

        preprints = preprints[preprints["creator_names"].apply(has_all_creators)]

    if "preprints_year_filter" in st.session_state and "created_date" in preprints.columns:
        year_choice = st.session_state.get("preprints_year_filter")
        if year_choice and year_choice != "All years":
            year_val = int(year_choice)
            years = pd.to_datetime(preprints["created_date"], errors="coerce").dt.year
            preprints = preprints[years == year_val]

    if licenses_selected and "license_name" in preprints.columns:
        preprints = preprints[preprints["license_name"].isin(licenses_selected)]

    if subjects_selected and "subject_terms" in preprints.columns:
        preprints = preprints[preprints["subject_terms"].isin(subjects_selected)]

    preprints_count_placeholder.markdown(f"**{len(preprints):,} Total Preprints**")

    with main_col:
        if preprints.empty:
            st.info("No preprints match the current filters.")
        else:
            df = preprints.copy()
            display = df.rename(
                columns={
                    "name_or_title": "Title",
                    "osf_link": "OSF Link",
                    "created_date": "Created date",
                    "modified_date": "Modified date",
                    "doi": "DOI",
                    "license_name": "License",
                    "creator_names": "Contributor name",
                    "view_count_30d": "Views (last 30 days)",
                    "download_count_30d": "Downloads (last 30 days)",
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
                with top_customize:
                    customize_columns_box(all_existing, "preprints")

            selected_cols = get_saved_columns(all_existing, "preprints")
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

            st.metric("Preprints (rows)", fmt(len(display)))

            st.markdown("#### Results")
            display_links = prepare_link_columns(display)
            page_df, total_rows = get_page_df(
                display_links, page_key="preprints_page", page_size=10
            )
            col_cfg = build_link_column_config(page_df)
            st.dataframe(page_df, hide_index=True, column_config=col_cfg)
            render_pagination_controls("preprints_page", total_rows, page_size=10)
