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
  corridor overnight POIs (`related_trails` Gudbrandsdalsleden + Romeriksleden)
  in the same single `trail.osm` as every other trail.
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
   national research outputs / summary JSON (not in the JOSM trail folder).
3. CMS overnight **gaps** appear in `trail.osm` as new suggestions tagged
   `note:proposed=Proposed addition`. Existing POIs have no that tag.
   Research keys such as `pilegrimsleden:match_status` are never written to
   `trail.osm`.

Most pilgrim route relations currently contain path ways only, so lodging
`already_member` counts are typically zero; the CSV missing lists are proposals
to review, not an instruction to upload.

Latest pass (`propose_relation_additions.py`, Romeriksleden via
`extract_romeriksleden.py`):

| folder | OSM relation | already | missing (CSV) | CMS gaps in trail.osm |
| --- | ---: | ---: | ---: | ---: |
| Borgleden | 5672944 | 0 | 256 | 8 |
| Gudbrandsdalsleden | 1370273 | 0 | 345 | 79 |
| Kystpilegrimsleia | 10508888 | 0 | 87 | 28 |
| Nordleden | 1585449 | 0 | 5 | 0 |
| Osterdalsleden | 5129262 | 0 | 191 | 36 |
| Romboleden | 1151161 | 0 | 441 | 5 |
| Romeriksleden | 1200009 | 0 | 345 | 29 |
| St-Olavsleden | 10524322 | 0 | 1208 | 96 |
| Tunsbergleden | 5661086 | 0 | 178 | 18 |
| Valldalsleden | 11218584 | 0 | 43 | 9 |

See `data/by_trail/README.md` and `data/relation_additions_all_trails_summary.json`.

## Directory layout

```
data/
  by_trail/<TrailName>/
    trail.osm           # ONLY OSM file: path + existing POIs + new suggestions
    README.md           # short trail notes (replaces per-trail CSV dumps)
    hiking_path.gpx     # optional path cache
    horseback_path.gpx  # St. Olavsleden only
  osm_comparison_results.csv
  pilegrimsleden_shelters_by_trail.csv
  pilgrim_centers.csv
  relation_additions_all_trails_summary.json
  pilegrimsleden_shelters.osm    # national combined extract (not per-trail)
  changeset_187258738_reference.json
  stolavsleden_api_reference.json
scripts (repo root):
  extract_pilegrimsleden_shelters.py
  compare_osm_shelters.py
  extract_stolavsleden.py
  extract_romeriksleden.py
  propose_relation_additions.py
  build_josm_review.py
  discover_map_api.py
```

Each trail folder has **exactly one** `.osm` file: `trail.osm`, plus a short
`README.md`. The OSM file must not carry research keys such as
`pilegrimsleden:match_status`. Only suggested nodes use
`note:proposed=Proposed addition`.

`trail.osm` is a local research `type=site` relation (negative IDs). It is not
the live OSM route relation and does not carry that relation’s hundreds of path
way members. Uploading it as written adds new objects only; it does not remove
or rewrite membership of existing OSM route relations.


Trail folder names normalize Norwegian characters (ae/o/a) and drop the dot in
`St-Olavsleden`. St. Olavsleden merges NO + SE POIs in `trail.osm`.

## How to use in JOSM

Open:

`data/by_trail/<TrailName>/trail.osm`

It contains:

1. **Path** — one densified research way derived from the OSM route geometry
2. **Existing POIs** (already in OSM) — no `note:proposed`
3. **New suggestions** — only these have `note:proposed=Proposed addition`

Search: `note:proposed=Proposed addition`. Relation roles: `path`, `existing`,
`proposed`. See the trail folder `README.md` for counts and suggestion names.

### `trail.osm` is not the live OSM route relation

Each trail folder’s `trail.osm` ships a **new local** `type=site` relation with
**negative IDs** (new path way + lodging nodes). It is a JOSM review aid, not a
copy of the live OSM hiking route (e.g. Romeriksleden
[relation/1200009](https://www.openstreetmap.org/relation/1200009) with its ~988
way members).

That is why member counts differ: the OSM route holds hundreds of path ways;
`trail.osm` holds one simplified path plus overnight POIs only.

Uploading `trail.osm` **as written** creates *additional* new objects. It does
**not** rewrite, replace, or remove members from any existing OSM relation
(including other pilgrimage routes). Membership of live route relations is only
changed if you deliberately edit those relations in JOSM/iD after review.

### Workflow

1. Open `trail.osm`.
2. Optionally download the real OSM route relation (IDs above) for comparison —
   do not replace it from this file.
3. Map only nodes with `note:proposed=Proposed addition` after verifying each
   on the ground or with current local sources.
4. Do not bulk-upload these nodes. Prefer uploading verified new POIs one by
   one; leave the live route relation alone unless you intentionally add
   specific lodging members after review.

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
relations based solely on these files. Uploading the local `trail.osm` site
relation does not by itself alter membership of live OSM route relations.


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

## Matching notes

False “new” overnight nodes (hotels/camping already in OSM) came from three gaps:

1. Matching used proximity only (100 m / 250 m) and ignored CMS interest-point
   `address` fields (GraphQL / pages such as
   [Hedmarktoppen](https://www.pilegrimsleden.no/en/interest-points/hedmarktoppen)).
2. Some OSM lodging types were dropped from the Geofabrik filter (notably
   `tourism=caravan_site`) or treated as weak (`hotel`), so nearby mapped
   objects never entered the candidate set.
3. CMS pins can be offset from the real site; without address/name fallback the
   pipeline treated the CMS row as a gap and wrote a duplicate guest_house.

The matcher now pulls CMS addresses, matches `addr:*` and names out to 2 km,
keeps hotels/caravan sites as lodging, and when OSM already has a `name` the
pilgrim CMS title is written as `alt_name`.

## Regenerating

```bash
# Norwegian extract + national OSM comparison (requires Geofabrik PBFs under data/geofabrik/)
python3 extract_pilegrimsleden_shelters.py
python3 compare_osm_shelters.py --split-by-trail

# Swedish St. Olavsleden + horseback layers
python3 extract_stolavsleden.py

# Romeriksleden corridor from OSM relation 1200009
python3 extract_romeriksleden.py

# Membership proposals for all trails (optional --skip / --reuse-pbf / --only)
python3 propose_relation_additions.py

# Rebuild the single per-trail OSM file (path + existing + suggestions)
python3 build_josm_review.py
```

Do not commit `data/geofabrik/*.osm.pbf` or lodging scan caches (see `.gitignore`).
