import math
from pathlib import Path
import base64
from urllib.request import Request, urlopen
from urllib.error import URLError

import altair as alt
import pandas as pd
import streamlit as st

# -----------------------------
# Configuration
# -----------------------------
DEFAULT_DATA_FILE = "osfi_dashboard_data.csv"

# Approximate OSF Institutions dashboard styling from screenshots
CSS = """
<style>
:root{
  --page-bg:#F3F8FC;
  --card-bg:#FFFFFF;
  --border:#E6EDF3;
  --text:#22313F;
  --muted:#6B7C93;
  --accent:#2E77D0;
  --accent-soft:#E8F1FB;
  --link:#2E77D0;
}
html, body, [data-testid="stAppViewContainer"]{
  background: var(--page-bg);
}
[data-testid="stHeader"]{ background: transparent; }
.main .block-container{
  padding-top: 1.2rem;
  max-width: 1280px;
}
.osfi-brand{
  display:flex; align-items:center; gap:16px;
  margin: 6px 0 14px 0;
}
.osfi-brand img{
  width:56px; height:56px; object-fit:contain;
}
.osfi-brand .title{
  font-size: 36px; font-weight: 750; color: var(--text);
  line-height: 1.1;
}
.osfi-brand .subtitle{
  font-size: 16px; color: var(--muted); margin-top: 4px;
}
.osfi-tabs { margin-top: 6px; }

.osfi-card{
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 18px 16px 18px;
}
.metric-wrap{
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  min-height: 142px;
}
.metric-circle{
  width: 86px; height: 86px; border-radius: 999px;
  background: var(--accent-soft);
  display:flex; align-items:center; justify-content:center;
  color: var(--accent);
  font-size: 24px; font-weight: 750;
  margin-bottom: 10px;
}
.metric-label{
  text-align:center;
  color: var(--text);
  font-size: 14px;
}
.section-title{
  font-size: 18px; font-weight: 750; color: var(--text);
  margin: 0 0 10px 0;
}
.kpi-title{
  font-size: 18px; font-weight: 750; color: var(--accent);
  margin: 10px 0 10px 0;
}
.small-muted{ color: var(--muted); font-size: 12px; }

a, a:visited { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }

.controls-row{
  display:flex; justify-content:flex-end; gap:12px; align-items:center;
}
.stDownloadButton button, .stButton>button{
  border-radius: 8px !important;
}
</style>
"""

# -----------------------------
# Utilities
# -----------------------------
def _norm(s: str) -> str:
    return (
        str(s)
        .strip()
        .replace("\ufeff", "")
        .lower()
        .replace(" ", "_")
    )

@st.cache_data(show_spinner=False)
def load_data(path: str) -> tuple[pd.DataFrame, pd.Series]:
    p = Path(path)
    if not p.exists():
        # try relative to app file
        p = Path(__file__).parent / path
    df = pd.read_csv(p, dtype=str).fillna("")
    original_cols = df.columns.tolist()
    df.columns = [_norm(c) for c in df.columns]

    # Accept either row_type or object_type
    if "row_type" not in df.columns and "object_type" in df.columns:
        df = df.rename(columns={"object_type": "row_type"})

    if "row_type" not in df.columns:
        raise ValueError(
            "CSV must include a 'row_type' column (summary/project/registration/preprint). "
            f"Found columns: {original_cols}"
        )

    # ensure required branding fields exist
    for c in ["branding_institution_name", "branding_institution_logo_url", "report_month"]:
        if c not in df.columns:
            df[c] = ""

    # summary row (single)
    summary = df[df["row_type"] == "summary"]
    summary_row = summary.iloc[0] if len(summary) else pd.Series(dtype=str)
    return df, summary_row

def _to_int(x: str) -> int:
    try:
        return int(float(str(x).strip() or 0))
    except Exception:
        return 0

def _to_float(x: str) -> float:
    try:
        return float(str(x).strip() or 0.0)
    except Exception:
        return 0.0

def make_link(cell: str) -> str:
    # If already looks like a URL, use it directly; else treat as OSF id
    s = str(cell).strip()
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        return s
    return f"https://osf.io/{s}/"

def build_display_df(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    cols_present = [c for c in cols if c in df.columns]
    out = df[cols_present].copy()

    # hyperlink formatting for osf_link and doi
    if "osf_link" in out.columns:
        out["osf_link"] = out["osf_link"].apply(make_link)
    if "doi" in out.columns:
        out["doi"] = out["doi"].apply(lambda d: f"https://doi.org/{d.strip()}" if str(d).strip() and not str(d).startswith("http") else str(d).strip())

    return out

def column_config_for(df: pd.DataFrame) -> dict:
    cfg = {}
    if "osf_link" in df.columns:
        cfg["osf_link"] = st.column_config.LinkColumn("OSF Link", display_text="Open")
    if "doi" in df.columns:
        cfg["doi"] = st.column_config.LinkColumn("DOI", display_text="Open")
    if "storage_gb" in df.columns:
        cfg["storage_gb"] = st.column_config.NumberColumn("Storage (GB)", format="%.2f")
    if "storage_byte_count" in df.columns:
        cfg["storage_byte_count"] = st.column_config.NumberColumn("Storage (bytes)")
    if "views_last_30_days" in df.columns:
        cfg["views_last_30_days"] = st.column_config.NumberColumn("Views (30d)")
    if "downloads_last_30_days" in df.columns:
        cfg["downloads_last_30_days"] = st.column_config.NumberColumn("Downloads (30d)")
    return cfg

def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    out = df.copy()
    for col, val in filters.items():
        if col not in out.columns or val in ("", None, "All"):
            continue
        out = out[out[col] == val]
    return out

def paginate(df: pd.DataFrame, page_key: str, page_size: int = 25) -> tuple[pd.DataFrame, int, int]:
    n = len(df)
    total_pages = max(1, math.ceil(n / page_size))
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    page = int(st.session_state[page_key])
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end].copy(), page, total_pages

def chart_donut(labels: list[str], values: list[int], title: str):
    d = pd.DataFrame({"label": labels, "value": values})
    d = d[d["value"] > 0]
    if d.empty:
        st.markdown(f"<div class='osfi-card'><div class='section-title'>{title}</div><div class='small-muted'>No data</div></div>", unsafe_allow_html=True)
        return

    chart = (
        alt.Chart(d)
        .mark_arc(innerRadius=80, outerRadius=120)
        .encode(theta="value:Q", color=alt.Color("label:N", legend=alt.Legend(title=None)))
        .properties(height=280)
    )
    st.markdown(f"<div class='osfi-card'><div class='section-title'>{title}</div>", unsafe_allow_html=True)
    st.altair_chart(chart, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

def chart_bar_top10(df: pd.DataFrame, col: str, title: str):
    if col not in df.columns:
        st.markdown(f"<div class='osfi-card'><div class='section-title'>{title}</div><div class='small-muted'>Missing column: {col}</div></div>", unsafe_allow_html=True)
        return
    s = df[col].replace("", "Unknown")
    top = s.value_counts().head(10).reset_index()
    top.columns = ["label", "count"]
    chart = (
        alt.Chart(top)
        .mark_bar()
        .encode(
            x=alt.X("label:N", sort="-y", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("count:Q", title=None),
            tooltip=["label", "count"],
        )
        .properties(height=260)
    )
    st.markdown(f"<div class='osfi-card'><div class='section-title'>{title}</div>", unsafe_allow_html=True)
    st.altair_chart(chart, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Pages
# -----------------------------
def render_branding(summary_row: pd.Series):
    """Render the header/branding block.

    We avoid relying on <img src=...> inside HTML because Streamlit deployments may apply CSP rules
    that prevent the browser from directly loading external images, particularly SVGs.
    Instead we fetch the logo server-side when possible and fall back to an embedded SVG.
    """

    name = str(summary_row.get("branding_institution_name", "")).strip() or "Institution"
    logo_url = str(summary_row.get("branding_institution_logo_url", "")).strip()
    report_month = (
        str(summary_row.get("report_month", "")).strip()
        or str(summary_row.get("report_yearmonth", "")).strip()
    )

    COS_SVG = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
        "<circle cx='32' cy='32' r='30' fill='#2d6cc0'/>"
        "<circle cx='32' cy='32' r='16' fill='#ffffff' opacity='0.9'/>"
        "<circle cx='32' cy='32' r='7' fill='#2d6cc0'/>"
        "</svg>"
    ).encode("utf-8")

    def _fetch_bytes(url: str) -> bytes | None:
        if not url:
            return None
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=10) as resp:
                return resp.read()
        except URLError:
            return None
        except Exception:
            return None

    logo_bytes = _fetch_bytes(logo_url) if logo_url else None
    if not logo_bytes and logo_url:
        # Some servers block unknown agents; try one more time with minimal headers.
        logo_bytes = _fetch_bytes(logo_url)
    if not logo_bytes:
        logo_bytes = COS_SVG

    # Layout using Streamlit columns; CSS handles spacing and font styling.
    left, right = st.columns([0.08, 0.92], gap="small")
    with left:
        # Streamlit's image renderer can be finicky with SVG bytes; handle SVG explicitly.
        try:
            if b"<svg" in logo_bytes[:500].lower():
                b64 = base64.b64encode(logo_bytes).decode("ascii")
                st.markdown(
                    f"<img src='data:image/svg+xml;base64,{b64}' width='44' height='44' alt='logo' />",
                    unsafe_allow_html=True,
                )
            else:
                st.image(logo_bytes, width=44)
        except Exception:
            st.markdown("<div class='osfi-logo-fallback'>COS</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            f"<div class='osfi-brand-text'>"
            f"<div class='title'>{name}</div>"
            f"<div class='subtitle'>Institutions Dashboard (Demo){(' • Report month: ' + report_month) if report_month else ''}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

def render_summary(df: pd.DataFrame, summary_row: pd.Series):
    # Totals that must be computed from tables
    preprints_total = (df["row_type"] == "preprint").sum()
    public_file_count = df.loc[df["row_type"].isin(["project", "registration", "preprint"]), "public_file_count"].apply(_to_int).sum() if "public_file_count" in df.columns else 0
    storage_gb_total = df.loc[df["row_type"].isin(["project", "registration", "preprint"]), "storage_gb"].apply(_to_float).sum() if "storage_gb" in df.columns else 0.0

    # Totals that must come from summary write-ins (privacy-sensitive)
    projects_public = _to_int(summary_row.get("projects_public_count", "0"))
    projects_private = _to_int(summary_row.get("projects_private_count", "0"))
    regs_public = _to_int(summary_row.get("registrations_public_count", "0"))
    regs_embargo = _to_int(summary_row.get("registrations_embargoed_count", "0"))

    # Other summary metrics
    total_users = _to_int(summary_row.get("summary_total_users", "0"))
    monthly_logged_in = _to_int(summary_row.get("summary_monthly_logged_in_users", "0"))
    monthly_active = _to_int(summary_row.get("summary_monthly_active_users", "0"))

    # Metric cards grid
    cards = [
        ("Total Users", total_users),
        ("Total Monthly Logged in Users", monthly_logged_in),
        ("Total Monthly Active Users", monthly_active),
        ("OSF Public and Private Projects", projects_public + projects_private),
        ("OSF Public and Embargoed Registrations", regs_public + regs_embargo),
        ("OSF Preprints", preprints_total),
        ("Total Public File Count", public_file_count),
        ("Total Storage in GB", round(storage_gb_total, 1)),
    ]

    st.markdown("<div class='osfi-card'>", unsafe_allow_html=True)
    cols = st.columns(4, gap="large")
    for i, (label, val) in enumerate(cards):
        with cols[i % 4]:
            st.markdown(
                "<div class='metric-wrap'>"
                f"<div class='metric-circle'>{val}</div>"
                f"<div class='metric-label'>{label}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Charts row
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        # Total OSF Objects donut EXCLUDING users
        labels = ["Public registrations", "Embargoed registrations", "Public projects", "Private projects", "Preprints"]
        values = [regs_public, regs_embargo, projects_public, projects_private, preprints_total]
        chart_donut(labels, values, "Total OSF Objects")
    with c2:
        proj = df[df["row_type"] == "project"]
        chart_bar_top10(proj, "license", "Top 10 Licenses")
    with c3:
        proj = df[df["row_type"] == "project"]
        chart_bar_top10(proj, "add_ons", "Top 10 Add-ons")

    # Second row of donuts (department/users removed) -> keep storage regions if present
    if "storage_region" in df.columns:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        c4 = st.columns(3, gap="large")[0]
        with c4:
            ent = df[df["row_type"].isin(["project", "registration", "preprint"])]
            sr = ent["storage_region"].replace("", "Unknown")
            top = sr.value_counts().head(10)
            chart_donut(top.index.tolist(), top.values.tolist(), "Top Storage Regions")

def render_entity_tab(df_all: pd.DataFrame, row_type: str, title: str, page_key: str):
    df = df_all[df_all["row_type"] == row_type].copy()

    st.markdown(f"<div class='kpi-title'>{len(df)} {title}</div>", unsafe_allow_html=True)

    # Controls aligned right
    left, right = st.columns([5, 7], gap="large")
    with right:
        st.markdown("<div class='controls-row'>", unsafe_allow_html=True)

    # Filter controls row (right aligned using columns)
    c_has, c_dept, c_filters, c_custom, c_dl = st.columns([1.4, 2.2, 1.3, 1.3, 1.8])

    filters = {}

    # Only show Department + Has ORCID if those columns exist (Users tab removed; keep for future-proofing)
    with c_has:
        if "orcid_id" in df.columns:
            has_orcid = st.checkbox("Has ORCID", value=False, key=f"{page_key}_has_orcid")
            if has_orcid:
                df = df[df["orcid_id"].astype(str).str.strip() != ""]
    with c_dept:
        if "department" in df.columns:
            opts = ["All"] + sorted([x for x in df["department"].replace("", "N/A").unique().tolist() if x])
            dept = st.selectbox("All departments", opts, index=0, key=f"{page_key}_dept")
            if dept != "All":
                df = df[df["department"].replace("", "N/A") == dept]

    with c_filters:
        with st.expander("Filters", expanded=False):
            if "resource_type" in df.columns:
                rt = st.selectbox("Resource Type", ["All"] + sorted([x for x in df["resource_type"].replace("", "Unknown").unique().tolist() if x]), 0, key=f"{page_key}_rt")
                if rt != "All":
                    filters["resource_type"] = rt
            if "license" in df.columns:
                lic = st.selectbox("License", ["All"] + sorted([x for x in df["license"].replace("", "Unknown").unique().tolist() if x]), 0, key=f"{page_key}_lic")
                if lic != "All":
                    filters["license"] = lic
            if "storage_region" in df.columns:
                sr = st.selectbox("Storage Region", ["All"] + sorted([x for x in df["storage_region"].replace("", "Unknown").unique().tolist() if x]), 0, key=f"{page_key}_sr")
                if sr != "All":
                    filters["storage_region"] = sr

    with c_custom:
        with st.expander("Customize", expanded=False):
            # Define default columns per tab
            default_cols = {
                "project": ["name_or_title","osf_link","created_date","modified_date","doi","license","resource_type","add_ons","storage_region","storage_gb","views_last_30_days","downloads_last_30_days","report_yearmonth"],
                "registration": ["name_or_title","osf_link","created_date","modified_date","doi","license","resource_type","storage_region","storage_gb","views_last_30_days","downloads_last_30_days","report_yearmonth"],
                "preprint": ["name_or_title","osf_link","created_date","modified_date","doi","license","resource_type","storage_region","storage_gb","views_last_30_days","downloads_last_30_days","report_yearmonth"],
            }
            all_cols = [c for c in default_cols.get(row_type, df.columns.tolist()) if c in df.columns]
            selected = st.multiselect("Columns", options=df.columns.tolist(), default=all_cols, key=f"{page_key}_cols")
    with c_dl:
        st.download_button(
            "Download CSV",
            data=df.to_csv(index=False),
            file_name=f"{row_type}s.csv",
            mime="text/csv",
            key=f"{page_key}_dl",
        )

    df = apply_filters(df, filters)

    # Build display dataframe (respect customize selection)
    selected_cols = st.session_state.get(f"{page_key}_cols", [])
    if not selected_cols:
        selected_cols = [c for c in df.columns if c != "row_type"]
    display = build_display_df(df, selected_cols)

    # Pagination BELOW the table (as requested)
    page_df, page, total_pages = paginate(display, f"{page_key}_page", page_size=25)

    st.dataframe(
        page_df,
        width="stretch",
        height=520,
        hide_index=True,
        column_config=column_config_for(page_df),
    )

    # Pagination controls
    pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns([1,1,2,1,1])
    with pcol1:
        if st.button("«", key=f"{page_key}_first"):
            st.session_state[f"{page_key}_page"] = 1
            st.rerun()
    with pcol2:
        if st.button("‹", key=f"{page_key}_prev"):
            st.session_state[f"{page_key}_page"] = max(1, page - 1)
            st.rerun()
    with pcol3:
        st.markdown(f"<div class='small-muted' style='text-align:center'>Page {page} of {total_pages}</div>", unsafe_allow_html=True)
    with pcol4:
        if st.button("›", key=f"{page_key}_next"):
            st.session_state[f"{page_key}_page"] = min(total_pages, page + 1)
            st.rerun()
    with pcol5:
        if st.button("»", key=f"{page_key}_last"):
            st.session_state[f"{page_key}_page"] = total_pages
            st.rerun()

# -----------------------------
# App
# -----------------------------
def main():
    st.set_page_config(page_title="OSF Institutions Dashboard (Demo)", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    data_file = st.sidebar.text_input("Data file", value=DEFAULT_DATA_FILE)
    df, summary_row = load_data(data_file)

    render_branding(summary_row)

    tabs = st.tabs(["Summary", "Projects", "Registrations", "Preprints"])
    with tabs[0]:
        render_summary(df, summary_row)
    with tabs[1]:
        render_entity_tab(df, "project", "Projects", "projects")
    with tabs[2]:
        render_entity_tab(df, "registration", "Registrations", "registrations")
    with tabs[3]:
        render_entity_tab(df, "preprint", "Preprints", "preprints")

if __name__ == "__main__":
    main()
