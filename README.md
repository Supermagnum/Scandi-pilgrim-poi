# Scandi pilgrim POI dataset

Points of interest for the Scandinavian pilgrim trail network — shelters,
cabins, lean-tos, campsites, pilgrim centers, and (for St. Olavsleden) horseback
service points — cross-referenced against existing OpenStreetMap data to show
what is already mapped versus what appears to be missing.

This is an unofficial, independently compiled research aid. It is not affiliated
with pilegrimsleden.no, stolavsleden.com, Naturkartan, or the OpenStreetMap
Foundation.

## Data sources

- **pilegrimsleden.no** (Craft CMS GraphQL / map APIs): Norwegian trail network
  Gudbrandsdalsleden, St. Olavsleden (NO), Borgleden, Kystpilegrimsleia,
  Tunsbergleden, Østerdalsleden, Valldalsleden, Romboleden, Nordleden.
- **stolavsleden.com** (WordPress site + Naturkartan embed, guide id 154):
  St. Olavsleden in Sweden, including hiking / biking / horseback path variants
  and horseback-oriented service points (veterinarians in the current extract;
  Naturkartan listed 0 farriers — that is a coverage gap in Naturkartan, not
  proof that no farriers exist on the route).
  The horseback GPX diverges from the hiking line by up to ~4.3 km in places
  (126/201 sampled points ≥150 m apart); riders should not rely on hiking-line
  POIs alone when planning.
- **OSM reference tagging**: changeset
  [187258738](https://www.openstreetmap.org/changeset/187258738) for pilgrim
  stamp-office conventions.
- **Existing OSM inventory**: Geofabrik `norway-latest.osm.pbf` and
  `sweden-latest.osm.pbf` (not stored in this repository — download from
  https://download.geofabrik.de/europe/ when re-running comparisons).

## Directory layout

```
data/
  by_trail/<TrailName>/
    shelters.csv              # overnight/shelter POIs + OSM match columns
    shelters.osm              # JOSM-loadable nodes (negative ids, version 0)
    pilgrim_centers.csv       # pilgrim-center / stamp-office comparison
    horseback_path.osm        # St. Olavsleden only: horse route geometry
    horseback_path.gpx        # St. Olavsleden only: source horseback GPX
    horseback_service_points.csv  # St. Olavsleden only: farrier/vet POIs
    hiking_path.gpx           # St. Olavsleden only: hiking GPX
  osm_comparison_results.csv
  pilegrimsleden_shelters.osm
  changeset_187258738_reference.json
  stolavsleden_api_reference.json
scripts (repo root):
  extract_pilegrimsleden_shelters.py
  compare_osm_shelters.py
  extract_stolavsleden.py
  discover_map_api.py
```

Trail folder names normalize Norwegian characters (ae/o/a) and drop the dot in
`St-Olavsleden`. The original trail name remains in CSV `trail` / OSM
`note:trail`. St. Olavsleden merges NO + SE POIs; use the `country` column to
filter.

## How to use in JOSM

1. Open one trail folder’s `shelters.osm` (or `horseback_path.osm`) in JOSM.
2. Download the surrounding OSM data and compare.
3. Prefer rows with `match_status=gap` as candidates for new mapping — still
   verify each object on the ground or with current local sources.

### match_status meanings

| status | meaning |
| --- | --- |
| matched | Compatible OSM object within 100 m (closest wins within 250 m) |
| possible | Candidate within 100–250 m, or weak/incompatible tags |
| gap | No suitable OSM object within 250 m |

Pilgrim-center matching uses any OSM node/way with `pilgrimage=*` (including way
centroids), not only `tourism=information` + `information=office`.

## Important: not an OSM import

This dataset is a **comparison / research aid**, not a ready-to-upload import.
Anyone merging features into OpenStreetMap must:

- individually verify category, existence, and location;
- follow the [Import Guidelines](https://wiki.openstreetmap.org/wiki/Import/Guidelines)
  and the [Automated Edits code of conduct](https://wiki.openstreetmap.org/wiki/Automated_Edits_code_of_conduct);
- discuss bulk work with the local community before uploading.

Do not bulk-upload these nodes.

## License

**Decision needed from the repository owner before treating this as final:**
derived POI comparison tables are intended to be published under a license
compatible with reuse alongside OSM (for example **ODbL** or **CC0**). Until
that choice is confirmed in writing, treat the files as all-rights-reserved
research notes belonging to the repository owner, while remembering that:

- OpenStreetMap data remains under ODbL;
- pilegrimsleden.no / stolavsleden.com / Naturkartan content remains under their
  respective terms — this project only stores derived comparison fields needed
  for mapping research.

Credit: pilegrimsleden.no, stolavsleden.com, Naturkartan, OpenStreetMap
contributors, and Geofabrik extracts.

## Regenerating

```bash
# Norwegian extract + national OSM comparison (requires Geofabrik PBFs under data/geofabrik/)
python3 extract_pilegrimsleden_shelters.py
python3 compare_osm_shelters.py --pilgrim-centers-only --split-by-trail

# Swedish St. Olavsleden + horseback layers
python3 extract_stolavsleden.py
```

Do not commit `data/geofabrik/*.osm.pbf` (see `.gitignore`).
