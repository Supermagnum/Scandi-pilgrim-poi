#!/usr/bin/env python3
"""Build data/by_trail/Romeriksleden from OSM relation 1200009.

Model (read-only w.r.t. OpenStreetMap):
1. Load OSM route relation 1200009 as source of truth for the trail geometry
   and for which objects are *already* members of that relation.
2. Discover lodging/shelter OSM objects near the route (Geofabrik PBF).
3. Partition them into:
   - already related: already members of relation 1200009 → leave alone
     (never modify existing OSM relations);
   - missing: near the route but not members → propose as local research
     additions only (negative-id relation + real OSM ids for visualization).
4. CMS overnight POIs (Gudbrandsdalsleden trailpoints within BUFFER_M) are
   matched for comparison; unmapped CMS gaps become proposed new nodes.

Does not upload or modify OpenStreetMap.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from extract_pilegrimsleden_shelters import (
    CATEGORY_PRIORITY,
    CORE_SHELTER_CATEGORIES,
    RASTEPLASS,
    osm_tags_for_category,
    primary_category,
)
from extract_stolavsleden import haversine_m, xml_escape

USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(OSM mapping research; Romeriksleden corridor extract; "
    "+https://github.com/Supermagnum/Scandi-pilgrim-poi)"
)
RELATION_ID = 1200009
RELATION_URL = f"https://www.openstreetmap.org/relation/{RELATION_ID}"
OSM_FULL_URL = f"https://www.openstreetmap.org/api/0.6/relation/{RELATION_ID}/full"
TRAILPOINTS_URL = (
    "https://www.pilegrimsleden.no/actions/pilegrimsleden/poi/trailpoints?trail=212"
)
BUFFER_M = 2000.0
SOURCE_TRAIL = "Gudbrandsdalsleden"
TRAIL_NAME = "Romeriksleden"
TRAIL_MEMBERSHIP = [SOURCE_TRAIL, TRAIL_NAME]


PROPOSED_ADDITION = "Proposed addition"


def proposal_note_for_existing_osm(osm_id: str = "") -> str:
    """Existing OSM lodging is not a new POI; no note:proposed on CMS matched rows."""
    return ""


def proposal_note_for_cms_gap() -> str:
    """Per-POI tag value for a CMS overnight POI with no OSM match."""
    return PROPOSED_ADDITION


# Overnight / shelter categories on the CMS map (trailpoints `cs` list).
OVERNIGHT_CATEGORIES = CORE_SHELTER_CATEGORIES | {
    "Overnatting",
    RASTEPLASS,
}
# Bare picnic benches etc. — only keep if already in the national shelter extract.
WEAK_ONLY = {RASTEPLASS, "Naturområde", "Sted", "Kulturminne", "Spisested", "Matbutikk", "Aktivitet"}


def log(message: str) -> None:
    print(message, flush=True)


def fetch_relation_geometry() -> tuple[
    dict[str, Any],
    list[list[tuple[float, float]]],
    set[tuple[str, int]],
]:
    """Download relation+members; return tags, ordered way polylines, member set.

    Member set is every (type, id) currently on OSM relation RELATION_ID.
    Those objects are treated as already related — never modified.
    """
    log(f"Downloading {OSM_FULL_URL}")
    req = urllib.request.Request(OSM_FULL_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as resp:
        xml_text = resp.read().decode("utf-8")
    root = ET.fromstring(xml_text)
    nodes: dict[str, tuple[float, float]] = {}
    for node in root.findall("node"):
        nodes[node.attrib["id"]] = (float(node.attrib["lat"]), float(node.attrib["lon"]))
    ways: dict[str, list[tuple[float, float]]] = {}
    for way in root.findall("way"):
        pts: list[tuple[float, float]] = []
        for nd in way.findall("nd"):
            ref = nd.attrib["ref"]
            if ref in nodes:
                pts.append(nodes[ref])
        if len(pts) >= 2:
            ways[way.attrib["id"]] = pts
    rel_el = root.find("relation")
    if rel_el is None:
        raise RuntimeError("relation element missing from OSM API response")
    tags = {tag.attrib["k"]: tag.attrib["v"] for tag in rel_el.findall("tag")}
    members: set[tuple[str, int]] = set()
    for member in rel_el.findall("member"):
        mtype = member.attrib.get("type") or ""
        try:
            mid = int(member.attrib["ref"])
        except (KeyError, ValueError):
            continue
        members.add((mtype, mid))
    segments: list[list[tuple[float, float]]] = []
    skipped_roles: dict[str, int] = {}
    for member in rel_el.findall("member"):
        if member.attrib.get("type") != "way":
            continue
        role = (member.attrib.get("role") or "").strip()
        if role and role not in {"main", "forward", "backward"}:
            skipped_roles[role] = skipped_roles.get(role, 0) + 1
            continue
        pts = ways.get(member.attrib["ref"])
        if pts:
            if role == "backward":
                pts = list(reversed(pts))
            segments.append(pts)
    if skipped_roles:
        log(f"Skipped non-main member roles for geometry stitch: {skipped_roles}")
    if not segments:
        raise RuntimeError("no member ways with resolvable geometry")
    log(
        f"OSM relation {RELATION_ID} existing members: {len(members)} "
        f"(nodes={sum(1 for t,_ in members if t=='node')}, "
        f"ways={sum(1 for t,_ in members if t=='way')}, "
        f"relations={sum(1 for t,_ in members if t=='relation')})"
    )
    return {"id": RELATION_ID, "tags": tags}, segments, members


def stitch_points(segments: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    if not segments:
        return []
    out: list[tuple[float, float]] = list(segments[0])
    for seg in segments[1:]:
        if not seg:
            continue
        if out and haversine_m(out[-1][0], out[-1][1], seg[-1][0], seg[-1][1]) < haversine_m(
            out[-1][0], out[-1][1], seg[0][0], seg[0][1]
        ):
            seg = list(reversed(seg))
        if out and seg and out[-1] == seg[0]:
            out.extend(seg[1:])
        else:
            out.extend(seg)
    return out


def densify_for_index(
    points: list[tuple[float, float]], step_m: float = 75.0
) -> list[tuple[float, float]]:
    if len(points) < 2:
        return list(points)
    out: list[tuple[float, float]] = [points[0]]
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:]):
        dist = haversine_m(lat1, lon1, lat2, lon2)
        if dist <= step_m:
            out.append((lat2, lon2))
            continue
        n = max(1, int(math.ceil(dist / step_m)))
        for i in range(1, n + 1):
            t = i / n
            out.append((lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t))
    return out


def min_dist_m(lat: float, lon: float, route: list[tuple[float, float]]) -> float:
    best = float("inf")
    for rlat, rlon in route:
        d = haversine_m(lat, lon, rlat, rlon)
        if d < best:
            best = d
    return best


def simplify_points(
    points: list[tuple[float, float]], max_points: int = 4000
) -> list[tuple[float, float]]:
    if len(points) <= max_points:
        return points
    step = math.ceil(len(points) / max_points)
    simplified = points[::step]
    if simplified[-1] != points[-1]:
        simplified.append(points[-1])
    return simplified


def write_hiking_gpx(path: Path, points: list[tuple[float, float]]) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="pilegrimsleden-osm-extractor 1.0" '
        'xmlns="http://www.topografix.com/GPX/1/1">',
        "  <metadata>",
        f"    <name>{TRAIL_NAME}</name>",
        f"    <desc>Derived from OSM relation {RELATION_ID}; research aid</desc>",
        f'    <link href="{RELATION_URL}"/>',
        "  </metadata>",
        f"  <trk><name>{TRAIL_NAME}</name><trkseg>",
    ]
    for lat, lon in points:
        lines.append(f'    <trkpt lat="{lat:.7f}" lon="{lon:.7f}"></trkpt>')
    lines.extend(["  </trkseg></trk>", "</gpx>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_hiking_osm(path: Path, points: list[tuple[float, float]]) -> int:
    """Write path-only OSM; returns the negative way id used."""
    points = simplify_points(points, max_points=4000)
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    node_ids: list[int] = []
    for index, (lat, lon) in enumerate(points, start=1):
        node_id = -index
        node_ids.append(node_id)
        lines.append(
            f"  <node id='{node_id}' version='0' action='modify' visible='true' "
            f"lat='{lat:.7f}' lon='{lon:.7f}'/>"
        )
    way_id = -(len(points) + 1)
    lines.append(f"  <way id='{way_id}' version='0' action='modify' visible='true'>")
    for node_id in node_ids:
        lines.append(f"    <nd ref='{node_id}'/>")
    tags = [
        ("name", TRAIL_NAME),
        ("alt_name", "Pilegrimsleden over Romerike"),
        ("route", "hiking"),
        ("pilgrimage", "yes"),
        ("network", "Pilegrimsleden"),
        ("note:trail", "; ".join(TRAIL_MEMBERSHIP)),
        ("source", f"openstreetmap.org/relation/{RELATION_ID}"),
        (
            "note",
            "Derived from OSM relation 1200009 for JOSM comparison; "
            "research aid, not an OSM import",
        ),
    ]
    for key, value in tags:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </way>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return way_id


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def fetch_trailpoints() -> list[dict[str, Any]]:
    log(f"Fetching {TRAILPOINTS_URL}")
    req = urllib.request.Request(TRAILPOINTS_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("unexpected trailpoints payload")
    return data


def is_corridor_overnight(cs: set[str], in_national_shelter: bool) -> bool:
    if not (cs & OVERNIGHT_CATEGORIES):
        return False
    strong = cs & (CORE_SHELTER_CATEGORIES | {"Overnatting"})
    if strong:
        # Skip hotel-only if somehow only Hotell — still allow Overnatting+Hotell.
        return True
    if cs <= WEAK_ONLY:
        return in_national_shelter
    return in_national_shelter


def category_label(cs: list[str]) -> str:
    rank = {name: index for index, name in enumerate(CATEGORY_PRIORITY)}
    ranked = [c for c in cs if c in rank]
    if ranked:
        return min(ranked, key=lambda c: rank[c])
    if "Overnatting" in cs:
        return "Overnatting"
    return cs[0] if cs else "Overnatting"


def load_match_index(data: Path) -> dict[str, dict[str, str]]:
    """Map pilegrimsleden id / rounded coords -> comparison row."""
    by_id: dict[str, dict[str, str]] = {}
    by_coord: dict[tuple[float, float], dict[str, str]] = {}
    path = data / "by_trail" / SOURCE_TRAIL / "shelters.csv"
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            by_coord[(round(float(row["lat"]), 7), round(float(row["lon"]), 7))] = row
    # ids from raw extract
    raw = json.loads((data / "pilegrimsleden_shelters_raw.json").read_text(encoding="utf-8"))
    for poi in raw.get("pois") or []:
        key = (round(float(poi["lat"]), 7), round(float(poi["lon"]), 7))
        if key in by_coord:
            by_id[str(poi["id"])] = by_coord[key]
    return by_id


def select_corridor_pois(
    trailpoints: list[dict[str, Any]],
    route: list[tuple[float, float]],
    data: Path,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    national_coords: set[tuple[float, float]] = set()
    with (data / "by_trail" / SOURCE_TRAIL / "shelters.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            national_coords.add((round(float(row["lat"]), 7), round(float(row["lon"]), 7)))
    match_by_id = load_match_index(data)
    match_by_coord = {
        (round(float(v["lat"]), 7), round(float(v["lon"]), 7)): v
        for v in match_by_id.values()
    }

    csv_rows: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for poi in trailpoints:
        if poi.get("lt") is None or poi.get("ln") is None:
            continue
        lat, lon = float(poi["lt"]), float(poi["ln"])
        cs = set(poi.get("cs") or [])
        coord = (round(lat, 7), round(lon, 7))
        if not is_corridor_overnight(cs, coord in national_coords):
            continue
        dist = min_dist_m(lat, lon, route)
        if dist > BUFFER_M:
            continue
        pid = str(poi["id"])
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        match = match_by_id.get(pid) or match_by_coord.get(coord) or {}
        categories = list(poi.get("cs") or [])
        if not categories and poi.get("c"):
            categories = [poi["c"]]
        primary = category_label(categories)
        csv_rows.append(
            {
                "trail": TRAIL_NAME,
                "poi_name": poi.get("t") or "",
                "category": " | ".join(categories) if categories else primary,
                "lat": f"{lat:.7f}",
                "lon": f"{lon:.7f}",
                "match_status": match.get("match_status") or "gap",
                "matched_osm_id": match.get("matched_osm_id") or "",
                "matched_osm_url": match.get("matched_osm_url") or "",
                "distance_m": match.get("distance_m") or "",
                "tag_diff": match.get("tag_diff") or "",
                "route_distance_m": f"{dist:.1f}",
                "related_trails": "; ".join(TRAIL_MEMBERSHIP),
                "pilegrimsleden_id": pid,
            }
        )
        records.append(
            {
                "id": pid,
                "title": poi.get("t") or "",
                "url": poi.get("u") or "",
                "categories": categories or [primary],
                "lat": lat,
                "lon": lon,
                "trails": list(TRAIL_MEMBERSHIP),
            }
        )

    csv_rows.sort(
        key=lambda r: (r.get("match_status") or "", (r.get("poi_name") or "").lower())
    )
    # Keep records in same order as csv for stable negative ids
    order = {(r["lat"], r["lon"], r["poi_name"]): i for i, r in enumerate(csv_rows)}
    records.sort(
        key=lambda r: order.get(
            (f"{r['lat']:.7f}", f"{r['lon']:.7f}", r["title"]), 10**9
        )
    )
    return csv_rows, records


def filter_pilgrim_rows(
    rows: list[dict[str, str]], route: list[tuple[float, float]]
) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    for row in rows:
        lat = float(row["lat"])
        lon = float(row["lon"])
        dist = min_dist_m(lat, lon, route)
        if dist <= BUFFER_M:
            copy = dict(row)
            copy["trail"] = TRAIL_NAME
            copy["related_trails"] = "; ".join(TRAIL_MEMBERSHIP)
            kept.append(copy)
    kept.sort(key=lambda r: (r.get("match_status") or "", (r.get("poi_name") or "").lower()))
    return kept


def write_shelters_osm_with_trails(path: Path, records: list[dict[str, Any]]) -> None:
    """Like write_osm but keeps multi-trail note:trail and maps Overnatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    for index, record in enumerate(records, start=1):
        node_id = -index
        lines.append(
            f"  <node id='{node_id}' version='0' action='modify' visible='true' "
            f"lat='{record['lat']:.7f}' lon='{record['lon']:.7f}'>"
        )
        cats = record.get("categories") or []
        primary = primary_category(cats) if any(c in CATEGORY_PRIORITY for c in cats) else (
            "Overnatting" if "Overnatting" in cats else (cats[0] if cats else "")
        )
        if primary == "Overnatting":
            mapping, uncertain = [("tourism", "guest_house")], True
        else:
            mapping, uncertain = osm_tags_for_category(primary)
        tags: list[tuple[str, str]] = [
            ("name", record["title"]),
            ("source", "pilegrimsleden.no"),
            ("url", record.get("url") or ""),
            ("network", "Pilegrimsleden"),
            ("note:trail", "; ".join(record.get("trails") or TRAIL_MEMBERSHIP)),
            ("note:osm_route_relation", str(RELATION_ID)),
            (
                "pilegrimsleden:poi_type",
                ";".join(
                    title
                    for title in cats
                    if title in CORE_SHELTER_CATEGORIES
                    or title in {RASTEPLASS, "Overnatting"}
                )
                or primary,
            ),
            ("pilegrimsleden:id", str(record.get("id") or "")),
        ]
        proposal = (record.get("proposal_note") or "").strip()
        if proposal:
            tags.append(("note:proposed", proposal))
            tags.append(("note", proposal))
        tags.extend(mapping)
        if uncertain:
            tags.append(
                (
                    "note:osm_mapping",
                    f"uncertain OSM equivalent for category {primary}",
                )
            )
        for key, value in tags:
            if not value:
                continue
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </node>")
    if records:
        node_ids = list(range(-1, -len(records) - 1, -1))
        rel_id = min(node_ids) - 1
        lines.append(
            f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>"
        )
        for node_id in node_ids:
            lines.append(f"    <member type='node' ref='{node_id}' role='shelter'/>")
        for key, value in [
            ("type", "site"),
            ("name", f"{TRAIL_NAME} overnight POIs"),
            ("network", "Pilegrimsleden"),
            ("note:trail", TRAIL_NAME),
            ("note:osm_route_relation", str(RELATION_ID)),
            ("source", f"openstreetmap.org/relation/{RELATION_ID}"),
            (
                "note",
                "Local JOSM research relation grouping overnight POIs for this trail; "
                "not an OSM import. Per-POI proposals are in note:proposed on each node.",
            ),
        ]:
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </relation>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_bundle_osm(
    path: Path,
    track: list[tuple[float, float]],
    records: list[dict[str, Any]],
) -> None:
    """Path + POI nodes + local relation linking them (JOSM research file)."""
    track = simplify_points(track, max_points=4000)
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    path_node_ids: list[int] = []
    next_id = -1
    for lat, lon in track:
        path_node_ids.append(next_id)
        lines.append(
            f"  <node id='{next_id}' version='0' action='modify' visible='true' "
            f"lat='{lat:.7f}' lon='{lon:.7f}'/>"
        )
        next_id -= 1
    way_id = next_id
    next_id -= 1
    lines.append(f"  <way id='{way_id}' version='0' action='modify' visible='true'>")
    for node_id in path_node_ids:
        lines.append(f"    <nd ref='{node_id}'/>")
    for key, value in [
        ("name", TRAIL_NAME),
        ("alt_name", "Pilegrimsleden over Romerike"),
        ("highway", "path"),
        ("pilgrimage", "yes"),
        ("network", "Pilegrimsleden"),
        ("note:trail", "; ".join(TRAIL_MEMBERSHIP)),
        ("source", f"openstreetmap.org/relation/{RELATION_ID}"),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </way>")

    poi_node_ids: list[int] = []
    for record in records:
        node_id = next_id
        next_id -= 1
        poi_node_ids.append(node_id)
        cats = record.get("categories") or []
        primary = primary_category(cats) if any(c in CATEGORY_PRIORITY for c in cats) else (
            "Overnatting" if "Overnatting" in cats else (cats[0] if cats else "")
        )
        if primary == "Overnatting":
            mapping, uncertain = [("tourism", "guest_house")], True
        else:
            mapping, uncertain = osm_tags_for_category(primary)
        lines.append(
            f"  <node id='{node_id}' version='0' action='modify' visible='true' "
            f"lat='{record['lat']:.7f}' lon='{record['lon']:.7f}'>"
        )
        tags: list[tuple[str, str]] = [
            ("name", record["title"]),
            ("source", "pilegrimsleden.no"),
            ("url", record.get("url") or ""),
            ("network", "Pilegrimsleden"),
            ("note:trail", "; ".join(record.get("trails") or TRAIL_MEMBERSHIP)),
            ("note:osm_route_relation", str(RELATION_ID)),
            ("pilegrimsleden:id", str(record.get("id") or "")),
            (
                "pilegrimsleden:poi_type",
                ";".join(
                    title
                    for title in cats
                    if title in CORE_SHELTER_CATEGORIES
                    or title in {RASTEPLASS, "Overnatting"}
                )
                or primary,
            ),
        ]
        proposal = (record.get("proposal_note") or "").strip()
        if proposal:
            tags.append(("note:proposed", proposal))
            tags.append(("note", proposal))
        tags.extend(mapping)
        if uncertain:
            tags.append(
                ("note:osm_mapping", f"uncertain OSM equivalent for category {primary}")
            )
        for key, value in tags:
            if not value:
                continue
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </node>")

    rel_id = next_id
    lines.append(f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>")
    lines.append(f"    <member type='way' ref='{way_id}' role=''/>")
    for node_id in poi_node_ids:
        lines.append(f"    <member type='node' ref='{node_id}' role='shelter'/>")
    for key, value in [
        ("type", "route"),
        ("route", "hiking"),
        ("name", TRAIL_NAME),
        ("alt_name", "Pilegrimsleden over Romerike"),
        ("network", "Pilegrimsleden"),
        ("pilgrimage", "yes"),
        ("note:trail", "; ".join(TRAIL_MEMBERSHIP)),
        ("source", f"openstreetmap.org/relation/{RELATION_ID}"),
        (
            "note",
            "Local JOSM research relation linking corridor overnight POIs to the "
            "Romeriksleden geometry derived from OSM relation 1200009; not an OSM import",
        ),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </relation>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rematch_against_norway_pbf(
    shelters: list[dict[str, str]],
    route_index: list[tuple[float, float]],
    data: Path,
    *,
    reuse_cache: bool = False,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Rematch corridor CMS rows against Norway PBF (includes tourism=hotel)."""
    from compare_osm_shelters import (
        POSSIBLE_RADIUS_M,
        buffer_bbox,
        classify_poi,
        extract_from_pbf,
        haversine_m as cmp_haversine,
        shelter_categories,
    )

    trail_dir = data / "by_trail" / TRAIL_NAME
    cache_along = trail_dir / "osm_along_route.csv"
    cache_shelters = trail_dir / "shelters.csv"
    if reuse_cache and cache_along.exists() and cache_shelters.exists():
        log(f"Reusing cached PBF results from {cache_along.name}")
        along = list(csv.DictReader(cache_along.open(encoding="utf-8")))
        # Drop stale status/note columns; repartition later.
        for row in along:
            row.pop("relation_status", None)
            row.pop("proposal_note", None)
        prev = {
            (r.get("pilegrimsleden_id") or "", r.get("poi_name") or ""): r
            for r in csv.DictReader(cache_shelters.open(encoding="utf-8"))
        }
        updated: list[dict[str, str]] = []
        for row in shelters:
            key = (row.get("pilegrimsleden_id") or "", row.get("poi_name") or "")
            old = prev.get(key) or prev.get(("", row.get("poi_name") or ""))
            copy = dict(row)
            if old:
                for field in (
                    "match_status",
                    "matched_osm_id",
                    "matched_osm_url",
                    "distance_m",
                    "tag_diff",
                ):
                    if old.get(field) not in (None, ""):
                        copy[field] = old[field]
            updated.append(copy)
        return updated, along

    pbf = data / "geofabrik" / "norway-latest.osm.pbf"
    if not pbf.exists():
        log(f"Norway PBF missing at {pbf}; skipping rematch")
        return shelters, []

    lats = [float(r["lat"]) for r in shelters] + [p[0] for p in route_index[::50]]
    lons = [float(r["lon"]) for r in shelters] + [p[1] for p in route_index[::50]]
    bbox = buffer_bbox(min(lats), min(lons), max(lats), max(lons), POSSIBLE_RADIUS_M + 50.0)
    log(f"Scanning {pbf.name} for lodging/shelter tags in Romeriksleden bbox")
    elements = extract_from_pbf(pbf, bbox)
    log(f"  kept {len(elements)} OSM elements in bbox")

    # OSM inventory within route buffer (discovery independent of CMS).
    along: list[dict[str, Any]] = []
    for el in elements:
        dist = min_dist_m(el["lat"], el["lon"], route_index)
        if dist > BUFFER_M:
            continue
        tags = el.get("tags") or {}
        along.append(
            {
                "osm_id": f"{el['type']}/{el['id']}",
                "osm_url": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
                "name": tags.get("name") or "",
                "lat": f"{el['lat']:.7f}",
                "lon": f"{el['lon']:.7f}",
                "tourism": tags.get("tourism") or "",
                "amenity": tags.get("amenity") or "",
                "building": tags.get("building") or "",
                "route_distance_m": f"{dist:.1f}",
                "note:osm_route_relation": str(RELATION_ID),
            }
        )
    along.sort(key=lambda r: (r["route_distance_m"], r["name"].lower()))

    updated: list[dict[str, str]] = []
    for row in shelters:
        cats = [c.strip() for c in (row.get("category") or "").split("|") if c.strip()]
        poi = {
            "title": row["poi_name"],
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "categories": cats,
            "shelter_categories": shelter_categories(cats) or cats,
            "our_tags": {},
        }
        nearby: list[tuple[float, dict[str, Any]]] = []
        for el in elements:
            dist = cmp_haversine(poi["lat"], poi["lon"], el["lat"], el["lon"])
            if dist <= POSSIBLE_RADIUS_M:
                nearby.append((dist, el))
        result = classify_poi(poi, nearby)
        copy = dict(row)
        copy["match_status"] = result["match_status"]
        copy["matched_osm_id"] = result["matched_osm_id"]
        copy["matched_osm_url"] = result["matched_osm_url"]
        copy["distance_m"] = (
            "" if result["distance_m"] == "" else str(result["distance_m"])
        )
        copy["tag_diff"] = result["tag_diff"]
        updated.append(copy)
    return updated, along


def write_along_route_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "osm_id",
        "osm_url",
        "name",
        "lat",
        "lon",
        "tourism",
        "amenity",
        "building",
        "route_distance_m",
        "note:osm_route_relation",
        "relation_status",
        "proposal_note",
    ]
    write_csv(path, [{k: r.get(k, "") for k in fields} for r in rows], fields)


def partition_by_relation_membership(
    along_route: list[dict[str, Any]],
    existing_members: set[tuple[str, int]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split nearby OSM objects into already-on-relation vs missing candidates.

    Already-related objects are never modified. Missing ones are proposed only
    in local research output.
    """
    already: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for row in along_route:
        osm_id = row.get("osm_id") or ""
        try:
            kind, oid_s = osm_id.split("/", 1)
            key = (kind, int(oid_s))
        except (ValueError, AttributeError):
            missing.append({**row, "relation_status": "missing"})
            continue
        if key in existing_members:
            already.append({**row, "relation_status": "already_member"})
        else:
            missing.append({**row, "relation_status": "missing"})
    return already, missing


def write_missing_additions_osm(
    path: Path,
    missing: list[dict[str, Any]],
    cms_gap_records: list[dict[str, Any]],
) -> None:
    """Local research file: propose adding missing OSM objects + CMS gaps.

    Uses a new negative-id relation that only lists proposed members.
    Does not copy or alter OSM relation RELATION_ID.
    """
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    member_refs: list[tuple[str, int, str]] = []
    next_neg = -1

    for row in missing:
        osm_id = row.get("osm_id") or ""
        try:
            kind, oid_s = osm_id.split("/", 1)
            oid = int(oid_s)
        except (ValueError, AttributeError):
            continue
        lat = float(row["lat"])
        lon = float(row["lon"])
        name = row.get("name") or ""
        note = proposal_note_for_existing_osm(osm_id)
        if kind == "node":
            lines.append(
                f"  <node id='{oid}' version='1' visible='true' "
                f"lat='{lat:.7f}' lon='{lon:.7f}'>"
            )
            if name:
                lines.append(f"    <tag k='name' v='{xml_escape(name)}'/>")
            for key in ("tourism", "amenity", "building"):
                val = row.get(key) or ""
                if val:
                    lines.append(
                        f"    <tag k='{xml_escape(key)}' v='{xml_escape(val)}'/>"
                    )
            lines.append(f"    <tag k='note:proposed' v='{xml_escape(note)}'/>")
            lines.append(f"    <tag k='note' v='{xml_escape(note)}'/>")
            lines.append(
                f"    <tag k='note:osm_route_relation' v='{RELATION_ID}'/>"
            )
            lines.append("  </node>")
            member_refs.append(("node", oid, "shelter"))
        else:
            lines.append(
                f"  <node id='{next_neg}' version='0' action='modify' visible='true' "
                f"lat='{lat:.7f}' lon='{lon:.7f}'>"
            )
            if name:
                lines.append(f"    <tag k='name' v='{xml_escape(name)}'/>")
            proxy_note = f"Centroid proxy for {osm_id}. {note}"
            lines.append(f"    <tag k='note:proposed' v='{xml_escape(proxy_note)}'/>")
            lines.append(f"    <tag k='note' v='{xml_escape(proxy_note)}'/>")
            lines.append(f"    <tag k='note:osm_object' v='{xml_escape(osm_id)}'/>")
            lines.append(
                f"    <tag k='note:osm_route_relation' v='{RELATION_ID}'/>"
            )
            for key in ("tourism", "amenity", "building"):
                val = row.get(key) or ""
                if val:
                    lines.append(
                        f"    <tag k='{xml_escape(key)}' v='{xml_escape(val)}'/>"
                    )
            lines.append("  </node>")
            member_refs.append(("node", next_neg, "shelter"))
            next_neg -= 1

    for record in cms_gap_records:
        lines.append(
            f"  <node id='{next_neg}' version='0' action='modify' visible='true' "
            f"lat='{record['lat']:.7f}' lon='{record['lon']:.7f}'>"
        )
        cats = record.get("categories") or []
        primary = (
            primary_category(cats)
            if any(c in CATEGORY_PRIORITY for c in cats)
            else ("Overnatting" if "Overnatting" in cats else (cats[0] if cats else ""))
        )
        if primary == "Overnatting":
            mapping = [("tourism", "guest_house")]
        else:
            mapping, _u = osm_tags_for_category(primary)
        gap_note = record.get("proposal_note") or proposal_note_for_cms_gap()
        tags: list[tuple[str, str]] = [
            ("name", record.get("title") or ""),
            ("source", "pilegrimsleden.no"),
            ("url", record.get("url") or ""),
            ("network", "Pilegrimsleden"),
            ("note:trail", "; ".join(TRAIL_MEMBERSHIP)),
            ("note:osm_route_relation", str(RELATION_ID)),
            ("note:proposed", gap_note),
            ("note", gap_note),
            ("pilegrimsleden:id", str(record.get("id") or "")),
        ]
        tags.extend(mapping)
        for key, value in tags:
            if not value:
                continue
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </node>")
        member_refs.append(("node", next_neg, "shelter"))
        next_neg -= 1

    rel_id = next_neg
    lines.append(f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>")
    for mtype, mid, role in member_refs:
        lines.append(
            f"    <member type='{mtype}' ref='{mid}' role='{xml_escape(role)}'/>"
        )
    for key, value in [
        ("type", "site"),
        ("name", f"Proposed additions to {TRAIL_NAME}"),
        ("network", "Pilegrimsleden"),
        ("note:trail", TRAIL_NAME),
        ("note:target_osm_relation", str(RELATION_ID)),
        ("source", f"openstreetmap.org/relation/{RELATION_ID}"),
        (
            "note",
            f"LOCAL research relation listing objects missing from OSM relation "
            f"{RELATION_ID}. Does not modify the existing OSM relation. "
            "Each proposed POI carries note:proposed. Not an import.",
        ),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </relation>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def patch_gudbrandsdalsleden_trail_notes(
    data: Path, corridor_names: set[str]
) -> int:
    """Add Romeriksleden to note:trail on Gudbrandsdalsleden shelters.osm for corridor POIs."""
    path = data / "by_trail" / SOURCE_TRAIL / "shelters.osm"
    if not path.exists() or not corridor_names:
        return 0
    text = path.read_text(encoding="utf-8")
    updated = 0

    def repl_node(match: re.Match[str]) -> str:
        nonlocal updated
        block = match.group(0)
        name_m = re.search(r"<tag k='name' v='([^']*)'/>", block)
        if not name_m:
            return block
        name = (
            name_m.group(1)
            .replace("&quot;", '"')
            .replace("&apos;", "'")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
        )
        if name not in corridor_names:
            return block
        trail_m = re.search(r"<tag k='note:trail' v='([^']*)'/>", block)
        if not trail_m:
            return block
        current = trail_m.group(1)
        if TRAIL_NAME in current:
            return block
        new_val = xml_escape(f"{current}; {TRAIL_NAME}" if current else TRAIL_NAME)
        updated += 1
        block2 = re.sub(
            r"<tag k='note:trail' v='[^']*'/>",
            f"<tag k='note:trail' v='{new_val}'/>",
            block,
            count=1,
        )
        if "note:osm_route_relation" not in block2:
            block2 = block2.replace(
                "</node>",
                f"    <tag k='note:osm_route_relation' v='{RELATION_ID}'/>\n  </node>",
                1,
            )
        return block2

    new_text = re.sub(
        r"<node id='-\d+'[^>]*>.*?</node>", repl_node, text, flags=re.S
    )
    if updated:
        path.write_text(new_text, encoding="utf-8")
    return updated


def main() -> int:
    root = Path(__file__).resolve().parent
    data = root / "data"
    trail_dir = data / "by_trail" / TRAIL_NAME
    trail_dir.mkdir(parents=True, exist_ok=True)

    rel, segments, existing_members = fetch_relation_geometry()
    track = stitch_points(segments)
    log(f"Relation members with geometry: {len(segments)}; track points: {len(track)}")
    if len(track) < 2:
        raise RuntimeError("route geometry too short")

    write_hiking_gpx(trail_dir / "hiking_path.gpx", track)
    write_hiking_osm(trail_dir / "hiking_path.osm", track)

    index = densify_for_index(track, step_m=75.0)
    log(f"Distance index points: {len(index)} (buffer {BUFFER_M:.0f} m)")

    trailpoints = fetch_trailpoints()
    shelters, records = select_corridor_pois(trailpoints, index, data)
    log(f"Corridor overnight POIs: {len(shelters)}")
    shelters, along_route = rematch_against_norway_pbf(
        shelters, index, data, reuse_cache=("--reuse-pbf" in sys.argv)
    )
    gap_n = sum(1 for r in shelters if r.get("match_status") == "gap")
    log(
        f"After Norway PBF rematch: gaps={gap_n}; "
        f"OSM objects within {int(BUFFER_M)} m of route={len(along_route)}"
    )

    already, missing = partition_by_relation_membership(along_route, existing_members)
    along_tagged = already + missing
    along_tagged.sort(
        key=lambda r: (
            r.get("relation_status") or "",
            r.get("route_distance_m") or "",
            (r.get("name") or "").lower(),
        )
    )
    log(
        f"Relation membership split vs OSM rel {RELATION_ID}: "
        f"already_member={len(already)} (leave alone); "
        f"missing={len(missing)} (propose local additions only)"
    )

    gap_by_coord = {
        (round(float(r["lat"]), 7), round(float(r["lon"]), 7))
        for r in shelters
        if r.get("match_status") == "gap"
    }
    cms_gap_records = [
        rec
        for rec in records
        if (round(float(rec["lat"]), 7), round(float(rec["lon"]), 7)) in gap_by_coord
    ]
    for rec in cms_gap_records:
        rec["proposal_note"] = proposal_note_for_cms_gap()
    log(f"CMS gap records proposed as new nodes: {len(cms_gap_records)}")

    # Per-POI proposal notes on corridor CMS rows:
    # - gap → propose new OSM object + relation membership
    # - matched/possible to an OSM object not already on the relation → propose membership
    # - matched to an already-related OSM object → no proposal (leave alone)
    missing_ids = {r.get("osm_id") for r in missing}
    for row, rec in zip(shelters, records):
        mid = row.get("matched_osm_id") or ""
        if row.get("match_status") == "gap" or not mid:
            note = proposal_note_for_cms_gap()
        elif mid in missing_ids:
            note = proposal_note_for_existing_osm(mid)
        else:
            # already on relation, or unmatched id not in along-route set
            try:
                kind, oid_s = mid.split("/", 1)
                if (kind, int(oid_s)) in existing_members:
                    note = ""
                else:
                    note = proposal_note_for_existing_osm(mid)
            except ValueError:
                note = proposal_note_for_existing_osm(mid)
        row["proposal_note"] = note
        rec["proposal_note"] = note

    for row in missing:
        row["proposal_note"] = proposal_note_for_existing_osm(row.get("osm_id") or "")
    for row in already:
        row["proposal_note"] = ""

    with (data / "by_trail" / SOURCE_TRAIL / "pilgrim_centers.csv").open(
        encoding="utf-8"
    ) as handle:
        pilgrim = filter_pilgrim_rows(list(csv.DictReader(handle)), index)

    shelter_fields = [
        "trail",
        "poi_name",
        "category",
        "lat",
        "lon",
        "match_status",
        "matched_osm_id",
        "matched_osm_url",
        "distance_m",
        "tag_diff",
        "related_trails",
        "pilegrimsleden_id",
        "proposal_note",
    ]
    pub_shelters = []
    for row in shelters:
        pub = {k: row.get(k, "") for k in shelter_fields}
        mid = pub.get("matched_osm_id") or ""
        if mid:
            try:
                kind, oid_s = mid.split("/", 1)
                if (kind, int(oid_s)) in existing_members:
                    pub["tag_diff"] = (
                        (pub["tag_diff"] + "; " if pub["tag_diff"] else "")
                        + "already_member_of_osm_relation_"
                        + str(RELATION_ID)
                    )
            except ValueError:
                pass
        pub_shelters.append(pub)
    write_csv(trail_dir / "shelters.csv", pub_shelters, shelter_fields)

    along_fields = [
        "osm_id",
        "osm_url",
        "name",
        "lat",
        "lon",
        "tourism",
        "amenity",
        "building",
        "route_distance_m",
        "note:osm_route_relation",
        "relation_status",
        "proposal_note",
    ]
    write_along_route_csv(trail_dir / "osm_along_route.csv", along_tagged)
    write_csv(
        trail_dir / "osm_already_related.csv",
        [{k: r.get(k, "") for k in along_fields} for r in already],
        along_fields,
    )
    write_csv(
        trail_dir / "osm_missing_for_relation.csv",
        [{k: r.get(k, "") for k in along_fields} for r in missing],
        along_fields,
    )
    write_missing_additions_osm(
        trail_dir / "missing_additions.osm", missing, cms_gap_records
    )

    pilgrim_fields = [
        "trail",
        "poi_name",
        "category",
        "lat",
        "lon",
        "match_status",
        "matched_osm_id",
        "matched_osm_url",
        "distance_m",
        "tag_diff",
        "related_trails",
    ]
    pub_pilgrim = [{k: r.get(k, "") for k in pilgrim_fields} for r in pilgrim]
    write_csv(trail_dir / "pilgrim_centers.csv", pub_pilgrim, pilgrim_fields)

    write_shelters_osm_with_trails(trail_dir / "shelters.osm", records)
    write_bundle_osm(trail_dir / "romeriksleden.osm", track, records)

    patched = patch_gudbrandsdalsleden_trail_notes(
        data, {r["title"] for r in records}
    )
    log(f"Patched Gudbrandsdalsleden note:trail on {patched} shelter nodes")

    names = {r["poi_name"] for r in pub_shelters}
    for example in (
        "Velkommen til Olasvehaugen i Brøttum",
        "Brøttum Camping",
        "Brynn i Bergsengroa",
    ):
        log(f"  example {'OK' if example in names else 'MISSING'}: {example}")
    for osm_id in (
        "node/1931260548",
        "node/937852318",
        "way/98520866",
        "node/8018787776",
        "way/136363816",
    ):
        hit = next((r for r in pub_shelters if r.get("matched_osm_id") == osm_id), None)
        along_hit = next((r for r in along_tagged if r.get("osm_id") == osm_id), None)
        status = (along_hit or {}).get("relation_status", "?")
        if hit:
            log(
                f"  osm {osm_id}: CMS match={hit['match_status']} "
                f"relation_status={status} ({hit['poi_name']})"
            )
        elif along_hit:
            log(
                f"  osm {osm_id}: along-route relation_status={status} "
                f"({along_hit.get('name')})"
            )
        else:
            log(f"  osm {osm_id}: NOT FOUND")

    summary = {
        "trail": TRAIL_NAME,
        "osm_relation": RELATION_ID,
        "osm_url": RELATION_URL,
        "buffer_m": BUFFER_M,
        "related_trails": TRAIL_MEMBERSHIP,
        "source_trail_pois": SOURCE_TRAIL,
        "track_points": len(track),
        "member_ways": len(segments),
        "existing_osm_relation_members": len(existing_members),
        "shelters": len(pub_shelters),
        "shelter_gaps": sum(1 for r in pub_shelters if r.get("match_status") == "gap"),
        "osm_along_route": len(along_tagged),
        "osm_already_related": len(already),
        "osm_missing_for_relation": len(missing),
        "cms_gap_proposed_nodes": len(cms_gap_records),
        "pilgrim_centers": len(pub_pilgrim),
        "pilgrim_gaps": sum(1 for r in pub_pilgrim if r.get("match_status") == "gap"),
        "gudbrandsdalsleden_note_trail_patched": patched,
        "relation_tags": rel.get("tags") or {},
        "policy": (
            "Never modify existing OSM relation members. Propose only missing "
            "nearby lodging objects + CMS gaps in missing_additions.osm "
            "(local research file)."
        ),
    }
    (data / "romeriksleden_extract_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(
        f"Romeriksleden shelters={len(pub_shelters)} "
        f"(gaps={summary['shelter_gaps']}) "
        f"already_related={len(already)} missing={len(missing)} "
        f"pilgrim_centers={len(pub_pilgrim)}"
    )

    readme_path = data / "by_trail" / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    note = (
        f"{TRAIL_NAME} is Gudbrandsdalsleden east (Oslo–Eidsvoll–Hamar–Lillehammer), "
        f"mapped in OSM as relation {RELATION_ID} but not a separate pilegrimsleden.no "
        f"trail entry. Discovery treats existing members of relation {RELATION_ID} as "
        f"already related (never modified). Nearby lodging/shelter OSM objects that are "
        f"not members are listed in `osm_missing_for_relation.csv` / "
        f"`missing_additions.osm` as local research proposals only. "
        f"`osm_already_related.csv` lists objects already on the relation. "
        f"CMS overnight POIs within {int(BUFFER_M)} m are in `shelters.*` with "
        f"`related_trails` {SOURCE_TRAIL} + {TRAIL_NAME}."
    )
    old_note_re = re.compile(
        r"Romeriksleden is Gudbrandsdalsleden east.*?(?=\n\nCombined national)",
        re.S,
    )
    if old_note_re.search(readme):
        readme = old_note_re.sub(note, readme, count=1)
    elif "Combined national files under `data/` are unchanged." in readme and note[:40] not in readme:
        readme = readme.replace(
            "Combined national files under `data/` are unchanged.",
            note + "\n\nCombined national files under `data/` are unchanged.",
            1,
        )
    row = (
        f"| {TRAIL_NAME} | {TRAIL_NAME} | {len(pub_shelters)} | {len(pub_pilgrim)} | "
        f"{summary['shelter_gaps']} | {summary['pilgrim_gaps']} | - |"
    )
    readme, n = re.subn(
        r"\| Romeriksleden \| Romeriksleden \| \d+ \| \d+ \| \d+ \| \d+ \| - \|",
        row,
        readme,
        count=1,
    )
    if n == 0 and "| Gudbrandsdalsleden | Gudbrandsdalsleden |" in readme:
        lines = readme.splitlines()
        out_lines: list[str] = []
        for line in lines:
            out_lines.append(line)
            if line.startswith("| Gudbrandsdalsleden | Gudbrandsdalsleden |"):
                out_lines.append(row)
        readme = "\n".join(out_lines) + ("\n" if readme.endswith("\n") else "")
    readme_path.write_text(readme, encoding="utf-8")
    log(f"Updated {readme_path}")
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
