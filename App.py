import streamlit as st 
import geopandas as gpd 
import pandas as pd 
import folium 
from streamlit_folium import st_folium 
from shapely.geometry import mapping

--- Load Data ---

zones = gpd.read_file("dubai_geojson/dubai.geojson") smart_groups = pd.read_csv("batch_tagged_output.csv")

--- Clean and Normalize Names for Matching ---

zones['CNAME_E_clean'] = zones['CNAME_E'].str.upper().str.strip() smart_groups['area_clean'] = smart_groups['area'].str.upper().str.strip()

--- Sidebar Filters ---

st.sidebar.title("Serdal Map Filters") unit_type = st.sidebar.selectbox("Select Unit Type", sorted(smart_groups['type'].unique())) rooms = st.sidebar.selectbox("Select Room Count", sorted(smart_groups['rooms'].unique())) quarter = st.sidebar.selectbox("Select Quarter", sorted(smart_groups['quarter'].unique(), reverse=True))

--- Filter Smart Groups ---

filtered = smart_groups[(smart_groups['type'] == unit_type) & (smart_groups['rooms'] == rooms) & (smart_groups['quarter'] == quarter)]

--- Merge with GeoJSON using cleaned fields ---

zones_filtered = zones.merge(filtered, left_on='CNAME_E_clean', right_on='area_clean')

--- Assign Color Based on Investor Recommendation ---

def get_color(advice): if advice == 'Buy': return 'green' elif advice == 'Wait': return 'yellow' elif advice == 'Avoid': return 'red' return 'gray'

zones_filtered['color'] = zones_filtered['Recommendation_Investor'].apply(get_color)

--- Create Folium Map ---

m = folium.Map(location=[25.2048, 55.2708], zoom_start=11)

for _, row in zones_filtered.iterrows(): feature = { "type": "Feature", "geometry": mapping(row['geometry']), "properties": { "CNAME_E": row['CNAME_E'], "Pattern ID": row['pattern_id'], "Investor Insight": row['Insight_Investor'], "Investor Recommendation": row['Recommendation_Investor'], "End User Insight": row['Insight_EndUser'], "End User Recommendation": row['Recommendation_EndUser'], "color": row['color'] } }

folium.GeoJson(
    data=feature,
    style_function=lambda x: {
        'fillColor': x['properties']['color'],
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.6
    },
    tooltip=folium.Tooltip(feature['properties']['CNAME_E']),
    popup=folium.Popup(f"""
        <b>Area:</b> {feature['properties']['CNAME_E']}<br>
        <b>Pattern ID:</b> {feature['properties']['Pattern ID']}<br>
        <b><u>Investor Insight:</u></b><br>{feature['properties']['Investor Insight']}<br>
        <b><u>Investor Recommendation:</u></b> {feature['properties']['Investor Recommendation']}<br><br>
        <b><u>End User Insight:</u></b><br>{feature['properties']['End User Insight']}<br>
        <b><u>End User Recommendation:</u></b> {feature['properties']['End User Recommendation']}<br>
    """, max_width=400)
).add_to(m)

--- Display Map ---

st.title("Serdal SmartZone Map") st.markdown(f"Quarter: {quarter} | Unit: {unit_type} | Rooms: {rooms}") st_folium(m, width=1200, height=700)

