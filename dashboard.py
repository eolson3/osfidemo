# dashboard.py
"""
Institutions Dashboard (Demo) – Single–CSV version with pure Streamlit tables.

Expects a CSV with a `row_type` column containing:
  - summary
  - user
  - project
  - registration
  - preprint

Other columns:
  name_or_title, osf_link, created_date, modified_date, doi,
  storage_region, storage_byte_count, storage_gb,
  views_last_30_days, downloads_last_30_days,
  license, resource_type, add_ons, funder_name,
  contributor_name, creator_orcid, department, orcid_id,
  public_projects, private_projects,
  public_registration_count, embargoed_registration_count,
  published_preprint_count, public_file_count,
  month_last_active, month_last_login, report_yearmonth,
  branding_institution_name, branding_institution_logo_url,
  report_month,
  projects_public_count, projects_private_count,
  registrations_public_count, registrations_embargoed_count,
  summary_monthly_logged_in_users, summary_monthly_active_users
"""

import math
from collections import Counter

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_FILE = "institution_dashboard_data.csv"

# --- Palette (approximate COS brand based on screenshots) ---
PRIMARY_BLUE = "#1668b8"      # main text / icons
ACCENT_BLUE = "#17a2ff"       # large donut teal
ACCENT_ORANGE = "#f9a65a"
ACCENT_PINK = "#ff6b6b"
ACCENT_PURPLE = "#8a6fd1"
LIGHT_BG = "#f5f8fc"
CARD_BORDER = "#e1e4eb"
TEXT_DARK = "#1f2933"
TEXT_MUTED = "#6b7280"


# -------------------------------------------------------------------
# Data loading & helpers
# -------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(path: str):
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    if "row_type" not in df.columns:
        raise ValueError(
            "CSV must include a 'row_type' column "
            "(branding/summary/user/project/registration/preprint)."
        )

    df = df.fillna("")

    summary = df[df["row_type"] == "summary"]
    if summary.empty:
        raise ValueError("CSV must include at least one row with row_type='summary'.")
    summary_row = summary.iloc[0]

    users = df[df["row_type"] == "user"].copy()
    projects = df[df["row_type"] == "project"].copy()
    registrations = df[df["row_type"] == "registration"].copy()
    preprints = df[df["row_type"] == "preprint"].copy()

    return df, summary_row, users, projects, registrations, preprints


def parse_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(str(value)))
    except Exception:
        return default


def parse_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(str(value))
    except Exception:
        return default


def compute_summary_metrics(summary_row, users, preprints):
    """All numbers for the top summary cards live here."""
    total_users = len(users)

    total_monthly_logged_in = parse_int(
        summary_row.get("summary_monthly_logged_in_users"), default=0
    )
    total_monthly_active = parse_int(
        summary_row.get("summary_monthly_active_users"), default=0
    )

    public_projects = parse_int(summary_row.get("projects_public_count"), 0)
    private_projects = parse_int(summary_row.get("projects_private_count"), 0)
    total_projects = public_projects + private_projects

    public_regs = parse_int(summary_row.get("registrations_public_count"), 0)
    embargoed_regs = parse_int(
        summary_row.get("registrations_embargoed_count"), 0
    )
    total_regs = public_regs + embargoed_regs

    total_preprints = len(preprints)

    total_public_files = parse_int(summary_row.get("public_file_count"), 0)
    total_storage_gb = parse_float(summary_row.get("storage_gb"), 0.0)

    return {
        "total_users": total_users,
        "total_monthly_logged_in": total_monthly_logged_in,
        "total_monthly_active": total_monthly_active,
        "total_projects": total_projects,
        "total_regs": total_regs,
        "total_preprints": total_preprints,
        "total_public_files": total_public_files,
        "total_storage_gb": total_storage_gb,
        "public_projects": public_projects,
        "private_projects": private_projects,
        "public_regs": public_regs,
        "embargoed_regs": embargoed_regs,
    }


# -------------------------------------------------------------------
# Styling
# -------------------------------------------------------------------
def inject_css():
    st.markdown(
        f"""
        <style>
        header {{visibility: hidden;}}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}

        .block-container {{
            padding-top: 2.2rem;
            padding-left: 2.5rem;
            padding-right: 2.5rem;
            background: {LIGHT_BG};
        }}

        .osf-brand-bar {{
            background: #0e3454;
            color: white;
            padding: 1.0rem 1.8rem;
            border-radius: 0.5rem;
            margin-bottom: 1.2rem;
            display: flex;
            align-items: center;
            gap: 0.9rem;
        }}

        .osf-logo-circle {{
            width: 40px;
            height: 40px;
            border-radius: 999px;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
            color: #0e3454;
            margin-right: 10px;
        }}

        .osf-brand-title {{
            font-size: 1.3rem;
            font-weight: 700;
        }}

        .osf-brand-subtitle {{
            font-size: 0.85rem;
            opacity: 0.9;
        }}

        .osf-summary-card {{
            background: white;
            border-radius: 0.7rem;
            border: 1px solid {CARD_BORDER};
            padding: 0.9rem 1.2rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 0.3rem;
        }}

        .osf-summary-number {{
            font-size: 1.6rem;
            font-weight: 700;
            color: {PRIMARY_BLUE};
        }}

        .osf-summary-label {{
            font-size: 0.9rem;
            color: {TEXT_MUTED};
            text-align: center;
        }}

        .osf-section-title {{
            font-size: 1.25rem;
            font-weight: 700;
            margin: 0.5rem 0 0.8rem 0;
            color: {TEXT_DARK};
        }}

        .osf-table-wrapper {{
            border-radius: 0.7rem;
            border: 1px solid {CARD_BORDER};
            overflow: hidden;
            background: white;
            padding: 0.25rem 0.25rem 0 0.25rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------
# Charts
# -------------------------------------------------------------------
def donut_chart(title, labels, values, colors):
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.65,
                marker=dict(colors=colors, line=dict(color="white", width=1)),
                textinfo="percent",
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=True,
        legend=dict(orientation="h", y=-0.2),
        title=dict(text=title, x=0.5, xanchor="center", y=0.99),
    )
    return fig


def bar_chart(title, items_counter: Counter, top_n=10):
    items = items_counter.most_common(top_n)
    if not items:
        fig = go.Figure()
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), title=title)
        return fig

    labels, counts = zip(*items)
    fig = go.Figure(
        data=[
            go.Bar(
                x=list(labels),
                y=list(counts),
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=40),
        title=dict(text=title, x=0.01, xanchor="left"),
        xaxis_tickangle=-35,
    )
    return fig


# -------------------------------------------------------------------
# Table helper (pagination + basic styling)
# -------------------------------------------------------------------
def render_table(
    df: pd.DataFrame,
    page_key: str,
    columns_to_show,
    link_columns=None,
    height=420,
):
    """
    Render a paginated, non-editable table with sorting via native
    Streamlit data editor. Index hidden; pagination controls appear below.
    """
    if link_columns is None:
        link_columns = []

    if not columns_to_show:
        columns_to_show = [c for c in df.columns if c != "row_type"]

    display_df = df[columns_to_show].copy()

    # Pagination state
    page_size = 10
    total_rows = len(display_df)
    total_pages = max(1, math.ceil(total_rows / page_size))

    current_page = st.session_state.get(page_key, 1)
    current_page = max(1, min(current_page, total_pages))
    st.session_state[page_key] = current_page

    start = (current_page - 1) * page_size
    end = start + page_size
    page_df = display_df.iloc[start:end]

    # Column configs for link columns
    col_config = {}
    for col in link_columns:
        if col in page_df.columns:
            # Expect these cells to contain full URLs; display text will be the URL itself
            col_config[col] = st.column_config.LinkColumn(col)

    with st.container():
        st.markdown('<div class="osf-table-wrapper">', unsafe_allow_html=True)
        st.data_editor(
            page_df,
            hide_index=True,
            disabled=True,
            column_config=col_config,
            height=height,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Pagination controls under table
    col_prev2, col_prev, col_next, col_next2, col_page = st.columns(
        [0.3, 0.3, 0.3, 0.3, 2.8]
    )
    with col_prev2:
        if st.button("≪", key=f"{page_key}_first", help="First page"):
            st.session_state[page_key] = 1
    with col_prev:
        if st.button("‹", key=f"{page_key}_prev", help="Previous page"):
            st.session_state[page_key] = max(1, current_page - 1)
    with col_next:
        if st.button("›", key=f"{page_key}_next", help="Next page"):
            st.session_state[page_key] = min(total_pages, current_page + 1)
    with col_next2:
        if st.button("≫", key=f"{page_key}_last", help="Last page"):
            st.session_state[page_key] = total_pages
    with col_page:
        st.write(f"Page {current_page} of {total_pages} • {total_rows} results")


# -------------------------------------------------------------------
# Page builders
# -------------------------------------------------------------------
def render_branding(summary_row):
    inst_name = summary_row.get("branding_institution_name", "").strip()
    logo_url = summary_row.get("branding_institution_logo_url", "").strip()
    report_month = summary_row.get("report_month", "").strip()

    if not inst_name:
        inst_name = "Center For Open Science [Test]"

    st.markdown("<div class='osf-brand-bar'>", unsafe_allow_html=True)

    if logo_url:
        st.markdown(
            f"<img src='{logo_url}' style='width:40px;height:40px;border-radius:999px;'>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='osf-logo-circle'>OSF</div>",
            unsafe_allow_html=True,
        )

    col_title, _ = st.columns([4, 1])
    with col_title:
        st.markdown(
            f"""
            <div>
              <div class="osf-brand-title">{inst_name}</div>
              <div class="osf-brand-subtitle">
                Institutions Dashboard (Demo){' • Report month: ' + report_month if report_month else ''}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_summary_tab(summary_row, users, projects, registrations, preprints):
    metrics = compute_summary_metrics(summary_row, users, preprints)

    st.markdown("## Summary")

    # Top cards
    top_cols = st.columns(4)
    cards = [
        ("Total Users", metrics["total_users"]),
        ("Total Monthly Logged in Users", metrics["total_monthly_logged_in"]),
        ("Total Monthly Active Users", metrics["total_monthly_active"]),
        ("OSF Public and Private Projects", metrics["total_projects"]),
    ]
    for col, (label, value) in zip(top_cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="osf-summary-card">
                  <div class="osf-summary-number">{value}</div>
                  <div class="osf-summary-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    bottom_cols = st.columns(4)
    cards2 = [
        ("OSF Public and Embargoed Registrations", metrics["total_regs"]),
        ("OSF Preprints", metrics["total_preprints"]),
        ("Total Public File Count", metrics["total_public_files"]),
        ("Total Storage in GB", metrics["total_storage_gb"]),
    ]
    for col, (label, value) in zip(bottom_cols, cards2):
        with col:
            st.markdown(
                f"""
                <div class="osf-summary-card">
                  <div class="osf-summary-number">{value}</div>
                  <div class="osf-summary-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Donuts row 1
    st.markdown('<div class="osf-section-title">Overview</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    # Total users by department
    dept_counts = Counter(
        (dept if dept else "Unknown") for dept in users.get("department", [])
    )
    with c1:
        fig = donut_chart(
            "Total Users by Department",
            list(dept_counts.keys()),
            list(dept_counts.values()),
            [ACCENT_BLUE, ACCENT_ORANGE, ACCENT_PINK, ACCENT_PURPLE],
        )
        st.plotly_chart(fig)

    # Public vs private projects
    with c2:
        fig = donut_chart(
            "Public vs Private Projects",
            ["Public", "Private"],
            [metrics["public_projects"], metrics["private_projects"]],
            [ACCENT_BLUE, ACCENT_PINK],
        )
        st.plotly_chart(fig)

    with c3:
        fig = donut_chart(
            "Public vs Embargoed Registrations",
            ["Public", "Embargoed"],
            [metrics["public_regs"], metrics["embargoed_regs"]],
            [ACCENT_BLUE, ACCENT_PINK],
        )
        st.plotly_chart(fig)

    st.markdown("<br>", unsafe_allow_html=True)

    # Total OSF objects donut + Top 10 Licenses + Top 10 Add-ons (bars)
    c1, c2, c3 = st.columns(3)

    with c1:
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
            metrics["total_preprints"],
        ]
        colors = [
            ACCENT_BLUE,
            ACCENT_PINK,
            ACCENT_ORANGE,
            ACCENT_PURPLE,
            "#ffb36b",
        ]
        fig = donut_chart("Total OSF Objects", labels, values, colors)
        st.plotly_chart(fig)

    with c2:
        license_counts = Counter(
            lic for lic in projects.get("license", []) if lic not in ("", "-")
        )
        fig = bar_chart("Top 10 Licenses", license_counts)
        st.plotly_chart(fig)

    with c3:
        add_on_counter = Counter()
        for val in projects.get("add_ons", []):
            if not val:
                continue
            for part in str(val).split(","):
                name = part.strip()
                if name:
                    add_on_counter[name] += 1
        fig = bar_chart("Top 10 Add-ons", add_on_counter)
        st.plotly_chart(fig)

    st.markdown("<br>", unsafe_allow_html=True)

    # Storage regions donut
    c1, _, _ = st.columns(3)
    with c1:
        storage_counts = Counter(
            region if region else "Unknown"
            for region in pd.concat(
                [
                    projects.get("storage_region", pd.Series(dtype=str)),
                    registrations.get("storage_region", pd.Series(dtype=str)),
                    preprints.get("storage_region", pd.Series(dtype=str)),
                ]
            )
        )
        fig = donut_chart(
            "Top Storage Regions",
            list(storage_counts.keys()),
            list(storage_counts.values()),
            [ACCENT_BLUE, ACCENT_ORANGE, ACCENT_PINK, ACCENT_PURPLE],
        )
        st.plotly_chart(fig)


def users_toolbar(users: pd.DataFrame):
    """Right-aligned: Has ORCID, Department dropdown, Customize, Download, Chart."""
    cols = st.columns([4, 1.4, 2.4, 1.4, 0.9, 0.9])

    has_orcid_key = "users_filter_has_orcid"
    dept_key = "users_filter_department"
    customize_key = "users_customize_cols"

    with cols[0]:
        st.markdown(
            f"<span style='font-weight:600;color:{PRIMARY_BLUE};font-size:0.95rem;'>"
            f"{len(users)} Total Users</span>",
            unsafe_allow_html=True,
        )

    with cols[1]:
        has_orcid = st.checkbox(
            "Has ORCID",
            key=has_orcid_key,
            value=st.session_state.get(has_orcid_key, False),
        )

    with cols[2]:
        departments = sorted(
            [d for d in users.get("department", "").unique() if d not in ("", "-")]
        )
        options = ["All departments"] + departments
        current = st.session_state.get(dept_key, "All departments")
        dept_choice = st.selectbox(
            "Department", options, index=options.index(current) if current in options else 0
        )
        st.session_state[dept_key] = dept_choice

    with cols[3]:
        with st.popover("Customize"):
            st.write("Show columns")
            default_cols = [
                "name_or_title",
                "department",
                "osf_link",
                "orcid_id",
                "public_projects",
                "private_projects",
                "public_registration_count",
                "embargoed_registration_count",
                "published_preprint_count",
                "public_file_count",
                "storage_gb",
                "created_date",
                "modified_date",
                "month_last_login",
                "month_last_active",
            ]
            all_possible = [c for c in users.columns if c not in ("row_type",)]
            selected = st.multiselect(
                "",
                options=all_possible,
                default=[c for c in default_cols if c in all_possible],
                label_visibility="collapsed",
                key=customize_key,
            )

    with cols[4]:
        if st.button("⬇️", help="Download CSV"):
            csv = users.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV",
                csv,
                "users.csv",
                "text/csv",
                key="users_download_real",
            )

    with cols[5]:
        st.button("📊", help="(placeholder) Additional charts")

    filtered = users.copy()
    if has_orcid:
        filtered = filtered[filtered["orcid_id"].astype(str).str.strip().ne("")]

    if dept_choice != "All departments":
        filtered = filtered[filtered["department"] == dept_choice]

    selected_cols = st.session_state.get(customize_key)
    if not selected_cols:
        selected_cols = [
            "name_or_title",
            "department",
            "osf_link",
            "orcid_id",
            "public_projects",
            "private_projects",
            "public_registration_count",
            "embargoed_registration_count",
            "published_preprint_count",
            "public_file_count",
            "storage_gb",
            "created_date",
            "modified_date",
            "month_last_login",
            "month_last_active",
        ]
    selected_cols = [c for c in selected_cols if c in filtered.columns]

    return filtered, selected_cols


def generic_toolbar(label: str, df: pd.DataFrame, customize_key: str, download_name: str):
    cols = st.columns([4, 1.4, 0.9, 0.9])

    with cols[0]:
        st.markdown(
            f"<span style='font-weight:600;color:{PRIMARY_BLUE};font-size:0.95rem;'>"
            f"{len(df)} {label}</span>",
            unsafe_allow_html=True,
        )

    with cols[1]:
        with st.popover("Customize"):
            st.write("Show columns")
            all_possible = [c for c in df.columns if c not in ("row_type",)]
            default = all_possible[:8]
            selected = st.multiselect(
                "",
                options=all_possible,
                default=default,
                label_visibility="collapsed",
                key=customize_key,
            )

    with cols[2]:
        if st.button("⬇️", help="Download CSV", key=f"{download_name}_button"):
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV",
                csv,
                f"{download_name}.csv",
                "text/csv",
                key=f"{download_name}_download",
            )

    with cols[3]:
        st.button("📊", help="(placeholder) Additional charts", key=f"{download_name}_charts")

    selected_cols = st.session_state.get(customize_key) or [
        c for c in df.columns if c not in ("row_type",)
    ]
    selected_cols = [c for c in selected_cols if c in df.columns]

    return df, selected_cols


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main():
    st.set_page_config(layout="wide", page_title="Institutions Dashboard (Demo)")

    inject_css()

    try:
        df, summary_row, users, projects, registrations, preprints = load_data(DATA_FILE)
    except Exception as exc:
        st.error(f"Error loading data from {DATA_FILE}: {exc}")
        return

    # Branding header
    render_branding(summary_row)

    tabs = st.tabs(["Summary", "Users", "Projects", "Registrations", "Preprints"])

    # Summary
    with tabs[0]:
        render_summary_tab(summary_row, users, projects, registrations, preprints)

    # Users
    with tabs[1]:
        st.markdown("### Users")
        filtered_users, user_cols = users_toolbar(users)
        render_table(
            filtered_users,
            page_key="users_page",
            columns_to_show=user_cols,
            link_columns=["osf_link", "creator_orcid"],
        )

    # Projects
    with tabs[2]:
        st.markdown("### Projects")
        filtered_projects, proj_cols = generic_toolbar(
            "Projects", projects, "projects_customize_cols", "projects"
        )
        render_table(
            filtered_projects,
            page_key="projects_page",
            columns_to_show=proj_cols,
            link_columns=["osf_link"],
        )

    # Registrations
    with tabs[3]:
        st.markdown("### Registrations")
        filtered_regs, reg_cols = generic_toolbar(
            "Registrations", registrations, "registrations_customize_cols", "registrations"
        )
        render_table(
            filtered_regs,
            page_key="registrations_page",
            columns_to_show=reg_cols,
            link_columns=["osf_link"],
        )

    # Preprints
    with tabs[4]:
        st.markdown("### Preprints")
        filtered_preprints, pre_cols = generic_toolbar(
            "Preprints", preprints, "preprints_customize_cols", "preprints"
        )
        render_table(
            filtered_preprints,
            page_key="preprints_page",
            columns_to_show=pre_cols,
            link_columns=["osf_link", "doi"],
        )


if __name__ == "__main__":
    main()
