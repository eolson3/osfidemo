import math
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

DATA_FILE = Path(__file__).parent / "osfi_dashboard_data_with_summary_and_branding.csv"

st.set_page_config(
    page_title="OSF Institutions Dashboard (Demo)",
    layout="wide",
)

# -------------------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------------------

def load_data(path: Path) -> Tuple[pd.Series, pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load unified CSV.

    Assumptions:
      - First column is row_type
      - row_type values: summary, user, project, registration, preprint
      - Branding + summary metrics live on the summary row.
    """
    df = pd.read_csv(path, dtype=str, sep=None, engine="python")

    # Normalize column names (strip whitespace, remove BOM)
    df.columns = [c.replace("\ufeff", "").strip() for c in df.columns]

    # Force first column to be 'row_type'
    if len(df.columns) == 0:
        st.error("CSV appears to have no columns.")
        st.stop()

    first_col = df.columns[0]
    if first_col != "row_type":
        df = df.rename(columns={first_col: "row_type"})

    df = df.fillna("")

    # Split by row_type
    summary_df = df[df["row_type"] == "summary"]
    users = df[df["row_type"] == "user"].copy()
    projects = df[df["row_type"] == "project"].copy()
    registrations = df[df["row_type"] == "registration"].copy()
    preprints = df[df["row_type"] == "preprint"].copy()

    if summary_df.empty:
        st.error("CSV must contain at least one row with row_type = 'summary'.")
        st.stop()

    summary_row = summary_df.iloc[0]
    branding_row = summary_row  # branding info is embedded in summary row

    return branding_row, summary_row, users, projects, registrations, preprints

# -------------------------------------------------------------------
# SMALL HELPERS
# -------------------------------------------------------------------

def _safe_int(value, default: int = 0) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except Exception:
        return default


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return default


def paginate_df(df: pd.DataFrame, key_prefix: str, page_size: int = 10):
    """
    Pure pagination logic.
    """
    total = len(df)
    if total == 0:
        return df, 0, 1, 1

    max_page = max(1, math.ceil(total / page_size))
    page_key = f"{key_prefix}_page"

    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    current = st.session_state[page_key]
    if current < 1:
        current = 1
    if current > max_page:
        current = max_page
    st.session_state[page_key] = current

    start = (current - 1) * page_size
    end = start + page_size
    return df.iloc[start:end], total, max_page, current


def download_link_from_df(df: pd.DataFrame, filename: str, label: str, key: str) -> None:
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
        key=key,
    )


def build_link_column_config(df: pd.DataFrame) -> Dict:
    """
    Treat obvious link/URL columns as clickable.
    """
    cfg: Dict[str, st.column_config.BaseColumn] = {}

    for col in df.columns:
        lower = col.lower()
        if "link" in lower or "url" in lower:
            cfg[col] = st.column_config.LinkColumn(col)
        else:
            sample = df[col].dropna().astype(str).head(20)
            if not sample.empty and (sample.str.startswith("http").mean() > 0.6):
                cfg[col] = st.column_config.LinkColumn(col)

    return cfg

# -------------------------------------------------------------------
# HEADER
# -------------------------------------------------------------------

def render_header(branding_row: pd.Series, summary_row: pd.Series) -> None:
    institution_name = branding_row.get("branding_institution_name", "OSF Institution [Demo]")
    logo_url = branding_row.get("branding_institution_logo_url", "").strip()
    report_month = summary_row.get("report_month", "")

    if logo_url:
        logo_html = (
            f'<img src="{logo_url}" '
            'style="width:48px;height:48px;border-radius:50%;object-fit:cover;'
            'margin-right:12px;" />'
        )
    else:
        initials = "".join([w[0] for w in institution_name.split()[:2]]).upper()
        logo_html = (
            '<div style="width:48px;height:48px;border-radius:50%;'
            'background:#0b2233;display:flex;align-items:center;justify-content:center;'
            'font-weight:700;font-size:20px;margin-right:12px;color:#ffffff;">'
            f'{initials}</div>'
        )

    subtitle_bits = ["Institutions Dashboard (Demo)"]
    if report_month:
        subtitle_bits.append(f"Report month: {report_month}")
    subtitle = " • ".join(subtitle_bits)

    st.markdown(
        f"""
        <div style="
            background:#12364a;
            padding:16px 32px;
            display:flex;
            align-items:center;
            justify-content:space-between;
            color:#ffffff;
            box-shadow:0 4px 10px rgba(0,0,0,0.18);
            margin-bottom:0.5rem;
        ">
          <div style="display:flex;align-items:center;">
            {logo_html}
            <div>
              <div style="font-size:20px;font-weight:700;letter-spacing:0.01em;">
                {institution_name}
              </div>
              <div style="font-size:13px;opacity:0.9;margin-top:2px;">
                {subtitle}
              </div>
            </div>
          </div>
          <div style="font-size:13px;opacity:0.9;">
            Demo view
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -------------------------------------------------------------------
# SUMMARY TAB
# -------------------------------------------------------------------

def render_summary_tab(summary_row: pd.Series,
                       users: pd.DataFrame,
                       projects: pd.DataFrame,
                       registrations: pd.DataFrame,
                       preprints: pd.DataFrame) -> None:
    st.markdown("### Summary")

    total_users = len(users)
    total_monthly_logged_in_users = _safe_int(summary_row.get("summary_monthly_logged_in_users", "0"))
    total_monthly_active_users = _safe_int(summary_row.get("summary_monthly_active_users", "0"))
    projects_public = _safe_int(summary_row.get("projects_public_count", "0"))
    projects_private = _safe_int(summary_row.get("projects_private_count", "0"))
    regs_public = _safe_int(summary_row.get("registrations_public_count", "0"))
    regs_embargoed = _safe_int(summary_row.get("registrations_embargoed_count", "0"))
    total_preprints = len(preprints)

    total_public_private_projects = projects_public + projects_private
    total_public_embargoed_regs = regs_public + regs_embargoed

    if "public_file_count" in users.columns:
        total_public_files = users["public_file_count"].apply(_safe_int).sum()
    else:
        total_public_files = 0

    all_content = pd.concat(
        [projects.assign(_src="project"),
         registrations.assign(_src="registration"),
         preprints.assign(_src="preprint")],
        ignore_index=True,
    )
    if "storage_gb" in all_content.columns:
        total_storage_gb = all_content["storage_gb"].apply(_safe_float).sum()
    else:
        total_storage_gb = 0.0

    metrics = {
        "Total Users": total_users,
        "Total Monthly Logged in Users": total_monthly_logged_in_users,
        "Total Monthly Active Users": total_monthly_active_users,
        "OSF Public and Private Projects": total_public_private_projects,
        "OSF Public and Embargoed Registrations": total_public_embargoed_regs,
        "OSF Preprints": total_preprints,
        "Total Public File Count": total_public_files,
        "Total Storage in GB": total_storage_gb,
    }

    labels = list(metrics.keys())
    values = list(metrics.values())

    top_row = st.columns(4)
    for col, idx in zip(top_row, range(4)):
        with col:
            st.metric(label=labels[idx], value=f"{values[idx]:,}")

    bottom_row = st.columns(4)
    for col, idx in zip(bottom_row, range(4, 8)):
        with col:
            val = values[idx]
            if isinstance(val, float) and not float(val).is_integer():
                v_str = f"{val:,.1f}"
            else:
                v_str = f"{int(val):,}"
            st.metric(label=labels[idx], value=v_str)

    st.write("---")

    # Donut helper
    def donut_from_counts(title: str, counts: Dict[str, int]) -> None:
        data = pd.DataFrame(
            {"category": list(counts.keys()), "value": list(counts.values())}
        )
        if data["value"].sum() <= 0:
            st.caption(f"{title}: no data")
            return

        spec = {
            "mark": {"type": "arc", "innerRadius": 60},
            "encoding": {
                "theta": {"field": "value", "type": "quantitative"},
                "color": {
                    "field": "category",
                    "type": "nominal",
                    "legend": {"orient": "bottom"},
                },
                "tooltip": [
                    {"field": "category", "type": "nominal"},
                    {"field": "value", "type": "quantitative"},
                ],
            },
        }
        st.vega_lite_chart(data, spec, width="stretch")
        st.caption(title)

    # Users by department
    dept_col = None
    for candidate in ["department", "Department", "dept"]:
        if candidate in users.columns:
            dept_col = candidate
            break

    users_by_dept: Dict[str, int] = {}
    if dept_col:
        users_by_dept = users[dept_col].replace("", "Unknown").value_counts().to_dict()

    proj_counts = {"Public": projects_public, "Private": projects_private}
    reg_counts = {"Public": regs_public, "Embargoed": regs_embargoed}

    c1, c2, c3 = st.columns(3)
    with c1:
        donut_from_counts("Total Users by Department", users_by_dept)
    with c2:
        donut_from_counts("Public vs Private Projects", proj_counts)
    with c3:
        donut_from_counts("Public vs Embargoed Registrations", reg_counts)

    st.write("---")

    # Total OSF Objects (no users)
    osf_objects = {
        "Public registrations": regs_public,
        "Embargoed registrations": regs_embargoed,
        "Public projects": projects_public,
        "Private projects": projects_private,
        "Preprints": total_preprints,
    }

    # Top 10 licenses
    license_counts: Dict[str, int] = {}
    if "license" in all_content.columns:
        series = (
            all_content["license"]
            .fillna("")
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .head(10)
        )
        license_counts = series.to_dict()

    # Top 10 add-ons
    addon_counts: Dict[str, int] = {}
    if "add_ons" in all_content.columns:
        all_addons: List[str] = []
        for cell in all_content["add_ons"].fillna(""):
            parts = [p.strip() for p in cell.replace(";", ",").split(",") if p.strip()]
            all_addons.extend(parts)
        if all_addons:
            s = pd.Series(all_addons).value_counts().head(10)
            addon_counts = s.to_dict()

    c4, c5, c6 = st.columns(3)
    with c4:
        donut_from_counts("Total OSF Objects", osf_objects)
    with c5:
        donut_from_counts("Top 10 Licenses", license_counts)
    with c6:
        donut_from_counts("Top 10 Add-ons", addon_counts)

    st.write("---")

    # Storage regions
    region_counts: Dict[str, int] = {}
    if "storage_region" in all_content.columns:
        region_counts = (
            all_content["storage_region"]
            .fillna("")
            .replace("", "Unknown")
            .value_counts()
            .to_dict()
        )

    c7, _, _ = st.columns([1, 1, 1])
    with c7:
        donut_from_counts("Top Storage Regions", region_counts)

# -------------------------------------------------------------------
# GENERIC TABLE TAB
# -------------------------------------------------------------------

def render_table_tab(
    label: str,
    df: pd.DataFrame,
    default_columns: List[str],
    filter_config: Dict,
    key_prefix: str,
    count_label: str,
) -> None:
    st.markdown(f"### {label}")
    st.markdown(f"**{len(df):,} {count_label}**")

    # ------------------------------------------------------------------
    # ACTION ROW: right-aligned buttons (Filters / Customize / Download)
    # ------------------------------------------------------------------
    spacer, action_col1, action_col2, action_col3 = st.columns([6, 1, 1, 1])

    filters_state_key = f"{key_prefix}_filters_open"
    customize_state_key = f"{key_prefix}_customize_open"
    if filters_state_key not in st.session_state:
        st.session_state[filters_state_key] = False
    if customize_state_key not in st.session_state:
        st.session_state[customize_state_key] = False

    with action_col1:
        if st.button("Filters", key=f"{key_prefix}_filters_btn"):
            st.session_state[filters_state_key] = not st.session_state[filters_state_key]

    with action_col2:
        if st.button("Customize", key=f"{key_prefix}_customize_btn"):
            st.session_state[customize_state_key] = not st.session_state[customize_state_key]

    # We'll fill the Download CSV button after we have the filtered view
    download_container = action_col3

    st.markdown("<div style='margin-top:0.25rem;margin-bottom:0.25rem;'></div>", unsafe_allow_html=True)

    work_df = df.copy()

    # --- Filters ---
    if st.session_state[filters_state_key] and filter_config:
        st.markdown("#### Filters")
        for col_name, cfg in filter_config.items():
            if col_name not in work_df.columns:
                continue
            col_label = cfg.get("label", col_name)
            ftype = cfg.get("type", "multiselect")

            options = sorted(
                [v for v in work_df[col_name].unique() if str(v).strip() != ""]
            )
            if not options:
                continue

            if ftype == "multiselect":
                selected = st.multiselect(
                    col_label,
                    options,
                    key=f"{key_prefix}_f_{col_name}",
                )
                if selected:
                    mask = pd.Series(True, index=work_df.index)
                    for val in selected:
                        mask &= work_df[col_name].astype(str).str.contains(str(val), na=False)
                    work_df = work_df[mask]
            elif ftype == "selectbox":
                choice = st.selectbox(
                    col_label,
                    ["All"] + options,
                    key=f"{key_prefix}_f_{col_name}",
                )
                if choice != "All":
                    work_df = work_df[work_df[col_name] == choice]

    # --- Customize columns ---
    visible_key = f"{key_prefix}_visible_columns"
    if visible_key not in st.session_state:
        visible = [c for c in default_columns if c in work_df.columns] or list(work_df.columns)
        st.session_state[visible_key] = visible

    if st.session_state[customize_state_key]:
        st.markdown("#### Customize columns")
        all_cols = list(work_df.columns)
        selected = st.multiselect(
            "Columns to display",
            all_cols,
            default=st.session_state[visible_key],
            key=f"{key_prefix}_custom_cols",
        )
        if selected:
            st.session_state[visible_key] = selected

    visible_cols = [c for c in st.session_state[visible_key] if c in work_df.columns]
    if not visible_cols:
        visible_cols = list(work_df.columns)

    work_df = work_df[visible_cols]

    # Download CSV (filtered + visible)
    with download_container:
        if not work_df.empty:
            download_link_from_df(
                work_df,
                filename=f"{label.lower()}_filtered.csv",
                label="Download CSV",
                key=f"{key_prefix}_download_btn",
            )

    if work_df.empty:
        st.info("No rows match the current filters.")
        return

    # --- Paginate then display ---
    page_df, total_filtered, max_page, current_page = paginate_df(work_df, key_prefix=key_prefix, page_size=10)

    st.markdown(
        f"<div style='font-size:0.9rem;color:#4A5568;margin-bottom:0.2rem;'>{total_filtered} results</div>",
        unsafe_allow_html=True,
    )

    col_cfg = build_link_column_config(page_df)

    st.dataframe(
        page_df,
        hide_index=True,
        width="stretch",
        column_config=col_cfg,
    )

    # Pagination BELOW the table
    st.markdown("<div style='margin-top:0.3rem;'></div>", unsafe_allow_html=True)

    page_key = f"{key_prefix}_page"
    pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns([3, 1, 1, 1, 3])

    with pcol2:
        if st.button("«", key=f"{page_key}_first") and total_filtered > 0:
            st.session_state[page_key] = 1
    with pcol3:
        if st.button("‹", key=f"{page_key}_prev") and current_page > 1:
            st.session_state[page_key] = current_page - 1
    with pcol4:
        if st.button("›", key=f"{page_key}_next") and current_page < max_page:
            st.session_state[page_key] = current_page + 1

    with pcol3:
        st.markdown(
            f"<div style='text-align:center;font-size:0.8rem;color:#4A5568;'>Page {current_page} of {max_page}</div>",
            unsafe_allow_html=True,
        )

# -------------------------------------------------------------------
# MAIN APP
# -------------------------------------------------------------------

def main() -> None:
    try:
        branding_row, summary_row, users, projects, registrations, preprints = load_data(DATA_FILE)
    except FileNotFoundError:
        st.error(
            f"Could not find CSV file at `{DATA_FILE.name}`. "
            "Make sure it is in the same folder as `dashboard.py` in your repo."
        )
        return

    render_header(branding_row, summary_row)

    tab_summary, tab_users, tab_projects, tab_regs, tab_preprints = st.tabs(
        ["Summary", "Users", "Projects", "Registrations", "Preprints"]
    )

    with tab_summary:
        render_summary_tab(summary_row, users, projects, registrations, preprints)

    with tab_users:
        users_default_cols = [
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
            "month_last_login",
            "month_last_active",
        ]

        users_filters = {
            "department": {"type": "selectbox", "label": "Department"},
        }

        render_table_tab(
            label="Users",
            df=users,
            default_columns=users_default_cols,
            filter_config=users_filters,
            key_prefix="users",
            count_label="Users",
        )

    with tab_projects:
        proj_default_cols = [
            "name_or_title",
            "osf_link",
            "created_date",
            "modified_date",
            "doi",
            "storage_region",
            "storage_gb",
            "contributor_name",
            "views_last_30_days",
            "license",
            "resource_type",
            "funder_name",
            "add_ons",
        ]

        proj_filters = {
            "contributor_name": {"type": "multiselect", "label": "Creator"},
            "license": {"type": "multiselect", "label": "License"},
            "resource_type": {"type": "multiselect", "label": "Resource type"},
            "storage_region": {"type": "multiselect", "label": "Storage region"},
            "funder_name": {"type": "multiselect", "label": "Funder"},
            "add_ons": {"type": "multiselect", "label": "Add-ons"},
        }

        render_table_tab(
            label="Projects",
            df=projects,
            default_columns=proj_default_cols,
            filter_config=proj_filters,
            key_prefix="projects",
            count_label="Projects",
        )

    with tab_regs:
        reg_default_cols = [
            "name_or_title",
            "osf_link",
            "created_date",
            "modified_date",
            "doi",
            "storage_region",
            "storage_gb",
            "contributor_name",
            "views_last_30_days",
            "license",
            "resource_type",
            "funder_name",
        ]

        reg_filters = {
            "contributor_name": {"type": "multiselect", "label": "Creator"},
            "license": {"type": "multiselect", "label": "License"},
            "resource_type": {"type": "multiselect", "label": "Resource type"},
            "storage_region": {"type": "multiselect", "label": "Storage region"},
            "funder_name": {"type": "multiselect", "label": "Funder"},
        }

        render_table_tab(
            label="Registrations",
            df=registrations,
            default_columns=reg_default_cols,
            filter_config=reg_filters,
            key_prefix="registrations",
            count_label="Registrations",
        )

    with tab_preprints:
        pp_default_cols = [
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

        pp_filters = {
            "contributor_name": {"type": "multiselect", "label": "Creator"},
            "license": {"type": "multiselect", "label": "License"},
        }

        render_table_tab(
            label="Preprints",
            df=preprints,
            default_columns=pp_default_cols,
            filter_config=pp_filters,
            key_prefix="preprints",
            count_label="Preprints",
        )


if __name__ == "__main__":
    main()
