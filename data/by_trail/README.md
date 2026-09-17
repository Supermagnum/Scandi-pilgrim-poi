# Outputs by trail

One folder per Pilegrimsleden trail. Folder names map ae/o/a from
Norwegian special letters and drop the dot in St. Olavsleden for
filesystem safety.

## Open in JOSM

Each trail folder contains:

- `trail.osm` — the **only** OSM file (path + existing POIs + new suggestions)
- `README.md` — short counts and suggestion names (replaces per-trail CSV files)
- optional `*.gpx` path caches

Only new suggestions carry `note:proposed=Proposed addition`. Existing POIs do
not. Research keys such as `pilegrimsleden:match_status` are not stored in
`trail.osm`.

Rebuild with `python3 build_josm_review.py`.

Known OSM route relations: Borgleden 5672944, Gudbrandsdalsleden 1370273,
Kystpilegrimsleia 10508888, Nordleden 1585449, Østerdalsleden 5129262,
Romboleden 1151161, Romeriksleden 1200009, St. Olavsleden superroute 10524322,
Tunsbergleden (Vestfoldveien) 5661086, Valldalsleden 11218584.

Romeriksleden is Gudbrandsdalsleden east (Oslo–Eidsvoll–Hamar–Lillehammer),
mapped in OSM as relation 1200009 but not a separate pilegrimsleden.no trail
entry.

National comparison CSVs (if regenerated) live under `data/`, not in the
per-trail JOSM folders.

St. Olavsleden merges Norwegian and Swedish overnight POIs in `trail.osm`.
Horseback alignment is `horseback_path.gpx` only (not a second OSM file).

| folder | trail | existing | suggestions |
| --- | --- | ---: | ---: |
| Gudbrandsdalsleden | Gudbrandsdalsleden | 81 | 88 |
| Romeriksleden | Romeriksleden | 29 | 32 |
| St-Olavsleden | St. Olavsleden | 58 | 118 |
| Borgleden | Borgleden | 8 | 8 |
| Kystpilegrimsleia | Kystpilegrimsleia | 20 | 29 |
| Tunsbergleden | Tunsbergleden | 15 | 18 |
| Osterdalsleden | Østerdalsleden | 14 | 36 |
| Valldalsleden | Valldalsleden | 13 | 9 |
| Romboleden | Romboleden | 4 | 5 |
| Nordleden | Nordleden | 2 | 0 |
