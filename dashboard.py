import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------
# Basic config
# ------------------------------------------------------------------

DATA_FILE = "osfi_dashboard_data_with_summary.csv"

st.set_page_config(
    page_title="OSF Institutions Dashboard (Demo)",
    layout="wide",
)

# ------------------------------------------------------------------
# CSS – approximate OSF Institutions look & feel
# ------------------------------------------------------------------

CUSTOM_CSS = """
<style>
/* Page background */
.main, .block-container {
    background-color: #f4f7fb;
}

/* Remove default top padding so banner isn't cut off */
.block-container {
    padding-top: 0.5rem !important;
}

/* Top banner */
.osf-banner {
    background-color: #0b3b5c;
    color: #ffffff;
    padding: 20px 32px 16px 32px;
    border-radius: 0 0 8px 8px;
    margin-bottom: 12px;
}

.osf-banner-inner {
    display: flex;
    align-items: center;
}

.osf-logo {
    width: 48px;
    height: 48px;
    border-radius: 999px;
    object-fit: contain;
    margin-right: 16px;
    background-color: #ffffff;
    padding: 4px;
}

.osf-inst-name {
    font-size: 24px;
    font-weight: 700;
}

.osf-inst-subtitle {
    font-size: 13px;
    opacity: 0.9;
    margin-top: 2px;
}

/* Tabs bar */
.osf-tabs-container {
    background-color: #f4f7fb;
    padding: 0 32px 8px 32px;
    border-bottom: 1px solid #e0e6f0;
}

/* Summary heading */
.osf-section-title {
    font-size: 24px;
    font-weight: 700;
    margin: 12px 0 8px 0;
}

/* Summary metric cards */
.metric-card {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    padding: 18px 24px;
    display: flex;
    align-items: center;
}

.metric-circle {
    background-color: #eef5ff;
    border-radius: 999px;
    width: 88px;
    height: 88px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 16px;
}

.metric-value {
    font-size: 24px;
    font-weight: 700;
    color: #115293;
}

.metric-label {
    font-size: 13px;
    color: #374151;
    margin-top: 4px;
}

/* Card shells for charts */
.chart-card {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    padding: 12px 16px 4px 16px;
}

/* Section subtitles under charts */
.chart-title {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
    margin-top: -8px;
}

/* Data table card */
.table-card {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    padding: 16px 16px 8px 16px;
    margin-top: 8px;
}

/* Table header (Total X) */
.table-heading {
    font-size: 16px;
    font-weight: 600;
    color: #1d4f91;
}

/* Filter row */
.filter-row {
    margin-top: 6px;
    margin-bottom: 6px;
}

/* Pagination */
.pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-top: 8px;
    gap: 8px;
    font-size: 13px;
    color: #4b5563;
}
.pagination button {
    border-radius: 999px;
}

/* Small helper text */
.helper-text {
    font-size: 12px;
    color: #6b7280;
}

/* Make Streamlit tabs look closer to OSF (roughly) */
[data-baseweb="tab-list"] {
    padding-left: 32px;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def to_int(val, default: int = 0) -> int:
    try:
        if pd.isna(val):
            return default
        return int(float(str(val)))
    except Exception:
        return default


def to_float(val, default: float = 0.0) -> float:
    try:
        if pd.isna(val):
            return default
        return float(str(val))
    except Exception:
        return default


@st.cache_data
def load_data(path: str):
    path_obj = Path(path)
    if not path_obj.exists():
        st.error(f"Data file not found: {path_obj}")
        st.stop()

    df = pd.read_csv(path_obj, dtype=str).fillna("")
    df.columns = [c.strip() for c in df.columns]

    if "row_type" not in df.columns:
        st.error(
            "CSV must include a 'row_type' column "
            "(branding/summary/user/project/registration/preprint)."
        )
        st.stop()

    # Normalize row_type casing
    df["row_type"] = df["row_type"].str.strip().str.lower()

    summary_df = df[df["row_type"] == "summary"]
    summary_row = summary_df.iloc[0] if not summary_df.empty else None

    users = df[df["row_type"] == "user"].copy()
    projects = df[df["row_type"] == "project"].copy()
    registrations = df[df["row_type"] == "registration"].copy()
    preprints = df[df["row_type"] == "preprint"].copy()

    return df, summary_row, users, projects, registrations, preprints


def compute_summary_numbers(
    summary_row: Optional[pd.Series],
    users: pd.DataFrame,
    projects: pd.DataFrame,
    registrations: pd.DataFrame,
    preprints: pd.DataFrame,
) -> Dict[str, float]:
    """Use explicit summary-row fields when present; fall back to counts."""
    total_users = len(users)

    # Projects & registrations, from the write-in summary fields
    def sr(field, fallback=0):
        if summary_row is None:
            return fallback
        return summary_row.get(field, fallback)

    public_projects = to_int(
        sr("projects_public_count", sr("public_projects", len(projects)))
    )
    private_projects = to_int(
        sr("projects_private_count", sr("private_projects", 0))
    )
    total_projects = public_projects + private_projects

    public_regs = to_int(
        sr(
            "registrations_public_count",
            sr("public_registration_count", len(registrations)),
        )
    )
    embargoed_regs = to_int(
        sr(
            "registrations_embargoed_count",
            sr("embargoed_registration_count", 0),
        )
    )
    total_regs = public_regs + embargoed_regs

    total_preprints = to_int(
        sr("published_preprint_count", len(preprints))
    )

    total_public_files = to_int(sr("public_file_count", 0))
    total_storage_gb = to_float(sr("storage_gb", 0.0))

    monthly_logged_in = to_int(sr("summary_monthly_logged_in_users", 0))
    monthly_active = to_int(sr("summary_monthly_active_users", 0))

    return {
        "total_users": total_users,
        "monthly_logged_in": monthly_logged_in,
        "monthly_active": monthly_active,
        "total_projects": total_projects,
        "public_projects": public_projects,
        "private_projects": private_projects,
        "total_regs": total_regs,
        "public_regs": public_regs,
        "embargoed_regs": embargoed_regs,
        "preprints": total_preprints,
        "public_files": total_public_files,
        "storage_gb": total_storage_gb,
    }


def hyper_link_columns(df: pd.DataFrame, entity: str) -> Tuple[pd.DataFrame, Dict]:
    """
    Prepare column_config for st.dataframe so that OSF links, DOIs and ORCIDs
    are clickable. This is intentionally simple – it doesn't try to be perfect,
    just close to the real dashboard.
    """
    df = df.copy()
    col_config: Dict[str, st.column_config.Column] = {}

    # OSF link column – treat value as a slug or full URL
    if "osf_link" in df.columns:
        def make_osf_url(x: str) -> str:
            x = str(x).strip()
            if not x:
                return ""
            if x.startswith("http://") or x.startswith("https://"):
                return x
            # assume it's an OSF slug
            return f"https://osf.io/{x}"

        df["osf_link"] = df["osf_link"].apply(make_osf_url)
        col_config["osf_link"] = st.column_config.LinkColumn(
            "OSF Link", help="Open this OSF object", display_text="OSF link"
        )

    # DOI column
    if "doi" in df.columns:
        def make_doi_url(x: str) -> str:
            x = str(x).strip()
            if not x:
                return ""
            if x.startswith("http://") or x.startswith("https://"):
                return x
            if x.startswith("10."):
                return f"https://doi.org/{x}"
            return x

        df["doi"] = df["doi"].apply(make_doi_url)
        col_config["doi"] = st.column_config.LinkColumn(
            "DOI", display_text="DOI"
        )

    # ORCID column(s)
    def make_orcid_url(x: str) -> str:
        x = str(x).strip()
        if not x or x in ["-", "None", "none"]:
            return ""
        if x.startswith("http://") or x.startswith("https://"):
            return x
        return f"https://orcid.org/{x}"

    if "orcid_id" in df.columns:
        df["orcid_id"] = df["orcid_id"].apply(make_orcid_url)
        col_config["orcid_id"] = st.column_config.LinkColumn(
            "ORCID", display_text="ORCID"
        )

    if "creator_orcid" in df.columns:
        df["creator_orcid"] = df["creator_orcid"].apply(make_orcid_url)
        col_config["creator_orcid"] = st.column_config.LinkColumn(
            "Creator ORCID", display_text="Creator ORCID"
        )

    return df, col_config


def paginate_df(df: pd.DataFrame, page_size: int, page_key: str) -> Tuple[pd.DataFrame, int, int]:
    """Return current page of df and pagination info."""
    total_rows = len(df)
    total_pages = max(1, math.ceil(total_rows / page_size))

    page = st.session_state.get(page_key, 1)
    page = max(1, min(page, total_pages))
    st.session_state[page_key] = page

    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], page, total_pages


def render_pagination(page: int, total_pages: int, page_key: str):
    col_prev2, col_prev, col_info, col_next, col_next2 = st.columns(
        [1, 1, 3, 1, 1]
    )
    with col_prev2:
        if st.button("≪", key=f"{page_key}_first"):
            st.session_state[page_key] = 1
            st.experimental_rerun()
    with col_prev:
        if st.button("‹", key=f"{page_key}_prev"):
            st.session_state[page_key] = max(1, page - 1)
            st.experimental_rerun()
    with col_info:
        st.markdown(
            f"<div class='pagination'>Page {page} of {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("›", key=f"{page_key}_next"):
            st.session_state[page_key] = min(total_pages, page + 1)
            st.experimental_rerun()
    with col_next2:
        if st.button("≫", key=f"{page_key}_last"):
            st.session_state[page_key] = total_pages
            st.experimental_rerun()


def render_summary_tab(
    summary_row: Optional[pd.Series],
    users: pd.DataFrame,
    projects: pd.DataFrame,
    registrations: pd.DataFrame,
    preprints: pd.DataFrame,
):
    metrics = compute_summary_numbers(
        summary_row, users, projects, registrations, preprints
    )

    st.markdown("<div class='osf-section-title'>Summary</div>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Metric cards – two rows of four cards
    # ------------------------------------------------------------------
    cards_row1 = st.columns(4)
    cards_row2 = st.columns(4)

    def metric_card(col, value, label):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                  <div class="metric-circle">
                    <div class="metric-value">{value}</div>
                  </div>
                  <div>
                    <div class="metric-label">{label}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    metric_card(cards_row1[0], metrics["total_users"], "Total Users")
    metric_card(
        cards_row1[1],
        metrics["monthly_logged_in"],
        "Total Monthly Logged in Users",
    )
    metric_card(
        cards_row1[2],
        metrics["monthly_active"],
        "Total Monthly Active Users",
    )
    metric_card(
        cards_row1[3],
        metrics["total_projects"],
        "OSF Public and Private Projects",
    )

    metric_card(
        cards_row2[0],
        metrics["total_regs"],
        "OSF Public and Embargoed Registrations",
    )
    metric_card(cards_row2[1], metrics["preprints"], "OSF Preprints")
    metric_card(cards_row2[2], metrics["public_files"], "Total Public File Count")
    metric_card(
        cards_row2[3],
        metrics["storage_gb"],
        "Total Storage in GB",
    )

    st.markdown("")  # small spacer

    # ------------------------------------------------------------------
    # Donuts and bar charts
    # ------------------------------------------------------------------

    # Row 1: Users by department, Public vs private projects, Public vs embargoed registrations
    donut_row = st.columns(3)

    # Total users by department donut
    with donut_row[0]:
        dept_counts = (
            users["department"]
            .replace({"": "Unknown", "-": "Unknown"})
            .value_counts()
        )
        if not dept_counts.empty:
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=dept_counts.index,
                        values=dept_counts.values,
                        hole=0.65,
                        textinfo="percent",
                    )
                ]
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=True,
                legend=dict(orientation="h", y=-0.05),
            )
            st.markdown(
                "<div class='chart-card'>", unsafe_allow_html=True
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(
                "<div class='chart-title'>Total Users by Department</div></div>",
                unsafe_allow_html=True,
            )

    # Public vs private projects donut
    with donut_row[1]:
        labels = ["Public projects", "Private projects"]
        values = [metrics["public_projects"], metrics["private_projects"]]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.65,
                    textinfo="percent",
                )
            ]
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )
        st.markdown(
            "<div class='chart-card'>", unsafe_allow_html=True
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            "<div class='chart-title'>Public vs Private Projects</div></div>",
            unsafe_allow_html=True,
        )

    # Public vs embargoed registrations donut
    with donut_row[2]:
        labels = ["Public registrations", "Embargoed registrations"]
        values = [metrics["public_regs"], metrics["embargoed_regs"]]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.65,
                    textinfo="percent",
                )
            ]
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )
        st.markdown(
            "<div class='chart-card'>", unsafe_allow_html=True
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            "<div class='chart-title'>Public vs Embargoed Registrations</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("")

    # Row 2: Total OSF objects donut, Top licenses bar, Top add-ons bar
    chart_row2 = st.columns(3)

    # Total OSF objects donut (no "Users" here)
    with chart_row2[0]:
        labels = [
            "Public registrations",
            "Embargoed registrations",
            "Public projects",
            "Private projects",
            "Preprints",
        ]
        values = [
            metrics["public_regs"],
            metrics["embargoed_regs"],
            metrics["public_projects"],
            metrics["private_projects"],
            metrics["preprints"],
        ]
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.65,
                    textinfo="percent",
                )
            ]
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=True,
            legend=dict(orientation="h", y=-0.1),
        )
        st.markdown(
            "<div class='chart-card'>", unsafe_allow_html=True
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            "<div class='chart-title'>Total OSF Objects</div></div>",
            unsafe_allow_html=True,
        )

    # Top 10 licenses – bar chart
    with chart_row2[1]:
        licenses = (
            pd.concat(
                [
                    projects["license"],
                    registrations["license"],
                    preprints["license"],
                ]
            )
            .replace({"": "Unknown", "-": "Unknown"})
        )
        lic_counts = licenses.value_counts().head(10)
        if not lic_counts.empty:
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=lic_counts.index.tolist(),
                        y=lic_counts.values.tolist(),
                    )
                ]
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=80),
                xaxis_tickangle=-45,
            )
            st.markdown(
                "<div class='chart-card'>", unsafe_allow_html=True
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(
                "<div class='chart-title'>Top 10 Licenses</div></div>",
                unsafe_allow_html=True,
            )

    # Top 10 add-ons – bar chart
    with chart_row2[2]:
        addons_series = (
            pd.concat(
                [
                    projects["add_ons"],
                    registrations["add_ons"],
                    preprints["add_ons"],
                ]
            )
            .astype(str)
            .str.split(";", expand=True)
            .stack()
            .str.strip()
        )
        addons_series = addons_series[addons_series != ""]
        add_counts = addons_series.value_counts().head(10)
        if not add_counts.empty:
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=add_counts.index.tolist(),
                        y=add_counts.values.tolist(),
                    )
                ]
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=80),
                xaxis_tickangle=-45,
            )
            st.markdown(
                "<div class='chart-card'>", unsafe_allow_html=True
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(
                "<div class='chart-title'>Top 10 Add-ons</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("")

    # Row 3: Top storage regions donut
    storage_row = st.columns(3)
    with storage_row[0]:
        stor_regions = (
            pd.concat(
                [
                    projects["storage_region"],
                    registrations["storage_region"],
                    preprints["storage_region"],
                ]
            )
            .replace({"": "Unknown", "-": "Unknown"})
        )
        stor_counts = stor_regions.value_counts()
        if not stor_counts.empty:
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=stor_counts.index.tolist(),
                        values=stor_counts.values.tolist(),
                        hole=0.65,
                        textinfo="percent",
                    )
                ]
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=True,
                legend=dict(orientation="h", y=-0.1),
            )
            st.markdown(
                "<div class='chart-card'>", unsafe_allow_html=True
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(
                "<div class='chart-title'>Top Storage Regions</div></div>",
                unsafe_allow_html=True,
            )


def render_entity_tab(
    label_singular: str,
    label_plural: str,
    df: pd.DataFrame,
    page_key: str,
    has_orcid_filter: bool = False,
    department_filter: bool = False,
):
    """Generic renderer for Users / Projects / Registrations / Preprints."""

    df_display, col_config = hyper_link_columns(df, label_plural)

    # Heading
    total = len(df_display)
    st.markdown(
        f"<div class='table-heading'>{total} Total {label_plural}</div>",
        unsafe_allow_html=True,
    )

    # ------------------ Filters + toolbar row ------------------------
    # We approximate layout: filters on left, toolbar on right.
    col1, col2, spacer, col_custom, col_dl, col_chart = st.columns(
        [1.2, 2.0, 4.0, 1.3, 0.8, 0.8]
    )

    # Filters
    has_orcid = False
    dept_choice = None

    if has_orcid_filter:
        with col1:
            has_orcid = st.checkbox("Has ORCID", key=f"{page_key}_has_orcid")

    if department_filter and "department" in df_display.columns:
        with col2:
            depts = (
                df_display["department"]
                .replace({"": "Unknown", "-": "Unknown"})
                .unique()
            )
            depts = sorted([d for d in depts if d])
            options = ["All departments"] + depts
            dept_choice = st.selectbox(
                "Departments",
                options,
                index=0,
                key=f"{page_key}_dept",
            )

    # Toolbar – right aligned buttons
    with col_custom:
        with st.popover("Customize", key=f"{page_key}_customize"):
            st.markdown("**Show columns**")
            all_cols = list(df_display.columns)
            default_cols = st.session_state.get(
                f"{page_key}_cols", all_cols
            )
            chosen_cols = st.multiselect(
                "Columns",
                all_cols,
                default=default_cols,
                key=f"{page_key}_cols_selector",
            )
            if not chosen_cols:
                chosen_cols = all_cols
            st.session_state[f"{page_key}_cols"] = chosen_cols
    with col_dl:
        csv_bytes = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name=f"{label_plural.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            key=f"{page_key}_download",
        )
    with col_chart:
        st.button("📊", help="Placeholder for chart actions", key=f"{page_key}_chart")

    # ------------------ Apply filters -----------------------------
    filtered = df_display.copy()
    if has_orcid_filter and has_orcid:
        # ORCID can be in orcid_id or creator_orcid
        orcid_cols = [
            c for c in ["orcid_id", "creator_orcid"] if c in filtered.columns
        ]
        if orcid_cols:
            mask = False
            for c in orcid_cols:
                colmask = filtered[c].astype(str)
                colmask = ~colmask.isin(["", "None", "none", "-"])
                mask = mask | colmask
            filtered = filtered[mask]

    if department_filter and dept_choice and dept_choice != "All departments":
        filtered = filtered[
            filtered["department"]
            .replace({"": "Unknown", "-": "Unknown"})
            .eq(dept_choice)
        ]

    # Column subset from Customize
    chosen_cols = st.session_state.get(
        f"{page_key}_cols", list(filtered.columns)
    )
    chosen_cols = [c for c in chosen_cols if c in filtered.columns]
    if not chosen_cols:
        chosen_cols = list(filtered.columns)
    filtered = filtered[chosen_cols]

    # ------------------ Table with pagination ----------------------
    with st.container():
        st.markdown("<div class='table-card'>", unsafe_allow_html=True)
        page_df, page, total_pages = paginate_df(filtered, 10, page_key)
        st.dataframe(
            page_df,
            column_config=col_config,
            hide_index=True,
            use_container_width=True,
        )
        render_pagination(page, total_pages, page_key)
        st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Main app
# ------------------------------------------------------------------

df, summary_row, users_df, projects_df, regs_df, preprints_df = load_data(
    DATA_FILE
)

inst_name = (
    summary_row.get("branding_institution_name", "")
    if summary_row is not None
    else ""
)
logo_url = (
    summary_row.get("branding_institution_logo_url", "")
    if summary_row is not None
    else ""
)
report_month = (
    summary_row.get("report_month", "")
    if summary_row is not None
    else ""
)

# ---------------- Top banner -----------------
banner_html = "<div class='osf-banner'><div class='osf-banner-inner'>"
if logo_url:
    banner_html += f"<img src='{logo_url}' class='osf-logo'/>"
banner_html += "<div>"
if inst_name:
    banner_html += f"<div class='osf-inst-name'>{inst_name}</div>"
else:
    banner_html += "<div class='osf-inst-name'>Your Institution</div>"
banner_html += (
    "<div class='osf-inst-subtitle'>Institutions Dashboard (Demo)"
)
if report_month:
    banner_html += f" · Report month: {report_month}"
banner_html += "</div></div></div></div>"

st.markdown(banner_html, unsafe_allow_html=True)

# ---------------- Tabs -----------------
summary_tab, users_tab, projects_tab, regs_tab, preprints_tab = st.tabs(
    ["Summary", "Users", "Projects", "Registrations", "Preprints"]
)

with summary_tab:
    render_summary_tab(summary_row, users_df, projects_df, regs_df, preprints_df)

with users_tab:
    render_entity_tab(
        "User",
        "Users",
        users_df,
        page_key="users",
        has_orcid_filter=True,
        department_filter=True,
    )

with projects_tab:
    render_entity_tab(
        "Project",
        "Projects",
        projects_df,
        page_key="projects",
        has_orcid_filter=False,
        department_filter=False,
    )

with regs_tab:
    render_entity_tab(
        "Registration",
        "Registrations",
        regs_df,
        page_key="registrations",
        has_orcid_filter=False,
        department_filter=False,
    )

with preprints_tab:
    render_entity_tab(
        "Preprint",
        "Preprints",
        preprints_df,
        page_key="preprints",
        has_orcid_filter=False,
        department_filter=False,
    )
