"""
Run this script ONE TIME locally to convert the shapefile to GeoJSON.
The output file (data/cincinnati_sna.geojson) gets committed to GitHub
so the deployed app never needs geopandas or GDAL.

  pip install pyshp
  python convert_shapefile.py
"""

import json
import shapefile

SHAPEFILE = (
    r"C:\Users\c950904\OneDrive - 8451\Desktop transition folder"
    r"\New Hire Docs\COVID 19\Food Security Important docs"
    r"\cincinnati_sna_shape_input"
    r"\Cincinnati_Statistical_Neighborhood_Approximations_(SNA).shp"
)
OUTPUT = r"data\cincinnati_sna.geojson"

sf = shapefile.Reader(SHAPEFILE)
fields = [f[0] for f in sf.fields[1:]]

print("Fields found in shapefile:", fields)

features = []
for i, (rec, shp) in enumerate(zip(sf.records(), sf.shapes())):
    features.append(
        {
            "type": "Feature",
            "id": i,
            "properties": dict(zip(fields, rec)),
            "geometry": shp.__geo_interface__,
        }
    )

geojson = {"type": "FeatureCollection", "features": features}

with open(OUTPUT, "w") as f:
    json.dump(geojson, f)

print(f"Saved {len(features)} neighborhoods to {OUTPUT}")
print("Sample property keys:", list(features[0]["properties"].keys()) if features else "none")
