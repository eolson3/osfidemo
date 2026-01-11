# dashboard_v4.py
# Streamlit OSF Institutions Dashboard (Demo)
# - Robust CSV discovery (prevents FileNotFoundError on Streamlit Cloud)
# - Branding header rendered as HTML (unsafe_allow_html)
# - OSF Link + DOI display as GUID/DOI text (not "Open")
# - "Customize" uses checkbox list (not multiselect chips)
# - No st-aggrid dependency

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st


# -----------------------------
# App config
# -----------------------------
st.set_page_config(
    page_title="Institutions Dashboard (Demo)",
    page_icon="📊",
    layout="wide",
)

# Prefer env var if set in Streamlit Cloud
ENV_DATA_FILE = os.getenv("OSFI_DATA_FILE", "").strip()

# Candidate CSV names (checked in this order)
CSV_CANDIDATES = [
    ENV_DATA_FILE,
    "osfi_dashboard_data.csv",
    "osfi_dashboard_data_v3_no_users_tab.csv",
    "osfi_dashboard_data_v2_no_users_tab.csv",
]


# -----------------------------
# Utilities
# -----------------------------
def _normalize_cols(cols: List[str]) -> List[str]:
    out = []
    for c in cols:
        c2 = (c or "").strip()
        c2 = c2.replace("\ufeff", "")
        out.append(c2)
    return out


def find_data_file() -> Optional[str]:
    """Find a CSV path that exists in the repo/app working directory.

    Returns:
        str path or None
    """
    # 1) Explicit env var
    if ENV_DATA_FILE:
        if Path(ENV_DATA_FILE).exists():
            return ENV_DATA_FILE

    cwd = Path(".").resolve()

    # 2) Known candidate filenames in cwd
    for name in CSV_CANDIDATES:
        if not name:
            continue
        p = (cwd / name).resolve()
        if p.exists() and p.is_file():
            return str(p)

    # 3) Any single CSV in root (if exactly one)
    csvs = sorted([str(p) for p in cwd.glob("*.csv") if p.is_file()])
    if len(csvs) == 1:
        return csvs[0]

    # 4) Heuristic: pick latest osfi*csv
    osfi_csvs = sorted([str(p) for p in cwd.glob("osfi*.csv") if p.is_file()])
    if osfi_csvs:
        # newest mtime
        osfi_csvs.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
        return osfi_csvs[0]

    return None


def ensure_row_type(df: pd.DataFrame) -> pd.DataFrame:
    cols = _normalize_cols(df.columns.tolist())
    df.columns = cols
    if "row_type" not in df.columns:
        raise ValueError("CSV must include a 'row_type' column (branding/summary/project/registration/preprint).")
    df["row_type"] = df["row_type"].astype(str).str.strip().str.lower()
    return df


def parse_guid_from_url(url: str) -> str:
    """Best-effort GUID extraction from OSF-like URLs."""
    if not url:
        return ""
    u = str(url).strip()
    # common OSF patterns end with GUID or contain /<guid>/
    m = re.search(r"/([a-z0-9]{4,10})(?:[_/]|$)", u, re.IGNORECASE)
    if m:
        return m.group(1)
    # fallback: last path token
    tok = re.split(r"[/?#]", u.rstrip("/"))[-1]
    return tok


def parse_doi_display(doi: str) -> str:
    if not doi:
        return ""
    d = str(doi).strip()
    d = d.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return d


@st.cache_data(show_spinner=False)
def load_data(path: str) -> Tuple[pd.DataFrame, Dict[str, str], Dict[str, str], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path, dtype=str).fillna("")
    df = ensure_row_type(df)

    # Split rows
    branding_row = df[df["row_type"] == "branding"].head(1)
    summary_row = df[df["row_type"] == "summary"].head(1)

    # Back-compat: branding fields embedded in summary row
    branding: Dict[str, str] = {}
    if len(branding_row) == 1:
        branding = branding_row.iloc[0].to_dict()
    elif len(summary_row) == 1:
        branding = summary_row.iloc[0].to_dict()

    summary: Dict[str, str] = summary_row.iloc[0].to_dict() if len(summary_row) == 1 else {}

    projects = df[df["row_type"] == "project"].copy()
    registrations = df[df["row_type"] == "registration"].copy()
    preprints = df[df["row_type"] == "preprint"].copy()

    # Add helper columns for nicer link display
    for dfx in (projects, registrations, preprints):
        if "osf_link" in dfx.columns:
            dfx["osf_guid"] = dfx["osf_link"].apply(parse_guid_from_url)
        else:
            dfx["osf_guid"] = ""
        if "doi" in dfx.columns:
            dfx["doi_display"] = dfx["doi"].apply(parse_doi_display)
        else:
            dfx["doi_display"] = ""

    return df, branding, summary, projects, registrations, preprints


def render_branding(branding: Dict[str, str], summary: Dict[str, str]) -> None:
    inst = branding.get("branding_institution_name") or summary.get("branding_institution_name") or "Institution"
    logo = branding.get("branding_institution_logo_url") or summary.get("branding_institution_logo_url") or ""
    report_month = branding.get("report_month") or summary.get("report_month") or summary.get("report_yearmonth") or ""

    # COS logo (fallback) to match screenshots
    cos_logo = "https://osf.io/static/img/cos-white.svg"

    # Ensure HTML is not escaped
    st.markdown(
        f"""
        <style>
          .osfi-header-wrap {{
            background: #F3F8FC;
            padding: 18px 18px 6px 18px;
            border-radius: 10px;
            margin-bottom: 10px;
          }}
          .osfi-header {{
            display:flex;
            gap:14px;
            align-items:center;
          }}
          .osfi-logo img {{
            width:44px; height:44px; display:block;
          }}
          .osfi-brand-text .osfi-inst-name {{
            font-size: 26px;
            font-weight: 700;
            color: #2B3B4C;
            line-height: 1.15;
          }}
          .osfi-brand-text .osfi-report {{
            font-size: 15px;
            color: #5B6B7B;
            margin-top: 4px;
          }}
          .osfi-tabs-spacer {{
            height: 6px;
          }}
        </style>
        <div class="osfi-header-wrap">
          <div class="osfi-header">
            <div class="osfi-logo">
              <img src="{logo if logo else cos_logo}" alt="logo"/>
            </div>
            <div class="osfi-brand-text">
              <div class="osfi-inst-name">{inst}</div>
              <div class="osfi-report">Institutions Dashboard (Demo) • Report month: {report_month}</div>
            </div>
          </div>
          <div class="osfi-tabs-spacer"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def summarize_counts(summary: Dict[str, str], projects: pd.DataFrame, registrations: pd.DataFrame, preprints: pd.DataFrame) -> Dict[str, float]:
    def _to_float(x: str) -> float:
        try:
            return float(str(x).strip())
        except Exception:
            return 0.0

    # These should reflect the actual tab totals (per your requirement)
    return {
        "OSF Preprints": float(len(preprints)),
        "Total Public File Count": _to_float(summary.get("public_file_count") or summary.get("total_public_file_count") or 0),
        "Total Storage in GB": _to_float(summary.get("storage_gb") or summary.get("total_storage_gb") or summary.get("total_storage_in_gb") or 0),
        "Projects total": float(len(projects)),
        "Registrations total": float(len(registrations)),
    }


def column_sets(entity: str) -> List[str]:
    """Return the intended columns per tab. Keep tight to avoid unintended filters."""
    base = [
        "name_or_title",
        "osf_link",
        "created_date",
        "modified_date",
        "doi",
        "license",
        "storage_region",
        "storage_byte_count",
        "storage_gb",
        "views_last_30_days",
        "downloads_last_30_days",
        "resource_type",
        "add_ons",
        "funder_name",
        "report_yearmonth",
    ]
    if entity == "project":
        return [c for c in base if c not in {"resource_type"}]
    if entity == "registration":
        return [c for c in base if c not in {"resource_type"}]
    if entity == "preprint":
        return [c for c in base if c not in {"resource_type"}]
    return base


def link_column_configs(df: pd.DataFrame) -> Dict[str, st.column_config.Column]:
    cfg: Dict[str, st.column_config.Column] = {}

    # OSF Link: show GUID text, click goes to URL
    if "osf_link" in df.columns:
        cfg["osf_link"] = st.column_config.LinkColumn(
            "OSF Link",
            help="OSF object link",
            display_text=r"/([a-z0-9]{4,10})(?:[_/]|$)",
        )

    # DOI: show DOI suffix, click goes to doi.org
    if "doi" in df.columns:
        # Ensure URL form for link column
        def _doi_url(x: str) -> str:
            d = parse_doi_display(x)
            return f"https://doi.org/{d}" if d else ""
        # We can't mutate original in-place across cached frames safely; do when rendering
        cfg["doi"] = st.column_config.LinkColumn(
            "DOI",
            help="DOI link",
            display_text=r"doi\.org/(.+)$",
        )

    # Pretty headers for a few
    for c, title in {
        "name_or_title": "Name",
        "created_date": "Created",
        "modified_date": "Modified",
        "storage_region": "Storage region",
        "storage_byte_count": "Storage (bytes)",
        "storage_gb": "Storage (GB)",
        "views_last_30_days": "Views (30d)",
        "downloads_last_30_days": "Downloads (30d)",
        "add_ons": "Add-ons",
    }.items():
        if c in df.columns:
            cfg[c] = st.column_config.TextColumn(title)

    return cfg


def render_customize(pop_key: str, available_cols: List[str], default_cols: List[str]) -> List[str]:
    """Checkbox-based column selection inside a popover."""
    selected = []
    with st.popover("Customize", use_container_width=False, key=f"{pop_key}_cust"):
        st.markdown("**Columns**")
        for c in available_cols:
            # Default checked if in default_cols
            checked = c in default_cols
            v = st.checkbox(c, value=checked, key=f"{pop_key}_col_{c}")
            if v:
                selected.append(c)

    # If user unchecks everything, fall back to defaults
    if not selected:
        selected = default_cols[:]
    return selected


def render_filters(entity: str, df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Entity-specific filters (kept minimal and correct)."""
    out = df.copy()

    with st.popover("Filters", use_container_width=False, key=f"{key}_filters"):
        # Only show relevant filters based on columns available
        if entity in {"project", "registration", "preprint"}:
            if "license" in out.columns:
                lic = sorted([x for x in out["license"].unique().tolist() if x])
                choice = st.selectbox("License", ["All"] + lic, key=f"{key}_lic")
                if choice != "All":
                    out = out[out["license"] == choice]

            if "storage_region" in out.columns:
                reg = sorted([x for x in out["storage_region"].unique().tolist() if x])
                choice = st.selectbox("Storage region", ["All"] + reg, key=f"{key}_reg")
                if choice != "All":
                    out = out[out["storage_region"] == choice]

            if "resource_type" in out.columns:
                rt = sorted([x for x in out["resource_type"].unique().tolist() if x])
                if rt:
                    choice = st.selectbox("Resource type", ["All"] + rt, key=f"{key}_rt")
                    if choice != "All":
                        out = out[out["resource_type"] == choice]

    return out


def render_table(entity_label: str, entity_key: str, df: pd.DataFrame) -> None:
    # Header row with count + buttons aligned right
    count = len(df)
    left, right = st.columns([1, 2], vertical_alignment="center")

    with left:
        st.markdown(f"### {count} {entity_label}")

    with right:
        # Right-aligned toolbar
        t1, t2 = st.columns([1, 1], vertical_alignment="center")
        with t1:
            # buttons live in popovers below; placeholder to keep spacing consistent
            st.write("")
        with t2:
            # download
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV",
                data=csv_bytes,
                file_name=f"{entity_key}_export.csv",
                mime="text/csv",
                width="content",
                key=f"{entity_key}_dl",
            )

    st.divider()

    # Determine available and default columns
    desired = column_sets(entity_key)
    available = [c for c in desired if c in df.columns]
    # Always include osf_link if present
    if "osf_link" in df.columns and "osf_link" not in available:
        available.insert(0, "osf_link")

    # Add DOI link column if present
    if "doi" in df.columns and "doi" not in available:
        available.append("doi")

    # Let user customize via checkboxes
    selected_cols = render_customize(entity_key, available_cols=available, default_cols=available)

    # Apply filters
    filtered = render_filters(entity_key, df, key=entity_key)

    # Pagination (below table, per requirement)
    page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1, key=f"{entity_key}_ps")
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page = st.session_state.get(f"{entity_key}_page", 1)
    page = min(max(1, page), total_pages)

    start = (page - 1) * page_size
    end = start + page_size
    page_df = filtered.iloc[start:end].copy()

    # Ensure DOI column is URL-form for LinkColumn
    if "doi" in page_df.columns:
        def _doi_url(x: str) -> str:
            d = parse_doi_display(x)
            return f"https://doi.org/{d}" if d else ""
        page_df["doi"] = page_df["doi"].apply(_doi_url)

    # Render
    cfg = link_column_configs(page_df)

    st.dataframe(
        page_df[selected_cols],
        column_config=cfg,
        hide_index=True,
        width="stretch",
        height=520,
    )

    # Pagination controls BELOW the table
    c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1], vertical_alignment="center")
    with c1:
        if st.button("«", key=f"{entity_key}_first", disabled=(page <= 1)):
            st.session_state[f"{entity_key}_page"] = 1
            st.rerun()
    with c2:
        if st.button("‹", key=f"{entity_key}_prev", disabled=(page <= 1)):
            st.session_state[f"{entity_key}_page"] = page - 1
            st.rerun()
    with c3:
        st.markdown(f"<div style='text-align:center; padding-top:6px;'>Page {page} of {total_pages}</div>", unsafe_allow_html=True)
    with c4:
        if st.button("›", key=f"{entity_key}_next", disabled=(page >= total_pages)):
            st.session_state[f"{entity_key}_page"] = page + 1
            st.rerun()
    with c5:
        if st.button("»", key=f"{entity_key}_last", disabled=(page >= total_pages)):
            st.session_state[f"{entity_key}_page"] = total_pages
            st.rerun()


def render_summary(summary: Dict[str, str], projects: pd.DataFrame, registrations: pd.DataFrame, preprints: pd.DataFrame) -> None:
    # Cards row – keep simple/clean; last three reflect tab totals where requested
    counts = summarize_counts(summary, projects, registrations, preprints)

    # Use summary row values where they are explicitly provided (monthly users)
    def _int(x: str) -> int:
        try:
            return int(float(str(x).strip()))
        except Exception:
            return 0

    total_users = _int(summary.get("total_users") or summary.get("users_total") or summary.get("users_count") or 0)
    monthly_logged_in = _int(summary.get("summary_monthly_logged_in_users") or 0)
    monthly_active = _int(summary.get("summary_monthly_active_users") or 0)

    # If totals not present, derive from tabs
    proj_total = int(counts["Projects total"])
    reg_total = int(counts["Registrations total"])
    pre_total = int(counts["OSF Preprints"])

    # Styled cards
    st.markdown(
        """
        <style>
          .metric-grid { display:grid; grid-template-columns: repeat(4, 1fr); gap:16px; }
          .metric-card {
            background: #ffffff;
            border: 1px solid #E6EDF5;
            border-radius: 10px;
            padding: 16px 18px;
            min-height: 84px;
          }
          .metric-label { color:#5B6B7B; font-size: 13px; margin-bottom: 6px; }
          .metric-value { color:#1F2D3D; font-size: 22px; font-weight: 700; }
          @media (max-width: 1100px) { .metric-grid { grid-template-columns: repeat(2, 1fr); } }
        </style>
        """,
        unsafe_allow_html=True,
    )

    cards = [
        ("Total Users", total_users),
        ("Total Monthly Logged in Users", monthly_logged_in),
        ("Total Monthly Active Users", monthly_active),
        ("Projects", proj_total),
        ("Registrations", reg_total),
        ("Preprints", pre_total),
        ("Total Public File Count", int(float(counts["Total Public File Count"] or 0))),
        ("Total Storage in GB", float(counts["Total Storage in GB"] or 0)),
    ]

    # 8 cards in two rows of 4
    st.markdown("<div class='metric-grid'>", unsafe_allow_html=True)
    for label, value in cards:
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-label">{label}</div>
              <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    # Data file handling
    data_path = find_data_file()

    if data_path is None:
        st.warning("No CSV found in the app directory. Upload one to continue.")
        up = st.file_uploader("Upload dashboard CSV", type=["csv"])
        if up is None:
            st.stop()
        df = pd.read_csv(up, dtype=str).fillna("")
        df = ensure_row_type(df)
        # Save into session only (no filesystem writes on Streamlit Cloud)
        st.session_state["_uploaded_df"] = df
        branding = df[df["row_type"].isin(["branding", "summary"])].head(1).iloc[0].to_dict() if len(df) else {}
        summary = df[df["row_type"] == "summary"].head(1).iloc[0].to_dict() if len(df[df["row_type"] == "summary"]) else {}
        projects = df[df["row_type"] == "project"].copy()
        registrations = df[df["row_type"] == "registration"].copy()
        preprints = df[df["row_type"] == "preprint"].copy()
    else:
        df, branding, summary, projects, registrations, preprints = load_data(data_path)

    render_branding(branding, summary)

    # Tabs (Users removed per your decision)
    tab_summary, tab_projects, tab_regs, tab_preprints = st.tabs(["Summary", "Projects", "Registrations", "Preprints"])

    with tab_summary:
        render_summary(summary, projects, registrations, preprints)

    with tab_projects:
        render_table("Projects", "project", projects)

    with tab_regs:
        render_table("Registrations", "registration", registrations)

    with tab_preprints:
        render_table("Preprints", "preprint", preprints)


if __name__ == "__main__":
    main()
