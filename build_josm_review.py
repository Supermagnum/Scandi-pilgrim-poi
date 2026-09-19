#!/usr/bin/env python3
"""Build exactly one OSM file per trail: data/by_trail/<Trail>/trail.osm

trail.osm contains:
  - trail path (densified research way)
  - existing CMS overnight POIs already in OSM
  - new CMS suggestions (note:proposed=Proposed addition)
  - existing OSM lodging near the route that is NOT yet a member of the live
    OSM route relation (real OSM nodes / ways / relations with full geometry)
    so they can be selected in JOSM and added to that relation

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
from extract_stolavsleden import haversine_m, xml_escape
from compare_osm_shelters import normalize_name
from propose_relation_additions import (
    TRAIL_RELATIONS,
    densify_for_index,
    fetch_route_segments,
    http_get,
    stitch_points,
)
from extract_pilegrimsleden_shelters import TRAILPOINTS_URL, USER_AGENT as SHELTER_UA

PROPOSED_ADDITION = "Proposed addition"
RELATION_MEMBER_NOTE = "Add as member of OSM route relation"
TRAIL_OSM_NAME = "trail.osm"

# CMS names that must not become local trail.osm nodes (already mapped in OSM).
SKIP_POI_NAMES: dict[str, set[str]] = {
    "Romeriksleden": {
        "Scandic hotell Gardermoen",
        "Scandic Hotel Gardermoen",
        "Scandic Gardermoen",
        "Thon Hotel Oslo Airport",
        "Thon Hotel Gardermoen",
        "Lysjøhimet",
        "Tangenodden Camping",
        "Fokhol Gård",
        "Fjetre gård - midelrtidig stengt",
        "Gapahuk ved Nordsveodden i Ottestad",
        "Vikingskipet Hotell og Spiseri",
        "Scandic Hotel Hamar",
        "Thon Partner Hotel - Victoria Hamar",
        "Pilegrimssenter Hamar - Pilegrimsherberge",
        "Hedmarktoppen",
        "Gapahuk i Furuberget",
        "Brøttum Camping",
        "Brynn i Bergsengroa",
        "Lillehammer Vandrerhjem Stasjonen",
        "Øvergaard i Lillehammer tilbyr overnatting i sentrum for pilegrimer",
        "Birkebeineren Hotel & Apartments",
    },
}

# Correct coordinates for CMS rows that exist but were misplaced in the extract.
MOVE_POI_COORDS: dict[str, dict[str, tuple[float, float]]] = {
    "Romeriksleden": {
        "Pilegrimsherberget Millom": (60.5506874, 11.2707785),  # Kjeldsrudvegen 95
        "Overnatting hos Atlungstad golf": (60.7586259, 11.0800532),  # Sandvikaveien 222
        "Sveen gård (Airbnb)": (60.7615665, 11.0810131),  # Sandvikavegen 180
    },
}

# Buildings / areas that must appear with real geometry in trail.osm (not proxies).
# NOTE: do not treat bare bygningsnr integers as OSM way ids (way/23439344 is in
# St. Petersburg and was a false positive from "23439344 building ref number").
REQUIRED_OSM_OBJECTS: dict[str, list[str]] = {
    "Romeriksleden": [
        "way/303953979",  # Vikingskipet Hotell og Spiseri
        "way/633872773",  # correct building for misplaced node/6800398116
        "way/98811698",  # Pilegrimssenter Hamar
        "way/1004901845",  # Brynn i Bergsengroa
        "way/315143760",  # Gapahuk i Furuberget
        "relation/3836486",  # Thon Partner Hotel Victoria Hamar (multipolygon)
    ],
}

# Strong overnight lodging suitable for OSM route-relation membership proposals.
ROUTE_ADD_LODGING_TOURISM = {
    "hotel",
    "hostel",
    "guest_house",
    "chalet",
    "cabin",
    "apartment",
    "camp_site",
    "caravan_site",
    "wilderness_hut",
    "alpine_hut",
}
ROUTE_ADD_CAMP_TOURISM = {
    "camp_site",
    "caravan_site",
    "wilderness_hut",
    "alpine_hut",
}
# Max distance from densified route geometry for route_add (metres).
ROUTE_ADD_MAX_M_LODGING = 500.0
ROUTE_ADD_MAX_M_CAMP = 1000.0
ROUTE_ADD_MAX_M_SHELTER = 100.0
ROUTE_ADD_MAX_M_PILGRIM = 2000.0
# route_add must also sit near an official kart overnight POI for that trail.
ROUTE_ADD_MAX_M_MAP_POI = 500.0

# folder -> Craft CMS trail id used by /actions/pilegrimsleden/poi/trailpoints
CMS_TRAIL_IDS: dict[str, int] = {
    "Norway/Gudbrandsdalsleden": 212,
    "Sweden/St-Olavsleden": 190,
    "Norway/Borgleden": 175,
    "Norway/Kystpilegrimsleia": 97,
    "Norway/Tunsbergleden": 6418,
    "Norway/Osterdalsleden": 182,
    "Norway/Valldalsleden": 132,
    "Norway/Romboleden": 202,
    "Norway/Nordleden": 194,
    # Norway/Romeriksleden is not a selectable trail on pilegrimsleden.no/kart
}

MAP_OVERNIGHT_CATEGORIES = {
    "Overnatting",
    "Hotell",
    "Gapahuk",
    "Rom og hytter",
    "Vandrerhjem",
    "Campingplass",
    "Teltplass",
    "Pilegrimsherberge",
    "Dagsturhytte",
    "Pilegrimsbu",
    "Rorbu",
    "Glamping",
    "Rasteplass",
}

# Research dumps replaced by README.md (removed after README is written).
RESEARCH_GLOBS = (
    "*.csv",
    "relation_additions_summary.json",
)


def log(message: str) -> None:
    print(message, flush=True)


def _is_pilgrimish_name(name: str) -> bool:
    n = (name or "").lower()
    return any(
        token in n
        for token in (
            "pilegrim",
            "pilgrim",
            "gapahuk",
            "vandrerhjem",
            "herberge",
        )
    )


def nearest_route_distance_m(
    lat: float, lon: float, path_points: list[tuple[float, float]]
) -> float:
    if not path_points:
        return float("nan")
    # Coarse sample then local refine around best coarse hit.
    step = max(1, len(path_points) // 2500)
    best_i = 0
    best = float("inf")
    for i in range(0, len(path_points), step):
        plat, plon = path_points[i]
        d = haversine_m(lat, lon, plat, plon)
        if d < best:
            best = d
            best_i = i
    lo = max(0, best_i - step)
    hi = min(len(path_points), best_i + step + 1)
    for plat, plon in path_points[lo:hi]:
        d = haversine_m(lat, lon, plat, plon)
        if d < best:
            best = d
    return best


def is_route_add_candidate(
    row: dict[str, str],
    *,
    path_points: list[tuple[float, float]] | None = None,
) -> bool:
    """Keep only lodging that belongs near the trail for route membership.

    The old 2 km vacuum included downtown hotels, picnic sites, and random
    amenity=shelter lean-tos that are not part of the pilgrim routes.
    """
    tourism = (row.get("tourism") or "").strip()
    amenity = (row.get("amenity") or "").strip()
    name = (row.get("name") or "").strip()
    pilgrimage = (row.get("pilgrimage") or "").strip()
    network = (row.get("network") or "").strip()
    try:
        dist = float(row.get("route_distance_m") or "nan")
    except ValueError:
        dist = float("nan")
    if math.isnan(dist) and path_points:
        try:
            lat = float(row["lat"])
            lon = float(row["lon"])
        except (KeyError, TypeError, ValueError):
            return False
        dist = nearest_route_distance_m(lat, lon, path_points)
        row["route_distance_m"] = f"{dist:.1f}"

    pilgrimish = bool(
        pilgrimage
        or network == "Pilegrimsleden"
        or _is_pilgrimish_name(name)
    )

    if tourism == "picnic_site":
        return False
    if tourism == "information":
        if not pilgrimish:
            return False
        return not math.isnan(dist) and dist <= ROUTE_ADD_MAX_M_PILGRIM

    if tourism in ROUTE_ADD_LODGING_TOURISM:
        if pilgrimish:
            limit = ROUTE_ADD_MAX_M_PILGRIM
        elif tourism in ROUTE_ADD_CAMP_TOURISM:
            limit = ROUTE_ADD_MAX_M_CAMP
        else:
            limit = ROUTE_ADD_MAX_M_LODGING
        return not math.isnan(dist) and dist <= limit

    if amenity == "shelter":
        limit = (
            ROUTE_ADD_MAX_M_PILGRIM if pilgrimish else ROUTE_ADD_MAX_M_SHELTER
        )
        return not math.isnan(dist) and dist <= limit

    # Bare buildings / other tags: only via REQUIRED_OSM_OBJECTS.
    return False


def filter_route_add_candidates(
    candidates: list[dict[str, str]],
    folder: str,
    *,
    path_points: list[tuple[float, float]] | None = None,
    map_overnight: list[dict[str, float | str]] | None = None,
) -> list[dict[str, str]]:
    required = set(REQUIRED_OSM_OBJECTS.get(folder, [])) | set(
        REQUIRED_OSM_OBJECTS.get(folder_basename(folder), [])
    )
    kept: list[dict[str, str]] = []
    dropped = 0
    dropped_off_map = 0
    for row in candidates:
        osm_id = (row.get("osm_id") or "").strip()
        if osm_id in required:
            kept.append(row)
            continue
        if not is_route_add_candidate(row, path_points=path_points):
            dropped += 1
            continue
        if map_overnight is not None:
            try:
                lat = float(row["lat"])
                lon = float(row["lon"])
            except (KeyError, TypeError, ValueError):
                dropped += 1
                dropped_off_map += 1
                continue
            near = False
            for poi in map_overnight:
                d = haversine_m(
                    lat, lon, float(poi["lat"]), float(poi["lon"])
                )
                if d <= ROUTE_ADD_MAX_M_MAP_POI:
                    near = True
                    break
            if not near:
                dropped += 1
                dropped_off_map += 1
                continue
        kept.append(row)
    if dropped:
        extra = (
            f", of which {dropped_off_map} not near kart overnight POIs"
            if dropped_off_map
            else ""
        )
        log(
            f"  filtered route_add: kept {len(kept)}, dropped {dropped} "
            f"(off-trail / picnic / weak shelter{extra})"
        )
    return kept


def fetch_map_overnight_pois(trail_id: int) -> list[dict[str, float | str]]:
    """Overnight/shelter POIs shown for a trail on pilegrimsleden.no/kart."""
    import json
    import urllib.parse
    import urllib.request

    url = (
        f"{TRAILPOINTS_URL}?{urllib.parse.urlencode({'trailId': trail_id})}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": SHELTER_UA,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        rows = json.loads(resp.read().decode("utf-8"))
    out: list[dict[str, float | str]] = []
    for row in rows:
        lat = row.get("lt")
        lon = row.get("ln")
        if lat is None or lon is None:
            continue
        cats = set(row.get("cs") or [])
        if row.get("c"):
            cats.add(row["c"])
        if not (cats & MAP_OVERNIGHT_CATEGORIES):
            continue
        out.append(
            {
                "id": row.get("id") or "",
                "title": row.get("t") or "",
                "lat": float(lat),
                "lon": float(lon),
            }
        )
    return out


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
        tags = {t.attrib["k"]: t.attrib["v"] for t in way.findall("tag")}
        # Prefer the densified research path; ignore real OSM building ways.
        if tags.get("highway") != "path" and "note:trail" not in tags:
            continue
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
    poi_name = (row.get("poi_name") or "").strip()
    osm_name = (row.get("matched_osm_name") or "").strip()
    # When OSM already has a name, keep it and store the pilgrim CMS title as alt_name.
    if osm_name and poi_name and normalize_name(osm_name) != normalize_name(poi_name):
        name_tags: list[tuple[str, str]] = [("name", osm_name), ("alt_name", poi_name)]
    else:
        name_tags = [("name", poi_name or osm_name)]
    tags: list[tuple[str, str]] = [
        *name_tags,
        ("source", "pilegrimsleden.no"),
        ("network", "Pilegrimsleden"),
        ("note:trail", row.get("trail") or ""),
    ]
    tags.extend(mapping)
    if proposed:
        tags.append(("note:proposed", PROPOSED_ADDITION))
    return [(k, v) for k, v in tags if v]


def load_relation_candidates(
    root: Path, folder: str
) -> list[dict[str, str]]:
    """OSM lodging near the route that is not yet on the live route relation."""
    research_dir = root / "data" / "research_by_trail" / folder
    trail_dir = root / "data" / "by_trail" / folder
    for path in (
        research_dir / "osm_missing_for_relation.csv",
        trail_dir / "osm_missing_for_relation.csv",
    ):
        rows = load_csv_rows(path)
        if rows:
            return rows
    recovered = recover_candidates_from_trail_osm(trail_dir / TRAIL_OSM_NAME)
    if recovered:
        log(
            f"  recovered {len(recovered)} relation candidates from existing "
            f"{TRAIL_OSM_NAME}"
        )
    return recovered


def recover_candidates_from_trail_osm(path: Path) -> list[dict[str, str]]:
    """Rebuild route_add candidate rows from an existing trail.osm."""
    if not path.exists():
        return []
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    nodes = {
        n.attrib["id"]: n
        for n in root.findall("node")
        if "lat" in n.attrib and "lon" in n.attrib
    }
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    def _append(
        osm_id: str,
        lat: str,
        lon: str,
        tags: dict[str, str],
    ) -> None:
        if osm_id in seen:
            return
        seen.add(osm_id)
        rows.append(
            {
                "osm_id": osm_id,
                "lat": lat,
                "lon": lon,
                "name": tags.get("name") or "",
                "tourism": tags.get("tourism") or "",
                "amenity": tags.get("amenity") or "",
                "building": tags.get("building") or "",
            }
        )

    for node in root.findall("node"):
        tags = {t.attrib["k"]: t.attrib["v"] for t in node.findall("tag")}
        if "note:relation_member" not in tags:
            continue
        lat = node.attrib.get("lat")
        lon = node.attrib.get("lon")
        if not lat or not lon:
            continue
        osm_object = (tags.get("note:osm_object") or "").strip()
        if osm_object:
            osm_id = osm_object
        else:
            try:
                nid = int(node.attrib["id"])
            except (KeyError, ValueError):
                continue
            if nid <= 0:
                continue
            osm_id = f"node/{nid}"
        _append(osm_id, lat, lon, tags)

    for way in root.findall("way"):
        tags = {t.attrib["k"]: t.attrib["v"] for t in way.findall("tag")}
        if "note:relation_member" not in tags:
            continue
        try:
            wid = int(way.attrib["id"])
        except (KeyError, ValueError):
            continue
        if wid <= 0:
            continue
        pts: list[tuple[float, float]] = []
        for nd in way.findall("nd"):
            node = nodes.get(nd.attrib.get("ref") or "")
            if node is None:
                continue
            pts.append((float(node.attrib["lat"]), float(node.attrib["lon"])))
        if not pts:
            continue
        lat = sum(p[0] for p in pts) / len(pts)
        lon = sum(p[1] for p in pts) / len(pts)
        _append(f"way/{wid}", f"{lat:.7f}", f"{lon:.7f}", tags)

    for rel in root.findall("relation"):
        tags = {t.attrib["k"]: t.attrib["v"] for t in rel.findall("tag")}
        if "note:relation_member" not in tags:
            continue
        try:
            rid = int(rel.attrib["id"])
        except (KeyError, ValueError):
            continue
        if rid <= 0:
            continue
        pts = []
        for member in rel.findall("member"):
            if member.attrib.get("type") != "way":
                continue
            way = root.find(f"./way[@id='{member.attrib.get('ref')}']")
            if way is None:
                continue
            for nd in way.findall("nd"):
                node = nodes.get(nd.attrib.get("ref") or "")
                if node is None:
                    continue
                pts.append((float(node.attrib["lat"]), float(node.attrib["lon"])))
        if not pts:
            continue
        lat = sum(p[0] for p in pts) / len(pts)
        lon = sum(p[1] for p in pts) / len(pts)
        _append(f"relation/{rid}", f"{lat:.7f}", f"{lon:.7f}", tags)

    return rows


def recover_cms_rows_from_trail_osm(path: Path, trail_name: str) -> list[dict[str, str]]:
    """Rebuild CMS shelter rows from existing/proposed nodes in trail.osm."""
    if not path.exists():
        return []
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    rows: list[dict[str, str]] = []
    for node in root.findall("node"):
        tags = {t.attrib["k"]: t.attrib["v"] for t in node.findall("tag")}
        if tags.get("source") != "pilegrimsleden.no":
            continue
        if "note:relation_member" in tags or tags.get("note:osm_object"):
            continue
        lat = node.attrib.get("lat")
        lon = node.attrib.get("lon")
        if not lat or not lon:
            continue
        proposed = "note:proposed" in tags
        rows.append(
            {
                "trail": tags.get("note:trail") or trail_name,
                "poi_name": tags.get("name") or tags.get("alt_name") or "",
                "category": "Overnatting",
                "lat": lat,
                "lon": lon,
                "match_status": "gap" if proposed else "matched",
                "matched_osm_name": tags.get("name") or "",
            }
        )
    return rows


def folder_basename(folder: str) -> str:
    return Path(folder).name


def merge_required_osm_objects(
    candidates: list[dict[str, str]], folder: str
) -> list[dict[str, str]]:
    """Ensure correction buildings/areas are present as route_add candidates."""
    required_ids = list(
        dict.fromkeys(
            REQUIRED_OSM_OBJECTS.get(folder, [])
            + REQUIRED_OSM_OBJECTS.get(folder_basename(folder), [])
        )
    )
    if not required_ids:
        return candidates
    by_id = {
        (row.get("osm_id") or "").strip(): row
        for row in candidates
        if (row.get("osm_id") or "").strip()
    }
    for osm_id in required_ids:
        if osm_id in by_id:
            continue
        try:
            kind, oid_s = osm_id.split("/", 1)
            oid = int(oid_s)
        except ValueError:
            continue
        lat, lon, name, tourism, amenity, building = lookup_osm_object_meta(
            kind, oid
        )
        if lat is None or lon is None:
            log(f"  WARNING: could not resolve required {osm_id}")
            continue
        row = {
            "osm_id": osm_id,
            "lat": f"{lat:.7f}",
            "lon": f"{lon:.7f}",
            "name": name,
            "tourism": tourism,
            "amenity": amenity,
            "building": building,
        }
        candidates.append(row)
        by_id[osm_id] = row
        log(f"  added required building/area {osm_id}")
    return candidates


def lookup_osm_object_meta(
    kind: str, oid: int
) -> tuple[float | None, float | None, str, str, str, str]:
    """Return centroid + key tags for an OSM node/way/relation."""
    url = f"https://www.openstreetmap.org/api/0.6/{kind}/{oid}/full"
    root = ET.fromstring(http_get(url, timeout=120))
    nodes = {
        n.attrib["id"]: (float(n.attrib["lat"]), float(n.attrib["lon"]))
        for n in root.findall("node")
        if "lat" in n.attrib and "lon" in n.attrib
    }
    if kind == "node":
        el = root.find("node")
        if el is None or el.attrib.get("id") != str(oid):
            return None, None, "", "", "", ""
        tags = {t.attrib["k"]: t.attrib["v"] for t in el.findall("tag")}
        return (
            float(el.attrib["lat"]),
            float(el.attrib["lon"]),
            tags.get("name") or "",
            tags.get("tourism") or "",
            tags.get("amenity") or "",
            tags.get("building") or "",
        )
    if kind == "way":
        el = root.find(f"./way[@id='{oid}']")
        if el is None:
            for way in root.findall("way"):
                if way.attrib.get("id") == str(oid):
                    el = way
                    break
        if el is None:
            return None, None, "", "", "", ""
        tags = {t.attrib["k"]: t.attrib["v"] for t in el.findall("tag")}
        pts = [
            nodes[nd.attrib["ref"]]
            for nd in el.findall("nd")
            if nd.attrib.get("ref") in nodes
        ]
        if not pts:
            return None, None, "", "", "", ""
        lat = sum(p[0] for p in pts) / len(pts)
        lon = sum(p[1] for p in pts) / len(pts)
        return (
            lat,
            lon,
            tags.get("name") or "",
            tags.get("tourism") or "",
            tags.get("amenity") or "",
            tags.get("building") or "",
        )
    el = None
    for rel in root.findall("relation"):
        if rel.attrib.get("id") == str(oid):
            el = rel
            break
    if el is None:
        return None, None, "", "", "", ""
    tags = {t.attrib["k"]: t.attrib["v"] for t in el.findall("tag")}
    if nodes:
        lat = sum(p[0] for p in nodes.values()) / len(nodes)
        lon = sum(p[1] for p in nodes.values()) / len(nodes)
    else:
        return None, None, "", "", "", ""
    return (
        lat,
        lon,
        tags.get("name") or "",
        tags.get("tourism") or "",
        tags.get("amenity") or "",
        tags.get("building") or "",
    )


def _attr_xml(attrs: dict[str, str], keys: list[str]) -> str:
    parts: list[str] = []
    for key in keys:
        if key in attrs:
            parts.append(f"{key}='{xml_escape(attrs[key])}'")
    for key, value in attrs.items():
        if key in keys:
            continue
        parts.append(f"{key}='{xml_escape(value)}'")
    return " ".join(parts)


def serialize_osm_element(
    el: ET.Element,
    *,
    extra_tags: list[tuple[str, str]] | None = None,
) -> list[str]:
    """Serialize one OSM XML element using the trail.osm single-quote style."""
    tag = el.tag
    attrs = dict(el.attrib)
    lines: list[str] = []
    if tag == "node":
        order = ["id", "version", "timestamp", "uid", "user", "changeset", "visible", "lat", "lon"]
        children = list(el)
        if not children and not extra_tags:
            lines.append(f"  <node {_attr_xml(attrs, order)}/>")
            return lines
        lines.append(f"  <node {_attr_xml(attrs, order)}>")
    elif tag == "way":
        order = ["id", "version", "timestamp", "uid", "user", "changeset", "visible"]
        lines.append(f"  <way {_attr_xml(attrs, order)}>")
        for nd in el.findall("nd"):
            lines.append(f"    <nd ref='{xml_escape(nd.attrib['ref'])}'/>")
    elif tag == "relation":
        order = ["id", "version", "timestamp", "uid", "user", "changeset", "visible"]
        lines.append(f"  <relation {_attr_xml(attrs, order)}>")
        for member in el.findall("member"):
            mtype = member.attrib.get("type") or ""
            ref = member.attrib.get("ref") or ""
            role = member.attrib.get("role") or ""
            lines.append(
                f"    <member type='{xml_escape(mtype)}' ref='{xml_escape(ref)}' "
                f"role='{xml_escape(role)}'/>"
            )
    else:
        return []

    existing = {t.attrib["k"] for t in el.findall("tag") if "k" in t.attrib}
    for tag_el in el.findall("tag"):
        key = tag_el.attrib.get("k")
        val = tag_el.attrib.get("v")
        if key is None or val is None:
            continue
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(val)}'/>")
    for key, val in extra_tags or []:
        if not val or key in existing:
            continue
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(val)}'/>")
        existing.add(key)
    lines.append(f"  </{tag}>")
    return lines


def append_full_osm_object(
    lines: list[str],
    *,
    kind: str,
    oid: int,
    relation_id: int,
    seen_elements: set[tuple[str, str]],
    name_fallback: str = "",
    pbf_cache: dict[tuple[str, int], dict] | None = None,
) -> bool:
    """Append real OSM geometry into trail.osm lines (PBF cache or API /full)."""
    note = f"{RELATION_MEMBER_NOTE} {relation_id}"
    extra = [
        ("note:relation_member", note),
        ("note:osm_route_relation", str(relation_id)),
    ]
    if name_fallback:
        extra.append(("name", name_fallback))

    cached = (pbf_cache or {}).get((kind, oid))
    if cached and kind == "way":
        primary_key = ("way", str(oid))
        if primary_key in seen_elements:
            return True
        for nid, (lat, lon) in cached["nodes"].items():
            nkey = ("node", str(nid))
            if nkey in seen_elements:
                continue
            seen_elements.add(nkey)
            lines.append(
                f"  <node id='{nid}' version='1' visible='true' "
                f"lat='{lat:.7f}' lon='{lon:.7f}'/>"
            )
        attrs = {"id": str(oid), "version": str(cached.get("version") or "1"), "visible": "true"}
        lines.append(f"  <way {_attr_xml(attrs, ['id', 'version', 'visible'])}>")
        for nid in cached["node_refs"]:
            lines.append(f"    <nd ref='{nid}'/>")
        existing = set(cached["tags"])
        for key, val in cached["tags"].items():
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(val)}'/>")
        for key, val in extra:
            if not val or key in existing:
                continue
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(val)}'/>")
            existing.add(key)
        lines.append("  </way>")
        seen_elements.add(primary_key)
        return True

    url = f"https://www.openstreetmap.org/api/0.6/{kind}/{oid}/full"
    root = ET.fromstring(http_get(url, timeout=120))
    primary_found = False
    for child_kind in ("node", "way", "relation"):
        for el in root.findall(child_kind):
            eid = el.attrib.get("id")
            if not eid:
                continue
            key = (child_kind, eid)
            is_primary = child_kind == kind and eid == str(oid)
            if key in seen_elements:
                if is_primary:
                    primary_found = True
                continue
            seen_elements.add(key)
            if is_primary:
                primary_found = True
                lines.extend(serialize_osm_element(el, extra_tags=extra))
            else:
                lines.extend(serialize_osm_element(el))
    return primary_found


def load_ways_from_pbf(
    pbf_path: Path, way_ids: set[int]
) -> dict[tuple[str, int], dict]:
    """Load selected ways + node coordinates from a Geofabrik PBF."""
    if not way_ids or not pbf_path.exists():
        return {}
    import osmium

    class Handler(osmium.SimpleHandler):
        def __init__(self) -> None:
            super().__init__()
            self.out: dict[tuple[str, int], dict] = {}

        def way(self, way: object) -> None:
            wid = int(way.id)  # type: ignore[attr-defined]
            if wid not in way_ids:
                return
            nodes: dict[int, tuple[float, float]] = {}
            refs: list[int] = []
            try:
                for node in way.nodes:  # type: ignore[attr-defined]
                    if not node.location.valid():
                        continue
                    nid = int(node.ref)
                    nodes[nid] = (float(node.location.lat), float(node.location.lon))
                    refs.append(nid)
            except osmium.InvalidLocationError:
                return
            if len(refs) < 2:
                return
            tags = {tag.k: tag.v for tag in way.tags}  # type: ignore[attr-defined]
            self.out[("way", wid)] = {
                "nodes": nodes,
                "node_refs": refs,
                "tags": tags,
                "version": int(getattr(way, "version", 1) or 1),
            }

    log(f"  loading {len(way_ids)} ways from {pbf_path.name}")
    handler = Handler()
    handler.apply_file(str(pbf_path), locations=True, idx="flex_mem")
    log(f"  loaded {len(handler.out)} ways from PBF")
    return handler.out


def load_ways_from_pbfs(
    pbf_paths: list[Path], way_ids: set[int]
) -> dict[tuple[str, int], dict]:
    """Load selected ways from one or more Geofabrik PBFs (merge hits)."""
    merged: dict[tuple[str, int], dict] = {}
    remaining = set(way_ids)
    for pbf_path in pbf_paths:
        if not remaining:
            break
        if not pbf_path.exists():
            continue
        found = load_ways_from_pbf(pbf_path, remaining)
        merged.update(found)
        remaining -= {oid for (_kind, oid) in found}
    return merged


def append_relation_candidate_nodes(
    lines: list[str],
    *,
    candidates: list[dict[str, str]],
    relation_id: int,
    next_id: int,
    pbf_paths: list[Path] | None = None,
) -> tuple[list[tuple[str, int]], int]:
    """Emit OSM lodging so JOSM can add them to the live route relation.

    Nodes keep their real positive OSM ids. Ways and relations are embedded with
    full geometry (building outlines / multipolygons), not centroids.
    """
    member_refs: list[tuple[str, int]] = []
    note = f"{RELATION_MEMBER_NOTE} {relation_id}"
    seen_elements: set[tuple[str, str]] = set()

    way_ids: set[int] = set()
    for row in candidates:
        osm_id = (row.get("osm_id") or "").strip()
        try:
            kind, oid_s = osm_id.split("/", 1)
            oid = int(oid_s)
        except ValueError:
            continue
        if kind == "way":
            way_ids.add(oid)
    pbf_cache: dict[tuple[str, int], dict] = {}
    if pbf_paths and way_ids:
        pbf_cache = load_ways_from_pbfs(pbf_paths, way_ids)

    for row in candidates:
        osm_id = (row.get("osm_id") or "").strip()
        try:
            kind, oid_s = osm_id.split("/", 1)
            oid = int(oid_s)
            lat = float(row["lat"])
            lon = float(row["lon"])
        except (ValueError, KeyError, TypeError):
            continue
        name = (row.get("name") or "").strip()
        if kind == "node":
            lines.append(
                f"  <node id='{oid}' version='1' visible='true' "
                f"lat='{lat:.7f}' lon='{lon:.7f}'>"
            )
            if name:
                lines.append(f"    <tag k='name' v='{xml_escape(name)}'/>")
            for key in ("tourism", "amenity", "building"):
                val = (row.get(key) or "").strip()
                if val:
                    lines.append(
                        f"    <tag k='{xml_escape(key)}' v='{xml_escape(val)}'/>"
                    )
            lines.append(f"    <tag k='note:relation_member' v='{xml_escape(note)}'/>")
            lines.append(
                f"    <tag k='note:osm_route_relation' v='{relation_id}'/>"
            )
            lines.append("  </node>")
            seen_elements.add(("node", str(oid)))
            member_refs.append(("node", oid))
            continue

        log(f"  embedding {osm_id}")
        ok = append_full_osm_object(
            lines,
            kind=kind,
            oid=oid,
            relation_id=relation_id,
            seen_elements=seen_elements,
            name_fallback=name,
            pbf_cache=pbf_cache,
        )
        if ok:
            member_refs.append((kind, oid))
        else:
            log(f"  WARNING: failed to embed {osm_id}")
    return member_refs, next_id


def write_trail_osm(
    trail_dir: Path,
    trail_name: str,
    relation_id: int,
    rows: list[dict[str, str]],
    path_points: list[tuple[float, float]],
    relation_candidates: list[dict[str, str]] | None = None,
    pbf_paths: list[Path] | None = None,
) -> tuple[int, int, int]:
    skip_names = SKIP_POI_NAMES.get(trail_dir.name, set()) | SKIP_POI_NAMES.get(
        trail_name, set()
    )
    move_coords = MOVE_POI_COORDS.get(trail_dir.name, {}) | MOVE_POI_COORDS.get(
        trail_name, {}
    )
    filtered: list[dict[str, str]] = []
    for r in rows:
        name = (r.get("poi_name") or "").strip()
        if name in skip_names:
            continue
        if name in move_coords:
            lat, lon = move_coords[name]
            r = dict(r)
            r["lat"] = f"{lat:.7f}"
            r["lon"] = f"{lon:.7f}"
        filtered.append(r)
    rows = filtered
    existing = [r for r in rows if r.get("match_status") in {"matched", "possible"}]
    gaps = [r for r in rows if (r.get("match_status") or "gap") == "gap"]
    candidates = list(relation_candidates or [])

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

    route_add_refs, next_id = append_relation_candidate_nodes(
        lines,
        candidates=candidates,
        relation_id=relation_id,
        next_id=next_id,
        pbf_paths=pbf_paths,
    )

    rel_id = next_id
    lines.append(f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>")
    if way_id is not None:
        lines.append(f"    <member type='way' ref='{way_id}' role='path'/>")
    for nid in existing_ids:
        lines.append(f"    <member type='node' ref='{nid}' role='existing'/>")
    for nid in gap_ids:
        lines.append(f"    <member type='node' ref='{nid}' role='proposed'/>")
    for mtype, mid in route_add_refs:
        lines.append(f"    <member type='{mtype}' ref='{mid}' role='route_add'/>")
    for key, value in [
        ("type", "site"),
        ("name", trail_name),
        ("network", "Pilegrimsleden"),
        ("note:trail", trail_name),
        (
            "note",
            "Local JOSM research file. role=route_add objects are existing OSM "
            f"lodging to consider adding to relation/{relation_id}.",
        ),
    ]:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </relation>")
    lines.append("</osm>")

    (trail_dir / TRAIL_OSM_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(
        f"  wrote {TRAIL_OSM_NAME}: path={'yes' if way_id else 'no'}, "
        f"existing={len(existing)}, suggestions={len(gaps)}, "
        f"route_add={len(route_add_refs)}"
    )
    return len(existing), len(gaps), len(route_add_refs)


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
    if national.exists():
        aliases = {trail_name, folder}
        if folder == "Osterdalsleden" or folder.endswith("/Osterdalsleden"):
            aliases.add("Østerdalsleden")
        if folder == "St-Olavsleden" or folder.endswith("/St-Olavsleden"):
            aliases.update({"St. Olavsleden", "St Olavsleden"})
        rows = [r for r in load_csv_rows(national) if (r.get("trail") or "") in aliases]
        if rows:
            return rows

    recovered = recover_cms_rows_from_trail_osm(trail_dir / TRAIL_OSM_NAME, trail_name)
    if recovered:
        log(f"  recovered {len(recovered)} CMS rows from existing {TRAIL_OSM_NAME}")
    return recovered


def write_trail_readme(
    trail_dir: Path,
    *,
    folder: str,
    trail_name: str,
    relation_id: int,
    shelters: list[dict[str, str]],
    existing_n: int,
    gaps_n: int,
    route_add_n: int,
) -> None:
    # folder may be nested (e.g. Sweden/St-Olavsleden)
    data_dir = trail_dir
    while data_dir.name != "by_trail" and data_dir.parent != data_dir:
        data_dir = data_dir.parent
    data_dir = data_dir.parent
    research_dir = data_dir / "research_by_trail" / folder
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
        "1. Trail **path** (one densified research way — not every OSM route way member)",
        "2. **Existing** overnight POIs (CMS matched) — no `note:proposed`",
        f"3. **New suggestions** — tagged `note:proposed={PROPOSED_ADDITION}`",
        "4. **OSM lodging to add to the live route relation** — role `route_add`, "
        f"search `note:relation_member={RELATION_MEMBER_NOTE}`",
        "",
        "Search in JOSM: `note:proposed=Proposed addition` or "
        f"`note:relation_member={RELATION_MEMBER_NOTE}`",
        "",
        "Do not expect research tags such as `pilegrimsleden:match_status` in this file.",
        "",
        "This file is a local `type=site` research relation. Uploading new CMS nodes",
        "as written does not rewrite membership of existing OSM route relations.",
        "Objects with role `route_add` are already in OSM; use them in JOSM to add",
        "members to the live route relation below (download/update those objects first).",
        "",
        "## OSM route relation",
        "",
        f"- Name: {trail_name}",
        f"- Relation: https://www.openstreetmap.org/relation/{relation_id}",
        "- Do not remove existing members of that relation from this research file.",
        "",
        "## Counts",
        "",
        f"| item | count |",
        f"| --- | ---: |",
        f"| Overnight POIs (CMS) | {len(shelters)} |",
        f"| Existing in trail.osm | {existing_n} |",
        f"| New suggestions in trail.osm | {gaps_n} |",
        f"| OSM lodging to add to route relation (`route_add`) | {route_add_n} |",
        f"| Pilgrim centers (reference) | {len(pilgrims)} |",
        f"| Pilgrim-center gaps (reference) | {pilgrim_gaps} |",
        f"| Lodging already on OSM relation | {len(already)} |",
        f"| Lodging near route not on relation (reference CSV) | {len(missing)} |",
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
            "Per-trail CSV dumps are not kept in this folder; relation candidates",
            "are embedded in `trail.osm` as `route_add` members.",
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
    candidates = load_relation_candidates(root, folder)
    candidates = merge_required_osm_objects(candidates, folder)
    map_overnight: list[dict[str, float | str]] | None = None
    cms_trail_id = CMS_TRAIL_IDS.get(folder)
    if cms_trail_id is not None:
        map_overnight = fetch_map_overnight_pois(cms_trail_id)
        log(
            f"  kart overnight POIs for trailId={cms_trail_id}: "
            f"{len(map_overnight)}"
        )
    else:
        log(
            "  no CMS trail id on pilegrimsleden.no/kart — "
            "route_add uses path distance only"
        )
    candidates = filter_route_add_candidates(
        candidates,
        folder,
        path_points=path_points,
        map_overnight=map_overnight,
    )
    if candidates:
        log(f"  relation candidates (route_add): {len(candidates)}")
    else:
        log(
            "  no osm_missing_for_relation.csv — run propose_relation_additions.py "
            "first to embed OSM lodging for relation membership"
        )
    geofabrik = root / "data" / "geofabrik"
    pbf_paths = [
        p
        for p in (
            geofabrik / "norway-latest.osm.pbf",
            geofabrik / "sweden-latest.osm.pbf",
        )
        if p.exists()
    ]
    # Prefer the country PBF that covers most of the trail first.
    if (folder == "St-Olavsleden" or folder.endswith("/St-Olavsleden")) and len(
        pbf_paths
    ) == 2:
        pbf_paths = [pbf_paths[1], pbf_paths[0]]
    existing_n, gaps_n, route_add_n = write_trail_osm(
        trail_dir,
        trail_name,
        relation_id,
        shelters,
        path_points,
        relation_candidates=candidates,
        pbf_paths=pbf_paths or None,
    )
    write_trail_readme(
        trail_dir,
        folder=folder,
        trail_name=trail_name,
        relation_id=relation_id,
        shelters=shelters,
        existing_n=existing_n,
        gaps_n=gaps_n,
        route_add_n=route_add_n,
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
