"""OSF Institutions Dashboard (Demo)

This version removes the CSV upload widget, fixes Summary rendering (no raw HTML output),
limits Customize to real per-tab columns, and renders OSF Link/DOI as GUID/DOI text
(not generic 'Open').

Expected input CSV: same directory as this script by default.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
DEFAULT_DATA_FILE = "osfi_dashboard_data_v5_no_users_tab.csv"  # keep in repo root next to dashboard.py

# Per-tab columns (only show these if present in the CSV)
PROJECT_COLS = [
    "name_or_title",
    "osf_link",
    "created_date",
    "modified_date",
    "storage_region",
    "storage_gb",
    "views_last_30_days",
    "downloads_last_30_days",
    "license",
    "resource_type",
    "add_ons",
    "funder_name",
]
REG_COLS = [
    "name_or_title",
    "osf_link",
    "created_date",
    "modified_date",
    "doi",
    "storage_region",
    "storage_gb",
    "views_last_30_days",
    "downloads_last_30_days",
    "license",
    "resource_type",
    "add_ons",
    "funder_name",
]
PREPRINT_COLS = [
    "name_or_title",
    "osf_link",
    "created_date",
    "modified_date",
    "doi",
    "license",
    "resource_type",
    "views_last_30_days",
    "downloads_last_30_days",
]

TAB_COLUMNS: Dict[str, List[str]] = {
    "project": PROJECT_COLS,
    "registration": REG_COLS,
    "preprint": PREPRINT_COLS,
}

# Filters that should exist on each tab
TAB_FILTERS: Dict[str, List[str]] = {
    "project": ["resource_type", "license", "storage_region"],
    "registration": ["resource_type", "license", "storage_region"],
    "preprint": ["resource_type", "license"],
}

# -----------------------------------------------------------------------------
# Styling
# -----------------------------------------------------------------------------

def inject_css() -> None:
    st.markdown(
        """
<style>
:root {
  --osfi-bg: #F3F8FC;
  --osfi-card: #FFFFFF;
  --osfi-border: #E6EEF6;
  --osfi-text: #22313F;
  --osfi-muted: #6B7C93;
  --osfi-link: #2E6DAD;
  --osfi-accent: #F04B4C;
}

.stApp {
  background: var(--osfi-bg);
}

/* Make tabs look more like the OSF dashboard */
.stTabs [data-baseweb="tab-list"] {
  gap: 20px;
}
.stTabs [data-baseweb="tab"] {
  height: 48px;
  padding: 0 10px;
}
.stTabs [aria-selected="true"] {
  border-bottom: 2px solid var(--osfi-accent) !important;
  color: var(--osfi-accent) !important;
}

/* Summary metrics */
div[data-testid="stMetric"] {
  background: var(--osfi-card);
  border: 1px solid var(--osfi-border);
  border-radius: 10px;
  padding: 14px 16px;
}
div[data-testid="stMetric"] label {
  color: var(--osfi-muted) !important;
}

/* Control row */
.osfi-controls {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  align-items: center;
}

/* Simple table wrapper */
.osfi-table-wrap {
  background: var(--osfi-card);
  border: 1px solid var(--osfi-border);
  border-radius: 10px;
  padding: 0;
  overflow: hidden;
}

.osfi-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.osfi-table thead th {
  text-align: left;
  color: var(--osfi-text);
  font-weight: 600;
  background: #FFFFFF;
  border-bottom: 1px solid var(--osfi-border);
  padding: 12px 12px;
  white-space: nowrap;
}
.osfi-table tbody td {
  padding: 12px 12px;
  border-bottom: 1px solid var(--osfi-border);
  color: var(--osfi-text);
  vertical-align: middle;
}
.osfi-table tbody tr:nth-child(odd) td {
  background: #F7FBFF;
}

.osfi-link a {
  color: var(--osfi-link);
  text-decoration: none;
  font-weight: 600;
}

/* Pagination */
.osfi-pagination {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  align-items: center;
  padding: 10px 0 0 0;
}

</style>
""",
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _normalize_cols(cols: List[str]) -> List[str]:
    return [re.sub(r"\s+", "_", c.strip().lower()) for c in cols]


def _as_int(val: str) -> int:
    try:
        return int(float(val))
    except Exception:
        return 0


def _as_float(val: str) -> float:
    try:
        return float(val)
    except Exception:
        return 0.0


def extract_osf_guid(value: str) -> str:
    if not value:
        return ""
    v = str(value).strip()
    # If it's already a bare GUID
    if re.fullmatch(r"[a-z0-9]{5}", v, flags=re.IGNORECASE):
        return v.lower()
    # Pull guid from URLs like https://osf.io/kr68a/ or .../registrations/kr68a
    m = re.search(r"/([a-z0-9]{5})(?:[_/]|$)", v, flags=re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return ""


def normalize_doi(value: str) -> str:
    if not value:
        return ""
    v = str(value).strip()
    v = re.sub(r"^https?://(dx\.)?doi\.org/", "", v, flags=re.IGNORECASE)
    v = re.sub(r"^doi:\s*", "", v, flags=re.IGNORECASE)
    return v.strip()


def make_osf_url(guid_or_url: str) -> str:
    guid = extract_osf_guid(guid_or_url)
    if guid:
        return f"https://osf.io/{guid}/"
    # If it's already a URL, return as-is
    if str(guid_or_url).startswith("http"):
        return str(guid_or_url)
    return ""


def make_doi_url(doi_or_url: str) -> str:
    doi = normalize_doi(doi_or_url)
    return f"https://doi.org/{doi}" if doi else ""


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_data(path: str) -> Tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path, dtype=str).fillna("")

    # Normalize column names
    original_cols = df.columns.tolist()
    df.columns = _normalize_cols(original_cols)

    if "row_type" not in df.columns:
        raise ValueError("CSV must include a 'row_type' column.")

    # Split out rows
    branding_row = df[df["row_type"].str.lower() == "summary"].head(1)
    summary_row = df[df["row_type"].str.lower() == "summary"].head(1)

    projects = df[df["row_type"].str.lower() == "project"].copy()
    registrations = df[df["row_type"].str.lower() == "registration"].copy()
    preprints = df[df["row_type"].str.lower() == "preprint"].copy()

    # Branding + summary
    branding = {}
    if not branding_row.empty:
        r = branding_row.iloc[0].to_dict()
        branding = {
            "institution_name": r.get("branding_institution_name") or r.get("name_or_title") or "",
            "logo_url": r.get("branding_institution_logo_url") or "",
            "report_month": r.get("report_month") or r.get("report_yearmonth") or "",
        }

    summary = {}
    if not summary_row.empty:
        r = summary_row.iloc[0].to_dict()
        summary = {
            "total_users": _as_int(r.get("total_users", "0")),
            "monthly_logged_in": _as_int(r.get("summary_monthly_logged_in_users", "0")),
            "monthly_active": _as_int(r.get("summary_monthly_active_users", "0")),
            # Table-derived totals (preferred)
            "projects_total": len(projects),
            "registrations_total": len(registrations),
            "preprints_total": len(preprints),
            "public_file_total": sum(_as_int(x) for x in pd.to_numeric(projects.get("public_file_count", "0"), errors="coerce").fillna(0).tolist()),
            "storage_gb_total": sum(_as_float(x) for x in pd.to_numeric(projects.get("storage_gb", "0"), errors="coerce").fillna(0).tolist()),
        }

    return df, branding, summary, projects, registrations, preprints


# -----------------------------------------------------------------------------
# UI components
# -----------------------------------------------------------------------------


def render_branding(branding: dict) -> None:
    # Avoid brittle HTML rendering: use native components.
    logo_url = branding.get("logo_url") or ""
    inst_name = branding.get("institution_name") or ""
    report_month = branding.get("report_month") or ""

    c1, c2 = st.columns([0.08, 0.92])
    with c1:
        if logo_url:
            try:
                st.image(logo_url, width=44)
            except Exception:
                st.write("")
    with c2:
        st.markdown(f"### {inst_name}" if inst_name else "### Institutions Dashboard")
        sub = "Institutions Dashboard (Demo)"
        if report_month:
            sub += f" • Report month: {report_month}"
        st.caption(sub)


def render_summary(summary: dict) -> None:
    # Two rows of 4 metrics (similar layout)
    row1 = st.columns(4)
    row1[0].metric("Total users", f"{summary.get('total_users', 0):,}")
    row1[1].metric("Monthly logged-in users", f"{summary.get('monthly_logged_in', 0):,}")
    row1[2].metric("Monthly active users", f"{summary.get('monthly_active', 0):,}")
    row1[3].metric("Projects", f"{summary.get('projects_total', 0):,}")

    row2 = st.columns(4)
    row2[0].metric("Registrations", f"{summary.get('registrations_total', 0):,}")
    row2[1].metric("Preprints", f"{summary.get('preprints_total', 0):,}")
    row2[2].metric("Total public file count", f"{summary.get('public_file_total', 0):,}")
    row2[3].metric("Total storage (GB)", f"{summary.get('storage_gb_total', 0.0):,.1f}")


def build_filters(entity_key: str, df_entity: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """Return filtered df + selected filter values."""
    selected = {}

    filter_fields = TAB_FILTERS.get(entity_key, [])
    if not filter_fields:
        return df_entity, selected

    with st.expander("Filters", expanded=False):
        for field in filter_fields:
            if field not in df_entity.columns:
                continue
            options = sorted([x for x in df_entity[field].unique().tolist() if x != ""])
            label = field.replace("_", " ").title()
            choice = st.selectbox(label, ["All"] + options, key=f"{entity_key}_flt_{field}")
            selected[field] = choice

    out = df_entity
    for field, choice in selected.items():
        if choice and choice != "All" and field in out.columns:
            out = out[out[field] == choice]

    return out, selected


def render_customize(entity_key: str, available_cols: List[str], default_cols: List[str]) -> List[str]:
    """Checkbox-based column selector; returns selected columns."""

    # Streamlit popover is not available in some deployments; fall back to expander.
    use_popover = hasattr(st, "popover")
    selected = []

    if use_popover:
        container = st.popover("Customize", key=f"{entity_key}_customize")
    else:
        container = st.expander("Customize", expanded=False)

    with container:
        st.caption("Columns")
        for col in available_cols:
            checked = col in default_cols
            checked = st.checkbox(col.replace("_", " "), value=checked, key=f"{entity_key}_col_{col}")
            if checked:
                selected.append(col)

    # Safety: if user deselects everything, keep at least one
    if not selected:
        selected = default_cols[:1] if default_cols else available_cols[:1]

    return selected


def dataframe_to_html(df: pd.DataFrame, columns: List[str]) -> str:
    """Render a lightweight HTML table matching the OSF-ish look."""

    def cell(col: str, val: str) -> str:
        v = "" if val is None else str(val)
        if col == "osf_link":
            guid = extract_osf_guid(v)
            if guid:
                url = make_osf_url(guid)
                return f'<span class="osfi-link"><a href="{url}" target="_blank" rel="noopener">{guid}</a></span>'
            url = make_osf_url(v)
            return f'<span class="osfi-link"><a href="{url}" target="_blank" rel="noopener">link</a></span>' if url else ""
        if col == "doi":
            doi = normalize_doi(v)
            if doi:
                url = make_doi_url(doi)
                return f'<span class="osfi-link"><a href="{url}" target="_blank" rel="noopener">{doi}</a></span>'
            return ""
        return v

    cols = [c for c in columns if c in df.columns]

    head = "".join([f"<th>{c.replace('_', ' ')}</th>" for c in cols])
    body_rows = []
    for _, r in df[cols].iterrows():
        tds = "".join([f"<td>{cell(c, r.get(c, ''))}</td>" for c in cols])
        body_rows.append(f"<tr>{tds}</tr>")

    body = "".join(body_rows)
    return (
        '<div class="osfi-table-wrap">'
        '<table class="osfi-table">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</div>"
    )


def paginate(df: pd.DataFrame, entity_key: str, page_size: int = 25) -> Tuple[pd.DataFrame, int, int]:
    total = len(df)
    if total == 0:
        return df, 1, 1

    total_pages = max(1, (total + page_size - 1) // page_size)
    page_key = f"{entity_key}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    # Clamp
    st.session_state[page_key] = max(1, min(total_pages, st.session_state[page_key]))

    start = (st.session_state[page_key] - 1) * page_size
    end = start + page_size
    return df.iloc[start:end].copy(), st.session_state[page_key], total_pages


def render_pagination_controls(entity_key: str, current_page: int, total_pages: int) -> None:
    st.markdown('<div class="osfi-pagination">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([0.08, 0.08, 0.2, 0.64])

    with c1:
        if st.button("«", key=f"{entity_key}_first", disabled=current_page == 1):
            st.session_state[f"{entity_key}_page"] = 1
            st.rerun()
    with c2:
        if st.button("‹", key=f"{entity_key}_prev", disabled=current_page == 1):
            st.session_state[f"{entity_key}_page"] = max(1, current_page - 1)
            st.rerun()
    with c3:
        st.write(f"Page {current_page} of {total_pages}")
    with c4:
        if st.button("›", key=f"{entity_key}_next", disabled=current_page >= total_pages):
            st.session_state[f"{entity_key}_page"] = min(total_pages, current_page + 1)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_entity_tab(entity_label: str, entity_key: str, df_entity: pd.DataFrame) -> None:
    # Title
    st.markdown(f"### {len(df_entity):,} {entity_label}")

    # Filters + controls row
    filtered, _ = build_filters(entity_key, df_entity)

    # Per-tab columns (only show actual columns)
    allowed_cols = [c for c in TAB_COLUMNS[entity_key] if c in df_entity.columns]
    default_cols = allowed_cols

    # Controls: Customize + Download are always available
    c_controls = st.columns([0.7, 0.3])[1]
    with c_controls:
        st.markdown('<div class="osfi-controls">', unsafe_allow_html=True)
        selected_cols = render_customize(entity_key, allowed_cols, default_cols)
        csv_bytes = filtered[selected_cols].to_csv(index=False).encode("utf-8")
        # Use new width API (Streamlit warning avoidance)
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name=f"{entity_key}s.csv",
            mime="text/csv",
            width="content",
            key=f"{entity_key}_download",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Paginate + render table
    page_df, page, pages = paginate(filtered, entity_key, page_size=25)
    table_html = dataframe_to_html(page_df, selected_cols)
    st.markdown(table_html, unsafe_allow_html=True)

    # Pagination BELOW the table
    render_pagination_controls(entity_key, page, pages)


# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="Institutions Dashboard (Demo)", layout="wide")
    inject_css()

    # No upload widget; expect a repo-local CSV.
    data_path = Path(__file__).parent / DEFAULT_DATA_FILE
    if not data_path.exists():
        st.error(
            "Dashboard data CSV not found. "
            f"Expected to find '{DEFAULT_DATA_FILE}' next to dashboard.py in the repository."
        )
        st.stop()

    _, branding, summary, projects, registrations, preprints = load_data(str(data_path))

    render_branding(branding)

    tabs = st.tabs(["Summary", "Projects", "Registrations", "Preprints"])

    with tabs[0]:
        render_summary(summary)

    with tabs[1]:
        render_entity_tab("Projects", "project", projects)

    with tabs[2]:
        render_entity_tab("Registrations", "registration", registrations)

    with tabs[3]:
        render_entity_tab("Preprints", "preprint", preprints)


if __name__ == "__main__":
    main()
