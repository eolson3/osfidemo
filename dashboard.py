import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st


# ---------------------------
# Page config & basic styling
# ---------------------------
st.set_page_config(
    page_title="OSF Institutions Demo Dashboard",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .osf-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0 1rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .osf-title {
        font-size: 1.8rem;
        font-weight: 700;
    }
    .osf-subtitle {
        font-size: 0.95rem;
        color: #666666;
    }
    .osf-badge {
        background-color: #f5f5f5;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        font-size: 0.75rem;
        color: #555555;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------
# Helper functions
# ---------------------------
def generate_demo_data(n_days: int = 180, n_users: int = 250) -> pd.DataFrame:
    """
    Synthetic OSFI-style event data.
    Each row ~ usage event for a project/registration/file/preprint.
    """
    today = dt.date.today()
    dates = pd.date_range(end=today, periods=n_days, freq="D")

    institutions = ["Sample University"]
    departments = ["Psychology", "Biology", "Computer Science", "Economics", "Library"]
    countries = ["US", "UK", "DE", "NL", "ZA", "BR"]
    resource_types = ["project", "registration", "file", "preprint"]
    visibility = ["public", "private"]
    storage_regions = ["US-East", "US-West", "Germany", "Canada", "Australia"]
    licenses = [
        "CC-By 4.0",
        "CC-By-SA 4.0",
        "CC0 1.0",
        "MIT",
        "Apache-2.0",
        "Other",
    ]
    add_ons = ["Dropbox", "Google Drive", "GitHub", "Figshare", "None"]
    funders = ["NSF", "NIH", "Wellcome Trust", "Horizon Europe", "None"]
    reg_schemas = ["OSF Preregistration", "AsPredicted", "Other"]

    rows = []
    rng = np.random.default_rng(42)

    for date in dates:
        n_events = rng.integers(50, 200)
        for _ in range(n_events):
            user_id = f"user_{rng.integers(1, n_users + 1)}"
            project_id = f"proj_{rng.integers(1, n_users * 3)}"
            inst = rng.choice(institutions)
            dept = rng.choice(departments)
            country = rng.choice(countries)
            rtype = rng.choice(resource_types, p=[0.45, 0.2, 0.2, 0.15])
            vis = rng.choice(visibility, p=[0.6, 0.4])
            size = rng.choice([10_000, 50_000, 200_000, 1_000_000]) * abs(
                rng.normal(1, 0.5)
            )
            has_orcid = rng.random() < 0.35  # 35% ORCID adoption (demo)

            rows.append(
                {
                    "date": date.date(),
                    "user_id": user_id,
                    "project_id": project_id,
                    "institution": inst,
                    "department": dept,
                    "country": country,
                    "resource_type": rtype,
                    "visibility": vis,
                    "size_bytes": max(int(size), 0),
                    "has_orcid": has_orcid,
                    # extra fields for content tabs / graphs
                    "storage_location": rng.choice(storage_regions),
                    "license": rng.choice(licenses),
                    "addon": rng.choice(add_ons),
                    "funder_name": rng.choice(funders),
                    "registration_schema": rng.choice(reg_schemas)
                    if rtype == "registration"
                    else None,
                }
            )

    df = pd.DataFrame(rows)
    return df


def parse_uploaded_data(uploaded_file) -> pd.DataFrame | None:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.lower().endswith(".json"):
            df = pd.read_json(uploaded_file)
        else:
            st.error("Unsupported file type. Please upload CSV or JSON.")
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

    # Normalize date
    date_cols = [
        c for c in df.columns if c.lower() in ["date", "event_date", "timestamp"]
    ]
    if date_cols:
        date_col = date_cols[0]
        df[date_col] = pd.to_datetime(df[date_col]).dt.date
        if date_col != "date":
            df.rename(columns={date_col: "date"}, inplace=True)

    if "size" in df.columns and "size_bytes" not in df.columns:
        df.rename(columns={"size": "size_bytes"}, inplace=True)

    return df


def ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    if "date" not in df.columns:
        df = df.copy()
        df["date"] = pd.date_range(
            end=dt.date.today(), periods=len(df), freq="D"
        ).date
    return df


def compute_overall_metrics(df: pd.DataFrame) -> dict:
    df = ensure_date_column(df)
    today = df["date"].max()
    last_30 = today - dt.timedelta(days=30)

    total_users = df["user_id"].nunique() if "user_id" in df.columns else None

    # For demo: treat "monthly logged in" as users seen in last 30 days,
    # "monthly active" as same set (we don't distinguish view vs action here).
    monthly_logged_in = (
        df.loc[df["date"] >= last_30, "user_id"].nunique()
        if "user_id" in df.columns
        else None
    )
    monthly_active = monthly_logged_in

    total_projects = (
        df.loc[df.get("resource_type", "") == "project", "project_id"].nunique()
        if "project_id" in df.columns and "resource_type" in df.columns
        else None
    )
    total_regs = (
        df.loc[df.get("resource_type", "") == "registration", "project_id"].nunique()
        if "project_id" in df.columns and "resource_type" in df.columns
        else None
    )
    total_preprints = (
        df.loc[df.get("resource_type", "") == "preprint", "project_id"].nunique()
        if "project_id" in df.columns and "resource_type" in df.columns
        else None
    )

    total_files = (
        df.loc[df.get("resource_type", "") == "file"].shape[0]
        if "resource_type" in df.columns
        else None
    )
    total_storage_gb = (
        df["size_bytes"].sum() / 1e9 if "size_bytes" in df.columns else None
    )

    public_share = None
    if "visibility" in df.columns:
        vis_counts = df["visibility"].value_counts(normalize=True)
        public_share = float(vis_counts.get("public", 0.0)) * 100

    orcid_share = None
    if "has_orcid" in df.columns:
        orcid_share = float(df["has_orcid"].mean()) * 100

    return {
        "snapshot_date": today,
        "total_users": total_users,
        "monthly_logged_in": monthly_logged_in,
        "monthly_active": monthly_active,
        "total_projects": total_projects,
        "total_registrations": total_regs,
        "total_preprints": total_preprints,
        "total_files": total_files,
        "total_storage_gb": total_storage_gb,
        "public_share": public_share,
        "orcid_share": orcid_share,
    }


def format_metric(value, default="—", fmt="{:,}"):
    if value is None:
        return default
    try:
        return fmt.format(value)
    except Exception:
        return str(value)


# ---------------------------
# Sidebar: navigation + upload
# ---------------------------
with st.sidebar:
    st.markdown("### 📊 OSF Institutions (Demo)")

    page = st.radio(
        "Tabs",
        [
            "Summary",
            "Users",
            "Projects",
            "Registrations",
            "Preprints",
        ],
        index=0,
    )

    st.markdown("---")
    uploaded_file = st.file_uploader(
        "Upload OSF-style data", type=["csv", "json"], help="CSV or JSON with usage events"
    )
    use_demo = st.checkbox("Use built-in demo data", value=(uploaded_file is None))

    st.markdown("---")
    st.caption(
        "Demo aligned with the OSF Institutions Metrics Dashboard help guide. "
        "Not connected to live OSF."
    )


# ---------------------------
# Load + basic filter (date)
# ---------------------------
if uploaded_file is not None and not use_demo:
    df = parse_uploaded_data(uploaded_file)
    if df is None:
        st.stop()
else:
    df = generate_demo_data()

df = ensure_date_column(df)

with st.sidebar:
    st.markdown("### Snapshot range")
    min_date, max_date = df["date"].min(), df["date"].max()
    date_range = st.date_input(
        "Include events between",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, (tuple, list)):
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

df_filtered = df[
    (df["date"] >= start_date) & (df["date"] <= end_date)
].copy()

# ---------------------------
# Header
# ---------------------------
st.markdown(
    f"""
    <div class="osf-header">
      <div>
        <div class="osf-title">OSF Institutions — Metrics Dashboard (Demo)</div>
        <div class="osf-subtitle">
          Snapshot-style metrics for affiliated users and content, modeled after the official dashboard.
        </div>
      </div>
      <div>
        <span class="osf-badge">Demo snapshot</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metrics = compute_overall_metrics(df_filtered)
st.caption(
    f"Snapshot range: **{start_date} → {end_date}** · "
    f"Rows in snapshot: **{len(df_filtered):,}**"
)


# ======================================================
# SUMMARY TAB
# ======================================================
if page == "Summary":
    st.subheader("Summary (snapshot counts)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total users", format_metric(metrics["total_users"]))
    c2.metric(
        "Total monthly logged in users",
        format_metric(metrics["monthly_logged_in"]),
    )
    c3.metric(
        "Total monthly active users",
        format_metric(metrics["monthly_active"]),
    )
    c4.metric(
        "Users with ORCID (%)",
        format_metric(metrics["orcid_share"], fmt="{:,.1f}%"),
    )

    c5, c6, c7, c8 = st.columns(4)
    c5.metric(
        "OSF public & private projects",
        format_metric(metrics["total_projects"]),
    )
    c6.metric(
        "OSF public & embargoed registrations",
        format_metric(metrics["total_registrations"]),
    )
    c7.metric("OSF preprints", format_metric(metrics["total_preprints"]))
    c8.metric(
        "Total public file count",
        format_metric(metrics["total_files"]),
    )

    c9, c10 = st.columns(2)
    c9.metric(
        "Total storage on OSF (GB)",
        format_metric(metrics["total_storage_gb"], fmt="{:,.2f}"),
    )
    c10.metric(
        "Public content (%)",
        format_metric(metrics["public_share"], fmt="{:,.1f}%"),
    )

    st.markdown("### Visualization graphs")

    # 1. Total users by department
    st.markdown("#### Total users by department")
    if "department" in df_filtered.columns and "user_id" in df_filtered.columns:
        dept_users = (
            df_filtered.groupby("department")["user_id"]
            .nunique()
            .sort_values(ascending=False)
        )
        st.bar_chart(dept_users)
    else:
        st.info("No department or user_id columns found.")

    # 2. Public vs private projects
    st.markdown("#### Public vs. private projects")
    if (
        "resource_type" in df_filtered.columns
        and "visibility" in df_filtered.columns
        and "project_id" in df_filtered.columns
    ):
        proj_vis = (
            df_filtered[df_filtered["resource_type"] == "project"]
            .groupby(["visibility"])["project_id"]
            .nunique()
        )
        st.bar_chart(proj_vis)
    else:
        st.info("No project data available for this chart.")

    # 3. Public vs embargoed registrations (demo: treat private as embargoed)
    st.markdown("#### Public vs. embargoed registrations")
    if (
        "resource_type" in df_filtered.columns
        and "visibility" in df_filtered.columns
        and "project_id" in df_filtered.columns
    ):
        reg_df = df_filtered[df_filtered["resource_type"] == "registration"].copy()
        reg_df["reg_status"] = reg_df["visibility"].replace(
            {"private": "embargoed"}
        )
        reg_status = reg_df.groupby("reg_status")["project_id"].nunique()
        st.bar_chart(reg_status)
    else:
        st.info("No registration data available for this chart.")

    # 4. Total OSF objects by type & visibility
    st.markdown("#### Total OSF objects (by type & visibility)")
    if "resource_type" in df_filtered.columns and "visibility" in df_filtered.columns:
        obj = (
            df_filtered[df_filtered["resource_type"].isin(
                ["project", "registration", "preprint"]
            )]
            .groupby(["resource_type", "visibility"])["project_id"]
            .nunique()
            .unstack(fill_value=0)
        )
        st.bar_chart(obj)
    else:
        st.info("No resource_type / visibility columns found.")

    # 5. Top 10 licenses
    st.markdown("#### Top 10 licenses")
    if "license" in df_filtered.columns:
        lic_counts = df_filtered["license"].value_counts().head(10)
        st.bar_chart(lic_counts)
    else:
        st.info("No license column found.")

    # 6. Top 10 add-ons
    st.markdown("#### Top 10 add-ons")
    if "addon" in df_filtered.columns:
        addon_counts = df_filtered["addon"].value_counts().head(10)
        st.bar_chart(addon_counts)
    else:
        st.info("No addon column found.")

    # 7. Top storage regions
    st.markdown("#### Top storage regions")
    if "storage_location" in df_filtered.columns and "project_id" in df_filtered.columns:
        region_counts = (
            df_filtered[df_filtered["resource_type"] == "project"]
            .groupby("storage_location")["project_id"]
            .nunique()
            .sort_values(ascending=False)
        )
        st.bar_chart(region_counts)
    else:
        st.info("No storage_location column found.")


# ======================================================
# USERS TAB
# ======================================================
elif page == "Users":
    st.subheader("Users")

    # Per-guide filters: Department + ORCID presence
    dept_filter = None
    orcid_filter = "All"
    if "department" in df_filtered.columns:
        depts = sorted(df_filtered["department"].unique().tolist())
        dept_filter = st.multiselect("Filter by department", depts, default=depts)
    if "has_orcid" in df_filtered.columns:
        orcid_filter = st.selectbox(
            "Filter by ORCID",
            ["All", "Has ORCID", "No ORCID"],
            index=0,
        )

    df_users = df_filtered.copy()
    if dept_filter is not None and len(dept_filter) > 0:
        df_users = df_users[df_users["department"].isin(dept_filter)]
    if orcid_filter != "All" and "has_orcid" in df_users.columns:
        if orcid_filter == "Has ORCID":
            df_users = df_users[df_users["has_orcid"] == True]
        else:
            df_users = df_users[df_users["has_orcid"] == False]

    metrics_users = compute_overall_metrics(df_users)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total users", format_metric(metrics_users["total_users"]))
    c2.metric(
        "Users with ORCID (%)",
        format_metric(metrics_users["orcid_share"], fmt="{:,.1f}%"),
    )
    c3.metric(
        "Monthly active users",
        format_metric(metrics_users["monthly_active"]),
    )

    # Build Users table to mirror help guide columns
    if "user_id" not in df_users.columns:
        st.info("No user_id column available.")
    else:
        base = df_users

        # Name – we don't have real names in demo, so synthesize from user_id
        user_index = base["user_id"].unique()
        users_df = pd.DataFrame(index=user_index)
        users_df.index.name = "OSF Link"

        users_df["Name"] = [uid.replace("user_", "User ") for uid in users_df.index]

        if "department" in base.columns:
            dept = (
                base.groupby("user_id")["department"]
                .agg(lambda x: x.mode().iat[0] if not x.mode().empty else None)
                .reindex(users_df.index)
            )
            users_df["Department"] = dept

        # ORCID flag
        if "has_orcid" in base.columns:
            orcid = (
                base.groupby("user_id")["has_orcid"]
                .max()
                .reindex(users_df.index)
            )
            users_df["ORCID?"] = orcid

        # Counts from events
        def _count_for(user_subset, condition):
            return (
                user_subset.loc[condition, "project_id"]
                .nunique()
                if not user_subset.loc[condition].empty
                else 0
            )

        pub_proj = []
        priv_proj = []
        pub_reg = []
        emb_reg = []
        preprints = []
        files = []
        data_bytes = []

        for uid in users_df.index:
            sub = base[base["user_id"] == uid]
            if sub.empty:
                pub_proj.append(0)
                priv_proj.append(0)
                pub_reg.append(0)
                emb_reg.append(0)
                preprints.append(0)
                files.append(0)
                data_bytes.append(0)
                continue

            if "resource_type" in sub.columns and "visibility" in sub.columns:
                proj_mask = sub["resource_type"] == "project"
                reg_mask = sub["resource_type"] == "registration"
                pp_mask = sub["resource_type"] == "preprint"
                file_mask = sub["resource_type"] == "file"

                pub_proj.append(
                    _count_for(sub, proj_mask & (sub["visibility"] == "public"))
                )
                priv_proj.append(
                    _count_for(sub, proj_mask & (sub["visibility"] == "private"))
                )
                pub_reg.append(
                    _count_for(sub, reg_mask & (sub["visibility"] == "public"))
                )
                emb_reg.append(
                    _count_for(sub, reg_mask & (sub["visibility"] == "private"))
                )
                preprints.append(
                    _count_for(sub, pp_mask)
                )
                files.append(
                    sub.loc[file_mask].shape[0]
                )
            else:
                pub_proj.append(0)
                priv_proj.append(0)
                pub_reg.append(0)
                emb_reg.append(0)
                preprints.append(0)
                files.append(0)

            if "size_bytes" in sub.columns:
                data_bytes.append(int(sub["size_bytes"].sum()))
            else:
                data_bytes.append(0)

        users_df["Public projects"] = pub_proj
        users_df["Private projects"] = priv_proj
        users_df["Public registrations"] = pub_reg
        users_df["Embargoed registrations"] = emb_reg
        users_df["Preprints"] = preprints
        users_df["Files on OSF"] = files
        users_df["Total data stored on OSF (GB)"] = [
            b / 1e9 for b in data_bytes
        ]

        # Account created / last login / last action (demo: infer from dates)
        date_group = base.groupby("user_id")["date"]
        users_df["Account created"] = date_group.min().reindex(users_df.index)
        users_df["Last login"] = date_group.max().reindex(users_df.index)
        users_df["Last action"] = date_group.max().reindex(users_df.index)

        # Order similar to guide
        display_cols = [
            "Name",
            "Department",
            "ORCID?",
            "Public projects",
            "Private projects",
            "Public registrations",
            "Embargoed registrations",
            "Preprints",
            "Files on OSF",
            "Total data stored on OSF (GB)",
            "Account created",
            "Last login",
            "Last action",
        ]
        existing = [c for c in display_cols if c in users_df.columns]

        st.markdown("#### Users table (modeled after Users tab)")
        st.dataframe(users_df[existing].sort_values("Name").head(500))


# ======================================================
# PROJECTS TAB
# ======================================================
elif page == "Projects":
    st.subheader("Projects")

    proj_df = df_filtered[df_filtered.get("resource_type") == "project"].copy()
    if proj_df.empty:
        st.info("No project data available in this snapshot.")
    else:
        # Basic license / storage filters (like OSF search-style filters)
        c1, c2 = st.columns(2)
        if "license" in proj_df.columns:
            licenses = sorted(proj_df["license"].dropna().unique().tolist())
            lic_sel = c1.multiselect("Filter by license", licenses, default=licenses)
            proj_df = proj_df[proj_df["license"].isin(lic_sel)]
        if "storage_location" in proj_df.columns:
            regions = sorted(proj_df["storage_location"].dropna().unique().tolist())
            reg_sel = c2.multiselect(
                "Filter by storage location", regions, default=regions
            )
            proj_df = proj_df[proj_df["storage_location"].isin(reg_sel)]

        # Aggregate to one row per project_id
        grp = proj_df.groupby("project_id")
        projects = pd.DataFrame(index=grp.size().index)
        projects.index.name = "Link"

        # Titles (fake)
        projects["Title"] = [f"Project {pid.split('_')[-1]}" for pid in projects.index]
        projects["Created date"] = grp["date"].min()
        projects["Modified date"] = grp["date"].max()

        if "storage_location" in proj_df.columns:
            projects["Storage location"] = grp["storage_location"].agg(
                lambda x: x.mode().iat[0] if not x.mode().empty else None
            )
        if "size_bytes" in proj_df.columns:
            projects["Total data stored on OSF (GB)"] = grp["size_bytes"].sum() / 1e9

        if "license" in proj_df.columns:
            projects["License"] = grp["license"].agg(
                lambda x: x.mode().iat[0] if not x.mode().empty else None
            )
        if "addon" in proj_df.columns:
            projects["Add-ons"] = grp["addon"].agg(
                lambda x: ", ".join(sorted(x.dropna().unique().tolist())[:3])
            )
        if "funder_name" in proj_df.columns:
            projects["Funder name"] = grp["funder_name"].agg(
                lambda x: ", ".join(sorted(x.dropna().unique().tolist())[:3])
            )

        # Views last 30 days (demo: count events in last 30 days)
        last_30 = metrics["snapshot_date"] - dt.timedelta(days=30)
        recent = proj_df[proj_df["date"] >= last_30]
        views_30 = (
            recent.groupby("project_id")["date"].count().reindex(projects.index).fillna(0)
        )
        projects["Views (last 30 days)"] = views_30.astype(int)

        # For demo, DOI and Contributor name left blank or simple placeholders
        projects["DOI"] = ""
        projects["Contributor name"] = ""

        display_cols = [
            "Title",
            "Created date",
            "Modified date",
            "DOI",
            "Storage location",
            "Total data stored on OSF (GB)",
            "Contributor name",
            "Views (last 30 days)",
            "License",
            "Add-ons",
            "Funder name",
        ]
        existing = [c for c in display_cols if c in projects.columns]

        cA, cB = st.columns(2)
        cA.metric(
            "Top-level projects (rows)",
            format_metric(len(projects)),
        )
        if "Total data stored on OSF (GB)" in projects.columns:
            cB.metric(
                "Total storage (GB)",
                format_metric(
                    projects["Total data stored on OSF (GB)"].sum(), fmt="{:,.2f}"
                ),
            )

        st.markdown("#### Projects table (modeled after Projects tab)")
        st.dataframe(
            projects[existing]
            .sort_values("Modified date", ascending=False)
            .head(500)
        )


# ======================================================
# REGISTRATIONS TAB
# ======================================================
elif page == "Registrations":
    st.subheader("Registrations")

    reg_df = df_filtered[df_filtered.get("resource_type") == "registration"].copy()
    if reg_df.empty:
        st.info("No registration data available in this snapshot.")
    else:
        c1, c2 = st.columns(2)
        if "license" in reg_df.columns:
            licenses = sorted(reg_df["license"].dropna().unique().tolist())
            lic_sel = c1.multiselect("Filter by license", licenses, default=licenses)
            reg_df = reg_df[reg_df["license"].isin(lic_sel)]
        if "storage_location" in reg_df.columns:
            regions = sorted(reg_df["storage_location"].dropna().unique().tolist())
            reg_sel = c2.multiselect(
                "Filter by storage location", regions, default=regions
            )
            reg_df = reg_df[reg_df["storage_location"].isin(reg_sel)]

        grp = reg_df.groupby("project_id")
        regs = pd.DataFrame(index=grp.size().index)
        regs.index.name = "Link"

        regs["Title"] = [
            f"Registration {pid.split('_')[-1]}" for pid in regs.index
        ]
        regs["Created date"] = grp["date"].min()
        regs["Modified date"] = grp["date"].max()

        if "storage_location" in reg_df.columns:
            regs["Storage location"] = grp["storage_location"].agg(
                lambda x: x.mode().iat[0] if not x.mode().empty else None
            )
        if "size_bytes" in reg_df.columns:
            regs["Total data stored on OSF (GB)"] = grp["size_bytes"].sum() / 1e9
        if "license" in reg_df.columns:
            regs["License"] = grp["license"].agg(
                lambda x: x.mode().iat[0] if not x.mode().empty else None
            )
        if "funder_name" in reg_df.columns:
            regs["Funder name"] = grp["funder_name"].agg(
                lambda x: ", ".join(sorted(x.dropna().unique().tolist())[:3])
            )
        if "registration_schema" in reg_df.columns:
            regs["Registration schema"] = grp["registration_schema"].agg(
                lambda x: x.mode().iat[0] if not x.mode().empty else None
            )

        last_30 = metrics["snapshot_date"] - dt.timedelta(days=30)
        recent = reg_df[reg_df["date"] >= last_30]
        views_30 = (
            recent.groupby("project_id")["date"].count().reindex(regs.index).fillna(0)
        )
        regs["Views (last 30 days)"] = views_30.astype(int)

        regs["DOI"] = ""
        regs["Contributor name"] = ""

        display_cols = [
            "Title",
            "Created date",
            "Modified date",
            "DOI",
            "Storage location",
            "Total data stored on OSF (GB)",
            "Contributor name",
            "Views (last 30 days)",
            "Resource type",
            "License",
            "Funder name",
            "Registration schema",
        ]
        # Resource type is fixed "registration" here
        regs["Resource type"] = "StudyRegistration"

        existing = [c for c in display_cols if c in regs.columns]

        cA, cB = st.columns(2)
        cA.metric("Registrations (rows)", format_metric(len(regs)))
        if "Total data stored on OSF (GB)" in regs.columns:
            cB.metric(
                "Total storage (GB)",
                format_metric(
                    regs["Total data stored on OSF (GB)"].sum(), fmt="{:,.2f}"
                ),
            )

        st.markdown("#### Registrations table (modeled after Registrations tab)")
        st.dataframe(
            regs[existing].sort_values("Modified date", ascending=False).head(500)
        )


# ======================================================
# PREPRINTS TAB
# ======================================================
elif page == "Preprints":
    st.subheader("Preprints")

    pp_df = df_filtered[df_filtered.get("resource_type") == "preprint"].copy()
    if pp_df.empty:
        st.info("No preprint data available in this snapshot.")
    else:
        if "license" in pp_df.columns:
            licenses = sorted(pp_df["license"].dropna().unique().tolist())
            lic_sel = st.multiselect("Filter by license", licenses, default=licenses)
            pp_df = pp_df[pp_df["license"].isin(lic_sel)]

        grp = pp_df.groupby("project_id")
        pps = pd.DataFrame(index=grp.size().index)
        pps.index.name = "Link"

        pps["Title"] = [f"Preprint {pid.split('_')[-1]}" for pid in pps.index]
        pps["Created date"] = grp["date"].min()
        pps["Modified date"] = grp["date"].max()

        if "license" in pp_df.columns:
            pps["License"] = grp["license"].agg(
                lambda x: x.mode().iat[0] if not x.mode().empty else None
            )

        last_30 = metrics["snapshot_date"] - dt.timedelta(days=30)
        recent = pp_df[pp_df["date"] >= last_30]
        views_30 = (
            recent.groupby("project_id")["date"].count().reindex(pps.index).fillna(0)
        )
        # For demo: treat same counts as both views and downloads
        pps["Views (last 30 days)"] = views_30.astype(int)
        pps["Downloads (last 30 days)"] = views_30.astype(int)

        pps["DOI"] = ""
        pps["Contributor name"] = ""

        display_cols = [
            "Title",
            "Created date",
            "Modified date",
            "DOI",
            "License",
            "Contributor name",
            "Views (last 30 days)",
            "Downloads (last 30 days)",
        ]
        existing = [c for c in display_cols if c in pps.columns]

        cA, cB = st.columns(2)
        cA.metric("Preprints (rows)", format_metric(len(pps)))
        cB.metric(
            "Avg. views (30 days)",
            format_metric(
                pps["Views (last 30 days)"].mean() if len(pps) else 0,
                fmt="{:,.1f}",
            ),
        )

        st.markdown("#### Preprints table (modeled after Preprints tab)")
        st.dataframe(
            pps[existing].sort_values("Modified date", ascending=False).head(500)
        )
