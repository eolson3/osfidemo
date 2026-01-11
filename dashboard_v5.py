
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st


DEFAULT_DATA_FILE = "osfi_dashboard_data_v5_no_users_tab.csv"


# ---------- Styling ----------
def inject_css() -> None:
    st.markdown(
        """
        <style>
            /* Page background approximating OSF Institutions UI */
            .stApp {
                background: #f3f8fb;
            }

            /* Keep content from hugging the top; avoid branding cutoff */
            section.main > div { padding-top: 1.5rem; }

            /* Header */
            .osfi-header {
                display: flex;
                align-items: center;
                gap: 14px;
                margin: 0.25rem 0 0.75rem 0;
            }
            .osfi-logo img {
                width: 44px;
                height: 44px;
                display: block;
            }
            .osfi-inst-name {
                font-size: 34px;
                font-weight: 800;
                line-height: 1.1;
                color: #2b3b4c;
            }
            .osfi-report {
                font-size: 14px;
                color: #6b7c93;
                margin-top: 4px;
            }

            /* Tabs */
            div[data-baseweb="tab-list"] {
                gap: 12px;
                border-bottom: 1px solid #e6edf3;
            }
            button[data-baseweb="tab"] {
                font-weight: 600;
                color: #2b3b4c;
            }
            button[data-baseweb="tab"][aria-selected="true"] {
                color: #f05a50;
                border-bottom: 2px solid #f05a50;
            }

            /* Cards */
            .osfi-cards {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 14px;
                margin: 0.75rem 0 0.75rem 0;
            }
            .osfi-card {
                background: #ffffff;
                border: 1px solid #e6edf3;
                border-radius: 10px;
                padding: 14px 14px;
                min-height: 74px;
            }
            .osfi-card-label {
                font-size: 12px;
                color: #6b7c93;
                margin-bottom: 6px;
                font-weight: 600;
            }
            .osfi-card-value {
                font-size: 20px;
                font-weight: 800;
                color: #2b3b4c;
            }

            /* Controls row */
            .osfi-controls-spacer { height: 6px; }

            /* HTML table */
            table.osfi-table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                background: #ffffff;
                border: 1px solid #e6edf3;
                border-radius: 10px;
                overflow: hidden;
            }
            table.osfi-table thead th {
                font-size: 13px;
                color: #2b3b4c;
                font-weight: 700;
                text-align: left;
                padding: 12px 10px;
                border-bottom: 1px solid #e6edf3;
                background: #ffffff;
                white-space: nowrap;
            }
            table.osfi-table tbody td {
                font-size: 13px;
                color: #2b3b4c;
                padding: 10px 10px;
                border-bottom: 1px solid #edf2f7;
                vertical-align: top;
            }
            table.osfi-table tbody tr:nth-child(odd) td {
                background: #f2f8fe;
            }
            table.osfi-table tbody tr:last-child td {
                border-bottom: none;
            }
            a.osfi-link {
                color: #1f6feb;
                text-decoration: none;
                font-weight: 600;
            }
            a.osfi-link:hover { text-decoration: underline; }

            /* Pagination */
            .osfi-pager {
                display: flex;
                align-items: center;
                justify-content: flex-end;
                gap: 10px;
                margin: 10px 0 2px 0;
            }
            .osfi-muted { color: #6b7c93; font-size: 12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------- Data ----------
@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        # allow relative lookup if running from repo root
        p = Path(__file__).parent / path
    if not p.exists():
        raise FileNotFoundError(f"Could not find data file: {path}")

    df = pd.read_csv(p, dtype=str).fillna("")
    if "row_type" not in df.columns:
        raise ValueError("CSV must include a 'row_type' column.")
    df["row_type"] = df["row_type"].str.strip().str.lower()
    return df


def get_summary_row(df: pd.DataFrame) -> pd.Series:
    s = df[df["row_type"] == "summary"]
    return s.iloc[0] if len(s) else pd.Series(dtype=str)


def subset(df: pd.DataFrame, row_type: str) -> pd.DataFrame:
    return df[df["row_type"] == row_type].copy()


# ---------- Helpers ----------
def human_int(x: str) -> str:
    try:
        if x is None or x == "":
            return "0"
        return f"{int(float(x)):,}"
    except Exception:
        return x or "0"


def human_float(x: str, digits: int = 1) -> str:
    try:
        if x is None or x == "":
            return "0.0"
        return f"{float(x):,.{digits}f}"
    except Exception:
        return x or "0.0"


def extract_osf_guid(osf_url: str) -> str:
    if not osf_url:
        return ""
    m = re.search(r"/([a-z0-9]{5})(?:/|$)", osf_url.strip(), flags=re.I)
    return m.group(1) if m else osf_url


def normalize_doi(doi: str) -> Tuple[str, str]:
    """
    Returns (doi_text, doi_url).
    Accepts DOI in forms like '10.xxxx/yyy' or full URL.
    """
    if not doi:
        return "", ""
    d = doi.strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I)
    d = re.sub(r"^doi:\s*", "", d, flags=re.I)
    return d, f"https://doi.org/{d}"


def render_header(summary_row: pd.Series) -> None:
    inst = (summary_row.get("branding_institution_name") or "").strip() or "Institution"
    report_month = (summary_row.get("report_month") or "").strip()
    logo_url = (summary_row.get("branding_institution_logo_url") or "").strip()

    if not logo_url:
        # safe fallback; avoids broken <img> if missing
        logo_url = "https://osf.io/static/img/cos-white.svg"

    header_html = f"""
    <div class="osfi-header">
        <div class="osfi-logo"><img src="{logo_url}" alt="logo"></div>
        <div class="osfi-brand-text">
            <div class="osfi-inst-name">{inst}</div>
            <div class="osfi-report">Institutions Dashboard (Demo) • Report month: {report_month}</div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def render_cards(items: List[Tuple[str, str]]) -> None:
    cards = []
    for label, value in items:
        cards.append(
            f"""
            <div class="osfi-card">
                <div class="osfi-card-label">{label}</div>
                <div class="osfi-card-value">{value}</div>
            </div>
            """
        )
    st.markdown(f'<div class="osfi-cards">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_customize(entity_key: str, all_cols: List[str], default_cols: List[str]) -> List[str]:
    """
    Checkbox-based column chooser (stable across Streamlit versions).
    """
    state_key = f"{entity_key}_selected_cols"
    if state_key not in st.session_state:
        st.session_state[state_key] = list(default_cols)

    selected = set(st.session_state[state_key])

    with st.expander("Customize", expanded=False):
        st.caption("Show/hide columns")
        # Keep consistent ordering: defaults first, then the rest.
        ordered = []
        for c in default_cols:
            if c in all_cols and c not in ordered:
                ordered.append(c)
        for c in all_cols:
            if c not in ordered:
                ordered.append(c)

        for c in ordered:
            checked = c in selected
            new_checked = st.checkbox(c, value=checked, key=f"{entity_key}_col_{c}")
            if new_checked:
                selected.add(c)
            else:
                selected.discard(c)

        st.session_state[state_key] = [c for c in ordered if c in selected]

    return st.session_state[state_key]


def render_filters(entity_key: str, df_entity: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filters", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            rt_vals = sorted([v for v in df_entity.get("resource_type", pd.Series([], dtype=str)).unique() if v])
            resource_type = st.selectbox("Resource Type", ["All"] + rt_vals, index=0, key=f"{entity_key}_rt")
        with col_b:
            lic_vals = sorted([v for v in df_entity.get("license", pd.Series([], dtype=str)).unique() if v])
            license_v = st.selectbox("License", ["All"] + lic_vals, index=0, key=f"{entity_key}_lic")
        with col_c:
            reg_vals = sorted([v for v in df_entity.get("storage_region", pd.Series([], dtype=str)).unique() if v])
            storage_region = st.selectbox("Storage Region", ["All"] + reg_vals, index=0, key=f"{entity_key}_sr")

    out = df_entity.copy()
    if "resource_type" in out.columns and resource_type != "All":
        out = out[out["resource_type"] == resource_type]
    if "license" in out.columns and license_v != "All":
        out = out[out["license"] == license_v]
    if "storage_region" in out.columns and storage_region != "All":
        out = out[out["storage_region"] == storage_region]
    return out


def html_table(df_show: pd.DataFrame, cols: List[str]) -> str:
    """
    Render a paged subset as HTML with OSF-ish styling.
    - OSF Link: display GUID, link to osf_link URL
    - DOI: display DOI text, link to doi URL
    """
    work = df_show.copy()

    # Link display columns
    if "osf_link" in work.columns:
        work["OSF Link"] = work["osf_link"].apply(lambda u: f'<a class="osfi-link" href="{u}" target="_blank">{extract_osf_guid(u)}</a>' if u else "")
    if "doi" in work.columns:
        def _doi_link(d: str) -> str:
            txt, url = normalize_doi(d)
            return f'<a class="osfi-link" href="{url}" target="_blank">{txt}</a>' if url else ""
        work["DOI"] = work["doi"].apply(_doi_link)

    # Friendly headers
    rename = {
        "name_or_title": "Name / Title",
        "created_date": "Created",
        "modified_date": "Modified",
        "storage_region": "Storage region",
        "storage_byte_count": "Storage (bytes)",
        "storage_gb": "Storage (GB)",
        "views_last_30_days": "Views (30d)",
        "downloads_last_30_days": "Downloads (30d)",
        "resource_type": "Resource type",
        "add_ons": "Add-ons",
    }
    work = work.rename(columns=rename)

    # Replace osf_link/doi with our display columns if present in chosen cols
    display_cols = []
    for c in cols:
        if c == "osf_link":
            display_cols.append("OSF Link")
        elif c == "doi":
            display_cols.append("DOI")
        else:
            display_cols.append(rename.get(c, c))

    # Ensure uniqueness and existence
    display_cols = [c for c in display_cols if c in work.columns]
    work = work[display_cols]

    # Build HTML
    html = work.to_html(index=False, escape=False, classes=["osfi-table"])
    return html


def render_entity_page(
    title: str,
    entity_key: str,
    df_entity: pd.DataFrame,
    default_cols: List[str],
) -> None:
    left, right1, right2 = st.columns([6, 2, 2])
    with left:
        st.markdown(f"### {title}")

    # Place expanders aligned right-ish
    with right1:
        df_filtered = render_filters(entity_key, df_entity)
    with right2:
        selected_cols = render_customize(entity_key, list(df_entity.columns), default_cols)

    st.markdown('<div class="osfi-controls-spacer"></div>', unsafe_allow_html=True)

    # Pagination config
    page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1, key=f"{entity_key}_ps")
    total_rows = len(df_filtered)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)

    # Keep page in range
    page_key = f"{entity_key}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    st.session_state[page_key] = max(1, min(st.session_state[page_key], total_pages))
    page = st.session_state[page_key]

    start = (page - 1) * page_size
    end = start + page_size
    df_page = df_filtered.iloc[start:end].copy()

    # Table
    st.markdown(html_table(df_page, selected_cols), unsafe_allow_html=True)

    # Pagination BELOW the table
    pager_cols = st.columns([6, 1, 1, 2])
    with pager_cols[1]:
        if st.button("«", key=f"{entity_key}_first", disabled=(page <= 1)):
            st.session_state[page_key] = 1
            st.rerun()
    with pager_cols[2]:
        if st.button("‹", key=f"{entity_key}_prev", disabled=(page <= 1)):
            st.session_state[page_key] = page - 1
            st.rerun()
    with pager_cols[3]:
        st.markdown(f"<div class='osfi-muted'>Page {page} of {total_pages}</div>", unsafe_allow_html=True)

    pager_cols2 = st.columns([6, 1, 1, 2])
    with pager_cols2[1]:
        if st.button("›", key=f"{entity_key}_next", disabled=(page >= total_pages)):
            st.session_state[page_key] = page + 1
            st.rerun()
    with pager_cols2[2]:
        if st.button("»", key=f"{entity_key}_last", disabled=(page >= total_pages)):
            st.session_state[page_key] = total_pages
            st.rerun()
    with pager_cols2[3]:
        st.markdown(f"<div class='osfi-muted'>{total_rows:,} results</div>", unsafe_allow_html=True)

    # Download currently-filtered dataset
    st.download_button(
        "Download CSV (filtered)",
        df_filtered.to_csv(index=False).encode("utf-8"),
        file_name=f"{entity_key}_filtered.csv",
        mime="text/csv",
        width="content",
        key=f"{entity_key}_dl",
    )


def main() -> None:
    st.set_page_config(page_title="OSF Institutions Dashboard (Demo)", layout="wide")
    inject_css()

    # Data source: file uploader first, else default file in repo
    uploaded = st.file_uploader("Upload dashboard CSV", type=["csv"])
    if uploaded is not None:
        df = pd.read_csv(uploaded, dtype=str).fillna("")
        if "row_type" not in df.columns:
            st.error("CSV must include a 'row_type' column.")
            st.stop()
        df["row_type"] = df["row_type"].str.strip().str.lower()
    else:
        try:
            df = load_data(DEFAULT_DATA_FILE)
        except FileNotFoundError as e:
            st.error(str(e))
            st.stop()

    summary_row = get_summary_row(df)
    render_header(summary_row)

    # Entities
    projects = subset(df, "project")
    registrations = subset(df, "registration")
    preprints = subset(df, "preprint")

    # Summary cards (no Users tab)
    # Logged-in/active users come from summary row if present; otherwise show blank.
    logged_in = human_int(summary_row.get("summary_monthly_logged_in_users", "0"))
    active_users = human_int(summary_row.get("summary_monthly_active_users", "0"))

    total_storage_gb = human_float(pd.to_numeric(pd.concat([projects["storage_gb"], registrations["storage_gb"], preprints["storage_gb"]], ignore_index=True), errors="coerce").fillna(0).sum(), 1)

    card_items = [
        ("Monthly logged-in users", logged_in),
        ("Monthly active users", active_users),
        ("Projects", human_int(str(len(projects)))),
        ("Registrations", human_int(str(len(registrations)))),
        ("Preprints", human_int(str(len(preprints)))),
        ("Total storage (GB)", total_storage_gb),
    ]

    # Keep grid balanced (4 columns); pad with empty cards if needed
    while len(card_items) % 4 != 0:
        card_items.append(("", ""))

    tabs = st.tabs(["Summary", "Projects", "Registrations", "Preprints"])

    with tabs[0]:
        render_cards(card_items)

    with tabs[1]:
        render_entity_page(
            title=f"{len(projects):,} Projects",
            entity_key="project",
            df_entity=projects,
            default_cols=[
                "name_or_title",
                "osf_link",
                "created_date",
                "modified_date",
                "storage_region",
                "storage_gb",
                "license",
                "resource_type",
                "add_ons",
            ],
        )

    with tabs[2]:
        render_entity_page(
            title=f"{len(registrations):,} Registrations",
            entity_key="registration",
            df_entity=registrations,
            default_cols=[
                "name_or_title",
                "osf_link",
                "created_date",
                "modified_date",
                "doi",
                "storage_region",
                "storage_gb",
                "license",
                "resource_type",
            ],
        )

    with tabs[3]:
        render_entity_page(
            title=f"{len(preprints):,} Preprints",
            entity_key="preprint",
            df_entity=preprints,
            default_cols=[
                "name_or_title",
                "osf_link",
                "created_date",
                "modified_date",
                "doi",
                "storage_region",
                "storage_gb",
                "license",
                "resource_type",
            ],
        )


if __name__ == "__main__":
    main()
