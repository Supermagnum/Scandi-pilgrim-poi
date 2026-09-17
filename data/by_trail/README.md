# Outputs by trail

One folder per Pilegrimsleden trail. Folder names map ae/o/a from
Norwegian special letters and drop the dot in St. Olavsleden for
filesystem safety; the original trail name is in the `trail` CSV column
and in `note:trail` on OSM nodes.

## Open in JOSM

Each trail folder has **exactly one** OSM file:

`trail.osm` — path + existing overnight POIs + new suggestions.

- Existing POIs (`match_status` matched/possible): no `note:proposed`
- New suggestions (`match_status=gap`): `note:proposed=Proposed addition`
- Site relation roles: `path`, `existing`, `proposed`

Rebuild with `python3 build_josm_review.py` (removes any other `*.osm` in the
folder).

Membership discovery (CSV) treats existing members of the OSM route relation as
already related and never modifies them. Nearby lodging not on the relation is
listed in `osm_missing_for_relation.csv` only (no second OSM file).

Known OSM route relations: Borgleden 5672944, Gudbrandsdalsleden 1370273,
Kystpilegrimsleia 10508888, Nordleden 1585449, Østerdalsleden 5129262,
Romboleden 1151161, Romeriksleden 1200009, St. Olavsleden superroute 10524322,
Tunsbergleden (Vestfoldveien) 5661086, Valldalsleden 11218584.

Romeriksleden is Gudbrandsdalsleden east (Oslo–Eidsvoll–Hamar–Lillehammer),
mapped in OSM as relation 1200009 but not a separate pilegrimsleden.no trail
entry. CMS overnight POIs within 2000 m are in `shelters.csv` / `trail.osm`
with `related_trails` Gudbrandsdalsleden + Romeriksleden.

Combined national files under `data/` are unchanged. Multi-trail POIs
are copied into every relevant trail folder.

Pilgrim-center matching uses any OSM node or way with `pilgrimage=*`
(way centroids included), not only the changeset 187258738
information-office combination. When several stamp-office objects lie
within 250 m of a CMS point, the closest one is chosen.

Nidaros Pilgrimsgård exists correctly in OSM as a pilgrim stamp office but is filed under a non-Pilegrimssenter category on the CMS map — a CMS taxonomy inconsistency, not an OSM gap.

St. Olavsleden merges Norwegian POIs from pilegrimsleden.no with Swedish
POIs from stolavsleden.com (Naturkartan guide 154). Rows include a
`country` column. Horseback-specific files live only under
`St-Olavsleden/`: `horseback_path.gpx` and
`horseback_service_points.csv` (veterinarians from the Naturkartan extract).
There is no separate horseback `.osm`; the hiking review layer is `trail.osm`.

Riders should not assume hiking-line POIs sit on the horse path: the official
horseback GPX diverges from the hiking line by up to about 4.3 km at some
points (126 of 201 sampled horseback points were ≥150 m from the hiking
geometry). Plan stops against the horseback track, not only the hiking line.

Naturkartan currently lists 0 farriers along the route. That reflects
Naturkartan's coverage, not a confirmed absence of farriers on
St. Olavsleden.

| folder | trail | shelters | pilgrim centers | shelter gaps | pilgrim gaps | horseback services |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Gudbrandsdalsleden | Gudbrandsdalsleden | 169 | 10 | 88 | 1 | - |
| Romeriksleden | Romeriksleden | 61 | 4 | 32 | 0 | - |
| St-Olavsleden | St. Olavsleden | 176 | 5 | 118 | 3 | 12 |
| Borgleden | Borgleden | 16 | 4 | 8 | 1 | - |
| Kystpilegrimsleia | Kystpilegrimsleia | 49 | 10 | 29 | 2 | - |
| Tunsbergleden | Tunsbergleden | 33 | 4 | 18 | 1 | - |
| Osterdalsleden | Østerdalsleden | 50 | 1 | 36 | 0 | - |
| Valldalsleden | Valldalsleden | 22 | 0 | 9 | 0 | - |
| Romboleden | Romboleden | 9 | 1 | 5 | 0 | - |
| Nordleden | Nordleden | 2 | 1 | 0 | 0 | - |

### Relation membership (CSV) and gaps in trail.osm

| folder | OSM relation | already members | missing (CSV) | CMS gaps (suggestions in trail.osm) |
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

Route relations are mostly path ways, so lodging `already members` is usually 0.
