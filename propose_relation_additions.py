#!/usr/bin/env python3
"""Propose OSM trail-relation lodging additions for every by_trail folder.

Model (read-only w.r.t. OpenStreetMap):
1. Load each trail's OSM route relation as source of truth for geometry and
   existing members (never modify those members).
2. Discover lodging/shelter OSM objects near the route (Geofabrik PBF).
3. Partition into already_member vs missing; write local research proposals
   with per-POI note:proposed / proposal_note.
4. CMS shelter gaps and matched OSM objects not on the relation also get
   per-POI proposal notes on shelters.csv / shelters.osm.

Does not upload or modify OpenStreetMap.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from compare_osm_shelters import buffer_bbox, extract_from_pbf
from extract_pilegrimsleden_shelters import (
    CATEGORY_PRIORITY,
    osm_tags_for_category,
    primary_category,
)
from extract_stolavsleden import haversine_m, xml_escape

USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(OSM mapping research; trail relation lodging proposals; "
    "+https://github.com/Supermagnum/Scandi-pilgrim-poi)"
)
BUFFER_M = 2000.0

# folder_name -> (display trail name, primary OSM route relation id)
TRAIL_RELATIONS: dict[str, tuple[str, int]] = {
    "Borgleden": ("Borgleden", 5672944),
    "Gudbrandsdalsleden": ("Gudbrandsdalsleden", 1370273),
    "Kystpilegrimsleia": ("Kystpilegrimsleia", 10508888),
    "Nordleden": ("Nordleden", 1585449),
    "Osterdalsleden": ("Østerdalsleden", 5129262),
    "Romboleden": ("Romboleden", 1151161),
    "Romeriksleden": ("Romeriksleden", 1200009),
    "St-Olavsleden": ("St. Olavsleden", 10524322),
    "Tunsbergleden": ("Tunsbergleden / Vestfoldveien", 5661086),
    "Valldalsleden": ("Valldalsleden", 11218584),
}


def log(message: str) -> None:
    print(message, flush=True)


PROPOSED_ADDITION = "Proposed addition"


def proposal_note_for_existing_osm(
    relation_id: int, trail_name: str, osm_id: str = ""
) -> str:
    # Existing OSM lodging is not a new POI addition; keep CSV empty.
    # Membership candidates are listed in osm_missing_for_relation.csv only.
    return ""


def proposal_note_for_cms_gap(relation_id: int, trail_name: str) -> str:
    return PROPOSED_ADDITION


def http_get(url: str, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            log(f"  retry {attempt}/4 after error: {exc}")
            time.sleep(2 * attempt)
    raise RuntimeError(f"failed to fetch {url}: {last}")


def parse_relation_members(root: ET.Element) -> tuple[dict[str, str], set[tuple[str, int]]]:
    rel_el = root.find("relation")
    if rel_el is None:
        raise RuntimeError("relation element missing")
    tags = {tag.attrib["k"]: tag.attrib["v"] for tag in rel_el.findall("tag")}
    members: set[tuple[str, int]] = set()
    for member in rel_el.findall("member"):
        mtype = member.attrib.get("type") or ""
        try:
            mid = int(member.attrib["ref"])
        except (KeyError, ValueError):
            continue
        members.add((mtype, mid))
    return tags, members


def fetch_relation_shallow(relation_id: int) -> tuple[dict[str, str], set[tuple[str, int]]]:
    url = f"https://www.openstreetmap.org/api/0.6/relation/{relation_id}"
    root = ET.fromstring(http_get(url, timeout=120))
    return parse_relation_members(root)


def expand_membership(
    relation_id: int, *, max_depth: int = 2
) -> tuple[dict[str, str], set[tuple[str, int]], list[int]]:
    """Collect members of relation_id, expanding nested relations up to max_depth.

    Returns primary tags, flattened member set, and list of relation ids visited
    (for geometry download of child routes on superroutes).
    """
    tags, members = fetch_relation_shallow(relation_id)
    visited = {relation_id}
    frontier = [rid for kind, rid in members if kind == "relation"]
    depth = 0
    while frontier and depth < max_depth:
        depth += 1
        nxt: list[int] = []
        for rid in frontier:
            if rid in visited:
                continue
            visited.add(rid)
            _t, child_members = fetch_relation_shallow(rid)
            members |= child_members
            nxt.extend(cid for kind, cid in child_members if kind == "relation")
        frontier = nxt
    return tags, members, sorted(visited)


def geometry_from_full_xml(
    xml_text: str,
) -> list[list[tuple[float, float]]]:
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
    segments: list[list[tuple[float, float]]] = []
    for rel_el in root.findall("relation"):
        for member in rel_el.findall("member"):
            if member.attrib.get("type") != "way":
                continue
            role = (member.attrib.get("role") or "").strip()
            if role and role not in {"main", "forward", "backward", ""}:
                continue
            pts = ways.get(member.attrib["ref"])
            if not pts:
                continue
            if role == "backward":
                pts = list(reversed(pts))
            segments.append(pts)
    return segments


def fetch_route_segments(relation_ids: list[int]) -> list[list[tuple[float, float]]]:
    segments: list[list[tuple[float, float]]] = []
    for rid in relation_ids:
        url = f"https://www.openstreetmap.org/api/0.6/relation/{rid}/full"
        log(f"  downloading relation/{rid}/full")
        xml_text = http_get(url, timeout=300).decode("utf-8")
        segs = geometry_from_full_xml(xml_text)
        log(f"    {len(segs)} way segments")
        segments.extend(segs)
    return segments


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
    points: list[tuple[float, float]], step_m: float = 100.0
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


def build_route_grid(
    route: list[tuple[float, float]], cell: float = 0.02
) -> dict[tuple[int, int], list[tuple[float, float]]]:
    grid: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for lat, lon in route:
        key = (int(lat / cell), int(lon / cell))
        grid.setdefault(key, []).append((lat, lon))
    return grid


def min_dist_grid_m(
    lat: float,
    lon: float,
    route_grid: dict[tuple[int, int], list[tuple[float, float]]],
    *,
    cell: float = 0.02,
    radius_m: float = BUFFER_M,
) -> float:
    """Approximate nearest route distance using a lat/lon cell grid."""
    gi, gj = int(lat / cell), int(lon / cell)
    # ~0.02 deg ≈ 2.2 km; span 2 covers > BUFFER_M with margin
    span = 2
    best = float("inf")
    for di in range(-span, span + 1):
        for dj in range(-span, span + 1):
            for rlat, rlon in route_grid.get((gi + di, gj + dj), ()):
                d = haversine_m(lat, lon, rlat, rlon)
                if d < best:
                    best = d
                    if best <= 1.0:
                        return best
    if best == float("inf") or best > radius_m:
        return best if best != float("inf") else float("inf")
    return best


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def partition_by_relation_membership(
    along_route: list[dict[str, Any]],
    existing_members: set[tuple[str, int]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
    *,
    trail_name: str,
    relation_id: int,
    missing: list[dict[str, Any]],
    cms_gap_rows: list[dict[str, str]],
) -> None:
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
        note = proposal_note_for_existing_osm(relation_id, trail_name, osm_id)
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
                f"    <tag k='note:osm_route_relation' v='{relation_id}'/>"
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
                f"    <tag k='note:osm_route_relation' v='{relation_id}'/>"
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

    for row in cms_gap_rows:
        cats = [c.strip() for c in (row.get("category") or "").split("|") if c.strip()]
        primary = (
            primary_category(cats)
            if any(c in CATEGORY_PRIORITY for c in cats)
            else ("Overnatting" if "Overnatting" in cats else (cats[0] if cats else ""))
        )
        if primary == "Overnatting":
            mapping = [("tourism", "guest_house")]
        else:
            mapping, _u = osm_tags_for_category(primary)
        gap_note = row.get("proposal_note") or proposal_note_for_cms_gap(
            relation_id, trail_name
        )
        lines.append(
            f"  <node id='{next_neg}' version='0' action='modify' visible='true' "
            f"lat='{float(row['lat']):.7f}' lon='{float(row['lon']):.7f}'>"
        )
        tags: list[tuple[str, str]] = [
            ("name", row.get("poi_name") or ""),
            ("source", "pilegrimsleden.no"),
            ("network", "Pilegrimsleden"),
            ("note:trail", row.get("trail") or trail_name),
            ("note:osm_route_relation", str(relation_id)),
            ("note:proposed", gap_note),
            ("note", gap_note),
            ("pilegrimsleden:id", row.get("pilegrimsleden_id") or ""),
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
        ("name", f"Proposed additions to {trail_name}"),
        ("network", "Pilegrimsleden"),
        ("note:trail", trail_name),
        ("note:target_osm_relation", str(relation_id)),
        ("source", f"openstreetmap.org/relation/{relation_id}"),
        (
            "note",
            f"LOCAL research relation listing objects missing from OSM relation "
            f"{relation_id}. Does not modify the existing OSM relation. "
            "Each proposed POI carries note:proposed. Not an import.",
        ),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </relation>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def patch_shelters_osm_notes(
    path: Path,
    notes_by_name: dict[str, str],
    relation_id: int,
) -> int:
    """Add/replace note:proposed and note on negative-id CMS nodes by name."""
    if not path.exists() or not notes_by_name:
        return 0
    text = path.read_text(encoding="utf-8")
    updated = 0

    def unescape(value: str) -> str:
        return (
            value.replace("&quot;", '"')
            .replace("&apos;", "'")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
        )

    def repl_node(match: re.Match[str]) -> str:
        nonlocal updated
        block = match.group(0)
        name_m = re.search(r"<tag k='name' v='([^']*)'/>", block)
        if not name_m:
            return block
        name = unescape(name_m.group(1))
        note = notes_by_name.get(name)
        if note is None:
            return block
        updated += 1
        # Drop prior note / note:proposed so we can rewrite cleanly.
        block2 = re.sub(r"\n?\s*<tag k='note:proposed' v='[^']*'/>", "", block)
        block2 = re.sub(r"\n?\s*<tag k='note' v='[^']*'/>", "", block2)
        if "note:osm_route_relation" not in block2:
            block2 = block2.replace(
                "</node>",
                f"    <tag k='note:osm_route_relation' v='{relation_id}'/>\n  </node>",
                1,
            )
        if note:
            insert = (
                f"    <tag k='note:proposed' v='{xml_escape(note)}'/>\n"
                f"    <tag k='note' v='{xml_escape(note)}'/>\n  </node>"
            )
            block2 = block2.replace("</node>", insert, 1)
        return block2

    new_text = re.sub(
        r"<node id='-\d+'[^>]*>.*?</node>", repl_node, text, flags=re.S
    )
    if updated:
        path.write_text(new_text, encoding="utf-8")
    return updated


def load_shelters(trail_dir: Path) -> list[dict[str, str]]:
    path = trail_dir / "shelters.csv"
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def process_trail(
    *,
    folder: str,
    trail_name: str,
    relation_id: int,
    trail_dir: Path,
    elements: list[dict[str, Any]],
    skip_geometry: bool = False,
) -> dict[str, Any]:
    log(f"\n=== {folder} ({trail_name}) relation/{relation_id} ===")
    tags, existing_members, visited_rels = expand_membership(relation_id)
    log(
        f"Existing OSM members (incl. nested): {len(existing_members)} "
        f"from relations {visited_rels}"
    )

    shelters = load_shelters(trail_dir)
    index: list[tuple[float, float]] = []
    # Superroutes (e.g. St. Olavsleden) expand membership across child relations
    # but use CMS POI corridor geometry — downloading every child /full is huge.
    use_poi_geometry = skip_geometry or tags.get("type") == "superroute"
    if not use_poi_geometry:
        segments = fetch_route_segments([relation_id])
        track = stitch_points(segments)
        log(f"Track points after stitch: {len(track)}")
        if len(track) >= 2:
            index = densify_for_index(track, step_m=100.0)
            log(f"Distance index points: {len(index)}")

    if not index:
        # Lodging near overnight stops (no dense stitch — keeps queries fast).
        index = [(float(r["lat"]), float(r["lon"])) for r in shelters]
        log(f"Geometry via CMS POI points: {len(index)} index points")

    route_grid = build_route_grid(index, cell=0.02)
    along: list[dict[str, Any]] = []
    for el in elements:
        dist = min_dist_grid_m(
            el["lat"], el["lon"], route_grid, cell=0.02, radius_m=BUFFER_M
        )
        if dist > BUFFER_M:
            continue
        tags_el = el.get("tags") or {}
        along.append(
            {
                "osm_id": f"{el['type']}/{el['id']}",
                "osm_url": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
                "name": tags_el.get("name") or "",
                "lat": f"{el['lat']:.7f}",
                "lon": f"{el['lon']:.7f}",
                "tourism": tags_el.get("tourism") or "",
                "amenity": tags_el.get("amenity") or "",
                "building": tags_el.get("building") or "",
                "route_distance_m": f"{dist:.1f}",
                "note:osm_route_relation": str(relation_id),
            }
        )
    along.sort(key=lambda r: (float(r["route_distance_m"]), (r["name"] or "").lower()))
    already, missing = partition_by_relation_membership(along, existing_members)
    log(
        f"Along route within {int(BUFFER_M)} m: {len(along)}; "
        f"already_member={len(already)}; missing={len(missing)}"
    )

    missing_ids = {r.get("osm_id") for r in missing}
    for row in missing:
        row["proposal_note"] = proposal_note_for_existing_osm(
            relation_id, trail_name, row.get("osm_id") or ""
        )
    for row in already:
        row["proposal_note"] = ""

    for row in shelters:
        mid = row.get("matched_osm_id") or ""
        if row.get("match_status") == "gap" or not mid:
            note = proposal_note_for_cms_gap(relation_id, trail_name)
        elif mid in missing_ids:
            note = proposal_note_for_existing_osm(relation_id, trail_name, mid)
        else:
            try:
                kind, oid_s = mid.split("/", 1)
                if (kind, int(oid_s)) in existing_members:
                    note = ""
                else:
                    note = proposal_note_for_existing_osm(relation_id, trail_name, mid)
            except ValueError:
                note = proposal_note_for_existing_osm(relation_id, trail_name, mid)
        row["proposal_note"] = note

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
    along_tagged = already + missing
    along_tagged.sort(
        key=lambda r: (
            r.get("relation_status") or "",
            float(r.get("route_distance_m") or 0),
            (r.get("name") or "").lower(),
        )
    )
    write_csv(trail_dir / "osm_along_route.csv", along_tagged, along_fields)
    write_csv(trail_dir / "osm_already_related.csv", already, along_fields)
    write_csv(trail_dir / "osm_missing_for_relation.csv", missing, along_fields)

    shelter_fields = list(shelters[0].keys()) if shelters else []
    if "proposal_note" not in shelter_fields:
        shelter_fields.append("proposal_note")
    write_csv(trail_dir / "shelters.csv", shelters, shelter_fields)

    cms_gaps = [r for r in shelters if r.get("match_status") == "gap"]
    log(
        f"CSV membership outputs written; CMS gaps={len(cms_gaps)}. "
        "Run build_josm_review.py to rebuild the single trail.osm per folder."
    )

    summary = {
        "folder": folder,
        "trail": trail_name,
        "osm_relation": relation_id,
        "osm_url": f"https://www.openstreetmap.org/relation/{relation_id}",
        "relation_tags": tags,
        "visited_relations": visited_rels,
        "existing_osm_relation_members": len(existing_members),
        "osm_along_route": len(along),
        "osm_already_related": len(already),
        "osm_missing_for_relation": len(missing),
        "cms_shelters": len(shelters),
        "cms_gaps": len(cms_gaps),
        "shelters_with_proposal_note": sum(
            1 for r in shelters if (r.get("proposal_note") or "").strip()
        ),
        "policy": (
            "Never modify existing OSM relation members. CSV lists missing nearby "
            "lodging; rebuild trail.osm with build_josm_review.py (path + existing "
            "POIs + gap suggestions only)."
        ),
    }
    (trail_dir / "relation_additions_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def collect_elements_for_trails(
    data: Path,
    trail_dirs: list[Path],
    *,
    reuse_cache: bool = False,
) -> list[dict[str, Any]]:
    cache_path = data / "geofabrik" / "lodging_all_trails_cache.json"
    if reuse_cache and cache_path.exists():
        log(f"Reusing lodging cache {cache_path}")
        return json.loads(cache_path.read_text(encoding="utf-8"))

    lats: list[float] = []
    lons: list[float] = []
    for trail_dir in trail_dirs:
        for row in load_shelters(trail_dir):
            lats.append(float(row["lat"]))
            lons.append(float(row["lon"]))
    if not lats:
        return []
    # Generous buffer so route geometry beyond outermost CMS POIs is covered.
    bbox = buffer_bbox(min(lats), min(lons), max(lats), max(lons), BUFFER_M + 5000.0)
    log(f"Union shelter bbox (+buffer): {bbox}")

    elements: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for pbf_name in ("norway-latest.osm.pbf", "sweden-latest.osm.pbf"):
        pbf = data / "geofabrik" / pbf_name
        if not pbf.exists():
            log(f"Missing {pbf}; skipping")
            continue
        log(f"Scanning {pbf.name} ...")
        batch = extract_from_pbf(pbf, bbox)
        for el in batch:
            key = (el["type"], int(el["id"]))
            if key in seen:
                continue
            seen.add(key)
            elements.append(el)
        log(f"  cumulative unique lodging elements: {len(elements)}")

    cache_path.write_text(
        json.dumps(elements, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log(f"Wrote lodging cache {cache_path}")
    return elements


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reuse-pbf",
        action="store_true",
        help="Reuse data/geofabrik/lodging_all_trails_cache.json if present",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="Folder name to skip (repeatable), e.g. Romeriksleden",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Only process these folder names (repeatable)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    data = root / "data"
    by_trail = data / "by_trail"

    folders = list(TRAIL_RELATIONS.keys())
    if args.only:
        folders = [f for f in folders if f in set(args.only)]
    skip = set(args.skip)
    folders = [f for f in folders if f not in skip]

    trail_dirs = [by_trail / f for f in folders if (by_trail / f / "shelters.csv").exists()]
    missing_csv = [f for f in folders if not (by_trail / f / "shelters.csv").exists()]
    if missing_csv:
        log(f"Skipping folders without shelters.csv: {missing_csv}")

    elements = collect_elements_for_trails(
        data, trail_dirs, reuse_cache=args.reuse_pbf
    )
    log(f"Lodging elements available for filtering: {len(elements)}")

    summaries: list[dict[str, Any]] = []
    for folder in folders:
        if not (by_trail / folder / "shelters.csv").exists():
            continue
        trail_name, relation_id = TRAIL_RELATIONS[folder]
        summary = process_trail(
            folder=folder,
            trail_name=trail_name,
            relation_id=relation_id,
            trail_dir=by_trail / folder,
            elements=elements,
        )
        summaries.append(summary)

    out = data / "relation_additions_all_trails_summary.json"
    out.write_text(
        json.dumps(summaries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log(f"\nWrote {out}")
    for s in summaries:
        log(
            f"  {s['folder']}: already={s['osm_already_related']} "
            f"missing={s['osm_missing_for_relation']} "
            f"cms_gaps={s['cms_gaps']} "
            f"notes={s['shelters_with_proposal_note']}/{s['cms_shelters']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
