# Outputs by trail

One folder per Pilegrimsleden trail. Folder names map ae/o/a from
Norwegian special letters and drop the dot in St. Olavsleden for
filesystem safety; the original trail name is in the `trail` CSV column
and in `note:trail` on OSM nodes. Each trail `shelters.osm` also includes a
local JOSM `type=site` relation that members the overnight POI nodes (research
aid only; not for upload). Where known, nodes carry `note:osm_route_relation`
pointing at the matching OSM hiking route relation.

Membership discovery (all trails with a known OSM route relation) treats
existing members of that relation as already related and never modifies them.
Nearby lodging/shelter OSM objects that are not members are listed per trail in
`osm_missing_for_relation.csv` / `missing_additions.osm` as local research
proposals only; `osm_already_related.csv` lists objects already on the
relation. Each proposed POI carries a `note:proposed` / `proposal_note`.
Regenerate with `propose_relation_additions.py` (optional `--skip` /
`--reuse-pbf`).

Known OSM route relations: Borgleden 5672944, Gudbrandsdalsleden 1370273,
Kystpilegrimsleia 10508888, Nordleden 1585449, Østerdalsleden 5129262,
Romboleden 1151161, Romeriksleden 1200009, St. Olavsleden superroute 10524322,
Tunsbergleden (Vestfoldveien) 5661086, Valldalsleden 11218584.

Romeriksleden is Gudbrandsdalsleden east (Oslo–Eidsvoll–Hamar–Lillehammer),
mapped in OSM as relation 1200009 but not a separate pilegrimsleden.no trail
entry. CMS overnight POIs within 2000 m are in `shelters.*` with
`related_trails` Gudbrandsdalsleden + Romeriksleden.

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
`St-Olavsleden/`: `horseback_path.osm` / `.gpx` and
`horseback_service_points.csv` (veterinarians from the Naturkartan extract).

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

### Relation membership proposals (latest pass)

| folder | OSM relation | already members | missing proposals | CMS gaps with notes |
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
Per-folder files: `osm_already_related.csv`, `osm_missing_for_relation.csv`,
`missing_additions.osm`, `relation_additions_summary.json`.
