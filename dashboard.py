import math
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
from streamlit.components.v1 import html  # <- add this line
import pandas as pd
# ... the rest of your imports


# -----------------------------------------------------------------------------
# Basic config
# -----------------------------------------------------------------------------

DATA_FILE = Path(__file__).parent / "osfi_dashboard_data_with_summary_and_branding.csv"

st.set_page_config(
    page_title="OSF Institutions Dashboard (Demo)",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Styling – OSF-ish look & feel
# -----------------------------------------------------------------------------

OSF_COLORS = {
    "navy": "#092A47",        # main text / nav
    "light_blue": "#E8F1FB",  # header background
    "accent": "#FF4B4B",      # active tab underline
    "border": "#E2E8F0",      # card & table borders
    "body_bg": "#F5F7FB",     # page background
    "metric_bg": "#F3F7FD",
}

def inject_osf_css() -> None:
    """Inject global CSS so the app looks closer to the OSF dashboards.

    We use components.html so the <style> block is guaranteed to land in <head>.
    """
    css = """
    <style>
    /* PAGE BACKGROUND */
    .stApp, .stAppViewContainer, .block-container {
        background-color: #F5F7FB;
    }

    .block-container {
        padding-top: 0.75rem !important;
        padding-bottom: 2rem !important;
    }

    /* HEADER BAR (logo + title area) */
    .osf-header {
        background: #E8F1FB;
        border-bottom: 1px solid #E2E8F0;
        padding: 0.75rem 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
    }

    .osf-header-topline {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .osf-header-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #092A47;
    }

    .osf-header-subtitle {
        font-size: 0.9rem;
        color: #3B4A5A;
    }

    /* TOP NAV TABS (Summary / Users / Projects / ...) */
    .stTabs [role="tablist"] {
        border-bottom: 1px solid #E2E8F0;
        padding-left: 1.5rem;
        gap: 1.5rem;
    }

    .stTabs [role="tab"] {
        font-weight: 600;
        font-size: 0.95rem;
        color: #092A47;
        background: transparent;
        padding: 0.6rem 0.2rem;
        border-radius: 0;
        border: none;
        box-shadow: none;
    }

    .stTabs [role="tab"]:focus-visible {
        outline: none;
        box-shadow: none;
    }

    .stTabs [role="tab"][aria-selected="true"] {
        border-bottom: 3px solid #FF4B4B;  /* red active underline */
    }

    /* SUMMARY METRIC CARDS */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-radius: 18px;
        padding: 1.5rem 1.75rem;
        border: 1px solid #E2E8F0;
    }

    [data-testid="stMetric"] > div > div:nth-child(1) {
        color: #4A5568;
        font-size: 0.85rem;
        font-weight: 500;
    }

    [data-testid="stMetric"] > div > div:nth-child(2) {
        color: #092A47;
        font-size: 1.6rem;
        font-weight: 700;
    }

    /* GENERIC CARD WRAPPER (around charts) */
    .osf-card {
        background: #FFFFFF;
        border-radius: 18px;
        border: 1px solid #E2E8F0;
        padding: 1rem 1.25rem 1.25rem 1.25rem;
    }

    .osf-card-title {
        font-weight: 600;
        font-size: 0.95rem;
        color: #092A47;
        margin-top: 0.25rem;
    }

    /* FILTER / CUSTOMIZE / DOWNLOAD BUTTON ROW */
    .osf-top-buttons .stButton > button {
        border-radius: 999px;
        border: 1px solid #E2E8F0;
        background-color: #FFFFFF;
        color: #092A47;
        font-weight: 600;
        padding: 0.35rem 1.4rem;
        font-size: 0.9rem;
    }

    .osf-top-buttons .stButton > button:hover {
        border-color: #092A47;
    }

    /* TABLE WRAPPERS */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        border: 1px solid #E2E8F0;
    }

    /* PAGINATION (our custom pager container) */
    .osf-pager {
        text-align: right;
        margin-top: 0.4rem;
        margin-bottom: 0.4rem;
    }

    .osf-pager button {
        border-radius: 999px;
        border: 1px solid #E2E8F0;
        background-color: #FFFFFF;
        padding: 0.15rem 0.6rem;
        margin-left: 0.25rem;
        font-size: 0.8rem;
    }

    .osf-table-count {
        font-size: 0.9rem;
        color: #4A5568;
        margin-bottom: 0.2rem;
    }
    </style>
    """
    # This actually injects <style> into the DOM root.
    html(css, height=0)


# -----------------------------------------------------------------------------
# Data loading & helpers
# -----------------------------------------------------------------------------

def load_data(path: Path) -> Tuple[pd.Series, pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load the unified CSV.

    Expects a column `row_type` with values:
      - branding
      - summary
      - user
      - project
      - registration
      - preprint
    """
    df = pd.read_csv(path, dtype=str).fillna("")

    if "row_type" not in df.columns:
        st.error("CSV must include a 'row_type' column.")
        st.stop()

    branding_df = df[df["row_type"] == "branding"]
    summary_df = df[df["row_type"] == "summary"]
    users = df[df["row_type"] == "user"].copy()
    projects = df[df["row_type"] == "project"].copy()
    registrations = df[df["row_type"] == "registration"].copy()
    preprints = df[df["row_type"] == "preprint"].copy()

    branding_row = branding_df.iloc[0] if not branding_df.empty else pd.Series(dtype=object)
    summary_row = summary_df.iloc[0] if not summary_df.empty else pd.Series(dtype=object)

    return branding_row, summary_row, users, projects, registrations, preprints


def _safe_int(series: pd.Series, key: str, default: int = 0) -> int:
    raw = series.get(key, "")
    try:
        return int(str(raw).replace(",", "").strip())
    except Exception:
        return default


def _safe_float(series: pd.Series, key: str, default: float = 0.0) -> float:
    raw = series.get(key, "")
    try:
        return float(str(raw).replace(",", "").strip())
    except Exception:
        return default


def paginate_df(df: pd.DataFrame, key_prefix: str, page_size: int = 10) -> pd.DataFrame:
    total = len(df)
    max_page = max(1, math.ceil(total / page_size))

    page_key = f"{key_prefix}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.markdown(f'<div class="osf-table-count">{total} results</div>', unsafe_allow_html=True)
    with col_right:
        st.markdown('<div class="osf-pager">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("«", key=f"{page_key}_first") and total > 0:
                st.session_state[page_key] = 1
        with c2:
            if st.button("‹", key=f"{page_key}_prev") and st.session_state[page_key] > 1:
                st.session_state[page_key] -= 1
        with c3:
            if st.button("›", key=f"{page_key}_next") and st.session_state[page_key] < max_page:
                st.session_state[page_key] += 1
        st.markdown("</div>", unsafe_allow_html=True)

    start = (st.session_state[page_key] - 1) * page_size
    end = start + page_size
    return df.iloc[start:end]


def download_link_from_df(df: pd.DataFrame, filename: str, label: str) -> None:
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
    )


# -----------------------------------------------------------------------------
# Header & layout helpers
# -----------------------------------------------------------------------------

def render_header(branding_row: pd.Series) -> None:
    name = branding_row.get("institution_name", "Center For Open Science [Test]")
    subtitle = branding_row.get("dashboard_subtitle", "Institutions Dashboard (Demo)")
    report_month = branding_row.get("report_month", "")

    if report_month:
        subtitle = f"{subtitle} • Report month: {report_month}"

    logo_url = branding_row.get("logo_url", "").strip()

    with st.container():
        st.markdown('<div class="osf-header">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([0.7, 6, 1.5])

        with c1:
            if logo_url:
                st.image(logo_url, width=52)
            else:
                st.write("")  # empty

        with c2:
            st.markdown(f'<div class="osf-header-title">{name}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="osf-header-subtitle">{subtitle}</div>', unsafe_allow_html=True)

        with c3:
            # Right-side placeholder (like user menu in real OSF)
            st.write("")

        st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Summary tab
# -----------------------------------------------------------------------------

def render_summary_tab(summary_row: pd.Series,
                       users: pd.DataFrame,
                       projects: pd.DataFrame,
                       registrations: pd.DataFrame,
                       preprints: pd.DataFrame) -> None:
    st.markdown("### Summary")

    # --- Top metric tiles (2 rows of 4) ---
    totals = {
        "Total Users": _safe_int(summary_row, "total_users"),
        "Total Monthly Logged in Users": _safe_int(summary_row, "total_monthly_logged_in_users"),
        "Total Monthly Active Users": _safe_int(summary_row, "total_monthly_active_users"),
        "OSF Public and Private Projects": _safe_int(summary_row, "total_public_private_projects"),
        "OSF Public and Embargoed Registrations": _safe_int(summary_row, "total_public_embargoed_registrations"),
        "OSF Preprints": _safe_int(summary_row, "total_preprints"),
        "Total Public File Count": _safe_int(summary_row, "total_public_file_count"),
        "Total Storage in GB": _safe_float(summary_row, "total_storage_gb"),
    }

    labels = list(totals.keys())
    values = list(totals.values())

    # first row
    row1 = st.columns(4)
    for col, idx in zip(row1, range(4)):
        with col:
            st.metric(label=labels[idx], value=f"{values[idx]:,}")

    # second row
    row2 = st.columns(4)
    for col, idx in zip(row2, range(4, 8)):
        with col:
            # allow float for GB
            val = values[idx]
            if isinstance(val, float) and not val.is_integer():
                v_str = f"{val:,.1f}"
            else:
                v_str = f"{int(val):,}"
            st.metric(label=labels[idx], value=v_str)

    st.write("")

    # --- Donut + bar charts ---
    # For charts we use Vega-Lite via st.vega_lite_chart (no extra deps).

    def donut_from_counts(title: str, counts: Dict[str, int]):
        data = pd.DataFrame(
            {"category": list(counts.keys()), "value": list(counts.values())}
        )
        if data["value"].sum() <= 0:
            st.markdown(f'<div class="osf-card"><div class="osf-card-title">{title}</div>'
                        '<p style="font-size:0.85rem;color:#718096;margin-top:0.5rem;">No data.</p></div>',
                        unsafe_allow_html=True)
            return

        spec = {
            "mark": {"type": "arc", "innerRadius": 60},
            "encoding": {
                "theta": {"field": "value", "type": "quantitative"},
                "color": {
                    "field": "category",
                    "type": "nominal",
                },
                "tooltip": [
                    {"field": "category", "type": "nominal"},
                    {"field": "value", "type": "quantitative"},
                ],
            },
        }

        st.markdown('<div class="osf-card">', unsafe_allow_html=True)
        st.vega_lite_chart(data, spec, use_container_width=True)
        st.markdown(f'<div class="osf-card-title">{title}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Users by department from users table
    dept_col = None
    for candidate in ["department", "Department", "dept"]:
        if candidate in users.columns:
            dept_col = candidate
            break

    users_by_dept = {}
    if dept_col:
        series = users[dept_col].replace("", "Unknown").value_counts()
        users_by_dept = series.to_dict()

    # Public vs Private Projects from summary
    proj_counts = {
        "Public": _safe_int(summary_row, "public_projects_count"),
        "Private": _safe_int(summary_row, "private_projects_count"),
    }

    # Public vs Embargoed Registrations from summary
    reg_counts = {
        "Public": _safe_int(summary_row, "public_registrations_count"),
        "Embargoed": _safe_int(summary_row, "embargoed_registrations_count"),
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        donut_from_counts("Total Users by Department", users_by_dept)
    with c2:
        donut_from_counts("Public vs Private Projects", proj_counts)
    with c3:
        donut_from_counts("Public vs Embargoed Registrations", reg_counts)

    st.write("")

    # Total OSF Objects donut: public/embargoed regs, public/private projects, preprints
    osf_objects = {
        "Public registrations": proj_counts.get("Public", 0) * 0,  # placeholder to keep keys consistent
    }
    osf_objects = {
        "Public registrations": _safe_int(summary_row, "public_registrations_count"),
        "Embargoed registrations": _safe_int(summary_row, "embargoed_registrations_count"),
        "Public projects": _safe_int(summary_row, "public_projects_count"),
        "Private projects": _safe_int(summary_row, "private_projects_count"),
        "Preprints": _safe_int(summary_row, "total_preprints"),
    }

    # Top 10 licenses from projects/registrations/preprints
    all_content = pd.concat(
        [projects.assign(_src="project"),
         registrations.assign(_src="registration"),
         preprints.assign(_src="preprint")],
        ignore_index=True,
    )

    license_col = None
    for candidate in ["license", "License"]:
        if candidate in all_content.columns:
            license_col = candidate
            break

    license_counts: Dict[str, int] = {}
    if license_col:
        series = (
            all_content[license_col]
            .fillna("")
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .head(10)
        )
        license_counts = series.to_dict()

    # Top Add-ons from summary row: any column starting with 'addon_'
    addon_counts: Dict[str, int] = {}
    for col in summary_row.index:
        if col.startswith("addon_"):
            label = col.replace("addon_", "").replace("_", " ").title()
            addon_counts[label] = _safe_int(summary_row, col)

    c4, c5, c6 = st.columns(3)
    with c4:
        donut_from_counts("Total OSF Objects", osf_objects)
    with c5:
        donut_from_counts("Top 10 Licenses", license_counts)
    with c6:
        donut_from_counts("Top 10 Add-ons", addon_counts)

    st.write("")

    # Storage regions from summary columns starting with storage_region_
    region_counts: Dict[str, int] = {}
    for col in summary_row.index:
        if col.startswith("storage_region_"):
            label = col.replace("storage_region_", "").replace("_", " ").title()
            region_counts[label] = _safe_int(summary_row, col)

    c7, _, _ = st.columns([1, 1, 1])
    with c7:
        donut_from_counts("Top Storage Regions", region_counts)


# -----------------------------------------------------------------------------
# Generic tab renderer for Users / Projects / Registrations / Preprints
# -----------------------------------------------------------------------------

def render_table_tab(
    label: str,
    df: pd.DataFrame,
    default_columns: List[str],
    filter_config: Dict,
    key_prefix: str,
) -> None:
    st.markdown(f"### {label}")

    total_label = f"{len(df):,} Total {label}"
    st.markdown(f"**{total_label}**")

    # --- Top right buttons (Filters / Customize / Download CSV) ---
    st.markdown('<div class="osf-top-buttons">', unsafe_allow_html=True)
    bcol1, bcol2, bcol3 = st.columns([1, 1, 1])
    with bcol1:
        show_filters = st.checkbox("Filters", key=f"{key_prefix}_filters_open", value=False)
    with bcol2:
        show_customize = st.checkbox("Customize", key=f"{key_prefix}_customize_open", value=False)
    with bcol3:
        download_clicked = st.checkbox("Download CSV", key=f"{key_prefix}_download_clicked", value=False)
    st.markdown("</div>", unsafe_allow_html=True)

    work_df = df.copy()

    # --- Filters (very simple AND filters, per-column) ---
    if show_filters:
        st.markdown("#### Filters")
        for col_name, cfg in filter_config.items():
            if col_name not in work_df.columns:
                continue

            col_type = cfg.get("type", "multiselect")
            label_txt = cfg.get("label", col_name)
            options = sorted([o for o in work_df[col_name].unique() if str(o).strip() != ""])

            if not options:
                continue

            if col_type == "multiselect":
                selected = st.multiselect(label_txt, options, key=f"{key_prefix}_f_{col_name}")
                if selected:
                    # AND semantics: row must match all selected values (for comma-separated lists)
                    mask = pd.Series(True, index=work_df.index)
                    for opt in selected:
                        mask &= work_df[col_name].astype(str).str.contains(str(opt), na=False)
                    work_df = work_df[mask]
            elif col_type == "selectbox":
                selected = st.selectbox(label_txt, ["All"] + options, key=f"{key_prefix}_f_{col_name}")
                if selected != "All":
                    work_df = work_df[work_df[col_name] == selected]

    # --- Customize columns ---
    visible_key = f"{key_prefix}_visible_columns"
    if visible_key not in st.session_state:
        # Initialize with intersection of defaults and actual columns
        st.session_state[visible_key] = [c for c in default_columns if c in work_df.columns]

    if show_customize:
        st.markdown("#### Show columns")
        all_cols = list(work_df.columns)
        selected = st.multiselect(
            "Choose columns to display",
            all_cols,
            default=st.session_state[visible_key],
            key=f"{key_prefix}_custom_cols",
        )
        if selected:
            st.session_state[visible_key] = selected

    visible_cols = [c for c in st.session_state[visible_key] if c in work_df.columns]
    if not visible_cols:
        visible_cols = list(work_df.columns)

    work_df = work_df[visible_cols]

    # --- Download CSV (filtered + visible columns) ---
    if download_clicked and not work_df.empty:
        download_link_from_df(work_df, f"{label.lower()}_filtered.csv", "Download current view as CSV")

    # --- Paginate and display ---
    if work_df.empty:
        st.info("No rows match the current filters.")
        return

    page_df = paginate_df(work_df, key_prefix=key_prefix, page_size=10)

    st.dataframe(
        page_df,
        use_container_width=True,
        hide_index=True,
    )


# -----------------------------------------------------------------------------
# Main app
# -----------------------------------------------------------------------------

def main():
    inject_osf_css()
    st.set_page_config(layout="wide", page_title="OSF Institutions Dashboard (Demo)")
    # ... rest of your code ...


    try:
        branding_row, summary_row, users, projects, registrations, preprints = load_data(DATA_FILE)
    except FileNotFoundError:
        st.error(
            f"Could not find CSV file at `{DATA_FILE.name}`. "
            "Make sure it is in the same folder as `dashboard.py`."
        )
        return

    render_header(branding_row)

    tab_labels = ["Summary", "Users", "Projects", "Registrations", "Preprints"]
    summary_tab, users_tab, projects_tab, regs_tab, preprints_tab = st.tabs(tab_labels)

    with summary_tab:
        render_summary_tab(summary_row, users, projects, registrations, preprints)

    with users_tab:
        users_default_cols = [
            "name",
            "department",
            "osf_link",
            "orcid",
            "public_projects",
            "private_projects",
            "public_registrations",
            "embargoed_registrations",
            "preprints",
            "public_files",
            "total_storage_gb",
            "account_created",
            "last_login",
            "last_active",
        ]

        users_filters = {
            "department": {"type": "selectbox", "label": "Department"},
            # Example extra filter: ORCID present/absent if you add such a column
        }

        render_table_tab(
            label="Users",
            df=users,
            default_columns=users_default_cols,
            filter_config=users_filters,
            key_prefix="users",
        )

    with projects_tab:
        proj_default_cols = [
            "title",
            "link",
            "created_date",
            "modified_date",
            "doi",
            "storage_location",
            "total_data_osf",
            "contributor_name",
            "views_last_30_days",
            "license",
            "resource_type",
            "funder_name",
            "institution",
            "is_collection",
        ]

        proj_filters = {
            "creator": {"type": "multiselect", "label": "Creator"},
            "license": {"type": "multiselect", "label": "License"},
            "resource_type": {"type": "multiselect", "label": "Resource type"},
            "institution": {"type": "multiselect", "label": "Institution"},
        }

        render_table_tab(
            label="Projects",
            df=projects,
            default_columns=proj_default_cols,
            filter_config=proj_filters,
            key_prefix="projects",
        )

    with regs_tab:
        reg_default_cols = [
            "title",
            "link",
            "created_date",
            "modified_date",
            "doi",
            "storage_location",
            "total_data_osf",
            "contributor_name",
            "views_last_30_days",
            "license",
            "subject",
        ]

        reg_filters = {
            "creator": {"type": "multiselect", "label": "Creator"},
            "license": {"type": "multiselect", "label": "License"},
            "subject": {"type": "multiselect", "label": "Subject"},
        }

        render_table_tab(
            label="Registrations",
            df=registrations,
            default_columns=reg_default_cols,
            filter_config=reg_filters,
            key_prefix="registrations",
        )

    with preprints_tab:
        pp_default_cols = [
            "title",
            "link",
            "created_date",
            "modified_date",
            "doi",
            "license",
            "contributor_name",
            "views_last_30_days",
            "subject",
        ]

        pp_filters = {
            "creator": {"type": "multiselect", "label": "Creator"},
            "license": {"type": "multiselect", "label": "License"},
            "subject": {"type": "multiselect", "label": "Subject"},
        }

        render_table_tab(
            label="Preprints",
            df=preprints,
            default_columns=pp_default_cols,
            filter_config=pp_filters,
            key_prefix="preprints",
        )


if __name__ == "__main__":
    main()
