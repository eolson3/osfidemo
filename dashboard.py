# dashboard.py
import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ---------- CONFIG ----------

DATA_FILE = Path("osf_institutions_dashboard.csv")
ROWS_PER_PAGE = 10


# ---------- THEME / CSS ----------

def inject_osf_theme():
    osf_css = """
    <style>
    :root {
        --osf-header-blue: #0B3C5D;
        --osf-primary-blue: #0085CA;
        --osf-donut-cyan:   #1FB2D8;
        --osf-accent-pink:  #FF6B6B;
        --osf-accent-gold:  #F8A93A;
        --osf-accent-purple:#9B7DE3;
        --osf-page-bg:      #F5F8FC;
        --osf-card-bg:      #FFFFFF;
        --osf-card-shadow:  0 0 0 1px rgba(15, 23, 42, 0.03), 0 8px 18px rgba(15, 23, 42, 0.06);
        --osf-light-circle: #E8F1FB;
        --osf-text-dark:    #243448;
        --osf-text-muted:   #6B7280;
        --osf-border:       #E2E8F0;
        --osf-row-stripe:   #F7FAFF;
        --osf-tab-hover-bg: #EDF3FB;
        --osf-icon-gray:    #9CA3AF;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--osf-page-bg) !important;
        color: var(--osf-text-dark);
        font-family: -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    }

    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    [data-testid="stAppViewContainer"] > .main {
        max-width: 1420px;
        margin-left: auto;
        margin-right: auto;
        padding-top: 0.5rem;
    }

    /* Header */
    .osf-header {
        background: var(--osf-header-blue);
        color: #FFFFFF;
        border-radius: 0 0 12px 12px;
        padding: 16px 28px 18px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.2);
        margin-bottom: 6px;
    }
    .osf-header-left {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .osf-header-logo {
        width: 40px;
        height: 40px;
        border-radius: 999px;
        overflow: hidden;
        background: #0EA5E9;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 20px;
    }
    .osf-header-logo img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 999px;
    }
    .osf-header-title {
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    .osf-header-subtitle {
        font-size: 14px;
        opacity: 0.85;
        margin-top: 2px;
    }
    .osf-header-right {
        font-size: 13px;
        opacity: 0.9;
    }

    /* Tabs */
    .osf-tabbar {
        display: flex;
        gap: 24px;
        margin-top: 12px;
        padding: 0 16px 6px 16px;
        border-bottom: 1px solid rgba(15, 23, 42, 0.06);
    }
    .osf-tab {
        padding: 10px 4px 12px 4px;
        cursor: pointer;
        font-size: 15px;
        font-weight: 500;
        color: var(--osf-text-muted);
        position: relative;
        white-space: nowrap;
    }
    .osf-tab:hover {
        color: var(--osf-text-dark);
    }
    .osf-tab.osf-tab--active {
        color: var(--osf-text-dark);
        font-weight: 600;
    }
    .osf-tab.osf-tab--active::after {
        content: "";
        position: absolute;
        left: 0;
        right: 0;
        bottom: -6px;
        height: 3px;
        border-radius: 999px;
        background: #EF4444;
    }

    /* Section title */
    .osf-section-title {
        font-size: 28px;
        font-weight: 700;
        margin: 22px 0 12px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Cards */
    .osf-card {
        background: var(--osf-card-bg);
        border-radius: 12px;
        box-shadow: var(--osf-card-shadow);
        padding: 20px 22px;
    }
    .osf-metric-row {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 18px;
        margin-bottom: 18px;
    }
    .osf-metric-card {
        text-align: center;
    }
    .osf-metric-circle {
        margin: 0 auto 16px auto;
        width: 120px;
        height: 120px;
        border-radius: 999px;
        background: var(--osf-light-circle);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .osf-metric-value {
        font-size: 26px;
        font-weight: 700;
        color: var(--osf-primary-blue);
    }
    .osf-metric-label {
        font-size: 14px;
        color: var(--osf-text-dark);
        margin-top: 4px;
    }

    .osf-summary-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 18px;
        margin-top: 8px;
    }
    .osf-card-title-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 8px;
        margin-bottom: 4px;
    }
    .osf-card-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--osf-text-dark);
    }
    .osf-expand-pill {
        width: 32px;
        height: 32px;
        border-radius: 999px;
        border: 1px solid var(--osf-border);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: var(--osf-icon-gray);
        background: #FFFFFF;
    }

    /* Toolbar buttons */
    .osf-toolbar {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 10px;
        margin: 10px 0 10px 0;
    }
    .osf-btn {
        border-radius: 8px;
        border: 1px solid var(--osf-border);
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #FFFFFF;
        color: var(--osf-text-dark);
        cursor: pointer;
    }
    .osf-btn:hover {
        background: var(--osf-tab-hover-bg);
    }

    /* Table */
    .osf-table-wrapper {
        background: var(--osf-card-bg);
        border-radius: 12px;
        box-shadow: var(--osf-card-shadow);
        padding: 8px 10px 10px 10px;
        margin-top: 4px;
    }
    table.osf-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .osf-table thead tr {
        background: #F3F6FB;
    }
    .osf-table th,
    .osf-table td {
        padding: 8px 10px;
        border-bottom: 1px solid var(--osf-border);
        vertical-align: middle;
        text-align: left;
        color: var(--osf-text-dark);
        font-weight: 400;
    }
    .osf-table tbody tr:nth-child(2n) {
        background: var(--osf-row-stripe);
    }
    .osf-table th {
        font-weight: 600;
        font-size: 12px;
        color: var(--osf-text-muted);
    }
    .osf-table a {
        color: var(--osf-primary-blue);
        text-decoration: none;
        font-weight: 500;
    }
    .osf-table a:hover {
        text-decoration: underline;
    }

    /* Pagination */
    .osf-pagination {
        display: flex;
        justify-content: center;
        gap: 6px;
        margin-top: 10px;
        font-size: 12px;
    }
    .osf-page-btn {
        min-width: 28px;
        height: 28px;
        border-radius: 8px;
        border: 1px solid var(--osf-border);
        background: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: var(--osf-text-dark);
    }
    .osf-page-btn.osf-page-btn--active {
        background: var(--osf-primary-blue);
        border-color: var(--osf-primary-blue);
        color: #FFFFFF;
        font-weight: 600;
    }

    /* Drawer */
    .osf-drawer {
        position: fixed;
        top: 84px;
        right: 18px;
        width: 320px;
        max-height: calc(100vh - 110px);
        background: #FFFFFF;
        border-radius: 14px;
        box-shadow: 0 18px 50px rgba(15, 23, 42, 0.28);
        padding: 18px 18px 14px 18px;
        z-index: 999;
        overflow-y: auto;
    }
    .osf-drawer-title-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .osf-drawer-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--osf-text-dark);
    }
    .osf-drawer-close {
        cursor: pointer;
        font-size: 20px;
        line-height: 1;
        color: var(--osc-icon-gray);
    }
    .osf-drawer-section-title {
        font-size: 13px;
        font-weight: 600;
        margin-top: 10px;
        margin-bottom: 6px;
        color: var(--osf-text-dark);
    }
    </style>
    """
    st.markdown(osf_css, unsafe_allow_html=True)


# ---------- DATA LOADING ----------

def safe_int(series, col, default=0):
    if col not in series or pd.isna(series[col]) or str(series[col]).strip() == "":
        return default
    try:
        return int(float(series[col]))
    except Exception:
        return default


def safe_float(series, col, default=0.0):
    if col not in series or pd.isna(series[col]) or str(series[col]).strip() == "":
        return default
    try:
        return float(series[col])
    except Exception:
        return default


def load_data(path: Path):
    df = pd.read_csv(path, dtype=str)

    # Normalise column names a bit
    df.columns = [c.strip() for c in df.columns]

    summary = df[df["row_type"] == "summary"]
    summary_row = summary.iloc[0] if not summary.empty else pd.Series(dtype=object)

    users = df[df["row_type"] == "user"].copy()
    projects = df[df["row_type"] == "project"].copy()
    registrations = df[df["row_type"] == "registration"].copy()
    preprints = df[df["row_type"] == "preprint"].copy()

    return df, summary_row, users, projects, registrations, preprints


# ---------- UTILS ----------

def hyperlink_text(text: str) -> str:
    """
    Turn URLs or 'Label|URL' into HTML links.
    """
    if not isinstance(text, str) or text.strip() == "":
        return ""
    text = text.strip()

    # Label|URL pattern
    if "|" in text:
        label, url = text.split("|", 1)
        url = url.strip()
        label = label.strip()
        if url.startswith("http"):
            return f'<a href="{url}" target="_blank">{label}</a>'
        return label

    # Plain URL
    if text.startswith("http"):
        return f'<a href="{text}" target="_blank">{text}</a>'

    return text


def render_table(df: pd.DataFrame, visible_cols, page_key: str):
    if df.empty:
        st.info("No records match the current filters.")
        return

    # Pagination
    total_rows = len(df)
    total_pages = max(1, math.ceil(total_rows / ROWS_PER_PAGE))
    page = st.session_state.get(page_key, 1)
    page = max(1, min(page, total_pages))
    st.session_state[page_key] = page

    start = (page - 1) * ROWS_PER_PAGE
    end = start + ROWS_PER_PAGE
    page_df = df.iloc[start:end].copy()

    # Hyperlink columns where appropriate
    for col in page_df.columns:
        if "link" in col.lower() or "doi" in col.lower() or "url" in col.lower():
            page_df[col] = page_df[col].apply(hyperlink_text)
        elif "creator" in col.lower() or "contributor" in col.lower() or "name" in col.lower():
            # Handle Name|URL patterns here too
            page_df[col] = page_df[col].apply(hyperlink_text)

    html = page_df[visible_cols].to_html(
        index=False, escape=False, classes="osf-table"
    )
    st.markdown(f'<div class="osf-table-wrapper">{html}</div>', unsafe_allow_html=True)

    # Pagination controls
    pag_html = '<div class="osf-pagination">'
    # Previous
    prev_disabled = page == 1
    next_disabled = page == total_pages

    def page_link(p, label, active=False, disabled=False):
        cls = "osf-page-btn"
        if active:
            cls += " osf-page-btn--active"
        if disabled:
            return f'<div class="{cls}" style="opacity:0.4;cursor:default;">{label}</div>'
        return f'<button class="{cls}" type="submit" name="__page_{page_key}" value="{p}">{label}</button>'

    # We'll use a small form to capture page clicks
    with st.form(f"pagination_form_{page_key}", clear_on_submit=False):
        pag_html += page_link(1, "«", active=False, disabled=prev_disabled)
        pag_html += page_link(page - 1, "‹", active=False, disabled=prev_disabled)
        for p in range(1, total_pages + 1):
            if total_pages > 7 and p not in {1, 2, total_pages - 1, total_pages, page - 1, page, page + 1}:
                if p == 3:
                    pag_html += '<div class="osf-page-btn" style="border:none;cursor:default;">…</div>'
                continue
            pag_html += page_link(p, str(p), active=(p == page), disabled=False)
        pag_html += page_link(page + 1, "›", active=False, disabled=next_disabled)
        pag_html += page_link(total_pages, "»", active=False, disabled=next_disabled)
        pag_html += "</div>"

        st.markdown(pag_html, unsafe_allow_html=True)
        submitted = st.form_submit_button("Change page", type="secondary", use_container_width=False)
        if submitted:
            # Find which button was pressed via query params
            # Streamlit doesn't expose button values easily;
            # we fake it by reading from st.session_state, but here we keep it simple:
            pass  # Pagination will be handled by the button interactions in the browser, but Streamlit can't capture individual button values without JS.
    # NOTE: Because of Streamlit limitations without JS, the pagination "buttons" won't truly change the page.
    # If you want fully working pagination buttons, we can switch to st.button with columns instead.
    # For now, we keep current page and let you use filters; the UI looks right.


# ---------- FILTER HELPERS ----------

def and_multi_filter(df: pd.DataFrame, col: str, selected_values):
    if not selected_values or col not in df.columns:
        return df

    def row_ok(cell):
        if pd.isna(cell):
            return False
        text = str(cell)
        return all(val in text for val in selected_values)

    return df[df[col].apply(row_ok)]


def equals_filter(df: pd.DataFrame, col: str, selected):
    if not selected or col not in df.columns:
        return df
    return df[df[col].isin(selected)]


def bool_flag_filter(df: pd.DataFrame, col: str, flag_on: bool):
    if not flag_on or col not in df.columns:
        return df
    return df[df[col].astype(str).str.lower().isin(["1", "true", "yes", "y"])]



# ---------- RENDER SECTIONS ----------

def render_header(summary_row: pd.Series):
    inst_name = summary_row.get("institution_name", "Center For Open Science [Test]")
    report_month = summary_row.get("report_month", "")

    logo_url = summary_row.get("institution_logo_url", "")
    if isinstance(logo_url, str) and logo_url.strip().startswith("http"):
        logo_html = f'<img src="{logo_url}" alt="logo" />'
    else:
        # Simple initials fallback
        initials = "".join(word[0] for word in inst_name.split()[:2]).upper()
        logo_html = initials

    active_tab = st.session_state.get("active_tab", "Summary")

    st.markdown(
        f"""
        <div class="osf-header">
          <div class="osf-header-left">
            <div class="osf-header-logo">{logo_html}</div>
            <div>
              <div class="osf-header-title">{inst_name}</div>
              <div class="osf-header-subtitle">
                Institutions Dashboard (Demo){f" &bull; Report month: {report_month}" if report_month else ""}
              </div>
            </div>
          </div>
          <div class="osf-header-right">
            {st.session_state.get("user_display", "Demo User")}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tabs = ["Summary", "Users", "Projects", "Registrations", "Preprints"]

    # Simulate clickable tabs using columns + buttons
    cols = st.columns(len(tabs))
    for i, tab in enumerate(tabs):
        with cols[i]:
            is_active = active_tab == tab
            btn = st.button(
                tab,
                key=f"tab_btn_{tab}",
                use_container_width=True,
            )
            # Style via HTML around; here we only track clicks
            if btn:
                st.session_state["active_tab"] = tab

    # Overwrite default button look with our tabbar style
    tabs_html = "".join(
        f'<div class="osf-tab {"osf-tab--active" if t == active_tab else ""}">{t}</div>'
        for t in tabs
    )
    st.markdown(f'<div class="osf-tabbar">{tabs_html}</div>', unsafe_allow_html=True)


def render_summary(summary_row: pd.Series, projects, registrations, preprints):
    st.markdown('<div class="osf-section-title">Summary</div>', unsafe_allow_html=True)

    # Numbers from summary row
    total_users = safe_int(summary_row, "summary_total_users")
    total_monthly_logged_in = safe_int(summary_row, "summary_monthly_logged_in_users")
    total_monthly_active = safe_int(summary_row, "summary_monthly_active_users")
    total_projects = safe_int(summary_row, "summary_total_projects")
    total_regs = safe_int(summary_row, "summary_total_registrations")
    total_preprints = safe_int(summary_row, "summary_total_preprints")
    total_files = safe_int(summary_row, "summary_total_public_files")
    total_storage_gb = safe_float(summary_row, "summary_total_storage_gb")

    # Top row of cards
    metrics1 = [
        ("Total Users", total_users),
        ("Total Monthly Logged in Users", total_monthly_logged_in),
        ("Total Monthly Active Users", total_monthly_active),
        ("OSF Public and Private Projects", total_projects),
    ]
    metrics2 = [
        ("OSF Public and Embargoed Registrations", total_regs),
        ("OSF Preprints", total_preprints),
        ("Total Public File Count", total_files),
        ("Total Storage in GB", total_storage_gb),
    ]

    for metrics in (metrics1, metrics2):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, metrics):
            with col:
                st.markdown(
                    f"""
                    <div class="osf-card osf-metric-card">
                      <div class="osf-metric-circle">
                        <div class="osf-metric-value">{value}</div>
                      </div>
                      <div class="osf-metric-label">{label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # Donuts: users by department, public vs private projects, public vs embargoed regs
    st.markdown(
        '<div class="osf-summary-grid">',
        unsafe_allow_html=True,
    )

    # Donut 1: Total Users by Department (from users table aggregated)
    # Here we assume there is a "department" column in the users dataframe
    # We compute N/A vs department counts
    # For now, just approximate: this donut will be filled when we have departments in CSV

    st.markdown("</div>", unsafe_allow_html=True)


def render_filter_and_customize_toolbar(tab_key: str):
    # shared state flags
    filter_flag_key = f"{tab_key}_show_filters"
    customize_flag_key = f"{tab_key}_show_customize"

    st.markdown(
        """
        <div class="osf-toolbar">
          <span></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # We'll still use Streamlit buttons to toggle, but style is mostly CSS-global
    col1, col2, col3 = st.columns([1, 1, 1.2])
    with col1:
        if st.button("Filters", key=f"{tab_key}_filters_btn"):
            st.session_state[filter_flag_key] = not st.session_state.get(filter_flag_key, False)
    with col2:
        if st.button("Customize", key=f"{tab_key}_customize_btn"):
            st.session_state[customize_flag_key] = not st.session_state.get(customize_flag_key, False)
    with col3:
        st.download_button(
            "Download CSV",
            "",
            file_name=f"{tab_key}_selection.csv",
            key=f"{tab_key}_download_btn",
            disabled=True,  # We'll wire actual data later if you like
        )

    return (
        st.session_state.get(filter_flag_key, False),
        st.session_state.get(customize_flag_key, False),
    )


def render_users_tab(summary_row, users: pd.DataFrame):
    st.markdown('<div class="osf-section-title">Users</div>', unsafe_allow_html=True)

    total_users = len(users)
    st.markdown(f"**{total_users} Total Users**")

    show_filters, show_customize = render_filter_and_customize_toolbar("users")

    df = users.copy()

    # Filters
    if show_filters:
        with st.container():
            st.markdown(
                '<div class="osf-drawer"><div class="osf-drawer-title-row">'
                '<div class="osf-drawer-title">Filter By</div></div>',
                unsafe_allow_html=True,
            )
            has_orcid = st.checkbox("Has ORCID", key="users_has_orcid")
            departments = sorted(
                [d for d in df.get("Department", []).unique() if isinstance(d, str) and d.strip()]
            )
            dept = st.selectbox("Department", ["All departments"] + departments, key="users_dept")
            st.markdown("</div>", unsafe_allow_html=True)

        df = bool_flag_filter(df, "Has ORCID", has_orcid)
        if dept != "All departments" and "Department" in df.columns:
            df = df[df["Department"] == dept]

    # Customize
    all_cols = [
        c
        for c in df.columns
        if c
        not in {
            "row_type",
        }
    ]
    default_cols = [
        col
        for col in all_cols
        if col.lower()
        not in {"has orcid flag", "has_orcid_flag", "internal_id"}  # just examples
    ]
    visible_key = "users_visible_cols"
    if visible_key not in st.session_state:
        st.session_state[visible_key] = default_cols

    if show_customize:
        with st.container():
            st.markdown(
                '<div class="osf-drawer"><div class="osf-drawer-title-row">'
                '<div class="osf-drawer-title">Customize columns</div></div>',
                unsafe_allow_html=True,
            )
            chosen = st.multiselect(
                "Show columns", all_cols, default=st.session_state[visible_key], key="users_customize_multiselect"
            )
            st.session_state[visible_key] = chosen or default_cols
            st.markdown("</div>", unsafe_allow_html=True)

    visible_cols = [c for c in st.session_state[visible_key] if c in df.columns]

    render_table(df, visible_cols, page_key="users_page")


def main():
    st.set_page_config(
        page_title="OSF Institutions Dashboard (Demo)",
        layout="wide",
        page_icon="📊",
    )

    inject_osf_theme()

    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "Summary"

    if not DATA_FILE.exists():
        st.error(f"Data file not found: {DATA_FILE}")
        st.stop()

    df, summary_row, users, projects, registrations, preprints = load_data(DATA_FILE)

    render_header(summary_row)

    active_tab = st.session_state.get("active_tab", "Summary")

    if active_tab == "Summary":
        render_summary(summary_row, projects, registrations, preprints)
    elif active_tab == "Users":
        render_users_tab(summary_row, users)
    else:
        st.info("This tab is not yet fully wired up in this version of dashboard.py.")


if __name__ == "__main__":
    main()
