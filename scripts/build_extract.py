"""Build the small committed extract from the full data.gov.sg downloads.

Usage: python scripts/build_extract.py RAW_DIR

RAW_DIR must contain the GeoJSON files named <dataset_id>.geojson (see
docs/sources.md). Not run in CI: the full land-use layer is ~190 MB.
"""
import hashlib
import json
import sys
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "extract"
AREAS = ["BISHAN", "DOWNTOWN CORE"]
IDS = {
    "landuse": "d_a8c3546b26712e35021f3a681d0353ae",  # MP2025 Land Use Layer
    "planning_area": "d_2cc750190544007400b2cfd5d7f53209",  # MP2025 PA (No Sea)
    "subzone": "d_8594ae9ff96d0c708bc2af633048edfb",  # MP2019 Subzone (No Sea)
    "mrt_exit": "d_b39d3a0871985372d7e1637193335da5",  # LTA MRT Station Exit
}
CRS = 3414  # SVY21 / Singapore TM, metres


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rounded(gdf):
    from shapely import set_precision
    gdf = gdf.copy()
    gdf["geometry"] = set_precision(gdf.geometry.values, 0.01)
    return gdf


def main(raw):
    raw = Path(raw)
    f = {k: raw / f"{v}.geojson" for k, v in IDS.items()}
    pa = gpd.read_file(f["planning_area"]).to_crs(CRS)
    pa_all_names = sorted(pa.PLN_AREA_N.unique())
    pa = pa[pa.PLN_AREA_N.isin(AREAS)][["PLN_AREA_N", "REGION_N", "geometry"]]
    sz = gpd.read_file(f["subzone"]).to_crs(CRS)
    sz = sz[sz.PLN_AREA_N.isin(AREAS)][["SUBZONE_N", "PLN_AREA_N", "geometry"]]
    lu = gpd.read_file(f["landuse"]).to_crs(CRS)
    rp = lu.copy()
    rp["geometry"] = lu.representative_point()
    j = gpd.sjoin(rp, pa[["PLN_AREA_N", "geometry"]], predicate="within", how="inner")
    j = j.drop(columns="index_right")
    j = gpd.sjoin(j, sz[["SUBZONE_N", "geometry"]], predicate="within", how="left")
    lu = lu.loc[j.index].copy()
    lu["PLN_AREA_N"] = j["PLN_AREA_N"]
    lu["SUBZONE_N"] = j["SUBZONE_N"].fillna("")
    lu = lu.rename(columns={"SHAPE.AREA": "SHAPE_AREA"})
    lu = lu[["OBJECTID", "LU_DESC", "GPR", "PLN_AREA_N", "SUBZONE_N", "SHAPE_AREA", "geometry"]]
    lu = lu.sort_values("OBJECTID")
    ex = gpd.read_file(f["mrt_exit"]).to_crs(CRS)
    st = ex.dissolve("STATION_NA").centroid.rename("geometry").reset_index()
    st = gpd.GeoDataFrame(st, geometry="geometry", crs=CRS)
    st = st[st.within(pa.geometry.union_all())].copy()
    st["STATION"] = st.STATION_NA.str.replace(r"\s+MRT STATION$", "", regex=True)
    st = st[["STATION", "geometry"]].sort_values("STATION")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, g in [("landuse", lu), ("planning_areas", pa), ("subzones", sz), ("mrt_stations", st)]:
        rounded(g).to_file(OUT / f"{name}.geojson", driver="GeoJSON",
                           COORDINATE_PRECISION=2, WRITE_BBOX="NO")
    manifest = {
        "planning_areas_in_extract": AREAS,
        "all_planning_area_names_mp2025": pa_all_names,
        "crs": f"EPSG:{CRS}",
        "parcel_assignment": "parcel representative point within MP2025 planning area / MP2019 subzone",
        "station_point": "centroid of the station's LTA exit points",
        "counts": {"landuse": len(lu), "planning_areas": len(pa), "subzones": len(sz), "mrt_stations": len(st)},
        "source_sha256": {k: sha256(p) for k, p in f.items()},
        "dataset_ids": IDS,
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"]))


if __name__ == "__main__":
    main(sys.argv[1])
