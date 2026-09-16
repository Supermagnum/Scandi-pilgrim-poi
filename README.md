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
- **OSM route relations** (source of truth for trail geometry and existing
  members; never modified by this project). Known IDs:

  | trail | OSM relation |
  | --- | ---: |
  | Borgleden | [5672944](https://www.openstreetmap.org/relation/5672944) |
  | Gudbrandsdalsleden | [1370273](https://www.openstreetmap.org/relation/1370273) |
  | Kystpilegrimsleia | [10508888](https://www.openstreetmap.org/relation/10508888) |
  | Nordleden | [1585449](https://www.openstreetmap.org/relation/1585449) |
  | Østerdalsleden | [5129262](https://www.openstreetmap.org/relation/5129262) |
  | Romboleden | [1151161](https://www.openstreetmap.org/relation/1151161) |
  | Romeriksleden | [1200009](https://www.openstreetmap.org/relation/1200009) |
  | St. Olavsleden | [10524322](https://www.openstreetmap.org/relation/10524322) (superroute) |
  | Tunsbergleden (Vestfoldveien) | [5661086](https://www.openstreetmap.org/relation/5661086) |
  | Valldalsleden | [11218584](https://www.openstreetmap.org/relation/11218584) |

  Romeriksleden is Gudbrandsdalsleden east (Oslo–Eidsvoll–Hamar–Lillehammer) and
  is not a separate CMS trail entry. Folder `data/by_trail/Romeriksleden/` holds
  the OSM route geometry, corridor overnight POIs (`related_trails`
  Gudbrandsdalsleden + Romeriksleden), and `romeriksleden.osm` linking path +
  POIs in a local JOSM relation.
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

## Trail-relation membership (research proposals)

For each trail with a known OSM route relation, discovery:

1. Treats existing members of that relation as already related and **never
   modifies** them.
2. Lists nearby lodging/shelter OSM objects that are **not** members in
   `osm_missing_for_relation.csv` / `missing_additions.osm` (local research
   only).
3. Puts a per-POI `note:proposed` / `proposal_note` on every proposed addition
   (existing OSM objects missing from the relation, and CMS overnight gaps).

Most pilgrim route relations currently contain path ways only, so lodging
`already_member` counts are typically zero; the missing lists are proposals to
review, not an instruction to upload.

Latest pass (`propose_relation_additions.py`, Romeriksleden via
`extract_romeriksleden.py`):

| folder | OSM relation | already | missing (propose) | CMS gaps |
| --- | ---: | ---: | ---: | ---: |
| Borgleden | 5672944 | 0 | 256 | 8 |
| Gudbrandsdalsleden | 1370273 | 0 | 345 | 88 |
| Kystpilegrimsleia | 10508888 | 0 | 87 | 29 |
| Nordleden | 1585449 | 0 | 5 | 0 |
| Osterdalsleden | 5129262 | 0 | 191 | 36 |
| Romboleden | 1151161 | 0 | 441 | 5 |
| Romeriksleden | 1200009 | 0 | 331 | 32 |
| St-Olavsleden | 10524322 | 0 | 1208 | 118 |
| Tunsbergleden | 5661086 | 0 | 178 | 18 |
| Valldalsleden | 11218584 | 0 | 43 | 9 |

See `data/by_trail/README.md` and `data/relation_additions_all_trails_summary.json`.

## Directory layout

```
data/
  by_trail/<TrailName>/
    shelters.csv                 # overnight/shelter POIs + OSM match + proposal_note
    shelters.osm                 # JOSM-loadable nodes (negative ids, version 0)
    pilgrim_centers.csv          # pilgrim-center / stamp-office comparison
    osm_along_route.csv          # lodging near route (membership status)
    osm_already_related.csv      # already members of the OSM route relation
    osm_missing_for_relation.csv # near route, not on relation (proposals)
    missing_additions.osm        # local research file of proposals only
    relation_additions_summary.json
    horseback_path.osm           # St. Olavsleden only: horse route geometry
    horseback_path.gpx           # St. Olavsleden only: source horseback GPX
    horseback_service_points.csv # St. Olavsleden only: farrier/vet POIs
    hiking_path.gpx              # St. Olavsleden / Romeriksleden route GPX
    hiking_path.osm              # Romeriksleden (from OSM rel 1200009); St. Olavsleden has GPX only
    romeriksleden.osm            # Romeriksleden only: path + POIs + local JOSM relation
  relation_additions_all_trails_summary.json
  osm_comparison_results.csv
  pilegrimsleden_shelters.osm
  changeset_187258738_reference.json
  stolavsleden_api_reference.json
scripts (repo root):
  extract_pilegrimsleden_shelters.py
  compare_osm_shelters.py
  extract_stolavsleden.py
  extract_romeriksleden.py
  propose_relation_additions.py
  discover_map_api.py
```

Each trail `shelters.osm` includes a local JOSM `type=site` relation grouping
overnight POI nodes (research aid; not for upload). Where known, nodes carry
`note:osm_route_relation` pointing at the matching OSM hiking route relation.

Trail folder names normalize Norwegian characters (ae/o/a) and drop the dot in
`St-Olavsleden`. The original trail name remains in CSV `trail` / OSM
`note:trail`. St. Olavsleden merges NO + SE POIs; use the `country` column to
filter.

## How to use in JOSM

1. Open one trail folder’s `shelters.osm` (or `horseback_path.osm` /
   `missing_additions.osm`) in JOSM.
2. Download the surrounding OSM data and compare.
3. Prefer rows with `match_status=gap` or objects in
   `osm_missing_for_relation.csv` as candidates — still verify each object on
   the ground or with current local sources.
4. Do not edit or replace the real OSM trail relation from these files; they
   only propose additions.

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

Do not bulk-upload these nodes. Do not modify existing members of OSM trail
relations based solely on these files.

## License

This dataset uses the **same license as OpenStreetMap data**:
[Open Database License (ODbL) v1.0](https://opendatacommons.org/licenses/odbl/1.0/),
with individual contents under the
[Database Contents License (DbCL) v1.0](https://opendatacommons.org/licenses/dbcl/1.0/).
See [LICENSE](LICENSE).

Upstream sources keep their own terms (OSM under ODbL; pilegrimsleden.no,
stolavsleden.com, and Naturkartan under theirs). This project only publishes
derived comparison fields needed for mapping research.

Credit: pilegrimsleden.no, stolavsleden.com, Naturkartan, OpenStreetMap
contributors, and Geofabrik extracts.

## Regenerating

```bash
# Norwegian extract + national OSM comparison (requires Geofabrik PBFs under data/geofabrik/)
python3 extract_pilegrimsleden_shelters.py
python3 compare_osm_shelters.py --pilgrim-centers-only --split-by-trail

# Swedish St. Olavsleden + horseback layers
python3 extract_stolavsleden.py

# Romeriksleden corridor from OSM relation 1200009
python3 extract_romeriksleden.py

# Membership proposals for all trails (optional --skip / --reuse-pbf / --only)
python3 propose_relation_additions.py
```

Do not commit `data/geofabrik/*.osm.pbf` or lodging scan caches (see `.gitignore`).
