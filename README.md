# Scandi pilgrim POI dataset

Points of interest for the Scandinavian pilgrim trail network — shelters,
cabins, lean-tos, campsites, pilgrim centers, and (for St. Olavsleden) horseback
service points — cross-referenced against existing OpenStreetMap data to show
what is already mapped versus what appears to be missing.

This is an unofficial, independently compiled research aid. It is not affiliated
with pilegrimsleden.no, stolavsleden.com, Naturkartan, Svenska kyrkan, or the
OpenStreetMap Foundation.

## Table of contents

- [Data sources](#data-sources)
  - [Norway (pilegrimsleden.no CMS)](#norway-pilegrimsledenno-cms)
  - [Norway (extra trails, not on CMS)](#norway-extra-trails-not-on-cms)
  - [Sweden](#sweden)
  - [Denmark](#denmark)
  - [Finland](#finland)
  - [OpenStreetMap](#openstreetmap)
- [Trail-relation membership (research proposals)](#trail-relation-membership-research-proposals)
- [Directory layout](#directory-layout)
- [Pilgrim-center tagging](#pilgrim-center-tagging)
- [How to import into OpenStreetMap](#how-to-import-into-openstreetmap)
- [Important: not an OSM import](#important-not-an-osm-import)
- [License](#license)
- [Matching notes](#matching-notes)
- [Regenerating](#regenerating)

## Data sources

### Norway (pilegrimsleden.no CMS)

- **pilegrimsleden.no** (Craft CMS GraphQL / map APIs): Gudbrandsdalsleden,
  Borgleden, Kystpilegrimsleia, Tunsbergleden, Østerdalsleden, Valldalsleden,
  Romboleden, Nordleden, and related overnight / pilgrim-center points.
  Romeriksleden is Gudbrandsdalsleden east (Oslo–Eidsvoll–Hamar–Lillehammer),
  not a separate CMS trail; folder `data/by_trail/Norway/Romeriksleden/`.

### Norway (extra trails, not on CMS)

- **kvitekyrkjer.no** — [GPX / turkart](https://www.kvitekyrkjer.no/norsk/nyttig-informasjon/gpx-turkart/):
  Kvite kyrkjer rundt Tinnsjøen (`Norway/Kvite-kyrkjer-rundt-Tinnsjoen`).
- Documented stage places (Nominatim geocode; no public full GPX yet):
  Glåmdalsleden ([Eidskog kommune](https://www.eidskog.kommune.no/tjenester/kultur-og-fritid/friluftsliv-turer-i-eidskog/turstier/pilegrimsleden/)),
  [Pilegrimsvegen i Valdres](https://ut.no/turforslag/1111726436/pilegrimsvegen-i-valdres),
  [Pilegrimsvegen til Røldal](https://visittelemark.no/produkter/pilegrimsvegen-til-roldal),
  [Sunnivaleia](https://sunnivaleia.no/).
- Inventory: `data/norway/trails_catalog.json`.

### Sweden

- **stolavsleden.com** (WordPress + Naturkartan embed, guide id 154): St. Olavsleden
  hiking / biking / horseback paths and horseback service points. Horseback GPX
  can diverge from the hiking line by up to ~4.3 km; riders should not rely on
  hiking-line POIs alone.
- **Svenska kyrkan** (Arvika) KMZ: Pilgrimsleden Västra Värmland — path
  [id=1148827](https://www.svenskakyrkan.se/default.aspx?id=1148827), POIs
  [id=1148829](https://www.svenskakyrkan.se/default.aspx?id=1148829), page
  [arvika/pilgrim](https://www.svenskakyrkan.se/arvika/pilgrim).
- **Swedish pilgrim network** (~40 folders under `data/by_trail/Sweden/`): research
  `trail.osm` / `hiking_path.gpx` for the inventory in
  `data/sweden/trails_catalog.json`. Path preference order:
  1. Official GPX/KMZ when available (cached under `data/sweden/official_tracks/`;
     Outdooractive/Paxwalk, Naturkartan, Svenska kyrkan Google Earth, FKT).
  2. OSM hiking / foot / superroute geometry from Geofabrik `sweden-latest.osm.pbf`
     (member ways reordered with greedy nearest-endpoint stitching).
  3. OSRM foot between catalog endpoints (or stage waypoints) when no usable OSM
     relation exists — replace with official tracks when published.
- Extractor: `extract_sweden_trails.py`. Romboleden stays under
  `data/by_trail/Norway/Romboleden/` (shared SE/NO corridor).

### Denmark

- **[santiagopilgrimme.dk](https://santiagopilgrimme.dk/)** — Den danske Pilgrimsrute
  / route directory (`Denmark/Den-danske-Pilgrimsrute` waypoints).
- **[haervej.dk](https://haervej.dk/vandring)** — Hærvejen (~645 km). Partial OSM
  coverage (e.g. [relation/13278515](https://www.openstreetmap.org/relation/13278515));
  catalog only, no full research extract.
- Inventory: `data/denmark/trails_catalog.json`.

### Finland

- **[stolavostrobothnia.fi](https://stolavostrobothnia.fi/)** — St Olav Ostrobothnia.
- **[oulunseurakunnat.fi](https://oulunseurakunnat.fi/)** — Oulujoki pilgrimage
  (Oulu → Vaala).
- **[henrikinvaellus.fi](https://henrikinvaellus.fi/pyhan-henrikin-tie--in-english-)** —
  Saint Henry's way / Pyhän Henrikin tie (`Finland/Saint-Henrys-way`; path from
  OSM [relation/8833791](https://www.openstreetmap.org/relation/8833791)).
- **[stolavwaterway.com](https://stolavwaterway.com/)** — St. Olav Waterway
  (Turku → Grisslehamn via Åland).
- **[citynomadi.com](https://citynomadi.com/route/cf992911d8c170ddf1db528b8cdafcf7)**
  (API) — The way of Jacob / Jaakontie Renko–Rymättylä (`Finland/Way-of-Jacob`).
- Inventory: `data/finland/trails_catalog.json`.

### OpenStreetMap

- **OSM route relations** — source of truth for trail geometry and existing
  members; never modified by this project. Known CMS-aligned IDs:

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
  | Pyhän Henrikin tie (FI) | [8833791](https://www.openstreetmap.org/relation/8833791) |
  | Hærvejen stage Viborg–Skelhøje (DK) | [13278515](https://www.openstreetmap.org/relation/13278515) |

- **Pilgrim-center tagging reference**: changeset
  [187258738](https://www.openstreetmap.org/changeset/187258738)
  (`tourism=information` + `information=office` + `pilgrimage=stamp_office`).
  Discussion:
  [Inconsistent tagging for pilgrim centers](https://community.openstreetmap.org/t/inconsistent-tagging-for-pilgrim-centers/146312).
  See `data/changeset_187258738_reference.json`.
- **Geofabrik extracts** (local, gitignored): `norway-latest.osm.pbf`,
  `sweden-latest.osm.pbf` from https://download.geofabrik.de/europe/ when
  re-running lodging comparisons.

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

| folder | OSM relation | already | missing / route_add | CMS gaps in trail.osm |
| --- | ---: | ---: | ---: | ---: |
| Norway/Borgleden | 5672944 | 0 | 21 | 8 |
| Norway/Gudbrandsdalsleden | 1370273 | 0 | 26 | 79 |
| Norway/Kystpilegrimsleia | 10508888 | 0 | 32 | 28 |
| Norway/Nordleden | 1585449 | 0 | 2 | 0 |
| Norway/Osterdalsleden | 5129262 | 0 | 18 | 36 |
| Norway/Romboleden | 1151161 | 0 | 6 | 5 |
| Norway/Romeriksleden | 1200009 | 0 | 64 | 29 |
| Sweden/St-Olavsleden | 10524322 | 0 | 102 | 96 |
| Norway/Tunsbergleden | 5661086 | 0 | 24 | 18 |
| Norway/Valldalsleden | 11218584 | 0 | 17 | 9 |

Those “missing” lodging objects are embedded in each `trail.osm` as members with
role `route_add` (search `note:relation_member=…`) so they can be added to the
live OSM route relation in JOSM. CSVs also live under `data/research_by_trail/`.

## Directory layout

```
data/
  by_trail/Norway/<TrailName>/
    trail.osm           # ONLY OSM file: path + existing POIs + new suggestions
    README.md           # short trail notes (replaces per-trail CSV dumps)
    hiking_path.gpx     # optional path cache
  by_trail/Sweden/<TrailName>/
    trail.osm
    README.md
    hiking_path.gpx
    horseback_path.gpx  # St. Olavsleden only
  by_trail/Denmark/<TrailName>/
  by_trail/Finland/<TrailName>/
  norway/trails_catalog.json
  sweden/trails_catalog.json
  denmark/trails_catalog.json
  finland/trails_catalog.json
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
  extract_vastra_varmland.py
  extract_extra_norway_trails.py
  extract_denmark_finland_trails.py
  propose_relation_additions.py
  build_josm_review.py
  discover_map_api.py
```

Each trail folder has **exactly one** `.osm` file: `trail.osm`, plus a short
`README.md`. The OSM file must not carry research tags such as
`pilegrimsleden:match_status`. Only suggested CMS nodes use
`note:proposed=Proposed addition`.

`trail.osm` is a local research `type=site` relation. It includes:

1. One densified path (not every live OSM route way member)
2. CMS overnight matches / gaps
3. **Existing OSM lodging near the route that is not yet on the live route
   relation** — role `route_add`, tagged `note:relation_member=…` so they are
   present in JOSM and can be added as members of the real OSM route relation

Uploading new CMS suggestion nodes as written does not rewrite membership of
existing OSM route relations. `route_add` objects are already in OSM; download
or update them in JOSM, then add them to the live relation.



Trail folder names normalize Norwegian characters (ae/o/a) and drop the dot in
`St-Olavsleden`. Norwegian routes live under `data/by_trail/Norway/`; Swedish
trails under `data/by_trail/Sweden/`; Denmark and Finland under
`data/by_trail/Denmark/` and `data/by_trail/Finland/`. Country inventories:
`data/norway/trails_catalog.json`, `data/sweden/trails_catalog.json`,
`data/denmark/trails_catalog.json`, `data/finland/trails_catalog.json`.

## Pilgrim-center tagging

Reference scheme from changeset
[187258738](https://www.openstreetmap.org/changeset/187258738)
(see [community thread](https://community.openstreetmap.org/t/inconsistent-tagging-for-pilgrim-centers/146312)):

| key | value |
| --- | --- |
| `tourism` | `information` |
| `information` | `office` |
| `pilgrimage` | `stamp_office` |

Optional / related: `checkpoint:type=stamp`, `opening_hours=*`, contact tags.

Live check against matched objects in `data/pilgrim_centers.csv` (2026-09):
most named centers follow the scheme; some still only have
`pilgrimage=stamp_office` (e.g. Avaldsnes, Bergen regional) or are primarily
lodging with a stamp (`Nidaros Pilgrimsgård`). Prefer the full three-tag
combination when mapping or fixing centers.

## How to import into OpenStreetMap

These files are a **research aid**, not a bulk import. Open a trail folder’s
`trail.osm` in JOSM (or another editor) only as a review layer.

Paths to open:

- `data/by_trail/Norway/<TrailName>/trail.osm`
- `data/by_trail/Sweden/<TrailName>/trail.osm`
- `data/by_trail/Denmark/<TrailName>/trail.osm`
- `data/by_trail/Finland/<TrailName>/trail.osm`

Each `trail.osm` may contain:

1. **Path** — densified research geometry (OSM route, official GPX, or waypoints)
2. **Existing POIs** already in OSM — no `note:proposed`
3. **New suggestions** — only these have `note:proposed=Proposed addition`
4. **`route_add` lodging** — existing OSM objects to consider adding to the live
   route relation (search `note:relation_member=…`)

**Before any upload:** treat every object as unverified. There may be errors in
coordinates, names, categories, or duplicates. Confirm each feature against
survey, current local sources, or aerial imagery. Do not bulk-upload. Do not
upload the local `type=site` research relation as if it were a live trail.

### `trail.osm` is not the live OSM route relation

Each trail folder’s `trail.osm` ships a **local** `type=site` research relation
for review. For trails with a known OSM route / superroute id (see table above),
`trail.osm` embeds **every live route way member** with full geometry so the path
snaps to OpenStreetMap (including `alternative` / `excursion` roles; superroutes
are expanded recursively). Densified `hiking_path.gpx` remains available as a
lightweight path cache for distance checks.

It does include, in the same layer:

- CMS overnight matches and new suggestions
- **Existing OSM lodging** near the route that is **not** yet a member of the
  live route relation (`role=route_add`). Those objects must be in `trail.osm`
  so an editor can select them and add them to the real relation. Search:
  `note:relation_member=Add as member of OSM route relation`

Uploading new CMS suggestion nodes **as written** creates additional objects; it
does **not** rewrite or remove members of any existing OSM relation. Adding
`route_add` lodging to the live route is a deliberate edit of that relation
after review.

### Workflow

1. Open `trail.osm` as a review layer.
2. Optionally download the real OSM route relation (IDs above) for comparison —
   do not replace it from this file.
3. Map only nodes with `note:proposed=Proposed addition` after verifying each
   on the ground or with current local sources.
4. Do not bulk-upload. Prefer uploading verified new POIs one by one; leave the
   live route relation alone unless you intentionally add specific lodging
   members after review.
5. Follow the [Import Guidelines](https://wiki.openstreetmap.org/wiki/Import/Guidelines)
   and the [Automated Edits code of conduct](https://wiki.openstreetmap.org/wiki/Automated_Edits_code_of_conduct);
   discuss bulk work with the local community first.

Pilgrim-center matching uses any OSM node/way with `pilgrimage=*` (including way
centroids), not only `tourism=information` + `information=office`.

## Important: not an OSM import

This dataset is a **comparison / research aid**, not a ready-to-upload import.
Anyone merging features into OpenStreetMap must individually verify category,
existence, and location. Do not bulk-upload these nodes. Do not modify existing
members of OSM trail relations based solely on these files. Uploading the local
`trail.osm` site relation does not by itself alter membership of live OSM route
relations.

## License

This dataset uses the **same license as OpenStreetMap data**:
[Open Database License (ODbL) v1.0](https://opendatacommons.org/licenses/odbl/1.0/),
with individual contents under the
[Database Contents License (DbCL) v1.0](https://opendatacommons.org/licenses/dbcl/1.0/).
See [LICENSE](LICENSE).

Upstream sources keep their own terms (OSM under ODbL; pilegrimsleden.no,
stolavsleden.com, Naturkartan, Svenska kyrkan, kvitekyrkjer.no,
santiagopilgrimme.dk, haervej.dk, citynomadi.com, and other trail operators under
theirs). This project only publishes derived comparison fields needed for
mapping research.

Credit: pilegrimsleden.no, stolavsleden.com, Naturkartan, Svenska kyrkan,
kvitekyrkjer.no, santiagopilgrimme.dk, haervej.dk, stolavostrobothnia.fi,
oulunseurakunnat.fi, henrikinvaellus.fi, stolavwaterway.com, citynomadi.com,
OpenStreetMap contributors, and Geofabrik extracts.

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

# Pilgrimsleden Västra Värmland (Svenska kyrkan KMZ)
python3 extract_vastra_varmland.py

# Other Swedish pilgrim trails (OSM PBF + OSRM fallback)
python3 extract_sweden_trails.py
# After download, prefer overwriting weak paths from data/sweden/official_tracks/
# (see that folder's README for Outdooractive / Naturkartan / KMZ sources).

# Extra Norway trails (Kvite kyrkjer GPX + waypoint trails)
python3 extract_extra_norway_trails.py

# Denmark + Finland catalogs / extracts
python3 extract_denmark_finland_trails.py

# Membership proposals for CMS trails with OSM relations (writes data/research_by_trail/)
python3 propose_relation_additions.py

# Rebuild per-trail trail.osm (embeds live OSM route/superroute ways + CMS + route_add)
python3 build_josm_review.py
```

Do not commit `data/geofabrik/*.osm.pbf` or lodging scan caches (see `.gitignore`).
