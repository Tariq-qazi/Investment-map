import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from shapely.geometry import mapping
import re

# --- Load Data ---
zones = gpd.read_file("dubai_geojson/dubai.geojson")
smart_groups = pd.read_csv("batch_tagged_output.csv")
pattern_matrix = pd.read_csv("PatternMatrix_with_Buckets.csv")
zone_map_df = pd.read_csv("GeoJSON_DLD_Mapped_Final_Auto (2).csv")

# Build direct mapping from DLD name to GeoJSON name
zone_map = dict(zip(
    zone_map_df['Official_DLD_Name_Match'].astype(str).str.upper().str.strip(),
    zone_map_df['GeoJSON_Zone_Name'].astype(str).str.upper().str.strip()
))

# --- Clean and Normalize Names for Matching ---
def normalize_name(name):
    name = str(name).upper().strip()
    name = re.sub(r"\\bFIRST\\b", "1", name)
    name = re.sub(r"\\bSECOND\\b", "2", name)
    name = re.sub(r"\\bTHIRD\\b", "3", name)
    name = re.sub(r"\\bFOURTH\\b", "4", name)
    name = re.sub(r"\\bFIFTH\\b", "5", name)
    name = name.replace("AL ", "")
    name = name.replace("SOUTH ", "S ")
    return name.strip()

zones['CNAME_E_clean'] = zones['CNAME_E'].apply(normalize_name)
smart_groups['area_clean'] = smart_groups['area'].apply(normalize_name)

# Start with default normalized name
smart_groups['CNAME_E_clean'] = smart_groups['area_clean']

# Override only if there's a known match
smart_groups['CNAME_E_clean'] = smart_groups.apply(
    lambda row: zone_map.get(row['area_clean'], row['CNAME_E_clean']),
    axis=1
)

# --- Merge pattern matrix into smart groups ---
smart_groups = smart_groups.merge(
    pattern_matrix[['PatternID', 'Bucket']],
    left_on='pattern_id',
    right_on='PatternID',
    how='left'
)

# --- Define accurate bucket-to-color mapping ---
bucket_colors = {
    "🟢 Strong Buy": "#007f00",
    "🟡 Cautious Buy / Watch": "#ffcc00",
    "🟠 Hold / Neutral": "#ff9900",
    "🔴 Caution / Avoid": "#cc0000",
    "🔁 Rotation Candidate": "#999999",
    "🧭 Strategic Waitlist": "#3366cc",
    "No Data": "#d3d3d3"
}

# --- Sidebar Filters ---
st.sidebar.title("Smart Investment Map Filters")
unit_type = st.sidebar.selectbox("Select Unit Type", sorted(smart_groups['type'].unique()))
rooms = st.sidebar.selectbox("Select Room Count", sorted(smart_groups['rooms'].unique()))
quarter = st.sidebar.selectbox("Select Quarter", sorted(smart_groups['quarter'].unique(), reverse=True))
insight_mode = st.sidebar.radio("View Insights For:", ["Investor", "End User"])

# --- Filter Smart Groups ---
filtered = smart_groups[
    (smart_groups['type'] == unit_type) &
    (smart_groups['rooms'] == rooms) &
    (smart_groups['quarter'] == quarter)
]

# --- Merge filtered info into ALL zones ---
zones = zones.merge(
    filtered[['CNAME_E_clean', 'pattern_id', 'Insight_Investor', 'Recommendation_Investor',
              'Insight_EndUser', 'Recommendation_EndUser', 'Bucket']],
    on='CNAME_E_clean', how='left'
)

# --- Create Folium Map ---
m = folium.Map(location=[25.2048, 55.2708], zoom_start=11)

for _, row in zones.iterrows():
    feature = {
        "type": "Feature",
        "geometry": mapping(row['geometry']),
        "properties": {
            "CNAME_E": row['CNAME_E'],
            "Pattern ID": row.get('pattern_id', 'N/A'),
            "Investor Insight": row.get('Insight_Investor', 'No data'),
            "Investor Recommendation": row.get('Recommendation_Investor', 'No data'),
            "End User Insight": row.get('Insight_EndUser', 'No data'),
            "End User Recommendation": row.get('Recommendation_EndUser', 'No data'),
            "Bucket": row.get('Bucket', 'No Data') or 'No Data'
        }
    }

    popup_html = f"""
        <b>Area:</b> {feature['properties']['CNAME_E']}<br>
        <b>Pattern ID:</b> {feature['properties']['Pattern ID']}<br>
    """
    if insight_mode == "Investor":
        popup_html += f"""
            <b><u>Insight:</u></b><br>{feature['properties']['Investor Insight']}<br>
            <b><u>Recommendation:</u></b> {feature['properties']['Investor Recommendation']}<br>
        """
    else:
        popup_html += f"""
            <b><u>Insight:</u></b><br>{feature['properties']['End User Insight']}<br>
            <b><u>Recommendation:</u></b> {feature['properties']['End User Recommendation']}<br>
        """

    color = bucket_colors.get(feature['properties']['Bucket'], '#d3d3d3')
    feature['properties']['Color'] = color

    folium.GeoJson(
        data=feature,
        style_function=lambda x: {
            'fillColor': x['properties']['Color'],
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.6
        },
        tooltip=folium.Tooltip(feature['properties']['CNAME_E']),
        popup=folium.Popup(popup_html, max_width=400)
    ).add_to(m)

# --- Add Legend ---
legend_html = '''
 <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999; background: white; padding: 10px; border: 1px solid black; font-size: 12px">
 <b>Legend</b><br>
 <i style="background: #007f00; width: 12px; height: 12px; float: left; margin-right: 5px;"></i> 🟢 Strong Buy<br>
 <i style="background: #ffcc00; width: 12px; height: 12px; float: left; margin-right: 5px;"></i> 🟡 Cautious Buy / Watch<br>
 <i style="background: #ff9900; width: 12px; height: 12px; float: left; margin-right: 5px;"></i> 🟠 Hold / Neutral<br>
 <i style="background: #cc0000; width: 12px; height: 12px; float: left; margin-right: 5px;"></i> 🔴 Caution / Avoid<br>
 <i style="background: #999999; width: 12px; height: 12px; float: left; margin-right: 5px;"></i> 🔁 Rotation Candidate<br>
 <i style="background: #3366cc; width: 12px; height: 12px; float: left; margin-right: 5px;"></i> 🧭 Strategic Waitlist<br>
 <i style="background: #d3d3d3; width: 12px; height: 12px; float: left; margin-right: 5px;"></i> No Data<br>
 </div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# --- Display Map ---
st.title("Smart Investment Zone Map")
st.markdown(f"**Quarter:** {quarter} | **Unit:** {unit_type} | **Rooms:** {rooms} | **Mode:** {insight_mode}")
st_folium(m, width=1200, height=700)
