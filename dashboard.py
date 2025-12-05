import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

DATA_FILE = Path(__file__).parent / "osfi_institutions_dashboard.csv"

st.set_page_config(
    page_title="OSF Institutions Dashboard (Demo)",
    layout="wide",
)

# ---------------------------------------------------
# STYLING
# ---------------------------------------------------

st.markdown(
    """
    <style>
    body { margin: 0; padding: 0; }
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
    .customize-box {
        background-color: #ffffff;
        border: 1px solid #d0d4da;
        border-radius: 8px;
        padding: 0.4rem 0.5rem 0.25rem 0.5rem;
        margin-top: 0.35rem;
        max-width: 260px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15);
    }
    .customize-box label {
        font-size: 0.85rem;
        padding: 0.1rem 0;
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

# ---------------------------------------------------
# DATA LOADING
# ---------------------------------------------------

def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)

    numeric_cols = [
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
        "summary_monthly_logged_in_users",
        "summary_monthly_active_users",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


data = load_data(DATA_FILE)

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

# ---------------------------------------------------
# BRANDING / HEADER
# ---------------------------------------------------

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
    INSTITUTION_LOGO_URL = ""
    REPORT_MONTH_LABEL = ""

if not REPORT_MONTH_LABEL and "report_yearmonth" in users_raw.columns:
    rm = (
        users_raw["report_yearmonth"]
        .dropna()
        .astype(str)
        .str.strip()
    )
    rm = rm[rm != ""]
    if not rm.empty:
        REPORT_MONTH_LABEL = rm.iloc[0]

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

# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def donut_chart(labels, values, title=None, height=280):
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
        height=height,
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


def build_link_column_config(df: pd.DataFrame):
    cfg = {}
    for col in df.columns:
        lower = col.lower()
        is_link_col = "link" in lower or "url" in lower
        if not is_link_col:
            sample = df[col].dropna().astype(str).head(20)
            if not sample.empty and (sample.str.startswith("http").mean() > 0.6):
                is_link_col = True
        if is_link_col:
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


# ---------------------------------------------------
# SUMMARY METRICS (TILES)
# ---------------------------------------------------

def compute_summary_metrics():
    # Total counts from data (still reliable)
    total_users = len(users_raw)

    # Projects/registrations from summary if provided, else from data
    proj_pub = summary_meta.get("projects_public_count") if not summary_meta.empty else None
    proj_priv = summary_meta.get("projects_private_count") if not summary_meta.empty else None
    reg_pub = summary_meta.get("registrations_public_count") if not summary_meta.empty else None
    reg_emb = summary_meta.get("registrations_embargoed_count") if not summary_meta.empty else None

    if pd.notna(proj_pub) or pd.notna(proj_priv):
        total_projects = (proj_pub or 0) + (proj_priv or 0)
    else:
        total_projects = len(projects_raw)

    if pd.notna(reg_pub) or pd.notna(reg_emb):
        total_regs = (reg_pub or 0) + (reg_emb or 0)
    else:
        total_regs = len(regs_raw)

    total_preprints = len(preprints_raw)

    total_public_files = (
        users_raw.get("public_file_count", pd.Series([], dtype=float)).fillna(0).sum()
    )

    total_storage_gb = (
        users_raw.get("storage_gb", pd.Series([], dtype=float)).fillna(0).sum()
    )

    # Monthly logged-in / active: prefer summary write-ins
    if not summary_meta.empty:
        logged_in_users = summary_meta.get("summary_monthly_logged_in_users")
        active_users = summary_meta.get("summary_monthly_active_users")
    else:
        logged_in_users = None
        active_users = None

    if pd.isna(logged_in_users):
        logged_in_users = (
            users_raw.get("month_last_login", pd.Series([], dtype=str)).notna().sum()
        )

    if pd.isna(active_users):
        active_users = (
            users_raw.get("month_last_active", pd.Series([], dtype=str)).notna().sum()
        )

    return dict(
        total_users=int(total_users),
        total_projects=int(total_projects),
        total_regs=int(total_regs),
        total_preprints=int(total_preprints),
        total_public_files=int(total_public_files),
        total_storage_gb=round(float(total_storage_gb), 1)
        if pd.notna(total_storage_gb)
        else 0,
        total_logged_in_users=int(logged_in_users or 0),
        total_active_users=int(active_users or 0),
    )


summary_metrics = compute_summary_metrics()

# ---------------------------------------------------
# TABS
# ---------------------------------------------------

st.markdown('<div class="osf-tab-strip"></div>', unsafe_allow_html=True)
tabs = st.tabs(["Summary", "Users", "Projects", "Registrations", "Preprints"])

# ---------------------------------------------------
# SUMMARY TAB
# ---------------------------------------------------

with tabs[0]:
    st.markdown('<div class="osf-section-title">Summary</div>', unsafe_allow_html=True)

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

    # Donuts row 1
    cA, cB, cC = st.columns(3)

    # Users by department
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

    # Public vs Private projects from summary row
    with cB:
        labels, values = [], []
        if not summary_meta.empty:
            pub = summary_meta.get("projects_public_count")
            priv = summary_meta.get("projects_private_count")
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
                "No public/private project counts yet. "
                "Edit the summary row in the CSV to add them."
            )

    # Public vs Embargoed registrations from summary row
    with cC:
        labels, values = [], []
        if not summary_meta.empty:
            pub = summary_meta.get("registrations_public_count")
            emb = summary_meta.get("registrations_embargoed_count")
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
                "No public/embargoed registration counts yet. "
                "Edit the summary row in the CSV to add them."
            )

    st.markdown("---")

    # Donuts row 2
    cD, cE, cF = st.columns(3)

    # Total OSF Objects (exclude users)
    with cD:
        obj_counts = (
            data_objects["object_type"]
            .loc[data_objects["object_type"].isin(["project", "registration", "preprint"])]
            .map(
                {
                    "project": "Projects",
                    "registration": "Registrations",
                    "preprint": "Preprints",
                }
            )
            .value_counts()
        )
        donut_chart(
            obj_counts.index.tolist(),
            obj_counts.values.tolist(),
            title="Total OSF Objects",
        )

    # Top 10 licenses (normalized)
    with cE:
        license_series_parts = []
        for df_ in (projects_raw, regs_raw, preprints_raw):
            if "license" in df_.columns:
                license_series_parts.append(df_["license"])

        if license_series_parts:
            s = pd.concat(license_series_parts, ignore_index=True)
            s = s.dropna().astype(str)
            s = s.str.normalize("NFKC").str.strip()
            s = s.str.replace(r"\s+", " ", regex=True)
            s = s.str.split("|").explode().str.strip()
            s = s.replace("", "Unknown")
            license_counts = s.value_counts().head(10)
            bar_chart(
                license_counts.index.tolist(),
                license_counts.values.tolist(),
                title="Top 10 Licenses",
            )
        else:
            st.info("No license data available.")

    # Top 10 add-ons (split)
    with cF:
        if "add_ons" in data_objects.columns:
            addons_series = data_objects["add_ons"].dropna().astype(str)
            exploded = addons_series.str.split("|").explode().str.strip()
            exploded = exploded[exploded != ""]
            addons_counts = exploded.value_counts().head(10)
            bar_chart(
                addons_counts.index.tolist(),
                addons_counts.values.tolist(),
                title="Top 10 Add-ons",
            )
        else:
            st.info("No add-ons data available.")

    st.markdown("---")

    # Storage regions donut (slimmed, ignore Unknown)
    cG, _, _ = st.columns(3)
    with cG:
        regions_parts = []
        if "storage_region" in projects_raw.columns:
            regions_parts.append(projects_raw["storage_region"])
        if "storage_region" in regs_raw.columns:
            regions_parts.append(regs_raw["storage_region"])
        if regions_parts:
            regions = (
                pd.concat(regions_parts, ignore_index=True)
                .dropna()
                .astype(str)
                .str.strip()
            )
            regions = regions[regions != ""]
            counts = regions.value_counts().head(8)
            donut_chart(
                counts.index.tolist(),
                counts.values.tolist(),
                title="Top Storage Regions",
                height=220,
            )
        else:
            st.info("No storage region data available.")

# ---------------------------------------------------
# USERS TAB
# ---------------------------------------------------

with tabs[1]:
    st.markdown('<div class="osf-section-title">Users</div>', unsafe_allow_html=True)

    if "users_show_customize" not in st.session_state:
        st.session_state["users_show_customize"] = False

    def toggle_users_customize():
        st.session_state["users_show_customize"] = not st.session_state[
            "users_show_customize"
        ]

    ctop1, ctop2, ctop3 = st.columns([4, 1, 1])
    count_placeholder = ctop1.empty()
    with ctop2:
        st.button(
            "Customize",
            key="users_customize_btn",
            on_click=toggle_users_customize,
            use_container_width=True,
        )

    # Filters: department + ORCID presence
    st.markdown("##### Filters")
    ucol1, ucol2 = st.columns([2, 1])

    with ucol1:
        dept_options = (
            sorted(
                users_raw["department"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )
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

        display = df.rename(
            columns={
                "name_or_title": "Name",
                "department": "Department",
                "orcid_id": "ORCID iD",
                "public_projects": "Public projects",
                "private_projects": "Private projects",
                "public_registration_count": "Public registrations",
                "embargoed_registration_count": "Embargoed registrations",
                "published_preprint_count": "Published preprints",
                "public_file_count": "Public files",
                "storage_gb": "Total data stored on OSF (GB)",
                "month_last_active": "Last active (YYYY-MM)",
                "month_last_login": "Last login (YYYY-MM)",
                "report_yearmonth": "Report month (YYYY-MM)",
            }
        )

        allowed_cols = [
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
            "Last active (YYYY-MM)",
            "Last login (YYYY-MM)",
            "Report month (YYYY-MM)",
        ]
        existing = [c for c in allowed_cols if c in display.columns]
        display = display[existing]

        if st.session_state["users_show_customize"]:
            with ctop2:
                customize_columns_box(existing, "users")

        selected_cols = get_saved_columns(existing, "users")
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

        page_size = 10
        page_state_key = "users_page"
        current_page = st.session_state.get(page_state_key, 0)
        page_df, total_pages = paginate_df(display, page_size, current_page)
        col_cfg = build_link_column_config(page_df)
        st.dataframe(page_df, hide_index=True, use_container_width=True, column_config=col_cfg)
        current_page = render_pagination_controls(total_pages, current_page, "users")
        st.session_state[page_state_key] = current_page

# ---------------------------------------------------
# PROJECTS TAB
# ---------------------------------------------------

with tabs[2]:
    st.markdown('<div class="osf-section-title">Projects</div>', unsafe_allow_html=True)

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
    proj_count_placeholder = top_left_col.empty()

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
    resource_types_selected = []
    addons_selected = []

    if filter_col is not None:
        with filter_col:
            st.markdown("#### Filter By")

            if "contributor_name" in projects_raw.columns:
                with st.expander("Creator", expanded=False):
                    creator_options = sorted(
                        projects_raw["contributor_name"]
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

            if "license" in projects_raw.columns:
                with st.expander("License", expanded=False):
                    license_options = sorted(
                        projects_raw["license"]
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

            if "funder_name" in projects_raw.columns:
                with st.expander("Funder", expanded=False):
                    funder_options = sorted(
                        projects_raw["funder_name"]
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

            if "add_ons" in projects_raw.columns:
                with st.expander("Add-ons", expanded=False):
                    addon_options = sorted(
                        projects_raw["add_ons"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    addons_selected = st.multiselect(
                        "Add-on",
                        options=addon_options,
                        default=[],
                        key="projects_addons_filter",
                    )

    projects = projects_raw.copy()

    # AND behavior for creators
    if creators_selected and "contributor_name" in projects.columns:
        def has_all_creators(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return all(c in text for c in creators_selected)

        projects = projects[projects["contributor_name"].apply(has_all_creators)]

    if "projects_year_filter" in st.session_state and "created_date" in projects.columns:
        year_choice = st.session_state.get("projects_year_filter")
        if year_choice and year_choice != "All years":
            year_val = int(year_choice)
            years = pd.to_datetime(projects["created_date"], errors="coerce").dt.year
            projects = projects[years == year_val]

    if licenses_selected and "license" in projects.columns:
        projects = projects[projects["license"].isin(licenses_selected)]

    if regions_selected and "storage_region" in projects.columns:
        projects = projects[projects["storage_region"].isin(regions_selected)]

    if funders_selected and "funder_name" in projects.columns:
        projects = projects[projects["funder_name"].isin(funders_selected)]

    if resource_types_selected and "resource_type" in projects.columns:
        projects = projects[projects["resource_type"].isin(resource_types_selected)]

    if addons_selected and "add_ons" in projects.columns:
        def has_any_addon(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return any(a in text for a in addons_selected)

        projects = projects[projects["add_ons"].apply(has_any_addon)]

    proj_count_placeholder.markdown(f"**{len(projects):,} Total Projects**")

    with main_col:
        if projects.empty:
            st.info("No projects match the current filters.")
        else:
            df = projects.copy()
            display = df.rename(
                columns={
                    "name_or_title": "Title",
                    "osf_link": "OSF Link",
                    "created_date": "Created date",
                    "modified_date": "Modified date",
                    "doi": "DOI",
                    "storage_region": "Storage region",
                    "storage_gb": "Total data stored on OSF (GB)",
                    "contributor_name": "Creator(s)",
                    "views_last_30_days": "Views (last 30 days)",
                    "resource_type": "Resource type",
                    "license": "License",
                    "add_ons": "Add-ons",
                    "funder_name": "Funder name",
                }
            )

            allowed_cols = [
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
            existing = [c for c in allowed_cols if c in display.columns]
            display = display[existing]

            if st.session_state["projects_show_customize"]:
                with top_customize:
                    customize_columns_box(existing, "projects")

            selected_cols = get_saved_columns(existing, "projects")
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

            page_size = 10
            page_state_key = "projects_page"
            current_page = st.session_state.get(page_state_key, 0)
            page_df, total_pages = paginate_df(display, page_size, current_page)
            col_cfg = build_link_column_config(page_df)
            st.dataframe(page_df, hide_index=True, use_container_width=True, column_config=col_cfg)
            current_page = render_pagination_controls(total_pages, current_page, "projects")
            st.session_state[page_state_key] = current_page

# ---------------------------------------------------
# REGISTRATIONS TAB
# ---------------------------------------------------

with tabs[3]:
    st.markdown('<div class="osf-section-title">Registrations</div>', unsafe_allow_html=True)

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
    resource_types_selected = []

    if filter_col is not None:
        with filter_col:
            st.markdown("#### Filter By")

            if "contributor_name" in regs_raw.columns:
                with st.expander("Creator", expanded=False):
                    creator_options = sorted(
                        regs_raw["contributor_name"]
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

            if "license" in regs_raw.columns:
                with st.expander("License", expanded=False):
                    license_options = sorted(
                        regs_raw["license"]
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

            if "resource_type" in regs_raw.columns:
                with st.expander("Resource type", expanded=False):
                    rt_options = sorted(
                        regs_raw["resource_type"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    resource_types_selected = st.multiselect(
                        "Resource type",
                        options=rt_options,
                        default=[],
                        key="regs_resource_type_filter",
                    )

    regs = regs_raw.copy()

    if creators_selected and "contributor_name" in regs.columns:
        def has_all_creators(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return all(c in text for c in creators_selected)

        regs = regs[regs["contributor_name"].apply(has_all_creators)]

    if "regs_year_filter" in st.session_state and "created_date" in regs.columns:
        year_choice = st.session_state.get("regs_year_filter")
        if year_choice and year_choice != "All years":
            year_val = int(year_choice)
            years = pd.to_datetime(regs["created_date"], errors="coerce").dt.year
            regs = regs[years == year_val]

    if licenses_selected and "license" in regs.columns:
        regs = regs[regs["license"].isin(licenses_selected)]

    if regions_selected and "storage_region" in regs.columns:
        regs = regs[regs["storage_region"].isin(regions_selected)]

    if resource_types_selected and "resource_type" in regs.columns:
        regs = regs[regs["resource_type"].isin(resource_types_selected)]

    regs_count_placeholder.markdown(f"**{len(regs):,} Total Registrations**")

    with main_col:
        if regs.empty:
            st.info("No registrations match the current filters.")
        else:
            df = regs.copy()
            display = df.rename(
                columns={
                    "name_or_title": "Title",
                    "osf_link": "OSF Link",
                    "created_date": "Created date",
                    "modified_date": "Modified date",
                    "doi": "DOI",
                    "storage_region": "Storage region",
                    "storage_gb": "Total data stored on OSF (GB)",
                    "contributor_name": "Creator(s)",
                    "views_last_30_days": "Views (last 30 days)",
                    "resource_type": "Resource type",
                    "license": "License",
                    "funder_name": "Funder name",
                }
            )

            allowed_cols = [
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
            ]
            existing = [c for c in allowed_cols if c in display.columns]
            display = display[existing]

            if st.session_state["regs_show_customize"]:
                with top_customize:
                    customize_columns_box(existing, "regs")

            selected_cols = get_saved_columns(existing, "regs")
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

            page_size = 10
            page_state_key = "regs_page"
            current_page = st.session_state.get(page_state_key, 0)
            page_df, total_pages = paginate_df(display, page_size, current_page)
            col_cfg = build_link_column_config(page_df)
            st.dataframe(page_df, hide_index=True, use_container_width=True, column_config=col_cfg)
            current_page = render_pagination_controls(total_pages, current_page, "regs")
            st.session_state[page_state_key] = current_page

# ---------------------------------------------------
# PREPRINTS TAB
# ---------------------------------------------------

with tabs[4]:
    st.markdown('<div class="osf-section-title">Preprints</div>', unsafe_allow_html=True)

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
    licenses_selected = []

    if filter_col is not None:
        with filter_col:
            st.markdown("#### Filter By")

            if "contributor_name" in preprints_raw.columns:
                with st.expander("Creator", expanded=False):
                    creator_options = sorted(
                        preprints_raw["contributor_name"]
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

            if "license" in preprints_raw.columns:
                with st.expander("License", expanded=False):
                    license_options = sorted(
                        preprints_raw["license"]
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

    if creators_selected and "contributor_name" in preprints.columns:
        def has_all_creators(val: str) -> bool:
            text = str(val) if pd.notna(val) else ""
            return all(c in text for c in creators_selected)

        preprints = preprints[preprints["contributor_name"].apply(has_all_creators)]

    if "preprints_year_filter" in st.session_state and "created_date" in preprints.columns:
        year_choice = st.session_state.get("preprints_year_filter")
        if year_choice and year_choice != "All years":
            year_val = int(year_choice)
            years = pd.to_datetime(preprints["created_date"], errors="coerce").dt.year
            preprints = preprints[years == year_val]

    if licenses_selected and "license" in preprints.columns:
        preprints = preprints[preprints["license"].isin(licenses_selected)]

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
                    "contributor_name": "Creator(s)",
                    "views_last_30_days": "Views (last 30 days)",
                    "downloads_last_30_days": "Downloads (last 30 days)",
                    "license": "License",
                }
            )

            allowed_cols = [
                "Title",
                "OSF Link",
                "Created date",
                "Modified date",
                "DOI",
                "Creator(s)",
                "Views (last 30 days)",
                "Downloads (last 30 days)",
                "License",
            ]
            existing = [c for c in allowed_cols if c in display.columns]
            display = display[existing]

            if st.session_state["preprints_show_customize"]:
                with top_customize:
                    customize_columns_box(existing, "preprints")

            selected_cols = get_saved_columns(existing, "preprints")
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

            page_size = 10
            page_state_key = "preprints_page"
            current_page = st.session_state.get(page_state_key, 0)
            page_df, total_pages = paginate_df(display, page_size, current_page)
            col_cfg = build_link_column_config(page_df)
            st.dataframe(page_df, hide_index=True, use_container_width=True, column_config=col_cfg)
            current_page = render_pagination_controls(total_pages, current_page, "preprints")
            st.session_state[page_state_key] = current_page
