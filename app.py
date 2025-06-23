import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import pydeck as pdk
import pgeocode

# Load dataset
df = pd.read_csv("final_courier_routes_dataset.csv")

# Generate ZIP-level summary for heatmap
all_zips = []
for _, row in df.iterrows():
    route = row["route_code"]
    stops = row["estimated_stops_per_day"]
    zip_list = str(row["zip_codes"]).split()
    for zip_code in zip_list:
        if zip_code.isdigit() and len(zip_code) == 5:
            all_zips.append({"route_code": route, "zip_code": zip_code, "estimated_stops": stops})

zip_df = pd.DataFrame(all_zips)
zip_summary = zip_df.groupby("zip_code")["estimated_stops"].sum().reset_index()

# Get ZIP coordinates using pgeocode
nomi = pgeocode.Nominatim("us")
zip_summary[["lat", "lon"]] = zip_summary["zip_code"].apply(
    lambda z: pd.Series(nomi.query_postal_code(z)[["latitude", "longitude"]])
)

# Classify zones for route-level context
def classify_zone(zips):
    zips_str = str(zips)
    if "191" in zips_str and "190" in zips_str:
        return "Mixed"
    elif "191" in zips_str:
        return "Philly Core"
    elif "190" in zips_str:
        return "Suburbs"
    else:
        return "Other Rural Areas"

df["zone"] = df["zip_codes"].apply(classify_zone)

# Sidebar slider to highlight stop thresholds
st.sidebar.subheader("⚙️ Customize Highlight Threshold")
threshold = st.sidebar.slider("Highlight routes with more than X stops:", min_value=35, max_value=60, value=50)

# Filter controls
with st.expander("🔍 Filter Options", expanded=True):
    selected_zone = st.selectbox(
        "Filter by Zone (optional):",
        ["All"] + sorted(df["zone"].unique())
    )

    if selected_zone != "All":
        zone_df = df[df["zone"] == selected_zone]
    else:
        zone_df = df.copy()

    route_options = zone_df["route_code"].sort_values().unique()

    selected_routes = st.multiselect(
        "Select Routes to View (leave blank to show all):",
        options=route_options
    )

# Display selected ZIPs
if selected_routes:
    st.subheader("📍 ZIP Codes for Selected Routes")
    for route in selected_routes:
        zips = df[df["route_code"] == route]["zip_codes"].values[0]
        st.markdown(f"**{route}** → {zips}")

st.markdown("---")

# Filter dataset
if selected_zone != "All":
    zone_df = df[df["zone"] == selected_zone]
else:
    zone_df = df.copy()

if selected_routes:
    filtered_df = zone_df[zone_df["route_code"].isin(selected_routes)]
else:
    filtered_df = zone_df.copy()

# Header and summary
st.title("📦 Courier Route Workload Dashboard")
st.markdown("""
> ⚠️ _Note: This app uses simulated routes and fake ZIP data.  
> It’s not meant for real-world operations. Just a personal project to learn Streamlit, explore data visualization, and prototype route logic._
""")
st.markdown("This dashboard lets you explore route coverage and workload across the Philadelphia region.")

# Summary stats
st.subheader("📈 Summary of Routes in View")
total_filtered_stops = filtered_df["estimated_stops_per_day"].sum()
avg_filtered_stops = filtered_df["estimated_stops_per_day"].mean()
num_filtered_routes = filtered_df.shape[0]

st.metric("📦 Total Stops in View", total_filtered_stops)
st.metric("📊 Avg Stops per Route", round(avg_filtered_stops, 2))
st.metric("🛣️ Routes in View", num_filtered_routes)

# Top and bottom stats from full dataset
max_row = df.loc[df["estimated_stops_per_day"].idxmax()]
min_row = df.loc[df["estimated_stops_per_day"].idxmin()]

st.markdown(f"**Most Loaded Route:** {max_row['route_code']} — {max_row['estimated_stops_per_day']} stops")
st.markdown(f"**Least Loaded Route:** {min_row['route_code']} — {min_row['estimated_stops_per_day']} stops")

st.markdown("---")

# Pie chart: zone breakdown
st.subheader("📍 Workload Distribution by Zone")
st.markdown("This pie chart gives a quick view of how daily stops are split across different types of areas.")
zone_totals = df.groupby("zone")["estimated_stops_per_day"].sum()
fig2, ax2 = plt.subplots()
ax2.pie(zone_totals, labels=zone_totals.index, autopct='%1.1f%%', startangle=140)
ax2.axis("equal")
st.pyplot(fig2)

st.markdown("---")

# Heatmap
st.subheader("🗺️ ZIP Code Heatmap (by Estimated Stops)")
st.markdown("The heatmap highlights areas of higher delivery activity based on ZIP code coverage.")
map_data = zip_summary.dropna(subset=["lat", "lon"])
color_range = [
    [255, 255, 204],
    [161, 218, 180],
    [65, 182, 196],
    [44, 127, 184],
    [37, 52, 148]
]

heat_layer = pdk.Layer(
    "HeatmapLayer",
    data=map_data,
    get_position='[lon, lat]',
    get_weight="estimated_stops",
    radiusPixels=30,
    colorRange=color_range,
    aggregation=pdk.types.String("SUM")
)

view_state = pdk.ViewState(
    latitude=map_data["lat"].mean(),
    longitude=map_data["lon"].mean(),
    zoom=9,
    pitch=0
)

st.pydeck_chart(pdk.Deck(
    layers=[heat_layer],
    initial_view_state=view_state,
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
))

# Bar chart
st.subheader("📊 Daily Stops per Route")
st.markdown("Each bar shows the estimated number of stops per day for individual routes.")
sorted_df = filtered_df.sort_values(by="estimated_stops_per_day", ascending=False)
colors = ["red" if stops > threshold else "skyblue" for stops in sorted_df["estimated_stops_per_day"]]
num_overloaded = (filtered_df["estimated_stops_per_day"] > threshold).sum()
st.sidebar.metric("Routes Overloaded", num_overloaded)

fig, ax = plt.subplots(figsize=(12, 5))
bars = ax.bar(sorted_df["route_code"], sorted_df["estimated_stops_per_day"], color=colors)
ax.set_ylabel("Estimated Stops")
ax.set_xlabel("Route")
ax.set_title("Route Stop Count (Descending)")
plt.xticks(rotation=90)
for i, val in enumerate(sorted_df["estimated_stops_per_day"]):
    ax.text(i, val + 0.5, str(val), ha='center', va='bottom', fontsize=8)
st.pyplot(fig)

# Export
st.markdown("---")
st.markdown("### 📁 Export Data")
st.markdown("You can download the filtered data as a CSV to share or work with externally.")
csv = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇️ Download Filtered CSV",
    data=csv,
    file_name='filtered_routes.csv',
    mime='text/csv',
    help="Exports only the routes you're currently viewing"
)
