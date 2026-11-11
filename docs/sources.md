# Sources

All data retrieved on 2026-11-11 (SGT) through the data.gov.sg download API
(`https://api-open.data.gov.sg/v1/public/api/datasets/<id>/poll-download`). SHA-256 of
each full download is in `data/extract/MANIFEST.json`.

| Layer | data.gov.sg dataset ID | Publisher | Last updated (per data.gov.sg) | Used for |
|---|---|---|---|---|
| Master Plan 2025 Land Use Layer | `d_a8c3546b26712e35021f3a681d0353ae` | URA | 2026-03-27 | parcels, LU_DESC, GPR |
| Master Plan 2025 Planning Area Boundary (No Sea) | `d_2cc750190544007400b2cfd5d7f53209` | URA | 2026-02-27 | planning areas |
| Master Plan 2019 Subzone Boundary (No Sea) (GEOJSON) | `d_8594ae9ff96d0c708bc2af633048edfb` | URA | 2025-12-03 | subzones |
| LTA MRT Station Exit (GEOJSON) | `d_b39d3a0871985372d7e1637193335da5` | LTA | 2026-10-18 | station points |

Dataset pages: `https://data.gov.sg/datasets/<id>/view`.
Metadata API: `https://api-production.data.gov.sg/v2/public/api/datasets/<id>/metadata`.

## Licence

- The Master Plan 2025 Land Use Layer page on data.gov.sg (checked 2026-11-11) states it is
  "Free forever for personal or commercial use, under the Open Data Licence". The same
  wording appears on the Master Plan 2019 Land Use layer page.
- Licence text: Singapore Open Data Licence version 1.0, https://data.gov.sg/open-data-licence
  (checked 2026-11-11). It asks for an attribution notice naming the dataset and date of
  access and linking to the licence. Attribution used here:
  *Contains information from Master Plan 2025 Land Use Layer, Master Plan 2025 Planning Area
  Boundary (No Sea), Master Plan 2019 Subzone Boundary (No Sea) and LTA MRT Station Exit,
  accessed on 2026-11-11 from data.gov.sg, made available under the Singapore Open Data
  Licence version 1.0 (https://data.gov.sg/open-data-licence).*
- The metadata API returns no licence field; the licence statement was read from the
  rendered dataset page only.

## Facts taken from the dataset descriptions

- Master Plan 2025 Land Use Layer: "extracted from the Master Plan 2025 that was gazetted on
  1 Dec 2025" (data.gov.sg description).
- Master Plan 2019 Land Use layer (`d_90d86daa5bfaa371668b84fa5f01424f`) was also downloaded and
  inspected but is not used: the 2025 layer is openly available and newer.

## What I could not verify

- **No Master Plan 2025 subzone layer was found on data.gov.sg.** A scan of the dataset
  catalogue on 2026-11-11 found a 2025 planning-area layer but no 2025 subzone layer, so
  subzones come from Master Plan 2019. Within Bishan and Downtown Core, two parcels fall
  outside every 2019 subzone (blank `SUBZONE_N`). The catalogue scan relied on the public
  listing API, which rate-limited some pages; a 2025 subzone layer could exist under a
  name I did not search for.
- The meaning of the non-numeric GPR codes (`LND`, `EVA`, `SDP`, `NA`) is my reading
  (landed housing, envelope control, special detailed plan, not applicable). I did not find
  a field dictionary on data.gov.sg; the metadata API lists the attributes without
  descriptions.
- Station points are the centroid of each station's exits, not an official station
  location. Interchange stations with exits far apart may be off by tens of metres.
- I did not check this data against URA's own Master Plan viewer. The layer is described
  as "indicative"; it is not a legal zoning record.
- The extract is cut by each parcel's representative point. Parcels that straddle the
  Bishan or Downtown Core boundary are wholly in or wholly out.
