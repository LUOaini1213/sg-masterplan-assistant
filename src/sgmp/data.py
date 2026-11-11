"""Load the committed extract (read-only, EPSG:3414 metres)."""
from functools import lru_cache

import geopandas as gpd

from .vocab import DATA_DIR


def gpr_number(v):
    """Numeric GPR, or None for non-numeric codes (LND landed, EVA envelope, SDP, NA)."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=1)
def load():
    lu = gpd.read_file(DATA_DIR / "landuse.geojson")
    lu["GPR_NUM"] = [gpr_number(v) for v in lu["GPR"]]
    lu["AREA_M2"] = lu.geometry.area
    return {
        "landuse": lu,
        "planning_areas": gpd.read_file(DATA_DIR / "planning_areas.geojson"),
        "subzones": gpd.read_file(DATA_DIR / "subzones.geojson"),
        "stations": gpd.read_file(DATA_DIR / "mrt_stations.geojson"),
    }
