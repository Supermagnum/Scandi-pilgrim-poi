#!/usr/bin/env python3
"""Extract Pilgrimsleden Västra Värmland path + POIs from Svenska kyrkan KMZ.

Sources (Arvika pastorat / svenskakyrkan.se):
  path KMZ: https://www.svenskakyrkan.se/default.aspx?id=1148827
  POI KMZ:  https://www.svenskakyrkan.se/default.aspx?id=1148829
  page:     https://www.svenskakyrkan.se/arvika/pilgrim

Writes data/by_trail/Sweden/Pilgrimsleden-Vastra-Varmland/
  trail.osm, hiking_path.gpx, README.md
"""

from __future__ import annotations

import io
import math
import re
import sys
import urllib.request
import zipfile
from html import unescape
from pathlib import Path
from xml.etree import ElementTree as ET

USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(OSM mapping research; Pilgrimsleden Västra Värmland; "
    "+https://github.com/Supermagnum/Scandi-pilgrim-poi)"
)
PATH_KMZ_URL = "https://www.svenskakyrkan.se/default.aspx?id=1148827"
POI_KMZ_URL = "https://www.svenskakyrkan.se/default.aspx?id=1148829"
TRAIL_NAME = "Pilgrimsleden Västra Värmland"
TRAIL_FOLDER = "Sweden/Pilgrimsleden-Vastra-Varmland"
PAGE_URL = "https://www.svenskakyrkan.se/arvika/pilgrim"

# Svenska kyrkan Typ -> OSM-ish tags for local research file
TYPE_TAGS: dict[str, list[tuple[str, str]]] = {
    "Boende": [("tourism", "guest_house")],
    "Kyrka": [("amenity", "place_of_worship"), ("religion", "christian")],
    "Servering": [("amenity", "cafe")],
    "Mataffär": [("shop", "convenience")],
    "Hembygdsgård": [("tourism", "museum")],
    "Sevärdhet": [("tourism", "attraction")],
    "Badplats": [("leisure", "bathing_place")],
}


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


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def kmz_doc_kml(blob: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        return zf.read("doc.kml").decode("utf-8", errors="replace")


def strip_kml_ns(root: ET.Element) -> None:
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]


def parse_path_points(kml_text: str) -> list[tuple[float, float]]:
    root = ET.fromstring(kml_text)
    strip_kml_ns(root)
    points: list[tuple[float, float]] = []
    for coords in root.findall(".//LineString/coordinates"):
        raw = (coords.text or "").replace("\n", " ")
        for token in raw.split():
            parts = token.split(",")
            if len(parts) < 2:
                continue
            lon, lat = float(parts[0]), float(parts[1])
            if points and points[-1] == (lat, lon):
                continue
            points.append((lat, lon))
    return points


def parse_table_field(html: str, label: str) -> str:
    m = re.search(
        rf"<td>\s*{re.escape(label)}\s*</td>\s*<td>([^<]*)</td>",
        html,
        re.I,
    )
    return unescape(m.group(1).strip()) if m else ""


def parse_pois(kml_text: str) -> list[dict[str, str | float]]:
    root = ET.fromstring(kml_text)
    strip_kml_ns(root)
    pois: list[dict[str, str | float]] = []
    for pm in root.findall(".//Placemark"):
        name_el = pm.find("name")
        name = (name_el.text or "").strip() if name_el is not None else ""
        if not name or name in {"Intressepunkter", "0"}:
            # Prefer Namn from description table when present
            pass
        desc_el = pm.find("description")
        desc = desc_el.text or "" if desc_el is not None else ""
        namn = parse_table_field(desc, "Namn") or name
        typ = parse_table_field(desc, "Typ")
        coords_el = pm.find(".//Point/coordinates")
        if coords_el is None or not (coords_el.text or "").strip():
            continue
        parts = (coords_el.text or "").strip().split(",")
        lon, lat = float(parts[0]), float(parts[1])
        if not namn or namn == "Intressepunkter":
            continue
        pois.append(
            {
                "name": namn,
                "type": typ or "Sevärdhet",
                "lat": lat,
                "lon": lon,
            }
        )
    return pois


def thin_points(points: list[tuple[float, float]], max_points: int = 5000) -> list[tuple[float, float]]:
    """Keep path shape; thin only if the KMZ geometry is very dense."""
    if len(points) <= max_points:
        return points
    step = math.ceil(len(points) / max_points)
    out = points[::step]
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def write_gpx(path: Path, points: list[tuple[float, float]]) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="pilegrimsleden-osm-extractor 1.0" '
        'xmlns="http://www.topografix.com/GPX/1/1">',
        f"  <trk><name>{xml_escape(TRAIL_NAME)}</name><trkseg>",
    ]
    for lat, lon in points:
        lines.append(f'    <trkpt lat="{lat:.7f}" lon="{lon:.7f}"></trkpt>')
    lines.extend(["  </trkseg></trk>", "</gpx>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_trail_osm(
    path: Path, points: list[tuple[float, float]], pois: list[dict[str, str | float]]
) -> None:
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    next_id = -1
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
        ("name", TRAIL_NAME),
        ("network", "Pilgrimsleder Sverige"),
        ("note:trail", TRAIL_NAME),
        ("note:country", "Sweden"),
        ("source", PAGE_URL),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </way>")
    next_id -= 1

    member_ids: list[tuple[str, int, str]] = [("way", way_id, "path")]
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
        lines.append(f"    <tag k='note:trail' v='{xml_escape(TRAIL_NAME)}'/>")
        lines.append("    <tag k='note:country' v='Sweden'/>")
        lines.append(f"    <tag k='source' v='{xml_escape(PAGE_URL)}'/>")
        for key, value in TYPE_TAGS.get(typ, [("tourism", "yes")]):
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        if typ == "Boende":
            lines.append("    <tag k='note:lodging' v='yes'/>")
        lines.append("  </node>")
        role = "lodging" if typ == "Boende" else "poi"
        member_ids.append(("node", next_id, role))
        next_id -= 1

    rel_id = next_id
    lines.append(f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>")
    for mtype, mid, role in member_ids:
        lines.append(
            f"    <member type='{mtype}' ref='{mid}' role='{xml_escape(role)}'/>"
        )
    for key, value in [
        ("type", "site"),
        ("name", TRAIL_NAME),
        ("network", "Pilgrimsleder Sverige"),
        ("note:trail", TRAIL_NAME),
        ("note:country", "Sweden"),
        (
            "note",
            "Local JOSM research file from Svenska kyrkan KMZ "
            f"(path id=1148827, POI id=1148829). Source {PAGE_URL}",
        ),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </relation>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(path: Path, n_path: int, pois: list[dict[str, str | float]]) -> None:
    from collections import Counter

    counts = Counter(str(p["type"]) for p in pois)
    lodging = [str(p["name"]) for p in pois if p["type"] == "Boende"]
    lines = [
        f"# {TRAIL_NAME}",
        "",
        f"Folder: `{TRAIL_FOLDER}`",
        "",
        "## Open in JOSM",
        "",
        "Open `trail.osm` in this folder (the only `.osm` file).",
        "",
        "It contains:",
        "",
        "1. Trail **path** from Svenska kyrkan KMZ (id=1148827)",
        "2. **Interest POIs** from KMZ (id=1148829), including lodging (`Boende`)",
        "",
        f"Page: {PAGE_URL}",
        "",
        "## Counts",
        "",
        "| item | count |",
        "| --- | ---: |",
        f"| Path points (densified) | {n_path} |",
        f"| POIs | {len(pois)} |",
    ]
    for typ, n in sorted(counts.items()):
        lines.append(f"| POI type {typ} | {n} |")
    lines.extend(["", "## Lodging (Boende)", ""])
    for name in lodging:
        lines.append(f"- {name}")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `trail.osm` — open this in JOSM",
            "- `hiking_path.gpx` — path cache",
            "- `README.md` — this file",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parent
    trail_dir = root / "data" / "by_trail" / "Sweden" / "Pilgrimsleden-Vastra-Varmland"
    trail_dir.mkdir(parents=True, exist_ok=True)
    cache = root / "data" / "sweden" / "vastra_varmland"
    cache.mkdir(parents=True, exist_ok=True)

    log("Downloading path KMZ…")
    path_blob = http_get(PATH_KMZ_URL)
    (cache / "path.kmz").write_bytes(path_blob)
    log("Downloading POI KMZ…")
    poi_blob = http_get(POI_KMZ_URL)
    (cache / "pois.kmz").write_bytes(poi_blob)

    path_kml = kmz_doc_kml(path_blob)
    poi_kml = kmz_doc_kml(poi_blob)
    (cache / "path.kml").write_text(path_kml, encoding="utf-8")
    (cache / "pois.kml").write_text(poi_kml, encoding="utf-8")

    raw_points = parse_path_points(path_kml)
    log(f"Raw path points: {len(raw_points)}")
    points = thin_points(raw_points, max_points=5000)
    log(f"Path points used: {len(points)}")
    pois = parse_pois(poi_kml)
    log(f"POIs: {len(pois)}")

    write_gpx(trail_dir / "hiking_path.gpx", points)
    write_trail_osm(trail_dir / "trail.osm", points, pois)
    write_readme(trail_dir / "README.md", len(points), pois)
    log(f"Wrote {trail_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
