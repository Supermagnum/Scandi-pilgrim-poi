# Gudbrandsdalsleden

Folder: `Gudbrandsdalsleden`

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

- Name: Gudbrandsdalsleden
- Relation: https://www.openstreetmap.org/relation/1370273
- Do not remove existing members of that relation from this research file.

## Counts

| item | count |
| --- | ---: |
| Overnight POIs (CMS) | 169 |
| Existing in trail.osm | 90 |
| New suggestions in trail.osm | 79 |
| OSM lodging to add to route relation (`route_add`) | 350 |
| Pilgrim centers (reference) | 0 |
| Pilgrim-center gaps (reference) | 0 |
| Lodging already on OSM relation | 0 |
| Lodging near route not on relation (reference CSV) | 350 |

## New suggestions (names)

- "Rastebu" at Farseggen #1
- "Rastebu" ved Farseggen #2
- Arteid Vestre
- Atelier Lefstorvet
- Audenhus - Pilegrimsherberge på Vingrom
- Aunan Gård
- Aurdal Gård
- Basecamp Frich's Hjerkinn
- Betania Kolbu
- Bittes Gjestehus
- Brurbakkvegen 79
- Bryggerhuset Nordre Ullern
- Bryggerhuset på Lander
- Bryhni Søndre – Gjestegård
- Brynn i Bergsengroa
- Båkinn Gård
- Bøndernes Hus Jevnaker
- Dalum herberge tilbyr enkel overnatting til pilegrimer
- Eidsvoll gamle prestegård - STENGT I 2026
- Engen kloster i Kolbu
- Fjellheim gård
- Fuglesang herberge
- Gamleveien 60
- Gapahuk "Pilegrimshvile"
- Gapahuk på Lindeberg etter Vilbergfjellet, før Arteid
- Gardlaus Markastue og pilegrimsherberge
- Gjesvold Gård
- Hagevandring Nordre Toten
- Haug pilegrimsrast og herberge
- Helgaker Gård
- Hoffsvangen Bygdestue
- Hos Margit
- Huset i skogen
- Hytte på Gørdammen
- Indal Forest Retreat
- Ingeborg Refling Hagens kulturhus Fredheim
- InnomHaug pilegrimsherberge
- Jørundgard Viking- og Middelaldersenter
- Kaldor Gård - overnatting og utsikt i Hafjell
- Klokkargården Halstad
- Konstadtunet
- Kronprinsens utsikt
- Kveldsro ved Fløyta
- Langklopp Fjellgård
- Lerfald gård
- Majer Gård
- Majors-Alm Gård
- Meslo Herberge
- Mjuklia - overnatting på Berkåk
- Mjøsli - glamping eller hytter
- Myhrer gård
- Nordre Helgaker Gård
- Nordrum Gård
- Pilegrimsbua ved Granerud
- Rastebu Falang Bru
- Rastebu Høgkorset
- Rastebu Kjølvegen
- Rastebu Sognstoppen
- Rudsødegården
- Sandbakken Camping - STENGT 2023
- Segard Hoel
- Skaun menighetshus
- Skogheim Pilegrimsherberge
- Skomakerstua
- Skysstasjonen Høgkorsplassen
- Slettum Gård
- Solvang overnatting
- Spitalen gamle skolehus - vertskap Sannfredstun
- Stabburet på Skjefstad
- Stensveen
- Stokke Nedre
- Sveastranda Camping
- Sveinhaug gård
- Svorkmo skytterhus
- Sætrangsgata 37
- Teltplass
- Vekve hyttetun
- Østre Aker pilegrimsherberge
- ØYGARDEN PILEGRIMSHERBERGE

## Files in this folder

- `trail.osm` — open this in JOSM
- `README.md` — this file (replaces per-trail CSV dumps)
- `hiking_path.gpx` — optional path cache

Per-trail CSV dumps are not kept in this folder; relation candidates
are embedded in `trail.osm` as `route_add` members.
