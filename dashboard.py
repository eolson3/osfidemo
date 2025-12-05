import math
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

DATA_FILE = "osfi_dashboard_data_with_summary_and_branding.csv"

# -----------------------------------
# Data loading
# -----------------------------------

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    # Convert numeric-ish columns to proper dtypes where helpful
    for col in [
        "storage_byte_count",
        "storage_gb",
        "views_last_30_days",
        "downloads_last_30_days",
        "public_projects",
        "private_projects",
        "public_registration_count",
        "embargoed_registration_count",
        "published_preprint_count",
        "public_file_count",
        "projects_public_count",
        "projects_private_count",
        "registrations_public_count",
        "registrations_embargoed_count",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


data = load_data(DATA_FILE)

# Split summary row from object rows
summary_row = data[data["object_type"] == "summary"]
if not summary_row.empty:
    summary_meta = summary_row.iloc[0]
else:
    summary_meta = pd.Series(dtype=object)

data_objects = data[data["object_type"] != "summary"].copy()

users_raw = data_objects[data_objects["object_type"] == "user"].copy()
projects_raw = data_objects[data_objects["object_type"] == "project"].copy()
regs_raw = data_objects[data_objects["object_type"] == "registration"].copy()
preprints_raw = data_objects[data_objects["object_type"] == "preprint"].copy()

# -----------------------------------
# Branding / header
# -----------------------------------

if not summary_meta.empty:
    INSTITUTION_NAME = str(
        summary_meta.get("branding_institution_name", "OSF Institution [Demo]")
    )
    INSTITUTION_LOGO_URL = str(
        summary_meta.get("branding_institution_logo_url", "")
    ).strip()
    REPORT_MONTH_LABEL = str(summary_meta.get("report_month", "")).strip()
else:
    INSTITUTION_NAME = "OSF Institution [Demo]"
    INSTITUTION_LOGO_URL = "https://osf.io/static/img/cos-white.svg"
    REPORT_MONTH_LABEL = ""

# Fallback: if no report_month in summary, use first from user rows
if not REPORT_MONTH_LABEL:
    rm = (
        users_raw.get("report_yearmonth", pd.Series([], dtype=str))
        .dropna()
        .astype(str)
    )
    rm = rm[rm != ""]
    if not rm.empty:
        REPORT_MONTH_LABEL = rm.iloc[0]

# -----------------------------------
# Helper styling
# -----------------------------------

st.set_page_config(
    page_title="OSF Institutions Dashboard (Demo)",
    layout="wide",
)

st.markdown(
    """
    <style>
    body {
        margin: 0;
        padding: 0;
    }
    .osf-header-bar {
        background-color: #12364a;
        padding: 18px 32px;
        display: flex;
        align-items: center;
        gap: 16px;
        color: white;
    }
    .osf-header-logo-fallback {
        width: 52px;
        height: 52px;
        border-radius: 50%;
        background: #0b2233;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 20px;
    }
    .osf-header-text-title {
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 2px;
    }
    .osf-header-text-subtitle {
        font-size: 14px;
        opacity: 0.9;
    }
    .osf-tab-strip {
        background-color: #f4f7fb;
        padding: 0 32px;
        border-bottom: 1px solid #e3e8f0;
    }
    .block-container {
        padding-top: 0.5rem;
    }
    .osf-section-title {
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .osf-metric-card {
        border-radius: 12px;
        border: 1px solid #e3e8f0;
        padding: 16px 18px;
        background-color: #ffffff;
    }
    .osf-metric-label {
        font-size: 13px;
        color: #6b7280;
        margin-bottom: 4px;
    }
    .osf-metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #111827;
    }
    .osf-toolbar {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
    }
    .osf-toolbar button {
        border-radius: 999px !important;
    }
    .osf-pagination {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        margin-top: 8px;
    }
    .osf-pagination span {
        font-size: 13px;
        color: #4b5563;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header bar
st.markdown('<div class="osf-header-bar">', unsafe_allow_html=True)
col_logo, col_text = st.columns([0.7, 5], gap="small")

with col_logo:
    if INSTITUTION_LOGO_URL:
        st.image(INSTITUTION_LOGO_URL, width=52)
    else:
        initials = "".join([w[0] for w in INSTITUTION_NAME.split()[:2]]).upper()
        st.markdown(
            f'<div class="osf-header-logo-fallback">{initials}</div>',
            unsafe_allow_html=True,
        )

with col_text:
    subtitle_bits = ["Institutions Dashboard (Demo)"]
    if REPORT_MONTH_LABEL:
        subtitle_bits.append(f"Report month: {REPORT_MONTH_LABEL}")
    subtitle = " • ".join(subtitle_bits)

    st.markdown(
        f"""
        <div class="osf-header-text-title">{INSTITUTION_NAME}</div>
        <div class="osf-header-text-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------
# Utility helpers
# -----------------------------------

def donut_chart(labels, values, title=None):
    if not labels or not values:
        st.info("No data available.")
        return
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                sort=False,
                direction="clockwise",
            )
        ]
    )
    fig.update_layout(
        showlegend=True,
        margin=dict(l=0, r=0, t=0, b=0),
        height=280,
    )
    if title:
        st.markdown(f"**{title}**")
    st.plotly_chart(fig, use_container_width=True)


def bar_chart(x, y, title=None):
    if len(x) == 0:
        st.info("No data available.")
        return
    fig = go.Figure([go.Bar(x=x, y=y)])
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=280,
    )
    if title:
        st.markdown(f"**{title}**")
    st.plotly_chart(fig, use_container_width=True)


def paginate_df(df: pd.DataFrame, page_size: int, page_number: int):
    total = len(df)
    if total == 0:
        return df, 0
    start = page_number * page_size
    end = start + page_size
    return df.iloc[start:end], math.ceil(total / page_size)


def render_pagination_controls(total_pages, current_page, key_prefix):
    if total_pages <= 1:
        return current_page

    col_prev2, col_prev, col_next, col_label = st.columns([0.5, 0.5, 0.5, 3])

    with col_prev2:
        if st.button("≪", key=f"{key_prefix}_first") and current_page > 0:
            current_page = 0
    with col_prev:
        if st.button("‹", key=f"{key_prefix}_prev") and current_page > 0:
            current_page -= 1
    with col_next:
        if st.button("›", key=f"{key_prefix}_next") and current_page < total_pages - 1:
            current_page += 1
    with col_label:
        st.markdown(
            f"<div class='osf-pagination'><span>Page {current_page+1} of {total_pages}</span></div>",
            unsafe_allow_html=True,
        )
    return current_page


def hyperlinkify(df: pd.DataFrame) -> pd.DataFrame:
    """Make URL-like fields clickable using markdown links."""
    df = df.copy()

    def make_link(text, url):
        if not isinstance(url, str) or url.strip() == "":
            return text
        if not isinstance(text, str) or text.strip() == "":
            text = url
        return f"[{text}]({url})"

    # osf_link already URL; linkify name_or_title if osf_link present
    if "osf_link" in df.columns and "name_or_title" in df.columns:
        df["name_or_title"] = [
            make_link(t, u) for t, u in zip(df["name_or_title"], df["osf_link"])
        ]

    # doi is URL-ish; linkify using itself
    if "doi" in df.columns:
        df["doi"] = [
            make_link(d, d) if isinstance(d, str) and d.startswith("http") else d
            for d in df["doi"]
        ]

    return df


# -----------------------------------
# Summary metrics (for top tiles)
# -----------------------------------

def compute_summary_metrics():
    total_users = len(users_raw)
    total_projects = len(projects_raw)
    total_regs = len(regs_raw)
    total_preprints = len(preprints_raw)

    total_public_files = (
        users_raw.get("public_file_count", pd.Series([], dtype=float)).fillna(0).sum()
    )

    total_storage_gb = (
        users_raw.get("storage_gb", pd.Series([], dtype=float)).fillna(0).sum()
    )

    logged_in_users = (
        users_raw.get("month_last_login", pd.Series([], dtype=str)).notna().sum()
    )
    active_users = (
        users_raw.get("month_last_active", pd.Series([], dtype=str)).notna().sum()
    )

    return dict(
        total_users=total_users,
        total_projects=total_projects,
        total_regs=total_regs,
        total_preprints=total_preprints,
        total_public_files=int(total_public_files),
        total_storage_gb=round(float(total_storage_gb), 1)
        if pd.notna(total_storage_gb)
        else 0,
        total_logged_in_users=logged_in_users,
        total_active_users=active_users,
    )


summary_metrics = compute_summary_metrics()

# -----------------------------------
# Tabs
# -----------------------------------

st.markdown('<div class="osf-tab-strip"></div>', unsafe_allow_html=True)

tab_labels = ["Summary", "Users", "Projects", "Registrations", "Preprints"]
current_tab = st.tabs(tab_labels)

# ------------ SUMMARY TAB ------------

with current_tab[0]:
    st.markdown('<div class="osf-section-title">Summary</div>', unsafe_allow_html=True)

    # Top metric tiles
    m = summary_metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"<div class='osf-metric-card'><div class='osf-metric-label'>Total Users</div><div class='osf-metric-value'>{m['total_users']}</div></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='osf-metric-card'><div class='osf-metric-label'>Total Monthly Logged in Users</div><div class='osf-metric-value'>{m['total_logged_in_users']}</div></div>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div class='osf-metric-card'><div class='osf-metric-label'>Total Monthly Active Users</div><div class='osf-metric-value'>{m['total_active_users']}</div></div>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"<div class='osf-metric-card'><div class='osf-metric-label'>OSF Public and Private Projects</div><div class='osf-metric-value'>{m['total_projects']}</div></div>",
            unsafe_allow_html=True,
        )

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown(
            f"<div class='osf-metric-card'><div class='osf-metric-label'>OSF Public and Embargoed Registrations</div><div class='osf-metric-value'>{m['total_regs']}</div></div>",
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            f"<div class='osf-metric-card'><div class='osf-metric-label'>OSF Preprints</div><div class='osf-metric-value'>{m['total_preprints']}</div></div>",
            unsafe_allow_html=True,
        )
    with c7:
        st.markdown(
            f"<div class='osf-metric-card'><div class='osf-metric-label'>Total Public File Count</div><div class='osf-metric-value'>{m['total_public_files']}</div></div>",
            unsafe_allow_html=True,
        )
    with c8:
        st.markdown(
            f"<div class='osf-metric-card'><div class='osf-metric-label'>Total Storage in GB</div><div class='osf-metric-value'>{m['total_storage_gb']}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Second row of donuts (users by dept; public/private projects; public/embargoed regs)
    cA, cB, cC = st.columns(3)

    # Total Users by Department
    with cA:
        if "department" in users_raw.columns:
            dept_counts = (
                users_raw["department"]
                .fillna("Unknown")
                .replace("", "Unknown")
                .value_counts()
            )
            donut_chart(
                dept_counts.index.tolist(),
                dept_counts.values.tolist(),
                title="Total Users by Department",
            )
        else:
            st.info("No department data available.")

    # Public vs Private Projects (summary counts)
    with cB:
        labels, values = [], []
        if not summary_meta.empty:
            pub = pd.to_numeric(
                summary_meta.get("projects_public_count"), errors="coerce"
            )
            priv = pd.to_numeric(
                summary_meta.get("projects_private_count"), errors="coerce"
            )
            if pd.notna(pub) and pub > 0:
                labels.append("Public")
                values.append(int(pub))
            if pd.notna(priv) and priv > 0:
                labels.append("Private")
                values.append(int(priv))

        if values:
            donut_chart(labels, values, title="Public vs Private Projects")
        else:
            st.info(
                "No public/private project counts provided yet. "
                "Edit the summary row in the CSV to add them."
            )

    # Public vs Embargoed Registrations (summary counts)
    with cC:
        labels, values = [], []
        if not summary_meta.empty:
            pub = pd.to_numeric(
                summary_meta.get("registrations_public_count"), errors="coerce"
            )
            emb = pd.to_numeric(
                summary_meta.get("registrations_embargoed_count"), errors="coerce"
            )
            if pd.notna(pub) and pub > 0:
                labels.append("Public")
                values.append(int(pub))
            if pd.notna(emb) and emb > 0:
                labels.append("Embargoed")
                values.append(int(emb))

        if values:
            donut_chart(labels, values, title="Public vs Embargoed Registrations")
        else:
            st.info(
                "No public/embargoed registration counts provided yet. "
                "Edit the summary row in the CSV to add them."
            )

    st.markdown("---")

    # Bottom row: Total OSF Objects; Top 10 Licenses; Top 10 Add-ons
    cD, cE, cF = st.columns(3)

    with cD:
        obj_counts = (
            data_objects["object_type"]
            .map(
                {
                    "project": "Projects",
                    "registration": "Registrations",
                    "preprint": "Preprints",
                    "user": "Users",
                }
            )
            .value_counts()
        )
        donut_chart(
            obj_counts.index.tolist(),
            obj_counts.values.tolist(),
            title="Total OSF Objects",
        )

    with cE:
        licenses = (
            data_objects["license"]
            .fillna("Unknown")
            .replace("", "Unknown")
            .value_counts()
            .head(10)
        )
        bar_chart(
            licenses.index.tolist(),
            licenses.values.tolist(),
            title="Top 10 Licenses",
        )

    with cF:
        if "add_ons" in data_objects.columns:
            addons = (
                data_objects["add_ons"]
                .fillna("Unknown")
                .replace("", "Unknown")
                .value_counts()
                .head(10)
            )
            bar_chart(
                addons.index.tolist(),
                addons.values.tolist(),
                title="Top 10 Add-ons",
            )
        else:
            st.info("No add-on data in CSV yet.")

# ------------ USERS TAB ------------

with current_tab[1]:
    st.markdown('<div class="osf-section-title">Users</div>', unsafe_allow_html=True)

    st.markdown(
        f"**{len(users_raw)} Total Users**",
    )

    # Toolbar (filters button exists but is just a placeholder for now)
    col_filt, col_cust, col_dl = st.columns([1, 1, 1])
    with col_filt:
        st.button("Filters")
    with col_cust:
        st.button("Customize")
    with col_dl:
        csv = users_raw.to_csv(index=False)
        st.download_button(
            "Download CSV",
            data=csv,
            file_name="users_filtered.csv",
            mime="text/csv",
        )

    # Table columns
    table_cols = [
        "name_or_title",
        "department",
        "orcid_id",
        "public_projects",
        "private_projects",
        "public_registration_count",
        "embargoed_registration_count",
        "published_preprint_count",
        "public_file_count",
        "storage_gb",
        "month_last_active",
        "month_last_login",
    ]
    df_display = users_raw.copy()
    df_display = df_display[table_cols]

    df_display = df_display.rename(
        columns={
            "name_or_title": "Name",
            "storage_gb": "Total Storage (GB)",
            "public_projects": "Public projects",
            "private_projects": "Private projects",
            "public_registration_count": "Public registrations",
            "embargoed_registration_count": "Embargoed registrations",
            "published_preprint_count": "Published preprints",
            "public_file_count": "Public file count",
            "month_last_active": "Last active",
            "month_last_login": "Last login",
        }
    )

    # Pagination
    page_size = 10
    page_state_key = "users_page"
    current_page = st.session_state.get(page_state_key, 0)
    df_page, total_pages = paginate_df(df_display, page_size, current_page)
    st.dataframe(df_page, use_container_width=True, hide_index=True)
    current_page = render_pagination_controls(total_pages, current_page, "users")
    st.session_state[page_state_key] = current_page

# ------------ PROJECTS TAB ------------

def render_object_tab(raw_df: pd.DataFrame, object_label: str, key_prefix: str):
    st.markdown(
        f"<div class='osf-section-title'>{object_label}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"**{len(raw_df)} Total {object_label}**")

    col_filt, col_cust, col_dl = st.columns([1, 1, 1])
    with col_filt:
        st.button("Filters", key=f"{key_prefix}_filters")
    with col_cust:
        st.button("Customize", key=f"{key_prefix}_customize")
    with col_dl:
        csv = raw_df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            data=csv,
            file_name=f"{key_prefix}_filtered.csv",
            mime="text/csv",
            key=f"{key_prefix}_download",
        )

    table_cols = [
        "name_or_title",
        "osf_link",
        "created_date",
        "modified_date",
        "doi",
        "storage_region",
        "storage_gb",
        "contributor_name",
        "views_last_30_days",
        "resource_type",
        "license",
        "add_ons",
        "funder_name",
    ]
    cols_existing = [c for c in table_cols if c in raw_df.columns]
    df_display = raw_df.copy()
    df_display = df_display[cols_existing]
    df_display = hyperlinkify(df_display)

    rename_map = {
        "name_or_title": "Title",
        "osf_link": "OSF Link",
        "created_date": "Created date",
        "modified_date": "Modified date",
        "storage_region": "Storage region",
        "storage_gb": "Total data stored on OSF (GB)",
        "contributor_name": "Creator(s)",
        "views_last_30_days": "Views (last 30 days)",
        "resource_type": "Resource type",
        "license": "License",
        "add_ons": "Add-ons",
        "funder_name": "Funder name",
    }
    df_display = df_display.rename(columns=rename_map)

    page_size = 10
    page_state_key = f"{key_prefix}_page"
    current_page = st.session_state.get(page_state_key, 0)
    df_page, total_pages = paginate_df(df_display, page_size, current_page)
    st.dataframe(df_page, use_container_width=True, hide_index=True)
    current_page = render_pagination_controls(total_pages, current_page, key_prefix)
    st.session_state[page_state_key] = current_page


with current_tab[2]:
    render_object_tab(projects_raw, "Projects", "projects")

# ------------ REGISTRATIONS TAB ------------

with current_tab[3]:
    render_object_tab(regs_raw, "Registrations", "registrations")

# ------------ PREPRINTS TAB ------------

with current_tab[4]:
    # Slightly different: also show downloads
    st.markdown(
        "<div class='osf-section-title'>Preprints</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"**{len(preprints_raw)} Total Preprints**")

    col_filt, col_cust, col_dl = st.columns([1, 1, 1])
    with col_filt:
        st.button("Filters", key="preprints_filters")
    with col_cust:
        st.button("Customize", key="preprints_customize")
    with col_dl:
        csv = preprints_raw.to_csv(index=False)
        st.download_button(
            "Download CSV",
            data=csv,
            file_name="preprints_filtered.csv",
            mime="text/csv",
            key="preprints_download",
        )

    table_cols = [
        "name_or_title",
        "osf_link",
        "created_date",
        "modified_date",
        "doi",
        "contributor_name",
        "views_last_30_days",
        "downloads_last_30_days",
        "license",
    ]
    cols_existing = [c for c in table_cols if c in preprints_raw.columns]
    df_display = preprints_raw.copy()
    df_display = df_display[cols_existing]
    df_display = hyperlinkify(df_display)

    df_display = df_display.rename(
        columns={
            "name_or_title": "Title",
            "osf_link": "OSF Link",
            "created_date": "Created date",
            "modified_date": "Modified date",
            "contributor_name": "Creator(s)",
            "views_last_30_days": "Views (last 30 days)",
            "downloads_last_30_days": "Downloads (last 30 days)",
        }
    )

    page_size = 10
    page_state_key = "preprints_page"
    current_page = st.session_state.get(page_state_key, 0)
    df_page, total_pages = paginate_df(df_display, page_size, current_page)
    st.dataframe(df_page, use_container_width=True, hide_index=True)
    current_page = render_pagination_controls(total_pages, current_page, "preprints")
    st.session_state[page_state_key] = current_page
