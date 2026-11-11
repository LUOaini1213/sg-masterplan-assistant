"""Fixed vocabulary: land-use codes, synonym groups and data metadata."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "extract"
MANIFEST = json.loads((DATA_DIR / "MANIFEST.json").read_text(encoding="utf-8"))

DATA_VINTAGE = ("URA Master Plan 2025 Land Use Layer (gazetted 1 Dec 2025), "
                "data.gov.sg d_a8c3546b26712e35021f3a681d0353ae")
COVERAGE = MANIFEST["planning_areas_in_extract"]
ALL_PLANNING_AREAS = MANIFEST["all_planning_area_names_mp2025"]

LAND_USE_CODES = [
    "AGRICULTURE", "BEACH AREA", "BUSINESS 1", "BUSINESS 1 - WHITE", "BUSINESS 2",
    "BUSINESS 2 - WHITE", "BUSINESS PARK", "BUSINESS PARK - WHITE", "CEMETERY",
    "CIVIC & COMMUNITY INSTITUTION", "COMMERCIAL", "COMMERCIAL & RESIDENTIAL",
    "COMMERCIAL / INSTITUTION", "EDUCATIONAL INSTITUTION", "HEALTH & MEDICAL CARE",
    "HOTEL", "LIGHT RAPID TRANSIT", "MASS RAPID TRANSIT", "OPEN SPACE", "PARK",
    "PLACE OF WORSHIP", "PORT / AIRPORT", "RESERVE SITE", "RESIDENTIAL",
    "RESIDENTIAL / INSTITUTION", "RESIDENTIAL WITH COMMERCIAL AT 1ST STOREY", "ROAD",
    "SPECIAL USE", "SPORTS & RECREATION", "TRANSPORT FACILITIES", "UTILITY", "WATERBODY",
    "WHITE",
]

# Documented meaning of plain-English zoning words. Longer phrases are matched first.
LAND_USE_GROUPS = [
    ("business park", ["BUSINESS PARK"]),
    ("business white", ["BUSINESS 1 - WHITE", "BUSINESS 2 - WHITE", "BUSINESS PARK - WHITE"]),
    ("business 1", ["BUSINESS 1"]),
    ("b1", ["BUSINESS 1"]),
    ("business 2", ["BUSINESS 2"]),
    ("b2", ["BUSINESS 2"]),
    ("industrial", ["BUSINESS 1", "BUSINESS 2"]),
    ("business", ["BUSINESS 1", "BUSINESS 2", "BUSINESS PARK"]),
    ("white", ["WHITE"]),
    ("commercial and residential", ["COMMERCIAL & RESIDENTIAL"]),
    ("commercial & residential", ["COMMERCIAL & RESIDENTIAL"]),
    ("mixed use", ["COMMERCIAL & RESIDENTIAL", "RESIDENTIAL WITH COMMERCIAL AT 1ST STOREY"]),
    ("all residential", ["RESIDENTIAL", "RESIDENTIAL / INSTITUTION",
                         "RESIDENTIAL WITH COMMERCIAL AT 1ST STOREY", "COMMERCIAL & RESIDENTIAL"]),
    ("residential", ["RESIDENTIAL"]),
    ("housing", ["RESIDENTIAL"]),
    ("commercial", ["COMMERCIAL"]),
    ("hotel", ["HOTEL"]),
    ("park", ["PARK"]),
    ("green", ["PARK", "OPEN SPACE"]),
    ("open space", ["OPEN SPACE"]),
    ("school", ["EDUCATIONAL INSTITUTION"]),
    ("educational", ["EDUCATIONAL INSTITUTION"]),
    ("place of worship", ["PLACE OF WORSHIP"]),
    ("worship", ["PLACE OF WORSHIP"]),
    ("civic", ["CIVIC & COMMUNITY INSTITUTION"]),
    ("community", ["CIVIC & COMMUNITY INSTITUTION"]),
    ("health", ["HEALTH & MEDICAL CARE"]),
    ("medical", ["HEALTH & MEDICAL CARE"]),
    ("utility", ["UTILITY"]),
    ("utilities", ["UTILITY"]),
    ("reserve site", ["RESERVE SITE"]),
    ("road", ["ROAD"]),
    ("waterbody", ["WATERBODY"]),
    ("sports", ["SPORTS & RECREATION"]),
    ("transport facilit", ["TRANSPORT FACILITIES"]),
]
