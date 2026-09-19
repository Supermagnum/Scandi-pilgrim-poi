#!/usr/bin/env python3
"""Extract Denmark / Finland pilgrim trails missing a full OSM route relation.

Writes:
  data/by_trail/Denmark/...
  data/by_trail/Finland/...
  data/denmark/trails_catalog.json
  data/finland/trails_catalog.json

OSM check (Nominatim + API, 2026-09):
  - Hærvejen: partial OSM route (e.g. relation/13278515 Viborg–Skelhøje) — catalog only
  - Pyhän Henrikin tie (Saint Henry's way): relation/8833791 → Finland/Saint-Henrys-way
  - Others: no full route relation found — research extracts below
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(OSM mapping research; Denmark/Finland pilgrim trails; "
    "+https://github.com/Supermagnum/Scandi-pilgrim-poi)"
)

ROOT = Path(__file__).resolve().parent
BY_TRAIL = ROOT / "data" / "by_trail"


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


def http_get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_json(url: str, timeout: int = 120) -> object:
    return json.loads(http_get(url, timeout=timeout).decode("utf-8"))


def thin_points(points: list[tuple[float, float]], max_points: int = 5000) -> list[tuple[float, float]]:
    if len(points) <= max_points:
        return points
    step = math.ceil(len(points) / max_points)
    out = points[::step]
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def nominatim_search(query: str, country: str | None) -> tuple[float, float] | None:
    params: dict[str, str | int] = {"q": query, "format": "jsonv2", "limit": 1}
    if country:
        params["countrycodes"] = country
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    hits = http_json(url)
    assert isinstance(hits, list)
    if not hits:
        return None
    return float(hits[0]["lat"]), float(hits[0]["lon"])


def geocode(
    items: list[tuple[str, str, str]], country: str
) -> list[dict[str, str | float]]:
    out: list[dict[str, str | float]] = []
    for name, query, poi_type in items:
        log(f"  geocode: {name}")
        try:
            coords = nominatim_search(query, country)
        except Exception as exc:
            log(f"    FAIL {exc}")
            coords = None
        time.sleep(1.1)
        if not coords:
            log("    no hit")
            continue
        lat, lon = coords
        out.append({"name": name, "type": poi_type, "lat": lat, "lon": lon})
    return out


TYPE_TAGS = {
    "church": [("amenity", "place_of_worship"), ("religion", "christian")],
    "lodging": [("tourism", "guest_house")],
    "camping": [("tourism", "camp_site")],
    "attraction": [("tourism", "attraction")],
    "waypoint": [("tourism", "yes")],
    "place": [("place", "town")],
    "pilgrim_center": [
        ("tourism", "information"),
        ("information", "office"),
        ("pilgrimage", "stamp_office"),
    ],
}


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


def write_trail_osm(
    path: Path,
    trail_name: str,
    country: str,
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
            ("note:trail", trail_name),
            ("note:country", country),
            ("source", source_url),
        ]:
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        if "waypoint" in extra_note.lower():
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
        lines.append(f"    <tag k='note:country' v='{xml_escape(country)}'/>")
        lines.append(f"    <tag k='source' v='{xml_escape(source_url)}'/>")
        for key, value in TYPE_TAGS.get(typ, [("tourism", "yes")]):
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </node>")
        role = "lodging" if typ in {"lodging", "camping"} else "poi"
        member_ids.append(("node", next_id, role))
        next_id -= 1

    rel_id = next_id
    lines.append(f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>")
    for mtype, mid, role in member_ids:
        lines.append(f"    <member type='{mtype}' ref='{mid}' role='{xml_escape(role)}'/>")
    note = f"Local JOSM research file for {trail_name}. {extra_note} Source {source_url}"
    for key, value in [
        ("type", "site"),
        ("name", trail_name),
        ("note:trail", trail_name),
        ("note:country", country),
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
    lines.extend(["", "## Files", "", "- `trail.osm`", "- `hiking_path.gpx` (if present)", "- `README.md`", ""])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_dir(country: str, slug: str) -> Path:
    d = BY_TRAIL / country / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_catalog(country_key: str, label: str, trails: list[dict]) -> None:
    out = ROOT / "data" / country_key / "trails_catalog.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "country": label,
        "updated": "2026-09-19",
        "trails": trails,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {out}")


def extract_waypoint_trail(
    *,
    country_folder: str,
    country_code: str,
    name: str,
    slug: str,
    source_url: str,
    waypoints: list[tuple[str, str, str]],
    notes: list[str],
    km: float | int | str | None,
) -> dict:
    trail_dir = ensure_dir(country_folder, slug)
    log(f"=== {name}")
    pois = geocode(waypoints, country_code)
    points = [(float(p["lat"]), float(p["lon"])) for p in pois] if len(pois) >= 2 else []
    if points:
        write_gpx(trail_dir / "hiking_path.gpx", name, points)
    write_trail_osm(
        trail_dir / "trail.osm",
        name,
        country_folder,
        source_url,
        points,
        pois,
        "Research waypoints geocoded from documented places; "
        "no public continuous official GPX was available.",
    )
    write_readme(
        trail_dir / "README.md",
        name,
        f"{country_folder}/{slug}",
        source_url,
        len(points),
        pois,
        notes
        + [
            "No full OSM hiking/pilgrimage route relation found (2026-09).",
            "Path (if present) only connects documented waypoints — replace with official GPX when published.",
        ],
    )
    return {
        "name": name,
        "folder": f"{country_folder}/{slug}",
        "km": km,
        "url": source_url,
        "status": "extracted_waypoints",
        "path_points": len(points),
        "pois": len(pois),
    }


def extract_way_of_jacob() -> dict:
    name = "The way of Jacob (Jaakontie)"
    slug = "Way-of-Jacob"
    source = "https://citynomadi.com/route/cf992911d8c170ddf1db528b8cdafcf7"
    api = "https://citynomadi.com/api/route/cf992911d8c170ddf1db528b8cdafcf7"
    trail_dir = ensure_dir("Finland", slug)
    log(f"=== {name}")
    data = http_json(api)
    assert isinstance(data, dict)
    path_pts: list[tuple[float, float]] = []
    pois: list[dict[str, str | float]] = []
    for layer in data.get("layers") or []:
        for gi in layer.get("geoItems") or []:
            coords = gi.get("coordinates") or []
            info = gi.get("info") or []
            title = ""
            if isinstance(info, list):
                for it in info:
                    if it.get("lang") in ("fi", "en", "de") and it.get("title"):
                        title = it["title"]
                        break
                if not title and info:
                    title = info[0].get("title") or ""
            if gi.get("type") == "track":
                for c in coords:
                    if isinstance(c, dict) and "lat" in c:
                        path_pts.append((float(c["lat"]), float(c["lon"])))
            elif gi.get("type") == "poi" and coords:
                c = coords[0]
                typ = "church" if "kirkko" in title.lower() or "kirk" in title.lower() else "waypoint"
                pois.append(
                    {
                        "name": title or "POI",
                        "type": typ,
                        "lat": float(c["lat"]),
                        "lon": float(c["lon"]),
                    }
                )
    points = thin_points(path_pts, max_points=6000)
    length = ((data.get("has") or {}).get("geoItems") or {}).get("length")
    write_gpx(trail_dir / "hiking_path.gpx", name, points)
    write_trail_osm(
        trail_dir / "trail.osm",
        name,
        "Finland",
        source,
        points,
        pois,
        "Path + POIs from Citynomadi route API (Jaakontie Renko–Rymättylä).",
    )
    write_readme(
        trail_dir / "README.md",
        name,
        f"Finland/{slug}",
        source,
        len(points),
        pois,
        [
            f"Citynomadi reported length ~{length} km (Renko/Hattula → Rymättylä).",
            "No OSM hiking route relation found under this name (2026-09).",
            f"API: {api}",
        ],
    )
    return {
        "name": name,
        "folder": f"Finland/{slug}",
        "from": "Renko",
        "to": "Rymättylä",
        "km": 250,
        "url": source,
        "status": "extracted",
        "path_source": "citynomadi_api",
        "path_points": len(points),
        "pois": len(pois),
    }


def extract_saint_henrys_way() -> dict:
    """Path from OSM relation 8833791 (Pyhän Henrikin tie)."""
    name = "Saint Henry's way"
    slug = "Saint-Henrys-way"
    source = "https://henrikinvaellus.fi/pyhan-henrikin-tie--in-english-"
    osm_rel = 8833791
    trail_dir = ensure_dir("Finland", slug)
    log(f"=== {name} (OSM relation/{osm_rel})")
    data = http_json(f"https://api.openstreetmap.org/api/0.6/relation/{osm_rel}/full.json")
    assert isinstance(data, dict)
    nodes: dict[int, tuple[float, float]] = {}
    ways: dict[int, dict] = {}
    rel = None
    for el in data.get("elements") or []:
        if el["type"] == "node":
            nodes[el["id"]] = (float(el["lat"]), float(el["lon"]))
        elif el["type"] == "way":
            ways[el["id"]] = el
        elif el["type"] == "relation" and el["id"] == osm_rel:
            rel = el
    if not rel:
        raise RuntimeError(f"OSM relation/{osm_rel} not in full download")
    points: list[tuple[float, float]] = []
    for m in rel.get("members") or []:
        if m.get("type") != "way":
            continue
        w = ways.get(m["ref"])
        if not w:
            continue
        coords = [nodes[n] for n in (w.get("nodes") or []) if n in nodes]
        if not coords:
            continue
        if (m.get("role") or "") == "backward":
            coords = list(reversed(coords))
        if points and coords:
            la, lo = points[-1]
            d0 = (coords[0][0] - la) ** 2 + (coords[0][1] - lo) ** 2
            d1 = (coords[-1][0] - la) ** 2 + (coords[-1][1] - lo) ** 2
            if d1 < d0:
                coords = list(reversed(coords))
            if coords[0] == points[-1]:
                coords = coords[1:]
        points.extend(coords)
    points = thin_points(points, max_points=6000)
    pois = geocode(
        [
            ("Turun tuomiokirkko", "Turun tuomiokirkko", "church"),
            ("Nousiainen", "Nousiaisten kirkko", "church"),
            ("Lieto", "Liedon kirkko", "church"),
            ("Pänttilänniemi", "Pänttilänniemi", "place"),
        ],
        "fi",
    )
    write_gpx(trail_dir / "hiking_path.gpx", name, points)
    write_trail_osm(
        trail_dir / "trail.osm",
        name,
        "Finland",
        source,
        points,
        pois,
        f"Path densified from OSM hiking relation/{osm_rel} (Pyhän Henrikin tie).",
    )
    write_readme(
        trail_dir / "README.md",
        name,
        f"Finland/{slug}",
        source,
        len(points),
        pois,
        [
            "Also known as Pyhän Henrikin tie (Åbo/Turku → Pänttilänniemi), about 140 km.",
            f"Path from OSM relation/{osm_rel} for local review.",
            f"Official site: {source}",
        ],
    )
    return {
        "name": "Saint Henry's way (Pyhän Henrikin tie)",
        "folder": f"Finland/{slug}",
        "from": "Åbo / Turku",
        "to": "Pänttilänniemi",
        "km": 140,
        "url": source,
        "status": "extracted",
        "osm_relation": osm_rel,
        "path_points": len(points),
        "pois": len(pois),
    }


def main() -> int:
    BY_TRAIL.mkdir(parents=True, exist_ok=True)

    danske = extract_waypoint_trail(
        country_folder="Denmark",
        country_code="dk",
        name="Den danske Pilgrimsrute",
        slug="Den-danske-Pilgrimsrute",
        source_url="https://santiagopilgrimme.dk/find-ruter/ruter-i-danmark/",
        km=None,
        waypoints=[
            ("Hirtshals", "Hirtshals", "place"),
            ("Aalborg", "Aalborg", "place"),
            ("Viborg Domkirke", "Viborg Domkirke", "church"),
            ("Viborg Pilgrimscentrum", "Viborg", "place"),
            ("Jelling", "Jelling kirke", "church"),
            ("Padborg", "Padborg", "place"),
        ],
        notes=[
            "Network / association page at santiagopilgrimme.dk (links Hærvejen and regional routes).",
            "No single OSM route relation for 'Den danske Pilgrimsrute' found.",
        ],
    )

    denmark_catalog = [
        {
            "name": "Den danske Pilgrimsrute",
            "url": "https://santiagopilgrimme.dk/",
            "folder": danske["folder"],
            "status": danske["status"],
            "path_points": danske["path_points"],
            "pois": danske["pois"],
        },
        {
            "name": "Hærvejen",
            "km": 645,
            "url": "https://haervej.dk/vandring",
            "status": "in_osm_partial",
            "osm_relation": 13278515,
            "note": (
                "At least one stage route exists in OSM "
                "(relation/13278515 Viborg–Skelhøje, 17.7 km). "
                "Full 645 km not duplicated as a research extract."
            ),
        },
    ]

    ostro = extract_waypoint_trail(
        country_folder="Finland",
        country_code="fi",
        name="St Olav Ostrobothnia",
        slug="St-Olav-Ostrobothnia",
        source_url="https://stolavostrobothnia.fi/",
        km=500,
        waypoints=[
            ("Vaasa", "Vaasa", "place"),
            ("Nykarleby", "Nykarleby", "place"),
            ("Jakobstad / Pietarsaari", "Jakobstad", "place"),
            ("Kokkola", "Kokkola", "place"),
            ("Kalajoki", "Kalajoki", "place"),
        ],
        notes=["~500 km Ostrobothnia St Olav route. No OSM route relation found."],
    )
    oulu = extract_waypoint_trail(
        country_folder="Finland",
        country_code="fi",
        name="Oulujoki pilgrimage",
        slug="Oulujoki-pilgrimage",
        source_url="https://oulunseurakunnat.fi/",
        km=113,
        waypoints=[
            ("Oulu tuomiokirkko", "Oulun tuomiokirkko", "church"),
            ("Oulujoki", "Oulujoki Oulu", "place"),
            ("Muhos", "Muhos kirkko", "church"),
            ("Utajärvi", "Utajärvi", "place"),
            ("Vaala", "Vaala", "place"),
        ],
        notes=[
            "Oulu → Vaala ~113 km (Oulujoen pyhiinvaellus).",
            "Listed deep URL returned 404 at extract time; using parish site root.",
        ],
    )

    log("=== St. Olav Waterway")
    waterway_dir = ensure_dir("Finland", "St-Olav-Waterway")
    waterway_pois = geocode(
        [
            ("Turku Cathedral", "Turun tuomiokirkko", "church"),
            ("Naantali", "Naantali", "place"),
            ("Mariehamn", "Mariehamn", "place"),
        ],
        "fi",
    )
    g = nominatim_search("Grisslehamn", "se")
    time.sleep(1.1)
    if g:
        waterway_pois.append(
            {"name": "Grisslehamn", "type": "place", "lat": g[0], "lon": g[1]}
        )
    else:
        log("  Grisslehamn: no hit")
    waterway_points = [(float(p["lat"]), float(p["lon"])) for p in waterway_pois]
    waterway_name = "St. Olav Waterway"
    waterway_url = "https://stolavwaterway.com/"
    write_gpx(waterway_dir / "hiking_path.gpx", waterway_name, waterway_points)
    write_trail_osm(
        waterway_dir / "trail.osm",
        waterway_name,
        "Finland",
        waterway_url,
        waterway_points,
        waterway_pois,
        "Research waypoints (FI+Åland+SE). No full OSM route relation found.",
    )
    write_readme(
        waterway_dir / "README.md",
        waterway_name,
        "Finland/St-Olav-Waterway",
        waterway_url,
        len(waterway_points),
        waterway_pois,
        [
            "Åbo/Turku → Grisslehamn via Åland.",
            "No full OSM route relation found (some guideposts exist).",
        ],
    )
    waterway = {
        "name": waterway_name,
        "folder": "Finland/St-Olav-Waterway",
        "status": "extracted_waypoints",
        "path_points": len(waterway_points),
        "pois": len(waterway_pois),
        "url": waterway_url,
        "from": "Åbo / Turku",
        "to": "Grisslehamn",
    }

    jacob = extract_way_of_jacob()
    henry = extract_saint_henrys_way()

    finland_catalog = [
        {
            "name": "St Olav Ostrobothnia",
            "km": 500,
            "url": "https://stolavostrobothnia.fi/",
            "folder": ostro["folder"],
            "status": ostro["status"],
            "path_points": ostro["path_points"],
            "pois": ostro["pois"],
        },
        {
            "name": "Oulujoki pilgrimage",
            "from": "Oulu",
            "to": "Vaala",
            "km": 113,
            "url": "https://oulunseurakunnat.fi/",
            "folder": oulu["folder"],
            "status": oulu["status"],
            "path_points": oulu["path_points"],
            "pois": oulu["pois"],
        },
        {
            "name": henry["name"],
            "from": henry["from"],
            "to": henry["to"],
            "km": henry["km"],
            "url": henry["url"],
            "folder": henry["folder"],
            "status": henry["status"],
            "osm_relation": henry["osm_relation"],
            "path_points": henry["path_points"],
            "pois": henry["pois"],
        },
        {
            "name": "St. Olav Waterway",
            "from": "Åbo / Turku",
            "to": "Grisslehamn",
            "url": waterway_url,
            "folder": waterway["folder"],
            "status": waterway["status"],
            "path_points": waterway["path_points"],
            "pois": waterway["pois"],
        },
        {
            "name": "The way of Jacob",
            "from": "Renko",
            "to": "Rymättylä",
            "km": 250,
            "url": "https://citynomadi.com/route/cf992911d8c170ddf1db528b8cdafcf7",
            "folder": jacob["folder"],
            "status": jacob["status"],
            "path_points": jacob["path_points"],
            "pois": jacob["pois"],
        },
    ]

    write_catalog("denmark", "Denmark", denmark_catalog)
    write_catalog("finland", "Finland", finland_catalog)
    log("Done.")
    for row in denmark_catalog + finland_catalog:
        log(
            f"  {row.get('folder') or row['name']}: status={row.get('status')} "
            f"path={row.get('path_points', '—')} pois={row.get('pois', '—')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
