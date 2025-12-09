import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Institutions Dashboard (Demo)",
    layout="wide",
)

DATA_FILE = "institution_dashboard_data.csv"
PAGE_SIZE = 10


# ---------- Utilities ----------

def _num(series):
    """Convert a string series to numeric safely, returning float with 0 for blanks."""
    return pd.to_numeric(series.replace("", pd.NA), errors="coerce").fillna(0.0)


@st.cache_data
def load_data(path):
    df = pd.read_csv(path, dtype=str).fillna("")
    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    if "row_type" not in df.columns:
        st.error(
            "CSV must include a 'row_type' column "
            "(branding/summary/user/project/registration/preprint)."
        )
        st.stop()

    df["row_type_norm"] = df["row_type"].str.lower().str.strip()

    branding_row = None
    summary_row = None

    if "branding" in df["row_type_norm"].values:
        branding_row = df[df["row_type_norm"] == "branding"].iloc[0]

    if "summary" in df["row_type_norm"].values:
        summary_row = df[df["row_type_norm"] == "summary"].iloc[0]

    users = df[df["row_type_norm"] == "user"].copy()
    projects = df[df["row_type_norm"] == "project"].copy()
    registrations = df[df["row_type_norm"] == "registration"].copy()
    preprints = df[df["row_type_norm"] == "preprint"].copy()

    # Numeric columns that may appear on object rows
    numeric_cols = [
        "public_projects",
        "private_projects",
        "public_registration_count",
        "embargoed_registration_count",
        "published_preprint_count",
        "public_file_count",
        "storage_gb",
        "storage_byte_count",
        "views_last_30_days",
        "downloads_last_30_days",
    ]

    for frame in (users, projects, registrations, preprints):
        for col in numeric_cols:
            if col in frame.columns:
                frame[col] = _num(frame[col])

    return branding_row, summary_row, users, projects, registrations, preprints


def compute_summary_metrics(summary_row, users, projects, registrations, preprints):
    """Combine explicit summary cells + totals from tab data."""
    def s_get(name, default=0.0):
        if summary_row is None or name not in summary_row.index:
            return float(default)
        val = summary_row[name]
        try:
            return float(val)
        except Exception:
            return float(default)

    total_users = len(users)

    total_monthly_logged_in = int(s_get("summary_monthly_logged_in_users", 0))
    total_monthly_active = int(s_get("summary_monthly_active_users", 0))

    projects_public = s_get("projects_public_count", 0)
    projects_private = s_get("projects_private_count", 0)
    total_projects = int(projects_public + projects_private)

    regs_public = s_get("registrations_public_count", 0)
    regs_emb = s_get("registrations_embargoed_count", 0)
    total_regs_pub_emb = int(regs_public + regs_emb)

    # These three MUST come from tab data, per your latest request
    total_preprints = len(preprints)

    total_public_files = 0.0
    for frame in (projects, registrations, preprints):
        if "public_file_count" in frame.columns:
            total_public_files += frame["public_file_count"].sum()

    total_storage_gb = 0.0
    for frame in (projects, registrations, preprints):
        if "storage_gb" in frame.columns:
            total_storage_gb += frame["storage_gb"].sum()

    return {
        "total_users": total_users,
        "total_monthly_logged_in": total_monthly_logged_in,
        "total_monthly_active": total_monthly_active,
        "total_projects": total_projects,
        "total_regs_pub_emb": total_regs_pub_emb,
        "total_preprints": int(total_preprints),
        "total_public_files": int(total_public_files),
        "total_storage_gb": round(float(total_storage_gb), 1),
        "projects_public": int(projects_public),
        "projects_private": int(projects_private),
        "regs_public": int(regs_public),
        "regs_embargoed": int(regs_emb),
    }


def format_link_cell(text):
    """Turn URLs and 'label|url' into HTML links, otherwise escape text."""
    if not isinstance(text, str):
        text = "" if pd.isna(text) else str(text)

    t = text.strip()
    if not t:
        return ""

    # Pattern: "Label|https://..."
    if "|" in t:
        label, url = t.split("|", 1)
        label = label.strip()
        url = url.strip()
        if url.startswith("http"):
            return f'<a href="{url}" target="_blank">{label}</a>'

    # Plain URL
    if t.startswith("http") or t.startswith("10."):
        # DOI-like, make it a link
        if t.startswith("10."):
            url = "https://doi.org/" + t
        else:
            url = t
        return f'<a href="{url}" target="_blank">{t}</a>'

    return t


def render_table(df, columns, page_key):
    """Render a paginated HTML table with links, 10 rows/page below the table."""
    if df.empty:
        st.write("No results.")
        return

    visible_df = df[columns].copy()

    # Links for obvious link-like columns
    linkish_cols = [
        "osf_link",
        "OSF Link",
        "osf project",
        "doi",
        "DOI",
        "orcid_id",
        "creator_orcid",
        "Creator ORCID",
    ]
    for col in visible_df.columns:
        if any(k.lower().replace(" ", "_") in col.lower().replace(" ", "_") for k in linkish_cols):
            visible_df[col] = visible_df[col].apply(format_link_cell)

    # Pagination state
    total_rows = len(visible_df)
    total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)

    page_state_key = f"{page_key}_page"
    if page_state_key not in st.session_state:
        st.session_state[page_state_key] = 1

    current_page = st.session_state[page_state_key]

    start = (current_page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_df = visible_df.iloc[start:end]

    st.markdown(
        page_df.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

    # Pagination controls under table
    col_prev_all, col_prev, col_page, col_next, col_next_all = st.columns(
        [1, 1, 2, 1, 1]
    )

    with col_prev_all:
        if st.button("≪", key=f"{page_key}_first", width="content") and current_page > 1:
            st.session_state[page_state_key] = 1

    with col_prev:
        if st.button("‹", key=f"{page_key}_prev", width="content") and current_page > 1:
            st.session_state[page_state_key] = current_page - 1

    with col_page:
        st.markdown(
            f"<div style='text-align:center; padding-top:6px;'>"
            f"Page {current_page} of {total_pages}</div>",
            unsafe_allow_html=True,
        )

    with col_next:
        if st.button("›", key=f"{page_key}_next", width="content") and current_page < total_pages:
            st.session_state[page_state_key] = current_page + 1

    with col_next_all:
        if st.button("≫", key=f"{page_key}_last", width="content") and current_page < total_pages:
            st.session_state[page_state_key] = total_pages


def summary_stat_card(label, value):
    card = f"""
    <div style="
        border-radius: 12px;
        border: 1px solid #E3E8F2;
        padding: 16px 24px;
        background-color: #FFFFFF;
        display:flex;
        flex-direction:column;
        justify-content:center;
        height: 140px;
    ">
      <div style="
          width:80px;
          height:80px;
          border-radius:40px;
          background-color:#F1F6FD;
          display:flex;
          align-items:center;
          justify-content:center;
          margin-bottom:12px;
      ">
        <span style="font-size:24px; font-weight:600; color:#1E4A8A;">
          {value}
        </span>
      </div>
      <div style="font-size:14px; color:#394150;">
        {label}
      </div>
    </div>
    """
    st.markdown(card, unsafe_allow_html=True)


# ---------- Page sections ----------

def render_header(branding_row):
    inst_name = "Center For Open Science [from the test env]"
    logo_url = ""
    report_month = ""

    if branding_row is not None:
        inst_name = branding_row.get("branding_institution_name", inst_name)
        logo_url = branding_row.get("branding_institution_logo_url", "")
        report_month = branding_row.get("report_month", "")

    header_html = f"""
    <div style="background-color:#0C3759; padding:16px 32px; color:white;
                border-radius:0 0 8px 8px;">
      <div style="display:flex; align-items:center;">
        <div style="margin-right:16px;">
          {'<img src="' + logo_url + '" alt="logo" style="width:40px;height:40px;border-radius:20px;"/>' if logo_url else ''}
        </div>
        <div>
          <div style="font-size:24px; font-weight:600; margin-bottom:2px;">
            {inst_name}
          </div>
          <div style="font-size:13px; opacity:0.9;">
            Institutions Dashboard (Demo){' • Report month: ' + report_month if report_month else ''}
          </div>
        </div>
      </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def render_summary_tab(summary_metrics, users, projects, registrations, preprints):
    st.markdown("### Summary")

    # Top stats: 8 cards in two rows of 4
    row1 = st.columns(4)
    row1[0].markdown("")
    with row1[0]:
        summary_stat_card("Total Users", summary_metrics["total_users"])
    with row1[1]:
        summary_stat_card(
            "Total Monthly Logged in Users", summary_metrics["total_monthly_logged_in"]
        )
    with row1[2]:
        summary_stat_card(
            "Total Monthly Active Users", summary_metrics["total_monthly_active"]
        )
    with row1[3]:
        summary_stat_card(
            "OSF Public and Private Projects", summary_metrics["total_projects"]
        )

    row2 = st.columns(4)
    with row2[0]:
        summary_stat_card(
            "OSF Public and Embargoed Registrations",
            summary_metrics["total_regs_pub_emb"],
        )
    with row2[1]:
        summary_stat_card("OSF Preprints", summary_metrics["total_preprints"])
    with row2[2]:
        summary_stat_card(
            "Total Public File Count", summary_metrics["total_public_files"]
        )
    with row2[3]:
        summary_stat_card("Total Storage in GB", summary_metrics["total_storage_gb"])

    st.markdown("---")

    # Total users by department donut
    col_dept, col_projects, col_regs = st.columns(3)

    with col_dept:
        if not users.empty and "department" in users.columns:
            dept_counts = users["department"].replace("", "Unknown").value_counts()
            fig = px.pie(
                values=dept_counts.values,
                names=dept_counts.index,
                hole=0.7,
            )
            fig.update_layout(
                title="Total Users by Department",
                showlegend=True,
                height=350,
                margin=dict(l=20, r=20, t=60, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

    # Public vs private projects donut (from summary metrics)
    with col_projects:
        public = summary_metrics["projects_public"]
        private = summary_metrics["projects_private"]
        proj_df = pd.DataFrame(
            {
                "Category": ["Public projects", "Private projects"],
                "Count": [public, private],
            }
        )
        fig = px.pie(proj_df, values="Count", names="Category", hole=0.7)
        fig.update_layout(
            title="Public vs Private Projects",
            showlegend=True,
            height=350,
            margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Public vs embargoed registrations donut
    with col_regs:
        reg_df = pd.DataFrame(
            {
                "Category": ["Public registrations", "Embargoed registrations"],
                "Count": [
                    summary_metrics["regs_public"],
                    summary_metrics["regs_embargoed"],
                ],
            }
        )
        fig = px.pie(reg_df, values="Count", names="Category", hole=0.7)
        fig.update_layout(
            title="Public vs Embargoed Registrations",
            showlegend=True,
            height=350,
            margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Middle row: total OSF objects + top 10 licenses + top 10 add-ons
    col_totals, col_lic, col_addons = st.columns(3)

    with col_totals:
        # From summary metrics
        d = {
            "Public registrations": summary_metrics["regs_public"],
            "Embargoed registrations": summary_metrics["regs_embargoed"],
            "Public projects": summary_metrics["projects_public"],
            "Private projects": summary_metrics["projects_private"],
            "Preprints": summary_metrics["total_preprints"],
        }
        total_df = pd.DataFrame({"Category": list(d.keys()), "Count": list(d.values())})
        fig = px.pie(total_df, values="Count", names="Category", hole=0.7)
        fig.update_layout(
            title="Total OSF Objects",
            showlegend=True,
            height=380,
            margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_lic:
        # Licenses across projects/registrations/preprints
        frames = []
        for df in (projects, registrations, preprints):
            if "license" in df.columns:
                frames.append(df[["license"]].rename(columns={"license": "License"}))
        if frames:
            lic_all = pd.concat(frames, ignore_index=True)
            lic_counts = (
                lic_all["License"]
                .replace("", "Unknown")
                .value_counts()
                .head(10)
                .reset_index()
            )
            lic_counts.columns = ["License", "Count"]
            fig = px.bar(lic_counts, x="License", y="Count")
            fig.update_layout(
                title="Top 10 Licenses",
                height=380,
                margin=dict(l=20, r=20, t=60, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_addons:
        frames = []
        for df in (projects, registrations, preprints):
            if "add_ons" in df.columns:
                frames.append(
                    df[["add_ons"]]
                    .rename(columns={"add_ons": "Add-on"})
                    .assign(Add_on=lambda x: x["Add-on"])
                )
        if frames:
            addon_series = pd.concat(frames, ignore_index=True)["Add-on"].fillna("")
            exploded = (
                addon_series.str.split(",", expand=True)
                .stack()
                .str.strip()
                .replace("", pd.NA)
                .dropna()
            )
            addon_counts = exploded.value_counts().head(10).reset_index()
            addon_counts.columns = ["Add-on", "Count"]
            fig = px.bar(addon_counts, x="Add-on", y="Count")
            fig.update_layout(
                title="Top 10 Add-ons",
                height=380,
                margin=dict(l=20, r=20, t=60, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Bottom: top storage regions donut
    if any("storage_region" in df.columns for df in (projects, registrations, preprints)):
        storage_frames = []
        for df in (projects, registrations, preprints):
            if "storage_region" in df.columns:
                storage_frames.append(
                    df[["storage_region"]].rename(
                        columns={"storage_region": "Storage region"}
                    )
                )
        if storage_frames:
            sr = pd.concat(storage_frames, ignore_index=True)
            sr_counts = (
                sr["Storage region"]
                .replace("", "Unknown")
                .value_counts()
                .reset_index()
            )
            sr_counts.columns = ["Storage region", "Count"]
            fig = px.pie(
                sr_counts, values="Count", names="Storage region", hole=0.7
            )
            fig.update_layout(
                title="Top Storage Regions",
                showlegend=True,
                height=380,
                margin=dict(l=20, r=20, t=60, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)


def render_entity_tab(
    title,
    df,
    page_key,
    total_label,
    filters_config,
    column_order,
    column_labels,
):
    st.markdown(f"### {title}")

    st.markdown(
        f"**{len(df)} {total_label}**",
    )

    # Right-aligned controls bar (filters / customize / download)
    c_left, c_right = st.columns([3, 2])

    with c_right:
        ctrl_cols = st.columns([1, 1, 1])
        # Placeholders – we keep labels to match layout; filters live in drawer below
        with ctrl_cols[0]:
            st.write("")  # spacer
        with ctrl_cols[1]:
            st.write("")
        with ctrl_cols[2]:
            if st.button("Download CSV", key=f"{page_key}_download", width="stretch"):
                st.download_button(
                    label="Download CSV",
                    data=df[column_order].to_csv(index=False).encode("utf-8"),
                    file_name=f"{page_key}.csv",
                    mime="text/csv",
                )

    # Filters drawer (closed by default)
    with st.expander("Filters", expanded=False):
        # Users tab: Has ORCID + Department
        if filters_config.get("has_orcid"):
            has_orcid = st.checkbox("Has ORCID", key=f"{page_key}_has_orcid")
            if has_orcid and "orcid_id" in df.columns:
                df = df[df["orcid_id"].str.strip() != ""].copy()

        if filters_config.get("department") and "department" in df.columns:
            depts = sorted(
                [d for d in df["department"].unique() if d.strip() != ""]
            )
            dept_choices = ["All departments"] + depts
            selected = st.selectbox(
                "Department",
                dept_choices,
                key=f"{page_key}_dept",
            )
            if selected != "All departments":
                df = df[df["department"] == selected].copy()

        # Resource type / license / storage region / add-ons
        if filters_config.get("resource_type") and "resource_type" in df.columns:
            rts = sorted([v for v in df["resource_type"].unique() if v.strip() != ""])
            rts = ["All"] + rts
            sel = st.selectbox(
                "Resource Type",
                rts,
                key=f"{page_key}_rt",
            )
            if sel != "All":
                df = df[df["resource_type"] == sel].copy()

        if filters_config.get("license") and "license" in df.columns:
            lics = sorted([v for v in df["license"].unique() if v.strip() != ""])
            lics = ["All"] + lics
            sel = st.selectbox(
                "License",
                lics,
                key=f"{page_key}_lic",
            )
            if sel != "All":
                df = df[df["license"] == sel].copy()

        if filters_config.get("storage_region") and "storage_region" in df.columns:
            srs = sorted([v for v in df["storage_region"].unique() if v.strip() != ""])
            srs = ["All"] + srs
            sel = st.selectbox(
                "Storage Region",
                srs,
                key=f"{page_key}_sr",
            )
            if sel != "All":
                df = df[df["storage_region"] == sel].copy()

        if filters_config.get("add_ons") and "add_ons" in df.columns:
            all_addons = (
                df["add_ons"]
                .fillna("")
                .str.split(",", expand=True)
                .stack()
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .unique()
            )
            addons_list = sorted(all_addons.tolist())
            addons_list = ["All"] + addons_list
            sel = st.selectbox(
                "Add-ons",
                addons_list,
                key=f"{page_key}_addons",
            )
            if sel != "All":
                df = df[df["add_ons"].str.contains(sel)].copy()

    # Column subset & labels
    existing_cols = [c for c in column_order if c in df.columns]
    display_df = df[existing_cols].rename(columns=column_labels)

    render_table(display_df, display_df.columns.tolist(), page_key)


# ---------- Main ----------

def main():
    branding_row, summary_row, users, projects, registrations, preprints = load_data(
        DATA_FILE
    )

    # Top header (brand bar)
    render_header(branding_row)

    # Tabs
    tab_summary, tab_users, tab_projects, tab_regs, tab_preprints = st.tabs(
        ["Summary", "Users", "Projects", "Registrations", "Preprints"]
    )

    summary_metrics = compute_summary_metrics(
        summary_row, users, projects, registrations, preprints
    )

    with tab_summary:
        render_summary_tab(
            summary_metrics, users, projects, registrations, preprints
        )

    with tab_users:
        user_cols = [
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
            "month_last_active",
            "month_last_login",
        ]
        user_labels = {
            "name_or_title": "Name",
            "department": "Department",
            "osf_link": "OSF Link",
            "orcid_id": "ORCID iD",
            "public_projects": "Public projects",
            "private_projects": "Private projects",
            "public_registration_count": "Public registrations",
            "embargoed_registration_count": "Embargoed registrations",
            "published_preprint_count": "Preprints",
            "public_file_count": "Files on OSF",
            "storage_gb": "Total data stored on OSF (GB)",
            "month_last_active": "Last active (YYYY-MM)",
            "month_last_login": "Last login (YYYY-MM)",
        }
        render_entity_tab(
            "Users",
            users,
            "users",
            "Total Users",
            filters_config={"has_orcid": True, "department": True},
            column_order=user_cols,
            column_labels=user_labels,
        )

    with tab_projects:
        proj_cols = [
            "name_or_title",
            "osf_link",
            "created_date",
            "modified_date",
            "doi",
            "storage_region",
            "storage_gb",
            "license",
            "resource_type",
            "add_ons",
            "funder_name",
            "contributor_name",
            "public_file_count",
        ]
        proj_labels = {
            "name_or_title": "Title",
            "osf_link": "OSF Link",
            "created_date": "Created date",
            "modified_date": "Modified date",
            "doi": "DOI",
            "storage_region": "Storage region",
            "storage_gb": "Total data stored on OSF (GB)",
            "license": "License",
            "resource_type": "Resource type",
            "add_ons": "Add-ons",
            "funder_name": "Funder name",
            "contributor_name": "Creator(s)",
            "public_file_count": "Public files",
        }
        render_entity_tab(
            "Projects",
            projects,
            "projects",
            "Total Projects",
            filters_config={
                "resource_type": True,
                "license": True,
                "storage_region": True,
                "add_ons": True,
            },
            column_order=proj_cols,
            column_labels=proj_labels,
        )

    with tab_regs:
        reg_cols = [
            "name_or_title",
            "osf_link",
            "created_date",
            "modified_date",
            "doi",
            "storage_region",
            "storage_gb",
            "license",
            "resource_type",
            "add_ons",
            "funder_name",
            "contributor_name",
            "public_file_count",
        ]
        reg_labels = {
            "name_or_title": "Title",
            "osf_link": "OSF Link",
            "created_date": "Created date",
            "modified_date": "Modified date",
            "doi": "DOI",
            "storage_region": "Storage region",
            "storage_gb": "Total data stored on OSF (GB)",
            "license": "License",
            "resource_type": "Resource type",
            "add_ons": "Add-ons",
            "funder_name": "Funder name",
            "contributor_name": "Creator(s)",
            "public_file_count": "Public files",
        }
        render_entity_tab(
            "Registrations",
            registrations,
            "registrations",
            "Registrations",
            filters_config={
                "resource_type": True,
                "license": True,
                "storage_region": True,
                "add_ons": True,
            },
            column_order=reg_cols,
            column_labels=reg_labels,
        )

    with tab_preprints:
        pp_cols = [
            "name_or_title",
            "osf_link",
            "created_date",
            "modified_date",
            "doi",
            "license",
            "resource_type",
            "contributor_name",
            "public_file_count",
        ]
        pp_labels = {
            "name_or_title": "Title",
            "osf_link": "Link",
            "created_date": "Created date",
            "modified_date": "Modified date",
            "doi": "DOI",
            "license": "License",
            "resource_type": "Resource type",
            "contributor_name": "Contributor name",
            "public_file_count": "Public files",
        }
        render_entity_tab(
            "Preprints",
            preprints,
            "preprints",
            "Preprints",
            filters_config={"license": True, "resource_type": True},
            column_order=pp_cols,
            column_labels=pp_labels,
        )


if __name__ == "__main__":
    main()
