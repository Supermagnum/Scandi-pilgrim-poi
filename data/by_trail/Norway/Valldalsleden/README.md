# Valldalsleden

Folder: `Norway/Valldalsleden`

## Open in JOSM

Open `trail.osm` in this folder (the only `.osm` file).

It contains:

1. Trail **path** (one densified research way — not every OSM route way member)
2. **Existing** overnight POIs (CMS matched) — no `note:proposed`
3. **New suggestions** — tagged `note:proposed=Proposed addition`
4. **OSM lodging to add to the live route relation** — role `route_add`, search `note:relation_member=Add as member of OSM route relation`

Search in JOSM: `note:proposed=Proposed addition` or `note:relation_member=Add as member of OSM route relation`

Do not expect research tags such as `pilegrimsleden:match_status` in this file.

This file is a local `type=site` research relation. Uploading new CMS nodes
as written does not rewrite membership of existing OSM route relations.
Objects with role `route_add` are already in OSM; use them in JOSM to add
members to the live route relation below (download/update those objects first).

## OSM route relation

- Name: Valldalsleden
- Relation: https://www.openstreetmap.org/relation/11218584
- Do not remove existing members of that relation from this research file.

## Counts

| item | count |
| --- | ---: |
| Overnight POIs (CMS) | 22 |
| Existing in trail.osm | 13 |
| New suggestions in trail.osm | 9 |
| OSM lodging to add to route relation (`route_add`) | 17 |
| Pilgrim centers (reference) | 0 |
| Pilgrim-center gaps (reference) | 0 |
| Lodging already on OSM relation | 0 |
| Lodging near route not on relation (reference CSV) | 45 |

## New suggestions (names)

- Elvebakken Camping
- Gammelstuggu
- Klosteret av Den Hellige Olav
- Koia - Hytte i Verma
- Kvennbekkhytta (stengt)
- Lesja Gjestgiveri
- Lorkverna
- Muri hytteutleige
- Sør-Einbu

## Files in this folder

- `trail.osm` — open this in JOSM
- `README.md` — this file (replaces per-trail CSV dumps)
- `hiking_path.gpx` — optional path cache

Per-trail CSV dumps are not kept in this folder; relation candidates
are embedded in `trail.osm` as `route_add` members.
