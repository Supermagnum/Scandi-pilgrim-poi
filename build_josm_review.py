#!/usr/bin/env python3
"""Build exactly one OSM file per trail: data/by_trail/<Trail>/trail.osm

trail.osm contains:
  - trail path
  - existing CMS overnight POIs (matched/possible) — no note:proposed
  - new suggestions (CMS gaps) — note:proposed=Proposed addition

Removes any other *.osm files in each trail folder.
"""

from __future__ import annotations

import csv
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from extract_pilegrimsleden_shelters import (
    CATEGORY_PRIORITY,
    osm_tags_for_category,
    primary_category,
)
from extract_stolavsleden import xml_escape
from propose_relation_additions import (
    TRAIL_RELATIONS,
    densify_for_index,
    fetch_route_segments,
    http_get,
    stitch_points,
)

PROPOSED_ADDITION = "Proposed addition"
TRAIL_OSM_NAME = "trail.osm"


def log(message: str) -> None:
    print(message, flush=True)


def points_from_hiking_osm(path: Path) -> list[tuple[float, float]]:
    if not path.exists():
        return []
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    nodes = {
        n.attrib["id"]: (float(n.attrib["lat"]), float(n.attrib["lon"]))
        for n in root.findall("node")
        if "lat" in n.attrib and "lon" in n.attrib
    }
    points: list[tuple[float, float]] = []
    for way in root.findall("way"):
        for nd in way.findall("nd"):
            ref = nd.attrib.get("ref")
            if ref in nodes:
                points.append(nodes[ref])
    return points


def points_from_gpx(path: Path) -> list[tuple[float, float]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'\sxmlns="[^"]+"', "", text, count=1)
    root = ET.fromstring(text)
    points: list[tuple[float, float]] = []
    for trkpt in root.findall(".//trkpt"):
        points.append((float(trkpt.attrib["lat"]), float(trkpt.attrib["lon"])))
    if not points:
        for wpt in root.findall(".//wpt"):
            points.append((float(wpt.attrib["lat"]), float(wpt.attrib["lon"])))
    return points


def write_gpx(path: Path, points: list[tuple[float, float]], trail_name: str) -> None:
    if len(points) < 2:
        return
    step = max(1, len(points) // 5000)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="pilegrimsleden-osm-extractor 1.0" '
        'xmlns="http://www.topografix.com/GPX/1/1">',
        f"  <trk><name>{xml_escape(trail_name)}</name><trkseg>",
    ]
    for lat, lon in points[::step]:
        lines.append(f'    <trkpt lat="{lat:.7f}" lon="{lon:.7f}"></trkpt>')
    lines.extend(["  </trkseg></trk>", "</gpx>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_path_points(
    trail_dir: Path, trail_name: str, relation_id: int
) -> list[tuple[float, float]]:
    # Prefer existing trail.osm path, then legacy hiking_path.*, then OSM API.
    for candidate in (
        trail_dir / TRAIL_OSM_NAME,
        trail_dir / "josm_review.osm",
        trail_dir / "hiking_path.osm",
        trail_dir / "romeriksleden.osm",
    ):
        points = points_from_hiking_osm(candidate)
        if len(points) >= 2:
            log(f"  path from {candidate.name}: {len(points)} points")
            return points

    gpx_path = trail_dir / "hiking_path.gpx"
    points = points_from_gpx(gpx_path)
    if len(points) >= 2:
        log(f"  path from {gpx_path.name}: {len(points)} points")
        return densify_for_index(points, step_m=150.0)

    log(f"  fetching path geometry from relation/{relation_id}")
    tags_root = ET.fromstring(
        http_get(
            f"https://www.openstreetmap.org/api/0.6/relation/{relation_id}",
            timeout=120,
        )
    )
    rel = tags_root.find("relation")
    rel_type = ""
    if rel is not None:
        for tag in rel.findall("tag"):
            if tag.attrib.get("k") == "type":
                rel_type = tag.attrib.get("v") or ""
    if rel_type == "superroute":
        log("  superroute without local path source — path omitted")
        return []

    segments = fetch_route_segments([relation_id])
    track = stitch_points(segments)
    if len(track) < 2:
        return []
    index = densify_for_index(track, step_m=100.0)
    write_gpx(trail_dir / "hiking_path.gpx", index, trail_name)
    log(f"  cached hiking_path.gpx ({len(index)} points)")
    return index


def shelter_tags_for_row(row: dict[str, str], *, proposed: bool) -> list[tuple[str, str]]:
    cats = [c.strip() for c in (row.get("category") or "").split("|") if c.strip()]
    primary = (
        primary_category(cats)
        if any(c in CATEGORY_PRIORITY for c in cats)
        else ("Overnatting" if "Overnatting" in cats else (cats[0] if cats else ""))
    )
    if primary == "Overnatting":
        mapping: list[tuple[str, str]] = [("tourism", "guest_house")]
        uncertain = True
    else:
        mapping, uncertain = osm_tags_for_category(primary)
    tags: list[tuple[str, str]] = [
        ("name", row.get("poi_name") or ""),
        ("source", "pilegrimsleden.no"),
        ("network", "Pilegrimsleden"),
        ("note:trail", row.get("trail") or ""),
        ("pilegrimsleden:id", row.get("pilegrimsleden_id") or ""),
        ("pilegrimsleden:poi_type", ";".join(cats) if cats else primary),
        ("pilegrimsleden:match_status", row.get("match_status") or ""),
    ]
    if row.get("matched_osm_id"):
        tags.append(("note:osm_object", row["matched_osm_id"]))
    if row.get("matched_osm_url"):
        tags.append(("url:osm", row["matched_osm_url"]))
    tags.extend(mapping)
    if uncertain and primary:
        tags.append(
            ("note:osm_mapping", f"uncertain OSM equivalent for category {primary}")
        )
    if proposed:
        tags.append(("note:proposed", PROPOSED_ADDITION))
    return [(k, v) for k, v in tags if v]


def write_trail_osm(
    trail_dir: Path,
    trail_name: str,
    relation_id: int,
    rows: list[dict[str, str]],
    path_points: list[tuple[float, float]],
) -> None:
    existing = [r for r in rows if r.get("match_status") in {"matched", "possible"}]
    gaps = [r for r in rows if (r.get("match_status") or "gap") == "gap"]

    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    next_id = -1
    way_id: int | None = None

    if len(path_points) >= 2:
        pts = path_points
        if len(pts) > 8000:
            step = math.ceil(len(pts) / 8000)
            pts = pts[::step]
        node_ids: list[int] = []
        for lat, lon in pts:
            lines.append(
                f"  <node id='{next_id}' version='0' action='modify' visible='true' "
                f"lat='{lat:.7f}' lon='{lon:.7f}'/>"
            )
            node_ids.append(next_id)
            next_id -= 1
        way_id = next_id
        lines.append(
            f"  <way id='{way_id}' version='0' action='modify' visible='true'>"
        )
        for nid in node_ids:
            lines.append(f"    <nd ref='{nid}'/>")
        for key, value in [
            ("highway", "path"),
            ("name", trail_name),
            ("network", "Pilegrimsleden"),
            ("note:trail", trail_name),
            ("note:osm_route_relation", str(relation_id)),
            (
                "note",
                "Research path from OSM route relation / official GPX; "
                "do not upload as a replacement of the real relation.",
            ),
        ]:
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </way>")
        next_id -= 1

    existing_ids: list[int] = []
    for row in existing:
        lines.append(
            f"  <node id='{next_id}' version='0' action='modify' visible='true' "
            f"lat='{float(row['lat']):.7f}' lon='{float(row['lon']):.7f}'>"
        )
        for key, value in shelter_tags_for_row(row, proposed=False):
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </node>")
        existing_ids.append(next_id)
        next_id -= 1

    gap_ids: list[int] = []
    for row in gaps:
        lines.append(
            f"  <node id='{next_id}' version='0' action='modify' visible='true' "
            f"lat='{float(row['lat']):.7f}' lon='{float(row['lon']):.7f}'>"
        )
        for key, value in shelter_tags_for_row(row, proposed=True):
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append(
            f"    <tag k='note:osm_route_relation' v='{relation_id}'/>"
        )
        lines.append("  </node>")
        gap_ids.append(next_id)
        next_id -= 1

    rel_id = next_id
    lines.append(f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>")
    if way_id is not None:
        lines.append(f"    <member type='way' ref='{way_id}' role='path'/>")
    for nid in existing_ids:
        lines.append(f"    <member type='node' ref='{nid}' role='existing'/>")
    for nid in gap_ids:
        lines.append(f"    <member type='node' ref='{nid}' role='proposed'/>")
    for key, value in [
        ("type", "site"),
        ("name", f"{trail_name} (path + existing POIs + suggestions)"),
        ("network", "Pilegrimsleden"),
        ("note:trail", trail_name),
        ("note:osm_route_relation", str(relation_id)),
        (
            "note",
            "Single JOSM research file: path, existing overnight POIs, and new "
            f"suggestions. Only role=proposed nodes have note:proposed={PROPOSED_ADDITION}. "
            "Not an OSM import.",
        ),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </relation>")
    lines.append("</osm>")

    out = trail_dir / TRAIL_OSM_NAME
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(
        f"  wrote {TRAIL_OSM_NAME}: path={'yes' if way_id else 'no'}, "
        f"existing={len(existing)}, suggestions={len(gaps)}"
    )


def remove_other_osm_files(trail_dir: Path) -> None:
    for path in sorted(trail_dir.glob("*.osm")):
        if path.name == TRAIL_OSM_NAME:
            continue
        path.unlink()
        log(f"  removed {path.name}")


def update_shelters_csv(path: Path, rows: list[dict[str, str]]) -> None:
    for row in rows:
        if (row.get("match_status") or "") == "gap":
            row["proposal_note"] = PROPOSED_ADDITION
        else:
            row["proposal_note"] = ""
    fields = list(rows[0].keys()) if rows else []
    if "proposal_note" not in fields and rows:
        fields.append("proposal_note")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def process_trail(folder: str, trail_name: str, relation_id: int, root: Path) -> None:
    trail_dir = root / "data" / "by_trail" / folder
    csv_path = trail_dir / "shelters.csv"
    if not csv_path.exists():
        log(f"skip {folder}: no shelters.csv")
        return
    log(f"=== {folder} ===")
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    path_points = ensure_path_points(trail_dir, trail_name, relation_id)
    write_trail_osm(trail_dir, trail_name, relation_id, rows, path_points)
    update_shelters_csv(csv_path, rows)
    remove_other_osm_files(trail_dir)


def main() -> int:
    root = Path(__file__).resolve().parent
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else set()
    for folder, (trail_name, relation_id) in TRAIL_RELATIONS.items():
        if only and folder not in only:
            continue
        process_trail(folder, trail_name, relation_id, root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
