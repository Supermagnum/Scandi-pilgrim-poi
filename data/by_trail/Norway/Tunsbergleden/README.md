# Tunsbergleden / Vestfoldveien

Folder: `Norway/Tunsbergleden`

## Open in JOSM

Open `trail.osm` in this folder (the only `.osm` file).

It contains:

1. Trail **path** — every live OSM route-relation way member with full geometry (snaps to OpenStreetMap; includes `alternative` / `excursion`)
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

- Name: Tunsbergleden / Vestfoldveien
- Relation: https://www.openstreetmap.org/relation/5661086
- Do not remove existing members of that relation from this research file.

## Counts

| item | count |
| --- | ---: |
| Overnight POIs (CMS) | 33 |
| Existing in trail.osm | 15 |
| New suggestions in trail.osm | 18 |
| OSM lodging to add to route relation (`route_add`) | 24 |
| Pilgrim centers (reference) | 0 |
| Pilgrim-center gaps (reference) | 0 |
| Lodging already on OSM relation | 0 |
| Lodging near route not on relation (reference CSV) | 184 |

## New suggestions (names)

- Berger Gård
- Brannåsen
- Engøy gjestegård
- Fuglesang herberge
- Gapahuk ved Stordammen
- Gardlaus Markastue og pilegrimsherberge
- Kaupang gård
- Kirkebakken Borre - midlertidig stengt
- Kjølholmen på Veierland
- Lavvoen Biggen
- Orrfuglstua pilegrimsherberge
- Poppel pilegrimsherberge
- Preståsen pilegrimsherberge
- Røyken Menighetshus
- Sande overnatting
- Tyristua
- Veierland skole
- Østre Aker pilegrimsherberge

## Files in this folder

- `trail.osm` — open this in JOSM
- `README.md` — this file (replaces per-trail CSV dumps)
- `hiking_path.gpx` — optional path cache

Per-trail CSV dumps are not kept in this folder; relation candidates
are embedded in `trail.osm` as `route_add` members.
