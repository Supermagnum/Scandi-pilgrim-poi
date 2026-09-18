# St. Olavsleden

Folder: `St-Olavsleden`

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

- Name: St. Olavsleden
- Relation: https://www.openstreetmap.org/relation/10524322
- Do not remove existing members of that relation from this research file.

## Counts

| item | count |
| --- | ---: |
| Overnight POIs (CMS) | 142 |
| Existing in trail.osm | 46 |
| New suggestions in trail.osm | 96 |
| OSM lodging to add to route relation (`route_add`) | 408 |
| Pilgrim centers (reference) | 0 |
| Pilgrim-center gaps (reference) | 0 |
| Lodging already on OSM relation | 0 |
| Lodging near route not on relation (reference CSV) | 408 |
| Horseback service points (reference) | 12 |

## New suggestions (names)

- Alsen, Stuga
- Andersböle, Fäbodvall
- Attefallshus, Undersåker
- Bakgården, Revsund
- Bellmangårdens Pilgrimsboende, Matfors
- Björnidet Mörsil
- Bo i ro, Gällö
- Boda borg
- Boende på gård, Kluk
- Boende på gård, Kvällsjön, Matfors
- Borgsjö Hembygdsgård Vandrarhem
- Dass och rastplats Glösa
- Dass och rastplats vid Revsundssjön
- Duvhökens Bed & Breakfast, Alsen
- Enkelt boende på Bondgård, Svedje
- Fin Attefallstuga med underbar utsikt i Vik, Åre
- Flottarstugan Nederede
- Folkan Matfors
- Friggebod i Lunne
- Frösövallens Vandrarhem
- Furulund, Stavre
- Glösa
- Grimnäsvägen 101, Grimnäs
- Gällö, Långnäsudden
- Gäststudio, Vattjom
- Gålvikens pilgrimsboende, Stöde
- Gården Bräcke
- Gården Eriksberg, Mordviken
- Hedmans fjällby, Undersåker
- Helleberg, Stuga
- Hovs Uppgård, Alsen
- Hällsluten 167
- Härbre, Bodsjöbränna
- Hållsta 325
- Kapellet i Byn, Fränsta
- Knut & Ruts, Undersåker kyrka
- Liljedalen, Stöde
- Lilla Bogården, Kälsta
- Lilla Äppelgården, Selånger
- Lindberga gård, Stöde
- Lindqvist Tjänst & Gästgiveri i Fränsta
- Lombäcksstugorna
- Lägenhet, Bodsjöbränna
- Medstugans Pilgrimsboende
- Mellgård, Grimnäsvägen
- Mitt Musteri i Borgsjö
- Mogården, Gimdalen
- Mörsils Gamla Prästgård
- Norrgården: boende i Fränsta 
- Nälden, Ishallen
- Pilgrimskullen, Vaplan
- Pilgrimstad Vandrarhem
- Pilgrimsvila - Båthuset på Rödön
- Pils gård, Alsen
- Pizzaros, Mörsil
- Rastplats med vindskydd
- Rastplats och badplats i Alsen
- Rastplats och dass i Slåttviken
- Revsunds Brewery & Distillery
- Revsunds Prästgård
- Ritas brygga, Pilgrimstad
- Rombäck 611, Fränsta
- Rum i Bräcke  +46734843566
- Röde 301
- Röde 585
- Rödebuan Wilderness Camp
- Rödösundet Acc. Rödön
- Sara's Bed & Breakfast, Erikslund
- Skalstugan pensionat
- Solbacken, Fränsta
- St Olavs Cabin, Hållsta, Brunflo
- Stalltjärnstugan
- Strandbergs Bed and Breakfast
- Stuga i Grytan
- Stuga i Sösjö
- Stuga Österböle 212, Balsta
- Stuga, Lövåsen, Sörnedansjö
- Stuga, Staa
- Stuga, Storharrsjön
- Stuga, Undersåker
- Stugor, Rödön
- Sundsvalls ridklubb
- Svedje, Brunflo
- Sweden4u - Usland, Stöde
- Syster Ruths Hus, Alsen
- Södra Gullgård, Fränsta
- Sörnedansjö 149
- Tuna Hembygdsgård
- Tälje lantgårdshotell, Erikslund
- Uppland, Måbragård, Mörsil
- Vaplan, Vaplansgård
- Vindskydd, grillplats, bänkar
- Viskansparken, Torpshammar
- Wångens Wärdshus, Alsen
- Åredalens Fjällgård
- Åsans pilgrimsboende, Mörsil

## Files in this folder

- `trail.osm` — open this in JOSM
- `README.md` — this file (replaces per-trail CSV dumps)
- `hiking_path.gpx` — optional path cache
- `horseback_path.gpx` — horseback alignment (St. Olavsleden); not in trail.osm

Per-trail CSV dumps are not kept in this folder; relation candidates
are embedded in `trail.osm` as `route_add` members.
