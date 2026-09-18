# Østerdalsleden

Folder: `Osterdalsleden`

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

- Name: Østerdalsleden
- Relation: https://www.openstreetmap.org/relation/5129262
- Do not remove existing members of that relation from this research file.

## Counts

| item | count |
| --- | ---: |
| Overnight POIs (CMS) | 50 |
| Existing in trail.osm | 14 |
| New suggestions in trail.osm | 36 |
| OSM lodging to add to route relation (`route_add`) | 194 |
| Pilgrim centers (reference) | 0 |
| Pilgrim-center gaps (reference) | 0 |
| Lodging already on OSM relation | 0 |
| Lodging near route not on relation (reference CSV) | 194 |

## New suggestions (names)

- Barmo -hus til leie
- Bjerkelihytten på Aasgårvollen
- Dagfinnstua på Oddheim
- Elgstua | Gjerfloen Fluefiske
- Eltdalen Grendehus
- Fagertun
- Fiskvik Søndre - Jaktslottet.
- Fjellavvo ved Osdalssjøhøgda naturreservat
- Flenåsstua, Ol-Jons garden
- Fluesonen | Gjerfloen fluefiske
- Heimvollen
- Hytte på Osåsan
- Hytte ved Nordstu Digre
- Hytte | Storbekkøya museumssæter
- Kari Maries Sommerresidens
- Kneppstua - stengt
- Koie ved Netsjøen
- Koie ved Nysledammen
- Mandfloen husmannsplass
- Negarn
- Perskoia
- Pilegrimsbu Vardan
- Pilegrimsbu ved Okstjønna
- Pilegrimslavvo ved Søndre Kvanntjønna
- Romenstad Gård
- Samatun
- Simensvollen - trivelig seterstue
- Skårsåsbua
- Småvangan skihytte
- Stengt- Pilegrimshytta i Otnes
- Svarttjønnbua
- Tollefkoia
- Tollefsa Gjestegård
- Trollhaugen
- Trollhytta
- Øyvindtjønna sælehus

## Files in this folder

- `trail.osm` — open this in JOSM
- `README.md` — this file (replaces per-trail CSV dumps)
- `hiking_path.gpx` — optional path cache

Per-trail CSV dumps are not kept in this folder; relation candidates
are embedded in `trail.osm` as `route_add` members.
