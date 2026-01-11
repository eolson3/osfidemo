# dashboard_v7.py
# OSF Institutions Dashboard (Demo) - Streamlit
# - No file upload UX (expects a CSV in repo / path)
# - Robust CSV parsing (row_type + summary counts)
# - Branding header rendering (logo + institution name + report month)
# - Customize popover uses checkboxes for REAL columns only
# - OSF Link / DOI rendered as GUID/DOI text (not "Open")

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st


# -----------------------------
# Configuration
# -----------------------------

DEFAULT_DATA_FILE = os.environ.get("OSFI_DASHBOARD_CSV", "osfi_dashboard_data.csv")

TABS = ["Summary", "Projects", "Registrations", "Preprints"]

# Column sets per entity tab (only show these by default; Customize can toggle within this universe)
ENTITY_COLUMNS: Dict[str, List[str]] = {
    "project": [
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
    ],
    "registration": [
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
    ],
    "preprint": [
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
        "funder_name",
    ],
}

# Filter controls per entity
ENTITY_FILTERS: Dict[str, List[str]] = {
    "project": ["resource_type", "license", "storage_region"],
    "registration": ["resource_type", "license", "storage_region"],
    "preprint": ["resource_type", "license", "storage_region"],
}

# Branding fields (embedded in summary row in your CSV)
BRANDING_FIELDS = [
    "branding_institution_name",
    "branding_institution_logo_url",
    "report_month",
]


# -----------------------------
# Utilities
# -----------------------------

def _norm_col(c: str) -> str:
    c = c.strip()
    c = re.sub(r"\s+", "_", c)
    return c.lower()


def _as_int(x) -> int:
    try:
        if x is None:
            return 0
        s = str(x).strip()
        if s == "":
            return 0
        # allow commas
        s = s.replace(",", "")
        return int(float(s))
    except Exception:
        return 0


def _as_float(x) -> float:
    try:
        if x is None:
            return 0.0
        s = str(x).strip()
        if s == "":
            return 0.0
        s = s.replace(",", "")
        return float(s)
    except Exception:
        return 0.0


def _extract_guid(value: str) -> str:
    """Return a short OSF GUID from a field that may be a GUID or URL."""
    if value is None:
        return ""
    s = str(value).strip()
    if s == "" or s.lower() in {"none", "nan"}:
        return ""
    # common: "kr68a" or "https://osf.io/kr68a/" or ".../preprints/.../abcd/"
    parts = re.split(r"[\/\s]+", s)
    parts = [p for p in parts if p]
    if not parts:
        return s
    cand = parts[-1]
    # sometimes trailing _v2 etc; keep base guid-like token
    cand = cand.split("?")[0].split("#")[0]
    cand = cand.split("_")[0]
    return cand


def _doi_url(doi: str) -> str:
    d = str(doi).strip()
    if d == "" or d.lower() in {"none", "nan"}:
        return ""
    # remove leading resolver if present
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I)
    return f"https://doi.org/{d}"


def _is_truthy(x: str) -> bool:
    return str(x).strip().lower() in {"1", "true", "t", "yes", "y"}


# -----------------------------
# Data loading
# -----------------------------

@st.cache_data(show_spinner=False)
def load_data(path: str) -> Tuple[pd.DataFrame, Dict[str, str], pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found at: {p.resolve()}")

    df = pd.read_csv(p, dtype=str).fillna("")
    # normalize column names
    df.columns = [_norm_col(c) for c in df.columns]

    if "row_type" not in df.columns:
        raise ValueError("CSV must include a 'row_type' column (summary/project/registration/preprint).")

    # normalize row_type values
    df["row_type"] = df["row_type"].astype(str).str.strip().str.lower()

    # summary row
    summary_df = df[df["row_type"] == "summary"]
    if summary_df.empty:
        # allow: infer summary by taking first row if it has branding/summary fields
        summary_row = pd.Series(dtype=str)
    else:
        summary_row = summary_df.iloc[0]

    # branding comes from summary row fields
    branding = {}
    for k in BRANDING_FIELDS:
        if k in df.columns and not summary_df.empty:
            branding[k] = str(summary_row.get(k, "")).strip()
        else:
            branding[k] = ""

    projects = df[df["row_type"] == "project"].copy()
    registrations = df[df["row_type"] == "registration"].copy()
    preprints = df[df["row_type"] == "preprint"].copy()

    return df, branding, summary_row, projects, registrations, preprints


def compute_summary_counts(summary_row: pd.Series, projects: pd.DataFrame, registrations: pd.DataFrame, preprints: pd.DataFrame) -> Dict[str, float]:
    """Prefer explicit summary_* fields when present; otherwise compute from entity tables."""
    out: Dict[str, float] = {}

    # Users counts (may be absent since no users tab)
    out["total_users"] = _as_int(summary_row.get("total_users", "0")) if isinstance(summary_row, pd.Series) else 0
    out["monthly_logged_in_users"] = _as_int(summary_row.get("summary_monthly_logged_in_users", "0")) if isinstance(summary_row, pd.Series) else 0
    out["monthly_active_users"] = _as_int(summary_row.get("summary_monthly_active_users", "0")) if isinstance(summary_row, pd.Series) else 0

    # Entity totals from the tables (per your requirement)
    out["projects"] = float(len(projects))
    out["registrations"] = float(len(registrations))
    out["preprints"] = float(len(preprints))

    # Total public file count / storage should be totals from the tables
    def _col_numeric_sum(frame: pd.DataFrame, col: str) -> float:
        if col not in frame.columns:
            return 0.0
        s = pd.to_numeric(frame[col], errors="coerce")
        s = s.fillna(0)
        return float(s.sum())

    out["total_public_file_count"] = (
        _col_numeric_sum(projects, "public_file_count")
        + _col_numeric_sum(registrations, "public_file_count")
        + _col_numeric_sum(preprints, "public_file_count")
    )

    # storage_gb may exist; otherwise compute from bytes
    total_storage_gb = _col_numeric_sum(projects, "storage_gb") + _col_numeric_sum(registrations, "storage_gb") + _col_numeric_sum(preprints, "storage_gb")
    if total_storage_gb == 0.0:
        total_storage_bytes = _col_numeric_sum(projects, "storage_byte_count") + _col_numeric_sum(registrations, "storage_byte_count") + _col_numeric_sum(preprints, "storage_byte_count")
        total_storage_gb = total_storage_bytes / (1024**3)
    out["total_storage_gb"] = float(total_storage_gb)

    return out


# -----------------------------
# UI helpers
# -----------------------------

def inject_css() -> None:
    st.markdown(
        """
<style>
/* Remove Streamlit default top padding so branding isn't cut off */
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* Branding header */
.osfi-brand-wrap{
  display:flex; align-items:center; gap:14px;
  padding: 8px 0 10px 0;
}
.osfi-logo{
  width:44px; height:44px; border-radius: 6px;
  display:flex; align-items:center; justify-content:center;
  overflow:hidden;
}
.osfi-logo img{ width:44px; height:44px; object-fit:contain; }
.osfi-inst-name{
  font-size: 34px; font-weight: 700; color:#243447; line-height: 1.05;
}
.osfi-report{
  font-size: 14px; color:#6b7785; margin-top: 6px;
}
.osfi-tabs-hr{ border-top: 1px solid #e6eaef; margin: 8px 0 16px 0; }

/* Right-aligned toolbar */
.osfi-toolbar{
  display:flex; justify-content:flex-end; gap:10px; align-items:center;
  margin: 6px 0 10px 0;
}

/* Summary cards */
.osfi-cards{
  display:grid; grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap:14px; margin-top: 8px;
}
@media (max-width: 1100px){
  .osfi-cards{ grid-template-columns: repeat(2, minmax(160px, 1fr)); }
}
.osfi-card{
  background:#ffffff; border:1px solid #e6eaef; border-radius:10px;
  padding:14px 14px 12px 14px;
}
.osfi-card-label{ font-size: 12px; color:#6b7785; margin-bottom: 6px; }
.osfi-card-value{ font-size: 22px; font-weight: 700; color:#243447; }

.osfi-section-title{
  font-size: 18px; font-weight: 700; margin: 18px 0 6px 0; color:#243447;
}

/* Streamlit popover button alignment */
div[data-testid="stPopoverButton"] > button { height: 40px; }

/* Make markdown links in dataframe look like OSF links */
a { text-decoration: none; }
</style>
        """,
        unsafe_allow_html=True,
    )


def render_branding(branding: Dict[str, str]) -> None:
    inst = (branding.get("branding_institution_name") or "").strip() or "Center For Open Science [Test]"
    logo = (branding.get("branding_institution_logo_url") or "").strip()
    report_month = (branding.get("report_month") or "").strip() or (branding.get("report_month") or "").strip()
    if not report_month:
        # sometimes present as report_yearmonth in summary row; not available here
        report_month = "2025-11"

    # Fallback logo (COS)
    fallback = "https://osf.io/static/img/cos-white.svg"
    logo_url = logo if logo else fallback

    # Use components.html so HTML isn't echoed as code
    html = f"""
<div class="osfi-brand-wrap">
  <div class="osfi-logo">
    <img src="{logo_url}" alt="logo" onerror="this.onerror=null;this.src='{fallback}';" />
  </div>
  <div class="osfi-brand-text">
    <div class="osfi-inst-name">{inst}</div>
    <div class="osfi-report">Institutions Dashboard (Demo) • Report month: {report_month}</div>
  </div>
</div>
<div class="osfi-tabs-hr"></div>
"""
    st.components.v1.html(html, height=92)


def _available_columns(frame: pd.DataFrame, entity_key: str) -> List[str]:
    allowed = ENTITY_COLUMNS[entity_key]
    return [c for c in allowed if c in frame.columns]


def render_customize(entity_key: str, available_cols: List[str], default_cols: List[str]) -> List[str]:
    """Checkbox-based customize list; returns selected columns."""
    state_key = f"{entity_key}_selected_cols"
    if state_key not in st.session_state:
        st.session_state[state_key] = [c for c in default_cols if c in available_cols]

    with st.popover("Customize", use_container_width=False):
        st.markdown("**Columns**")
        selected = []
        for c in available_cols:
            checked = c in st.session_state[state_key]
            if st.checkbox(c, value=checked, key=f"{state_key}_{c}"):
                selected.append(c)
        # persist (preserve order from available_cols)
        st.session_state[state_key] = [c for c in available_cols if c in selected]

    return st.session_state[state_key]


def render_filters(entity_key: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Simple popover filters based on real columns present."""
    filters = ENTITY_FILTERS.get(entity_key, [])
    if not filters:
        return frame

    with st.popover("Filters", use_container_width=False):
        temp = frame
        # resource_type
        if "resource_type" in filters and "resource_type" in temp.columns:
            opts = sorted([x for x in temp["resource_type"].unique().tolist() if str(x).strip() != ""])
            sel = st.selectbox("Resource Type", options=["All"] + opts, index=0, key=f"{entity_key}_flt_resource_type")
            if sel != "All":
                temp = temp[temp["resource_type"] == sel]

        if "license" in filters and "license" in temp.columns:
            opts = sorted([x for x in temp["license"].unique().tolist() if str(x).strip() != ""])
            sel = st.selectbox("License", options=["All"] + opts, index=0, key=f"{entity_key}_flt_license")
            if sel != "All":
                temp = temp[temp["license"] == sel]

        if "storage_region" in filters and "storage_region" in temp.columns:
            opts = sorted([x for x in temp["storage_region"].unique().tolist() if str(x).strip() != ""])
            sel = st.selectbox("Storage Region", options=["All"] + opts, index=0, key=f"{entity_key}_flt_region")
            if sel != "All":
                temp = temp[temp["storage_region"] == sel]

        return temp

    return frame


def add_link_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()

    # OSF Link => markdown displaying GUID
    if "osf_link" in out.columns:
        def _osf_md(v: str) -> str:
            guid = _extract_guid(v)
            if not guid:
                return ""
            url = f"https://osf.io/{guid}/"
            return f"[{guid}]({url})"
        out["osf_link"] = out["osf_link"].apply(_osf_md)

    # DOI => markdown displaying DOI (or blank)
    if "doi" in out.columns:
        def _doi_md(v: str) -> str:
            d = str(v).strip()
            if d == "" or d.lower() in {"none", "nan"}:
                return ""
            url = _doi_url(d)
            # display bare DOI
            d_disp = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I)
            return f"[{d_disp}]({url})"
        out["doi"] = out["doi"].apply(_doi_md)

    return out


def render_table(entity_label: str, entity_key: str, frame: pd.DataFrame) -> None:
    # Title
    st.markdown(f'<div class="osfi-section-title">{len(frame)} {entity_label}</div>', unsafe_allow_html=True)

    # Right aligned toolbar (Filters + Customize)
    st.markdown('<div class="osfi-toolbar">', unsafe_allow_html=True)
    toolbar_cols = st.columns([1, 1, 6], gap="small")
    with toolbar_cols[0]:
        filtered = render_filters(entity_key, frame)
    with toolbar_cols[1]:
        available = _available_columns(filtered, entity_key)
        default_cols = available[:]  # start with all available by default
        selected_cols = render_customize(entity_key, available_cols=available, default_cols=default_cols)
    st.markdown('</div>', unsafe_allow_html=True)

    # Apply selection (ensure at least one)
    if not selected_cols:
        selected_cols = _available_columns(filtered, entity_key)[:1]

    df_show = filtered[selected_cols].copy()

    # Link formatting
    df_show = add_link_columns(df_show)

    # Pagination (below table)
    page_size = st.session_state.get(f"{entity_key}_page_size", 25)
    total = len(df_show)
    pages = max(1, (total + page_size - 1) // page_size)
    page = st.session_state.get(f"{entity_key}_page", 1)
    page = max(1, min(page, pages))

    start = (page - 1) * page_size
    end = min(start + page_size, total)
    page_df = df_show.iloc[start:end].reset_index(drop=True)

    st.dataframe(
        page_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "osf_link": st.column_config.MarkdownColumn("OSF Link"),
            "doi": st.column_config.MarkdownColumn("DOI"),
        },
    )

    # Pagination controls below
    pag_cols = st.columns([2, 2, 2, 6])
    with pag_cols[0]:
        if st.button("‹ Prev", key=f"{entity_key}_prev", disabled=(page <= 1)):
            st.session_state[f"{entity_key}_page"] = page - 1
            st.rerun()
    with pag_cols[1]:
        st.markdown(f"Page **{page}** of **{pages}**")
    with pag_cols[2]:
        if st.button("Next ›", key=f"{entity_key}_next", disabled=(page >= pages)):
            st.session_state[f"{entity_key}_page"] = page + 1
            st.rerun()
    with pag_cols[3]:
        new_size = st.selectbox("Rows per page", options=[10, 25, 50, 100], index=[10,25,50,100].index(page_size) if page_size in [10,25,50,100] else 1, key=f"{entity_key}_page_size_select")
        if new_size != page_size:
            st.session_state[f"{entity_key}_page_size"] = new_size
            st.session_state[f"{entity_key}_page"] = 1
            st.rerun()


def render_summary(summary_row: pd.Series, projects: pd.DataFrame, registrations: pd.DataFrame, preprints: pd.DataFrame) -> None:
    counts = compute_summary_counts(summary_row, projects, registrations, preprints)

    # Summary cards in a 4x2 grid
    cards = [
        ("Total Users", int(counts["total_users"])),
        ("Total Monthly Logged in Users", int(counts["monthly_logged_in_users"])),
        ("Total Monthly Active Users", int(counts["monthly_active_users"])),
        ("Projects", int(counts["projects"])),
        ("Registrations", int(counts["registrations"])),
        ("Preprints", int(counts["preprints"])),
        ("Total Public File Count", int(counts["total_public_file_count"])),
        ("Total Storage in GB", round(float(counts["total_storage_gb"]), 1)),
    ]

    # render grid
    st.markdown('<div class="osfi-cards">', unsafe_allow_html=True)
    for label, val in cards:
        st.markdown(
            f"""
<div class="osfi-card">
  <div class="osfi-card-label">{label}</div>
  <div class="osfi-card-value">{val}</div>
</div>
""",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------
# App
# -----------------------------

def main() -> None:
    st.set_page_config(page_title="Institutions Dashboard (Demo)", layout="wide")
    inject_css()

    data_path = Path(DEFAULT_DATA_FILE)
    try:
        _, branding, summary_row, projects, registrations, preprints = load_data(str(data_path))
    except Exception as e:
        st.error(str(e))
        st.stop()

    render_branding(branding)

    tab_summary, tab_projects, tab_regs, tab_preprints = st.tabs(TABS)

    with tab_summary:
        render_summary(summary_row, projects, registrations, preprints)

    with tab_projects:
        render_table("Projects", "project", projects)

    with tab_regs:
        render_table("Registrations", "registration", registrations)

    with tab_preprints:
        render_table("Preprints", "preprint", preprints)


if __name__ == "__main__":
    main()
