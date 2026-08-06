import json

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="SAFE – Cincinnati Food Security",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("SAFE: Cincinnati Food Security Dashboard")

# ─── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data
def load_df():
    df = pd.read_csv("data/monthly_all_sources_21Jul2026.csv")
    df["date"] = pd.to_datetime({"year": df["year"], "month": df["month"], "day": 1})
    df = df.sort_values(["date", "SNA_NAME"]).reset_index(drop=True)
    df["month_year"] = df["date"].dt.strftime("%b %Y")
    df["meal_gap"] = 1 - df["pre_charity_coverage"]
    return df


@st.cache_data
def load_geojson():
    with open("data/shapefile/cincinnati_sna.geojson") as f:
        gj = json.load(f)
    for i, feat in enumerate(gj["features"]):
        feat["id"] = i
    return gj


df = load_df()
geojson = load_geojson()

month_year_order = (
    df.drop_duplicates("date").sort_values("date")["month_year"].tolist()
)

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["📊 Trends", "🗺️ Coverage Map", "🥗 Food Resources"])

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1 – Trends
# ══════════════════════════════════════════════════════════════════════════════

with tab1:

    # ── Stacked bar: one chart per neighborhood, chosen via dropdown ───────────

    st.subheader("Meal Coverage by Source")

    sna_list = sorted(df["SNA_NAME"].unique())
    selected = st.selectbox("Select a Neighborhood", sna_list)
    df_sna = df[df["SNA_NAME"] == selected].copy()

    COVERAGE_COLS = [
        "meal_percent_income_covered",
        "meal_percent_snap_covered",
        "meal_percent_cps_covered",
    ]
    LABEL_MAP = {
        "meal_percent_income_covered": "Income",
        "meal_percent_snap_covered": "SNAP",
        "meal_percent_cps_covered": "CPS",
    }
    COLOR_MAP = {"Income": "#4C9BE8", "SNAP": "#F4A442", "CPS": "#5CB85C"}

    df_bar = df_sna.melt(
        id_vars=["month_year", "date"],
        value_vars=COVERAGE_COLS,
        var_name="Source",
        value_name="Coverage",
    ).assign(Source=lambda x: x["Source"].map(LABEL_MAP))

    fig_bar = px.bar(
        df_bar,
        x="month_year",
        y="Coverage",
        color="Source",
        barmode="stack",
        title=f"Meal Coverage – {selected}",
        labels={"month_year": "Month / Year", "Coverage": "% of Meals Covered"},
        color_discrete_map=COLOR_MAP,
        category_orders={
            "month_year": month_year_order,
            "Source": list(LABEL_MAP.values()),
        },
    )
    fig_bar.update_xaxes(tickangle=45)
    fig_bar.update_layout(yaxis_tickformat=".0%", height=450)
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Line chart: meal gap across all neighborhoods ─────────────────────────

    st.subheader("Meal Gap by Neighborhood")
    st.caption(
        "Meal gap = 1 − pre-charity coverage.  "
        "Values above 0 indicate meals not yet covered by income, SNAP, or CPS."
    )

    fig_line = px.line(
        df,
        x="month_year",
        y="meal_gap",
        color="SNA_NAME",
        title="Meal Gap Over Time",
        labels={
            "month_year": "Month / Year",
            "meal_gap": "Meal Gap (1 − Pre-Charity Coverage)",
            "SNA_NAME": "Neighborhood",
        },
        category_orders={"month_year": month_year_order},
    )
    fig_line.update_xaxes(tickangle=45)
    fig_line.update_traces(line=dict(width=1.5), opacity=0.85)
    fig_line.update_layout(
        legend_title_text="Neighborhood",
        yaxis_tickformat=".0%",
        height=520,
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2 – Coverage Heat Map
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    latest_date = df["date"].max()
    st.subheader(f"Pre-Charity Coverage by Neighborhood – {latest_date.strftime('%B %Y')}")

    df_latest = df[df["date"] == latest_date][
        ["SNA_NAME", "pre_charity_coverage"]
    ].copy()

    # Detect the neighborhood name field from the GeoJSON properties
    sample_props = geojson["features"][0]["properties"] if geojson["features"] else {}
    sna_col_candidates = ["SNA_NAME", "SNA_Name", "NHOOD", "NAME", "SNA"]
    sna_col = next((c for c in sna_col_candidates if c in sample_props), None)

    if sna_col is None:
        st.error(
            f"Could not find a neighborhood name field in the GeoJSON. "
            f"Available fields: {list(sample_props.keys())}"
        )
    else:
        # Build a DataFrame from the GeoJSON properties and merge coverage data
        props_df = pd.DataFrame(
            [{"_id": feat["id"], sna_col: feat["properties"][sna_col]}
             for feat in geojson["features"]]
        )
        merged = props_df.merge(
            df_latest, left_on=sna_col, right_on="SNA_NAME", how="left"
        )

        fig_map = px.choropleth_mapbox(
            merged,
            geojson=geojson,
            locations="_id",
            featureidkey="id",
            color="pre_charity_coverage",
            hover_name=sna_col,
            hover_data={"pre_charity_coverage": ":.1%", "_id": False},
            color_continuous_scale="RdYlGn",
            range_color=[0.5, 1.0],
            mapbox_style="carto-positron",
            zoom=10.5,
            center={"lat": 39.1031, "lon": -84.512},
            opacity=0.75,
            labels={"pre_charity_coverage": "Pre-Charity Coverage"},
        )
        fig_map.update_layout(margin={"r": 0, "t": 10, "l": 0, "b": 0}, height=650)
        st.plotly_chart(fig_map, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3 – Food Resources Map
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.subheader("Food Resources in Greater Cincinnati")
    st.components.v1.iframe(
        src="https://uwgc211.org/embed/map?keyword=food-and-groceries&keyword=meals",
        height=720,
        scrolling=True,
    )
