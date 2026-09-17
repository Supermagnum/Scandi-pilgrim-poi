#!/usr/bin/env python3
"""Build exactly one OSM file per trail: data/by_trail/<Trail>/trail.osm

trail.osm contains:
  - trail path
  - existing CMS overnight POIs (already in OSM) — no note:proposed
  - new suggestions (CMS gaps) — note:proposed=Proposed addition

Does not write research tags such as pilegrimsleden:match_status into the OSM file.
Replaces per-trail CSV/JSON research dumps with a short README.md, then removes
those CSV/JSON files from the trail folder.
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

# Research dumps replaced by README.md (removed after README is written).
RESEARCH_GLOBS = (
    "*.csv",
    "relation_additions_summary.json",
)


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
    """OSM tags suitable for JOSM — no research/match_status keys."""
    cats = [c.strip() for c in (row.get("category") or "").split("|") if c.strip()]
    primary = (
        primary_category(cats)
        if any(c in CATEGORY_PRIORITY for c in cats)
        else ("Overnatting" if "Overnatting" in cats else (cats[0] if cats else ""))
    )
    if primary == "Overnatting":
        mapping: list[tuple[str, str]] = [("tourism", "guest_house")]
    else:
        mapping, _uncertain = osm_tags_for_category(primary)
    tags: list[tuple[str, str]] = [
        ("name", row.get("poi_name") or ""),
        ("source", "pilegrimsleden.no"),
        ("network", "Pilegrimsleden"),
        ("note:trail", row.get("trail") or ""),
    ]
    tags.extend(mapping)
    if proposed:
        tags.append(("note:proposed", PROPOSED_ADDITION))
    return [(k, v) for k, v in tags if v]


def write_trail_osm(
    trail_dir: Path,
    trail_name: str,
    relation_id: int,
    rows: list[dict[str, str]],
    path_points: list[tuple[float, float]],
) -> tuple[int, int]:
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
        ("name", trail_name),
        ("network", "Pilegrimsleden"),
        ("note:trail", trail_name),
        (
            "note",
            "Local research site relation grouping path, existing overnight POIs, "
            f"and new suggestions. Only role=proposed nodes have note:proposed={PROPOSED_ADDITION}. "
            "Not an OSM import.",
        ),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </relation>")
    lines.append("</osm>")

    (trail_dir / TRAIL_OSM_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(
        f"  wrote {TRAIL_OSM_NAME}: path={'yes' if way_id else 'no'}, "
        f"existing={len(existing)}, suggestions={len(gaps)}"
    )
    return len(existing), len(gaps)


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_shelters_for_trail(root: Path, folder: str, trail_name: str) -> list[dict[str, str]]:
    trail_dir = root / "data" / "by_trail" / folder
    research_dir = root / "data" / "research_by_trail" / folder
    for path in (
        trail_dir / "shelters.csv",
        research_dir / "shelters.csv",
    ):
        rows = load_csv_rows(path)
        if rows:
            return rows

    national = root / "data" / "osm_comparison_results.csv"
    if not national.exists():
        return []
    aliases = {trail_name, folder}
    if folder == "Osterdalsleden":
        aliases.add("Østerdalsleden")
    if folder == "St-Olavsleden":
        aliases.update({"St. Olavsleden", "St Olavsleden"})
    return [r for r in load_csv_rows(national) if (r.get("trail") or "") in aliases]


def write_trail_readme(
    trail_dir: Path,
    *,
    folder: str,
    trail_name: str,
    relation_id: int,
    shelters: list[dict[str, str]],
    existing_n: int,
    gaps_n: int,
) -> None:
    research_dir = trail_dir.parent.parent / "research_by_trail" / folder
    missing = load_csv_rows(research_dir / "osm_missing_for_relation.csv")
    if not missing:
        missing = load_csv_rows(trail_dir / "osm_missing_for_relation.csv")
    already = load_csv_rows(research_dir / "osm_already_related.csv")
    if not already:
        already = load_csv_rows(trail_dir / "osm_already_related.csv")
    pilgrims = load_csv_rows(research_dir / "pilgrim_centers.csv")
    if not pilgrims:
        pilgrims = load_csv_rows(trail_dir / "pilgrim_centers.csv")
    pilgrim_gaps = sum(1 for r in pilgrims if r.get("match_status") == "gap")
    horse = load_csv_rows(research_dir / "horseback_service_points.csv")
    if not horse:
        horse = load_csv_rows(trail_dir / "horseback_service_points.csv")
    gap_names = [
        r.get("poi_name") or ""
        for r in shelters
        if (r.get("match_status") or "gap") == "gap" and r.get("poi_name")
    ]
    gap_names.sort(key=str.lower)

    lines = [
        f"# {trail_name}",
        "",
        f"Folder: `{folder}`",
        "",
        "## Open in JOSM",
        "",
        f"Open `{TRAIL_OSM_NAME}` in this folder (the only `.osm` file).",
        "",
        "It contains:",
        "",
        "1. Trail **path**",
        "2. **Existing** overnight POIs (already present in OSM) — no `note:proposed`",
        f"3. **New suggestions** — tagged `note:proposed={PROPOSED_ADDITION}`",
        "",
        "Search in JOSM: `note:proposed=Proposed addition`",
        "",
        "Do not expect research tags such as `pilegrimsleden:match_status` in this file.",
        "",
        "## OSM route relation",
        "",
        f"- Name: {trail_name}",
        f"- Relation: https://www.openstreetmap.org/relation/{relation_id}",
        "- Do not modify existing members of that relation from this research file.",
        "",
        "## Counts",
        "",
        f"| item | count |",
        f"| --- | ---: |",
        f"| Overnight POIs (CMS) | {len(shelters)} |",
        f"| Existing in trail.osm | {existing_n} |",
        f"| New suggestions in trail.osm | {gaps_n} |",
        f"| Pilgrim centers (reference) | {len(pilgrims)} |",
        f"| Pilgrim-center gaps (reference) | {pilgrim_gaps} |",
        f"| Lodging already on OSM relation | {len(already)} |",
        f"| Lodging near route not on relation (reference) | {len(missing)} |",
    ]
    if horse:
        lines.append(f"| Horseback service points (reference) | {len(horse)} |")
    lines.extend(["", "## New suggestions (names)", ""])
    if gap_names:
        for name in gap_names:
            lines.append(f"- {name}")
    else:
        lines.append("- (none)")
    lines.extend(
        [
            "",
            "## Files in this folder",
            "",
            f"- `{TRAIL_OSM_NAME}` — open this in JOSM",
            "- `README.md` — this file (replaces per-trail CSV dumps)",
            "- `hiking_path.gpx` — optional path cache",
        ]
    )
    if (trail_dir / "horseback_path.gpx").exists():
        lines.append(
            "- `horseback_path.gpx` — horseback alignment (St. Olavsleden); not in trail.osm"
        )
    lines.extend(
        [
            "",
            "Per-trail CSV dumps are not kept in this folder.",
            "",
        ]
    )
    (trail_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    log("  wrote README.md")


def remove_other_osm_files(trail_dir: Path) -> None:
    for path in sorted(trail_dir.glob("*.osm")):
        if path.name == TRAIL_OSM_NAME:
            continue
        path.unlink()
        log(f"  removed {path.name}")


def remove_research_csvs(trail_dir: Path) -> None:
    removed: list[str] = []
    for pattern in RESEARCH_GLOBS:
        for path in sorted(trail_dir.glob(pattern)):
            path.unlink()
            removed.append(path.name)
    for name in removed:
        log(f"  removed {name}")


def process_trail(folder: str, trail_name: str, relation_id: int, root: Path) -> None:
    trail_dir = root / "data" / "by_trail" / folder
    log(f"=== {folder} ===")
    shelters = load_shelters_for_trail(root, folder, trail_name)
    if not shelters:
        log("  no shelter rows found — skip")
        return
    path_points = ensure_path_points(trail_dir, trail_name, relation_id)
    existing_n, gaps_n = write_trail_osm(
        trail_dir, trail_name, relation_id, shelters, path_points
    )
    write_trail_readme(
        trail_dir,
        folder=folder,
        trail_name=trail_name,
        relation_id=relation_id,
        shelters=shelters,
        existing_n=existing_n,
        gaps_n=gaps_n,
    )
    remove_other_osm_files(trail_dir)
    remove_research_csvs(trail_dir)


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
