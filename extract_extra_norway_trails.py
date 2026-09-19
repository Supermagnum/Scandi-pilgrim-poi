#!/usr/bin/env python3
"""Extract Norwegian pilgrim trails that are not on pilegrimsleden.no CMS / OSM routes.

Writes under data/by_trail/Norway/<Trail>/ :
  trail.osm, hiking_path.gpx (when path geometry exists), README.md

Trails:
  - Kvite-kyrkjer-rundt-Tinnsjoen  (official stage GPX from kvitekyrkjer.no)
  - Glamdalsleden                  (documented waypoints; no public GPX yet)
  - Pilegrimsvegen-i-Valdres       (documented stage churches; no public GPX)
  - Pilegrimsvegen-til-Roldal      (documented stages + OSM named path fragment)
  - Sunnivaleia                    (documented stage places; no public GPX)

Also writes/updates data/norway/trails_catalog.json inventory.
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(OSM mapping research; extra Norway trails; "
    "+https://github.com/Supermagnum/Scandi-pilgrim-poi)"
)

ROOT = Path(__file__).resolve().parent
BY_TRAIL = ROOT / "data" / "by_trail" / "Norway"
CACHE = ROOT / "data" / "norway" / "cache"


def log(msg: str) -> None:
    print(msg, flush=True)


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def http_get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def thin_points(points: list[tuple[float, float]], max_points: int = 5000) -> list[tuple[float, float]]:
    if len(points) <= max_points:
        return points
    step = math.ceil(len(points) / max_points)
    out = points[::step]
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def parse_gpx_points(gpx_bytes: bytes) -> list[tuple[float, float]]:
    root = ET.fromstring(gpx_bytes)
    # strip ns
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    points: list[tuple[float, float]] = []
    for tag in ("trkpt", "rtept"):
        for pt in root.findall(f".//{tag}"):
            lat = pt.attrib.get("lat")
            lon = pt.attrib.get("lon")
            if lat is None or lon is None:
                continue
            lat_f, lon_f = float(lat), float(lon)
            if points and points[-1] == (lat_f, lon_f):
                continue
            points.append((lat_f, lon_f))
    return points


def nominatim_search(query: str) -> tuple[float, float] | None:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "no",
        }
    )
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as resp:
        hits = json.load(resp)
    if not hits:
        return None
    return float(hits[0]["lat"]), float(hits[0]["lon"])


def geocode_waypoints(
    items: list[tuple],
) -> list[dict[str, str | float]]:
    """items: (name, nominatim_query, poi_type[, lat, lon])."""
    out: list[dict[str, str | float]] = []
    for item in items:
        name, query, poi_type = item[0], item[1], item[2]
        if len(item) >= 5 and item[3] is not None and item[4] is not None:
            lat, lon = float(item[3]), float(item[4])
            log(f"  fixed: {name} @ {lat},{lon}")
            out.append({"name": name, "type": poi_type, "lat": lat, "lon": lon, "query": query})
            continue
        log(f"  geocode: {name} ({query})")
        try:
            coords = nominatim_search(query)
        except Exception as exc:
            log(f"    FAIL {exc}")
            coords = None
        time.sleep(1.1)
        if not coords:
            log("    no hit")
            continue
        lat, lon = coords
        out.append({"name": name, "type": poi_type, "lat": lat, "lon": lon, "query": query})
    return out


def write_gpx(path: Path, trail_name: str, points: list[tuple[float, float]]) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="pilegrimsleden-osm-extractor 1.0" '
        'xmlns="http://www.topografix.com/GPX/1/1">',
        f"  <trk><name>{xml_escape(trail_name)}</name><trkseg>",
    ]
    for lat, lon in points:
        lines.append(f'    <trkpt lat="{lat:.7f}" lon="{lon:.7f}"></trkpt>')
    lines.extend(["  </trkseg></trk>", "</gpx>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


TYPE_TAGS: dict[str, list[tuple[str, str]]] = {
    "church": [("amenity", "place_of_worship"), ("religion", "christian")],
    "lodging": [("tourism", "guest_house")],
    "camping": [("tourism", "camp_site")],
    "attraction": [("tourism", "attraction")],
    "waypoint": [("tourism", "yes")],
    "border": [("barrier", "border_control")],
    "place": [("place", "village")],
}


def write_trail_osm(
    path: Path,
    trail_name: str,
    source_url: str,
    points: list[tuple[float, float]],
    pois: list[dict[str, str | float]],
    extra_note: str,
) -> None:
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    next_id = -1
    member_ids: list[tuple[str, int, str]] = []

    if points:
        node_ids: list[int] = []
        for lat, lon in points:
            lines.append(
                f"  <node id='{next_id}' version='0' action='modify' visible='true' "
                f"lat='{lat:.7f}' lon='{lon:.7f}'/>"
            )
            node_ids.append(next_id)
            next_id -= 1
        way_id = next_id
        lines.append(f"  <way id='{way_id}' version='0' action='modify' visible='true'>")
        for nid in node_ids:
            lines.append(f"    <nd ref='{nid}'/>")
        for key, value in [
            ("highway", "path"),
            ("name", trail_name),
            ("network", "Pilgrimsleder Norge"),
            ("note:trail", trail_name),
            ("note:country", "Norway"),
            ("source", source_url),
        ]:
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        if "waypoint" in extra_note.lower() or "approximate" in extra_note.lower():
            lines.append(
                "    <tag k='note:path' v='Research path from documented waypoints; "
                "not an official continuous GPX'/>"
            )
        lines.append("  </way>")
        member_ids.append(("way", way_id, "path"))
        next_id -= 1

    for poi in pois:
        lat = float(poi["lat"])
        lon = float(poi["lon"])
        name = str(poi["name"])
        typ = str(poi["type"])
        lines.append(
            f"  <node id='{next_id}' version='0' action='modify' visible='true' "
            f"lat='{lat:.7f}' lon='{lon:.7f}'>"
        )
        lines.append(f"    <tag k='name' v='{xml_escape(name)}'/>")
        lines.append(f"    <tag k='note:poi_type' v='{xml_escape(typ)}'/>")
        lines.append(f"    <tag k='note:trail' v='{xml_escape(trail_name)}'/>")
        lines.append("    <tag k='note:country' v='Norway'/>")
        lines.append(f"    <tag k='source' v='{xml_escape(source_url)}'/>")
        for key, value in TYPE_TAGS.get(typ, [("tourism", "yes")]):
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        if typ in {"lodging", "camping"}:
            lines.append("    <tag k='note:lodging' v='yes'/>")
        lines.append("  </node>")
        role = "lodging" if typ in {"lodging", "camping"} else "poi"
        member_ids.append(("node", next_id, role))
        next_id -= 1

    rel_id = next_id
    lines.append(f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>")
    for mtype, mid, role in member_ids:
        lines.append(
            f"    <member type='{mtype}' ref='{mid}' role='{xml_escape(role)}'/>"
        )
    note = (
        f"Local JOSM research file for {trail_name}. {extra_note} Source {source_url}"
    )
    for key, value in [
        ("type", "site"),
        ("name", trail_name),
        ("network", "Pilgrimsleder Norge"),
        ("note:trail", trail_name),
        ("note:country", "Norway"),
        ("note", note),
        ("source", source_url),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </relation>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(
    path: Path,
    trail_name: str,
    folder: str,
    source_url: str,
    n_path: int,
    pois: list[dict[str, str | float]],
    notes: list[str],
) -> None:
    lines = [
        f"# {trail_name}",
        "",
        f"Folder: `{folder}`",
        "",
        "## Open in JOSM",
        "",
        "Open `trail.osm` in this folder (the only `.osm` file).",
        "",
        f"Source: {source_url}",
        "",
        "## Notes",
        "",
    ]
    for n in notes:
        lines.append(f"- {n}")
    lines.extend(
        [
            "",
            "## Counts",
            "",
            "| item | count |",
            "| --- | ---: |",
            f"| Path points | {n_path} |",
            f"| POIs / waypoints | {len(pois)} |",
            "",
            "## Waypoints",
            "",
        ]
    )
    for p in pois:
        lines.append(f"- {p['name']} ({p['type']})")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `trail.osm` — open this in JOSM",
            "- `hiking_path.gpx` — path cache (if present)",
            "- `README.md` — this file",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_trail_dir(slug: str) -> Path:
    d = BY_TRAIL / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Trail extractors
# ---------------------------------------------------------------------------


def extract_kvite() -> dict:
    name = "Kvite kyrkjer rundt Tinnsjøen"
    slug = "Kvite-kyrkjer-rundt-Tinnsjoen"
    source = "https://www.kvitekyrkjer.no/norsk/nyttig-informasjon/gpx-turkart/"
    page_url = "https://www.kvitekyrkjer.no/"
    trail_dir = ensure_trail_dir(slug)
    cache = CACHE / "kvite_kyrkjer"
    cache.mkdir(parents=True, exist_ok=True)

    log(f"=== {name}")
    html = http_get(source).decode("utf-8", errors="replace")
    hrefs = sorted(set(re.findall(r'href=["\']([^"\']+\.gpx[^"\']*)["\']', html, re.I)))
    all_points: list[tuple[float, float]] = []
    for href in hrefs:
        url = urllib.parse.urljoin("https://www.kvitekyrkjer.no", href)
        fname = urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).name)
        log(f"  GPX {fname}")
        blob = http_get(url)
        (cache / fname.replace(" ", "_")).write_bytes(blob)
        pts = parse_gpx_points(blob)
        log(f"    {len(pts)} points")
        if not pts:
            continue
        if all_points and all_points[-1] == pts[0]:
            pts = pts[1:]
        all_points.extend(pts)

    points = thin_points(all_points, max_points=6000)
    # Stage / lodging names from GPX filenames + known churches
    pois = geocode_waypoints(
        [
            ("Hovin kirke", "Hovin kirke Tinn Telemark", "church"),
            ("Austbygde kirke", "Austbygde kirke Tinn", "church"),
            ("Mæl kirke", "Mæl kirke Tinn", "church"),
            ("Sandviken Camping", "Sandviken Camping Tinn Austbygde", "camping"),
            ("Tinnsjø Kro og Camping", "Tinnsjø Kro Tinn", "camping"),
        ]
    )
    write_gpx(trail_dir / "hiking_path.gpx", name, points)
    write_trail_osm(
        trail_dir / "trail.osm",
        name,
        page_url,
        points,
        pois,
        "Path merged from official stage GPX files on kvitekyrkjer.no.",
    )
    write_readme(
        trail_dir / "README.md",
        name,
        f"Norway/{slug}",
        page_url,
        len(points),
        pois,
        [
            "Official stage GPX from kvitekyrkjer.no (gpx-turkart).",
            "No OSM hiking/pilgrimage route relation found (2026-09).",
            f"About 89 km around Tinnsjøen. GPX page: {source}",
        ],
    )
    return {
        "name": name,
        "folder": f"Norway/{slug}",
        "km": 89,
        "url": page_url,
        "status": "extracted",
        "path_source": "official_gpx",
        "path_points": len(points),
        "pois": len(pois),
    }


def extract_waypoint_trail(
    name: str,
    slug: str,
    source_url: str,
    waypoints: list[tuple[str, str, str]],
    notes: list[str],
    km: float | int | str | None,
    connect_as_path: bool = True,
) -> dict:
    trail_dir = ensure_trail_dir(slug)
    log(f"=== {name}")
    pois = geocode_waypoints(waypoints)
    points: list[tuple[float, float]] = []
    if connect_as_path and len(pois) >= 2:
        points = [(float(p["lat"]), float(p["lon"])) for p in pois]
        write_gpx(trail_dir / "hiking_path.gpx", name, points)
    write_trail_osm(
        trail_dir / "trail.osm",
        name,
        source_url,
        points,
        pois,
        "Research waypoints geocoded from documented stage places; "
        "no public continuous official GPX was available.",
    )
    write_readme(
        trail_dir / "README.md",
        name,
        f"Norway/{slug}",
        source_url,
        len(points),
        pois,
        notes
        + [
            "No OSM hiking/pilgrimage route relation found (2026-09).",
            "Path in trail.osm (if present) only connects documented waypoints — replace with official GPX when published.",
        ],
    )
    return {
        "name": name,
        "folder": f"Norway/{slug}",
        "km": km,
        "url": source_url,
        "status": "extracted_waypoints",
        "path_source": "geocoded_waypoints" if points else "none",
        "path_points": len(points),
        "pois": len(pois),
    }


def extract_glamdalsleden() -> dict:
    return extract_waypoint_trail(
        name="Glåmdalsleden",
        slug="Glamdalsleden",
        source_url="https://www.eidskog.kommune.no/tjenester/kultur-og-fritid/friluftsliv-turer-i-eidskog/turstier/pilegrimsleden/",
        km=150,
        waypoints=[
            ("Riksgrensen / Rudsenga (riksrøys 56)", "Rudsenga Eidskog", "border"),
            ("Vestmarka kirke", "Vestmarka kirke Eidskog", "church"),
            ("Eidskog kirke", "Eidskog kirke", "church"),
            ("Åbogen", "Åbogen Eidskog", "place"),
            ("Kongsvinger", "Kongsvinger", "place"),
            ("Grue kirke", "Grue kirke Innlandet", "church"),
            ("Åsnes kirke", "Åsnes kirke Flisa", "church"),
            ("Våler kirke", "Våler kirke Innlandet", "church"),
            ("Elverum (mot Østerdalsleden)", "Elverum kirke", "church"),
        ],
        notes=[
            "Continues Pilgrimsleden Västra Värmland into Norway (Eidskog → Solør → Østerdalsleden).",
            "Opened through Eidskog 2024; no public GPX found.",
            "See also https://lokalhistoriewiki.no/wiki/Glåmdalsleden",
        ],
    )


def extract_valdres() -> dict:
    return extract_waypoint_trail(
        name="Pilegrimsvegen i Valdres",
        slug="Pilegrimsvegen-i-Valdres",
        source_url="https://ut.no/turforslag/1111726436/pilegrimsvegen-i-valdres",
        km=162,
        waypoints=[
            ("Hedalen stavkirke", "Hedalen stavkirke", "church"),
            ("Reinli stavkirke", "Reinli stavkyrkje", "church"),
            ("Aurdal kirke", "Aurdal kirke Nord-Aurdal", "church"),
            ("Fagernes", "Fagernes Nord-Aurdal", "place"),
            ("Ulnes kirke", "Ulnes kirke Nord-Aurdal", "church"),
            ("Slidredomen", "Slidredomen Vestre Slidre", "church"),
            ("Lomen stavkirke", "Lomen stavkirke", "church"),
            ("Høre stavkirke", "Høre stavkyrkje", "church"),
            ("Øye stavkirke", "Øye stavkyrkje", "church"),
            # Not in Nominatim/OSM yet; approximate from Filefjell massif endpoint
            ("Filefjell (mot St. Thomaskirken)", "Filefjell Vang", "place"),
        ],
        notes=[
            "162 km Hedalen → St. Thomaskirken on Filefjell (ut.no turforslag).",
            "ut.no page has no downloadable GPX/geometry API for this trip.",
        ],
    )


def extract_roldal() -> dict:
    return extract_waypoint_trail(
        name="Pilegrimsvegen til Røldal",
        slug="Pilegrimsvegen-til-Roldal",
        source_url="https://visittelemark.no/produkter/pilegrimsvegen-til-roldal",
        km=165,
        waypoints=[
            ("Seljord kirke", "Seljord kirke", "church"),
            ("Morgedal", "Morgedal", "place"),
            ("Øyfjell", "Øyfjell Telemark", "place"),
            ("Åmot i Vinje", "Åmot Vinje Telemark", "place"),
            ("Mjønøy", "Mjønøy Vinje", "place"),
            ("Haukeligrend", "Haukeligrend", "place"),
            ("Vågslid", "Vågslid", "place"),
            ("Ulevå", "Ulevå Vinje", "place"),
            ("Røldal stavkirke", "Røldal stavkirke", "church"),
        ],
        notes=[
            "Seljord → Røldal (~165 km). Kartbok exists; no public full GPX found.",
            "OSM has orphan path way/1531240634 named Pilegrimsvegen til Røldal (no parent route relation).",
            "See also https://www.telemarkfylke.no/no/meny/tjenester/idrett-friluftsliv/pa-tur-i-vestfold-og-telemark/pilgrimsled/",
        ],
    )


def extract_sunnivaleia() -> dict:
    return extract_waypoint_trail(
        name="Sunnivaleia",
        slug="Sunnivaleia",
        source_url="https://sunnivaleia.no/",
        km=None,
        waypoints=[
            ("Kinn kyrkje", "Kinn kyrkje", "church"),
            ("Florø", "Florø", "place"),
            ("Måløy", "Måløy", "place"),
            ("Bryggja", "Bryggja Stad", "place"),
            ("Bremangerlandet", "Bremangerlandet", "place"),
            ("Selje", "Selje Stad", "place"),
            ("Selja kloster", "Selja kloster", "attraction"),
        ],
        notes=[
            "Kinn / Florø → Selja (Selje). Stages documented on sunnivaleia.no.",
            "No public GPX; Google Maps embed only shows Kinnakyrkja → Selja endpoints.",
            "Lodging list: https://sunnivaleia.no/planlegg-turen/overnatting/",
        ],
    )


EXISTING_CMS = [
    {
        "name": "Borgleden",
        "from": "Halden",
        "to": "Oslo",
        "km": 176,
        "url": "https://pilegrimsleden.no/pilegrimsledene/borgleden",
        "folder": "Norway/Borgleden",
        "status": "extracted",
    },
    {
        "name": "Gudbrandsdalsleden",
        "from": "Oslo",
        "to": "Trondheim",
        "km": 643,
        "url": "https://pilegrimsleden.no/pilegrimsledene/gudbrandsdalsleden",
        "folder": "Norway/Gudbrandsdalsleden",
        "status": "extracted",
    },
    {
        "name": "Kystpilegrimsleia",
        "from": "Egersund",
        "to": "Trondheim",
        "km": 1080,
        "url": "https://pilegrimsleden.no/pilegrimsledene/kystpilegrimsleia",
        "folder": "Norway/Kystpilegrimsleia",
        "status": "extracted",
    },
    {
        "name": "Nordleden",
        "from": "Grong",
        "to": "Stiklestad",
        "km": 135,
        "url": "https://pilegrimsleden.no/pilegrimsledene/nordleden",
        "folder": "Norway/Nordleden",
        "status": "extracted",
    },
    {
        "name": "Tunsbergleden",
        "from": "Larvik",
        "to": "Bærum",
        "km": 190,
        "url": "https://pilegrimsleden.no/pilegrimsledene/tunsbergleden",
        "folder": "Norway/Tunsbergleden",
        "status": "extracted",
    },
    {
        "name": "Valldalsleden",
        "from": "Valldal",
        "to": "Dovrefjell",
        "km": 150,
        "url": "https://pilegrimsleden.no/pilegrimsledene/valldalsleden",
        "folder": "Norway/Valldalsleden",
        "status": "extracted",
    },
    {
        "name": "Østerdalsleden",
        "from": "Trysil/Rena",
        "to": "Trondheim",
        "km": 320,
        "url": "https://pilegrimsleden.no/pilegrimsledene/osterdalsleden",
        "folder": "Norway/Osterdalsleden",
        "status": "extracted",
    },
    {
        "name": "Romboleden",
        "folder": "Norway/Romboleden",
        "status": "extracted",
        "note": "Shared SE/NO",
    },
    {
        "name": "Romeriksleden",
        "folder": "Norway/Romeriksleden",
        "status": "extracted",
        "note": "Gudbrandsdalsleden east (OSM relation 1200009)",
    },
]


def write_catalog(extra: list[dict]) -> None:
    catalog = {
        "country": "Norway",
        "label": "NORGE",
        "updated": "2026-09-19",
        "notes": [
            "Inventory of Norwegian pilgrim trails for Scandi-pilgrim-poi.",
            "CMS trails use pilegrimsleden.no + OSM route relations.",
            "Extra trails below had no OSM route relation; extracted from GPX or waypoints.",
        ],
        "trails": EXISTING_CMS + extra,
    }
    out = ROOT / "data" / "norway" / "trails_catalog.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {out}")


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    BY_TRAIL.mkdir(parents=True, exist_ok=True)
    extra = [
        extract_kvite(),
        extract_glamdalsleden(),
        extract_valdres(),
        extract_roldal(),
        extract_sunnivaleia(),
    ]
    write_catalog(extra)
    log("Done.")
    for e in extra:
        log(
            f"  {e['folder']}: path_points={e['path_points']} pois={e['pois']} "
            f"source={e['path_source']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
