# Romeriksleden

Folder: `Romeriksleden`

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

- Name: Romeriksleden
- Relation: https://www.openstreetmap.org/relation/1200009
- Do not remove existing members of that relation from this research file.

## Counts

| item | count |
| --- | ---: |
| Overnight POIs (CMS) | 61 |
| Existing in trail.osm | 13 |
| New suggestions in trail.osm | 29 |
| OSM lodging to add to route relation (`route_add`) | 345 |
| Pilgrim centers (reference) | 10 |
| Pilgrim-center gaps (reference) | 0 |
| Lodging already on OSM relation | 0 |
| Lodging near route not on relation (reference CSV) | 345 |

## New suggestions (names)

- "Rastebu" at Farseggen #1
- "Rastebu" ved Farseggen #2
- Arteid Vestre
- Atelier Lefstorvet
- Brynn i Bergsengroa
- Eidsvoll gamle prestegård - STENGT I 2026
- Fjellheim gård
- Frich`s Motell og Spiseri Rudshøgda
- Gapahuk "Pilegrimshvile"
- Gapahuk på Lindeberg etter Vilbergfjellet, før Arteid
- Haug pilegrimsrast og herberge
- Herkestad gård – overnatting og liten kafé
- Hytte på Gørdammen
- Ingeborg Refling Hagens kulturhus Fredheim
- InnomHaug pilegrimsherberge
- Kammerpikene
- Koss gård
- Kveldsro ved Fløyta
- Myhrer gård
- Overnatting hos Atlungstad golf
- Pilegrimsbua ved Granerud
- Pilegrimsherberget Millom
- Ringen Rehabiliteringssenter
- Seiersted Pensjonat
- Solvang overnatting
- Spitalen gamle skolehus - vertskap Sannfredstun
- Sveinhaug gård
- Tjelde herberge
- Velkommen til Olasvehaugen i Brøttum
- Østre Aker pilegrimsherberge

## Files in this folder

- `trail.osm` — open this in JOSM
- `README.md` — this file (replaces per-trail CSV dumps)
- `hiking_path.gpx` — optional path cache

Per-trail CSV dumps are not kept in this folder; relation candidates
are embedded in `trail.osm` as `route_add` members.
