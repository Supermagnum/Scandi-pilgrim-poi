# Outputs by trail

One folder per Pilegrimsleden trail. Folder names map ae/o/a from
Norwegian special letters and drop the dot in St. Olavsleden for
filesystem safety; the original trail name is in the `trail` CSV column
and in `note:trail` on OSM nodes.

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
| St-Olavsleden | St. Olavsleden | 176 | 5 | 118 | 3 | 12 |
| Borgleden | Borgleden | 16 | 4 | 8 | 1 | - |
| Kystpilegrimsleia | Kystpilegrimsleia | 49 | 10 | 29 | 2 | - |
| Tunsbergleden | Tunsbergleden | 33 | 4 | 18 | 1 | - |
| Osterdalsleden | Østerdalsleden | 50 | 1 | 36 | 0 | - |
| Valldalsleden | Valldalsleden | 22 | 0 | 9 | 0 | - |
| Romboleden | Romboleden | 9 | 1 | 5 | 0 | - |
| Nordleden | Nordleden | 2 | 1 | 0 | 0 | - |
