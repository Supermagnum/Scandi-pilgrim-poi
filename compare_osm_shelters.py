#!/usr/bin/env python3
"""Read-only comparison of Pilegrimsleden shelter POIs against existing OSM data.

Uses OSM changeset 187258738 as the reference tagging scheme for pilgrim centers.
Does not upload or modify OpenStreetMap.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(OSM mapping research; read-only comparison of Pilegrimsleden shelters "
    "against existing OSM data; +https://www.openstreetmap.org/)"
)
OSM_CHANGESET_META = "https://www.openstreetmap.org/api/0.6/changeset/187258738"
OSM_CHANGESET_DOWNLOAD = "https://www.openstreetmap.org/api/0.6/changeset/187258738/download"
GEOFABRIK_EXTRACTS = [
    {
        "name": "norway-latest.osm.pbf",
        "url": "https://download.geofabrik.de/europe/norway-latest.osm.pbf",
    },
    {
        "name": "sweden-latest.osm.pbf",
        "url": "https://download.geofabrik.de/europe/sweden-latest.osm.pbf",
    },
]
GRAPHQL_URL = "https://www.pilegrimsleden.no/actions/graphql/api"
MAPLIST_URL = "https://www.pilegrimsleden.no/actions/pilegrimsleden/poi/maplist"
REQUEST_GAP_SEC = 2.0
MATCH_RADIUS_M = 100.0
POSSIBLE_RADIUS_M = 250.0
# Wider search when CMS coords are offset but address/name still identify the OSM object.
NAME_MATCH_RADIUS_M = 2000.0
BBOX_BUFFER_M = 5000.0
PILEGRIMSSENTER_TYPE_ID = 5048
TRAIL_ENTRIES = [
    {"id": 212, "title": "Gudbrandsdalsleden"},
    {"id": 190, "title": "St. Olavsleden"},
    {"id": 175, "title": "Borgleden"},
    {"id": 97, "title": "Kystpilegrimsleia"},
    {"id": 6418, "title": "Tunsbergleden"},
    {"id": 182, "title": "Østerdalsleden"},
    {"id": 132, "title": "Valldalsleden"},
    {"id": 202, "title": "Romboleden"},
    {"id": 194, "title": "Nordleden"},
]
PBF_PILGRIMAGE_VALUES = {
    "norway-latest.osm.pbf": {"stamp_office": 35, "yes": 146, "kvite kyrkjer": 5},
    "sweden-latest.osm.pbf": {"yes": 43},
}
RECHECK_OSM = [
    {
        "label": "Stiklestad pilegrimssenter",
        "type": "node",
        "id": 14086452092,
        "old_status": "no CMS Pilegrimssenter match within 250 m",
    },
    {
        "label": "Regional Pilgrim Center Avaldsnes (second node, ~8 km off)",
        "type": "node",
        "id": 14086526408,
        "old_status": "no CMS Pilegrimssenter match within 250 m (nearest Avaldsnes ~8012 m)",
    },
    {
        "label": "Nidaros Pilgrimsgård",
        "type": "way",
        "id": 167823309,
        "cited_way_id": 167823311,
        "old_status": "no CMS Pilegrimssenter match within 250 m",
    },
]
SHELTER_CSV_FIELDS = [
    "trail",
    "poi_name",
    "category",
    "lat",
    "lon",
    "address",
    "match_status",
    "matched_osm_id",
    "matched_osm_url",
    "matched_osm_name",
    "distance_m",
    "tag_diff",
]

CATEGORY_PRIORITY = [
    "Gapahuk",
    "Pilegrimsherberge",
    "Vandrerhjem",
    "Rom og hytter",
    "Rorbu",
    "Pilegrimsbu",
    "Dagsturhytte",
    "Campingplass",
    "Glamping",
    "Teltplass",
    "Rasteplass",
]
CORE_SHELTER_CATEGORIES = set(CATEGORY_PRIORITY)
TRAIL_ORDER = [
    "Gudbrandsdalsleden",
    "St. Olavsleden",
    "Borgleden",
    "Kystpilegrimsleia",
    "Tunsbergleden",
    "Østerdalsleden",
    "Valldalsleden",
    "Romboleden",
    "Nordleden",
]
PRIORITY_GAPS = [
    ("Valldalsleden", "Gapahuk"),
    ("Nordleden", "Gapahuk"),
    ("Romboleden", "Campingplass"),
    ("Nordleden", "Campingplass"),
    ("Nordleden", None),
]

COMPATIBLE_TOURISM = {
    "wilderness_hut",
    "hostel",
    "camp_site",
    "caravan_site",
    "chalet",
    "guest_house",
    "alpine_hut",
    "apartment",
    "cabin",
    "hotel",
}
COMPATIBLE_AMENITY = {"shelter"}
WEAK_TOURISM = {"picnic_site", "information", "attraction", "viewpoint", "yes"}
WEAK_AMENITY = {"bbq", "bench", "toilets", "hunting_stand"}

CATEGORY_EXPECTED_TAGS = {
    "Gapahuk": {("amenity", "shelter"), ("tourism", "wilderness_hut")},
    "Pilegrimsherberge": {("tourism", "hostel"), ("tourism", "guest_house")},
    "Vandrerhjem": {("tourism", "hostel")},
    "Rom og hytter": {("tourism", "chalet"), ("tourism", "guest_house"), ("tourism", "cabin")},
    "Rorbu": {("tourism", "chalet"), ("tourism", "guest_house")},
    "Pilegrimsbu": {("tourism", "wilderness_hut"), ("amenity", "shelter")},
    "Dagsturhytte": {("tourism", "wilderness_hut"), ("amenity", "shelter")},
    "Campingplass": {("tourism", "camp_site"), ("tourism", "caravan_site")},
    "Glamping": {("tourism", "camp_site"), ("tourism", "caravan_site")},
    "Teltplass": {("tourism", "camp_site")},
    "Rasteplass": {("amenity", "shelter"), ("tourism", "picnic_site")},
    # CMS parent / hotel labels used on corridor overnight POIs (e.g. Romeriksleden).
    "Hotell": {("tourism", "hotel")},
    "Overnatting": {
        ("tourism", "hotel"),
        ("tourism", "guest_house"),
        ("tourism", "hostel"),
        ("tourism", "chalet"),
        ("tourism", "cabin"),
        ("tourism", "apartment"),
        ("tourism", "camp_site"),
        ("tourism", "caravan_site"),
    },
}


def log(message: str) -> None:
    print(message, file=sys.stderr)


def http_get(url: str, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("errors"):
        raise RuntimeError(f"GraphQL errors: {result['errors']}")
    return result["data"]


def parse_changeset_meta(xml_bytes: bytes) -> dict[str, Any]:
    root = ET.fromstring(xml_bytes)
    cs = root.find("changeset")
    if cs is None:
        raise RuntimeError("Changeset metadata XML has no <changeset> element")
    tags = {tag.attrib["k"]: tag.attrib["v"] for tag in cs.findall("tag")}
    return {
        "id": int(cs.attrib["id"]),
        "user": cs.attrib.get("user"),
        "uid": cs.attrib.get("uid"),
        "created_at": cs.attrib.get("created_at"),
        "closed_at": cs.attrib.get("closed_at"),
        "changes_count": int(cs.attrib.get("changes_count", "0")),
        "min_lat": float(cs.attrib["min_lat"]),
        "min_lon": float(cs.attrib["min_lon"]),
        "max_lat": float(cs.attrib["max_lat"]),
        "max_lon": float(cs.attrib["max_lon"]),
        "tags": tags,
        "comment": tags.get("comment", ""),
        "source": tags.get("source", ""),
    }


def parse_osmchange(xml_bytes: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    elements: list[dict[str, Any]] = []
    for action in list(root):
        for el in list(action):
            tags = {tag.attrib["k"]: tag.attrib["v"] for tag in el.findall("tag")}
            elements.append(
                {
                    "action": action.tag,
                    "type": el.tag,
                    "id": int(el.attrib["id"]),
                    "version": int(el.attrib.get("version", "0")),
                    "lat": float(el.attrib["lat"]) if el.attrib.get("lat") else None,
                    "lon": float(el.attrib["lon"]) if el.attrib.get("lon") else None,
                    "tags": tags,
                }
            )
    return elements


def is_pilgrim_center_element(tags: dict[str, str]) -> bool:
    if tags.get("pilgrimage") == "stamp_office":
        return True
    if tags.get("tourism") == "information" and tags.get("information") == "office":
        name = (tags.get("name") or "").lower()
        if "pilegrim" in name or "pilgrim" in name:
            return True
    return False


def tag_scheme_from_changeset(elements: list[dict[str, Any]]) -> dict[str, Any]:
    centers = [el for el in elements if is_pilgrim_center_element(el["tags"])]
    key_values: dict[str, Counter[str]] = defaultdict(Counter)
    for el in centers:
        for key, value in el["tags"].items():
            key_values[key][value] += 1
    common = []
    n = max(len(centers), 1)
    for key, counts in sorted(key_values.items()):
        value, freq = counts.most_common(1)[0]
        if freq >= max(2, math.ceil(n * 0.5)) or key in {
            "tourism",
            "information",
            "pilgrimage",
            "name",
        }:
            common.append(
                {
                    "key": key,
                    "typical_value": value,
                    "values": dict(counts),
                    "present_on": sum(counts.values()),
                }
            )
    return {
        "description": (
            "Named pilgrim centers in changeset 187258738 are tagged as "
            "tourism=information + information=office + pilgrimage=stamp_office. "
            "That combination is the reference scheme. Nodes that only received "
            "opening_hours in this changeset are not the pilgrim-center objects."
        ),
        "required_combination": {
            "tourism": "information",
            "information": "office",
            "pilgrimage": "stamp_office",
        },
        "overpass_filters": [
            'nwr["pilgrimage"="stamp_office"]',
            'nwr["tourism"="information"]["information"="office"]["pilgrimage"="stamp_office"]',
        ],
        "tag_frequency": common,
        "pilgrim_center_element_count": len(centers),
    }


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def buffer_bbox(min_lat: float, min_lon: float, max_lat: float, max_lon: float, meters: float) -> tuple[float, float, float, float]:
    dlat = meters / 111320.0
    mid_lat = (min_lat + max_lat) / 2.0
    dlon = meters / (111320.0 * max(math.cos(math.radians(mid_lat)), 0.2))
    return (
        round(min_lat - dlat, 6),
        round(min_lon - dlon, 6),
        round(max_lat + dlat, 6),
        round(max_lon + dlon, 6),
    )


def trail_bboxes(pois: list[dict[str, Any]]) -> dict[str, tuple[float, float, float, float]]:
    by_trail: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for poi in pois:
        for trail in poi.get("trails") or []:
            by_trail[trail].append((poi["lat"], poi["lon"]))
    boxes = {}
    for trail, points in by_trail.items():
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        boxes[trail] = buffer_bbox(min(lats), min(lons), max(lats), max(lons), BBOX_BUFFER_M)
    return boxes


KEEP_TOURISM = COMPATIBLE_TOURISM | {"picnic_site"}


def overall_bbox(pois: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    lats = [poi["lat"] for poi in pois]
    lons = [poi["lon"] for poi in pois]
    return buffer_bbox(min(lats), min(lons), max(lats), max(lons), BBOX_BUFFER_M)


def tags_wanted(tags: Any) -> bool:
    pilgrimage = tags.get("pilgrimage")
    if pilgrimage == "stamp_office":
        return True
    if pilgrimage and not tags.get("highway") and not tags.get("route"):
        return True
    if tags.get("network") == "Pilegrimsleden":
        return True
    if tags.get("amenity") == "shelter":
        return True
    if tags.get("tourism") in KEEP_TOURISM:
        return True
    if tags.get("tourism") == "information" and tags.get("information") == "office":
        name = (tags.get("name") or "").lower()
        if "pilegrim" in name or "pilgrim" in name:
            return True
    return False


def copy_tags(obj: Any) -> dict[str, str]:
    return {tag.k: tag.v for tag in obj.tags}


def in_bbox(lat: float, lon: float, bbox: tuple[float, float, float, float]) -> bool:
    south, west, north, east = bbox
    return south <= lat <= north and west <= lon <= east


def download_geofabrik(dest_dir: Path) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    min_bytes = {
        "norway-latest.osm.pbf": 1_200_000_000,
        "sweden-latest.osm.pbf": 700_000_000,
    }
    paths: list[Path] = []
    for item in GEOFABRIK_EXTRACTS:
        path = dest_dir / item["name"]
        expected = min_bytes.get(item["name"], 1_000_000)
        if path.exists() and path.stat().st_size >= expected:
            log(f"Reusing Geofabrik extract {path} ({path.stat().st_size} bytes)")
            paths.append(path)
            continue
        log(f"Downloading Geofabrik extract {item['url']} -> {path}")
        command = [
            "wget",
            "-c",
            "--progress=dot:giga",
            "-O",
            str(path),
            "--user-agent",
            USER_AGENT,
            item["url"],
        ]
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"wget failed for {item['url']} (exit {result.returncode})")
        if not path.exists() or path.stat().st_size < 1_000_000:
            raise RuntimeError(f"Geofabrik extract missing or too small: {path}")
        log(f"  {path.name}: {path.stat().st_size} bytes")
        paths.append(path)
        time.sleep(REQUEST_GAP_SEC)
    return paths


def extract_from_pbf(pbf_path: Path, bbox: tuple[float, float, float, float]) -> list[dict[str, Any]]:
    import osmium

    class Handler(osmium.SimpleHandler):
        def __init__(self) -> None:
            super().__init__()
            self.elements: list[dict[str, Any]] = []

        def node(self, node: Any) -> None:
            if not node.location.valid() or not tags_wanted(node.tags):
                return
            lat, lon = float(node.location.lat), float(node.location.lon)
            if not in_bbox(lat, lon, bbox):
                return
            self.elements.append(
                {
                    "type": "node",
                    "id": int(node.id),
                    "lat": lat,
                    "lon": lon,
                    "tags": copy_tags(node),
                    "source_extract": pbf_path.name,
                }
            )

        def way(self, way: Any) -> None:
            if not tags_wanted(way.tags):
                return
            lats: list[float] = []
            lons: list[float] = []
            try:
                for node in way.nodes:
                    if node.location.valid():
                        lats.append(float(node.location.lat))
                        lons.append(float(node.location.lon))
            except osmium.InvalidLocationError:
                return
            if not lats:
                return
            lat, lon = sum(lats) / len(lats), sum(lons) / len(lons)
            if not in_bbox(lat, lon, bbox):
                return
            self.elements.append(
                {
                    "type": "way",
                    "id": int(way.id),
                    "lat": lat,
                    "lon": lon,
                    "center": {"lat": lat, "lon": lon},
                    "tags": copy_tags(way),
                    "source_extract": pbf_path.name,
                }
            )

    log(f"Scanning {pbf_path.name} for shelter/pilgrim tags")
    handler = Handler()
    handler.apply_file(str(pbf_path), locations=True, idx="flex_mem")
    log(f"  kept {len(handler.elements)} elements from {pbf_path.name}")
    return handler.elements


def element_coords(el: dict[str, Any]) -> tuple[float, float] | None:
    if el.get("lat") is not None and el.get("lon") is not None:
        return float(el["lat"]), float(el["lon"])
    center = el.get("center") or {}
    if center.get("lat") is not None and center.get("lon") is not None:
        return float(center["lat"]), float(center["lon"])
    return None


def osm_url(el: dict[str, Any]) -> str:
    return f"https://www.openstreetmap.org/{el['type']}/{el['id']}"


def is_pilgrim_center_osm(tags: dict[str, str]) -> bool:
    """POI with pilgrimage=*, not a highway/route way tagged pilgrimage=yes."""
    value = (tags.get("pilgrimage") or "").strip()
    if not value:
        return False
    if tags.get("highway") or tags.get("route"):
        return False
    if value == "stamp_office":
        return True
    poi_keys = (
        "tourism",
        "amenity",
        "building",
        "office",
        "information",
        "checkpoint:type",
    )
    return any(tags.get(key) for key in poi_keys)


def trail_dirname(title: str) -> str:
    translated = title.translate(
        str.maketrans({"æ": "ae", "ø": "o", "å": "a", "Æ": "Ae", "Ø": "O", "Å": "A"})
    )
    name = translated.replace(".", "").replace(" ", "-")
    # Country split: Swedish St. Olavsleden vs Norwegian Pilegrimsleden routes.
    if name == "St-Olavsleden":
        return "Sweden/St-Olavsleden"
    return f"Norway/{name}"


def osm_tag_scheme(tags: dict[str, str]) -> str:
    keys = [
        "tourism",
        "information",
        "pilgrimage",
        "building",
        "checkpoint:type",
        "amenity",
        "office",
        "network",
    ]
    return "; ".join(f"{key}={tags[key]}" for key in keys if tags.get(key))


def collect_pilgrimage_values(elements: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for el in elements:
        value = (el.get("tags") or {}).get("pilgrimage")
        if value:
            counts[value] += 1
    return counts


def compatible_for_poi(poi: dict[str, Any], tags: dict[str, str]) -> bool:
    tourism = tags.get("tourism")
    amenity = tags.get("amenity")
    # Hotels/hostels/camps: tourism tags only. amenity=shelter is too common
    # (bus stops, lean-tos) to treat as a universal overnight match.
    if tourism in COMPATIBLE_TOURISM:
        return True
    expected: set[tuple[str, str]] = set()
    for category in poi.get("shelter_categories") or []:
        expected |= CATEGORY_EXPECTED_TAGS.get(category, set())
    if not expected:
        for category in poi.get("categories") or []:
            expected |= CATEGORY_EXPECTED_TAGS.get(category, set())
    if expected:
        return any(tags.get(key) == value for key, value in expected)
    if amenity in COMPATIBLE_AMENITY or tags.get("building") in {"cabin", "hut"}:
        return True
    return False


def is_weak_poi(tags: dict[str, str]) -> bool:
    return tags.get("tourism") in WEAK_TOURISM or tags.get("amenity") in WEAK_AMENITY


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    stop = {"the", "og", "and", "at", "ved", "i"}
    tokens = [tok for tok in text.split() if tok not in stop]
    return " ".join(tokens)


def names_similar(a: str, b: str) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    sa, sb = set(na.split()), set(nb.split())
    if not sa or not sb:
        return False
    overlap = len(sa & sb) / len(sa | sb)
    return overlap >= 0.6 and len(sa & sb) >= 2


def normalize_street(value: str) -> str:
    text = normalize_name(value)
    # Norwegian street suffixes often glue to the stem: Limhusveien / Limhusvegen.
    text = re.sub(r"(vei|veg)en$", "vegen", text)
    text = re.sub(r"(gata|gaten|gt)$", "gata", text)
    text = re.sub(r"\bv$", "vegen", text)
    return text


def normalize_housenumber(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").lower())


def parse_norwegian_address(value: str) -> dict[str, str] | None:
    """Parse CMS strings like 'Limhusveien 15, 2315 Hamar'."""
    text = (value or "").strip()
    if not text:
        return None
    # street + housenumber, optional postcode + city
    match = re.match(
        r"^\s*(.+?)\s+(\d+[a-zA-Z]?)\s*,\s*(\d{4})\s+(.+?)\s*$",
        text,
    )
    if match:
        return {
            "street": match.group(1).strip(),
            "housenumber": match.group(2).strip(),
            "postcode": match.group(3).strip(),
            "city": match.group(4).strip(),
            "raw": text,
        }
    match = re.match(r"^\s*(.+?)\s+(\d+[a-zA-Z]?)\s*$", text)
    if match:
        return {
            "street": match.group(1).strip(),
            "housenumber": match.group(2).strip(),
            "postcode": "",
            "city": "",
            "raw": text,
        }
    return None


def osm_display_name(tags: dict[str, str]) -> str:
    for key in ("name", "official_name", "alt_name", "loc_name", "short_name"):
        value = (tags.get(key) or "").strip()
        if value:
            return value
    return ""


def address_matches_tags(parsed: dict[str, str] | None, tags: dict[str, str]) -> bool:
    if not parsed:
        return False
    street = tags.get("addr:street") or ""
    number = tags.get("addr:housenumber") or ""
    if not street or not number:
        return False
    if normalize_street(street) != normalize_street(parsed["street"]):
        return False
    if normalize_housenumber(number) != normalize_housenumber(parsed["housenumber"]):
        return False
    postcode = tags.get("addr:postcode") or ""
    if parsed.get("postcode") and postcode and postcode != parsed["postcode"]:
        return False
    return True


def tag_diff(our_tags: dict[str, str], osm_tags: dict[str, str]) -> str:
    ignore = {
        "source",
        "url",
        "network",
        "note:trail",
        "note:osm_mapping",
        "pilegrimsleden:poi_type",
        "pilegrimsleden:id",
    }
    parts: list[str] = []
    keys = sorted((set(our_tags) | set(osm_tags)) - ignore)
    for key in keys:
        ours = our_tags.get(key)
        theirs = osm_tags.get(key)
        if ours and theirs and ours != theirs:
            parts.append(f"{key}:{ours}->{theirs}")
        elif ours and not theirs:
            parts.append(f"+{key}={ours}")
        elif theirs and not ours and key in {"tourism", "amenity", "shelter_type", "name", "tents"}:
            parts.append(f"osm:{key}={theirs}")
    return "; ".join(parts)


def primary_category(categories: list[str]) -> str:
    rank = {name: index for index, name in enumerate(CATEGORY_PRIORITY)}
    matching = [title for title in categories if title in rank]
    if not matching:
        return categories[0] if categories else ""
    return min(matching, key=lambda title: rank[title])


def shelter_categories(categories: list[str]) -> list[str]:
    allowed = CORE_SHELTER_CATEGORIES | {"Hotell", "Overnatting"}
    return [title for title in categories if title in allowed]


def load_pois(raw_path: Path, osm_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    osm_by_id: dict[str, dict[str, str]] = {}
    root = ET.parse(osm_path).getroot()
    for node in root.findall("node"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in node.findall("tag")}
        cms_id = tags.get("pilegrimsleden:id")
        if cms_id:
            osm_by_id[cms_id] = tags
    pois = []
    for poi in raw["pois"]:
        cats = shelter_categories(poi.get("categories") or [])
        pois.append(
            {
                "id": str(poi["id"]),
                "title": poi["title"],
                "url": poi.get("url") or "",
                "address": (poi.get("address") or "").strip(),
                "lat": float(poi["lat"]),
                "lon": float(poi["lon"]),
                "trails": list(poi.get("trails") or []),
                "categories": list(poi.get("categories") or []),
                "shelter_categories": cats,
                "category": " | ".join(cats) or primary_category(poi.get("categories") or []),
                "our_tags": osm_by_id.get(str(poi["id"]), {}),
            }
        )
    missing_address = [poi["id"] for poi in pois if not poi["address"]]
    if missing_address:
        log(f"Fetching CMS addresses for {len(missing_address)} POIs")
        addresses = fetch_cms_addresses(missing_address)
        for poi in pois:
            if not poi["address"] and poi["id"] in addresses:
                poi["address"] = addresses[poi["id"]]
    return pois


def fetch_cms_addresses(ids: list[str]) -> dict[str, str]:
    """Fetch pilegrimsleden.no interest-point addresses via GraphQL."""
    if not ids:
        return {}
    query = """
    query Addresses($id: [QueryArgument], $limit: Int) {
      poiEntries(id: $id, limit: $limit) {
        ... on poi_Entry {
          id
          address
        }
      }
    }
    """
    found: dict[str, str] = {}
    chunk_size = 50
    for start in range(0, len(ids), chunk_size):
        chunk = ids[start : start + chunk_size]
        data = graphql(query, {"id": [int(value) for value in chunk], "limit": len(chunk)})
        for item in data.get("poiEntries") or []:
            address = (item.get("address") or "").strip()
            if address:
                found[str(item["id"])] = address
        if start + chunk_size < len(ids):
            time.sleep(REQUEST_GAP_SEC)
    return found


def fetch_cms_pilgrim_centers() -> list[dict[str, Any]]:
    query = """
    query Centers($types: [QueryArgument], $limit: Int, $offset: Int) {
      poiEntries(poiType: $types, limit: $limit, offset: $offset) {
        ... on poi_Entry {
          id
          title
          slug
          url
          location { lat lng }
          poiType { id title slug }
        }
      }
    }
    """
    items: list[dict[str, Any]] = []
    offset = 0
    while True:
        data = graphql(query, {"types": [PILEGRIMSSENTER_TYPE_ID], "limit": 100, "offset": offset})
        page = data.get("poiEntries") or []
        items.extend(page)
        if len(page) < 100:
            break
        offset += 100
        time.sleep(REQUEST_GAP_SEC)
    trails_by_id = fetch_related_trails(poi_type_ids=[PILEGRIMSSENTER_TYPE_ID])
    centers = []
    for item in items:
        loc = item.get("location") or {}
        try:
            lat = float(loc.get("lat"))
            lon = float(loc.get("lng"))
        except (TypeError, ValueError):
            continue
        if lat == 0 and lon == 0:
            continue
        categories = [
            (ptype or {}).get("title")
            for ptype in (item.get("poiType") or [])
            if (ptype or {}).get("title")
        ]
        centers.append(
            {
                "id": str(item["id"]),
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "lat": lat,
                "lon": lon,
                "categories": categories,
                "category": " | ".join(categories) or "Pilegrimssenter",
                "trails": trails_by_id.get(str(item["id"]), []),
                "is_pilegrimssenter": True,
            }
        )
    return centers


def fetch_related_trails(
    poi_type_ids: list[int] | None = None,
    search: str | None = None,
) -> dict[str, list[str]]:
    if search:
        query = """
        query TrailSearch($trailId: [QueryArgument], $search: String, $limit: Int, $offset: Int) {
          poiEntries(relatedTo: $trailId, search: $search, limit: $limit, offset: $offset) {
            ... on poi_Entry { id title }
          }
        }
        """
    else:
        query = """
        query TrailPois($types: [QueryArgument], $trailId: [QueryArgument], $limit: Int, $offset: Int) {
          poiEntries(poiType: $types, relatedTo: $trailId, limit: $limit, offset: $offset) {
            ... on poi_Entry { id }
          }
        }
        """
    by_id: dict[str, list[str]] = defaultdict(list)
    for trail in TRAIL_ENTRIES:
        offset = 0
        while True:
            variables: dict[str, Any] = {
                "trailId": [trail["id"]],
                "limit": 100,
                "offset": offset,
            }
            if poi_type_ids:
                variables["types"] = poi_type_ids
            if search:
                variables["search"] = search
            data = graphql(query, variables)
            page = data.get("poiEntries") or []
            for item in page:
                if search and "mottak" not in (item.get("title") or "").lower():
                    continue
                poi_id = str(item["id"])
                if trail["title"] not in by_id[poi_id]:
                    by_id[poi_id].append(trail["title"])
            if len(page) < 100:
                break
            offset += 100
            time.sleep(0.6)
        time.sleep(0.6)
    return dict(by_id)


def fetch_cms_maplist() -> list[dict[str, Any]]:
    from urllib.parse import urlencode

    payload = urlencode({"lang": "nb"}).encode("utf-8")
    req = urllib.request.Request(
        MAPLIST_URL,
        data=payload,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        items = json.loads(response.read().decode("utf-8"))
    pois: list[dict[str, Any]] = []
    for item in items:
        try:
            lat = float(item.get("lt"))
            lon = float(item.get("ln"))
        except (TypeError, ValueError):
            continue
        if lat == 0 and lon == 0:
            continue
        categories = [str(title) for title in (item.get("cs") or []) if title]
        cids = [int(cid) for cid in (item.get("cids") or []) if cid is not None]
        pois.append(
            {
                "id": str(item.get("id")),
                "title": item.get("t") or "",
                "url": item.get("u") or "",
                "lat": lat,
                "lon": lon,
                "categories": categories,
                "category": " | ".join(categories) or (item.get("c") or ""),
                "trails": [],
                "is_pilegrimssenter": PILEGRIMSSENTER_TYPE_ID in cids,
            }
        )
    return pois


def fetch_cms_titles(ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    query = """
    query ById($id: [QueryArgument], $limit: Int) {
      poiEntries(id: $id, limit: $limit) {
        ... on poi_Entry {
          id
          title
          url
          address
          poiType { title }
        }
      }
    }
    """
    found: dict[str, dict[str, Any]] = {}
    chunk_size = 50
    for start in range(0, len(ids), chunk_size):
        chunk = ids[start : start + chunk_size]
        data = graphql(query, {"id": [int(value) for value in chunk], "limit": len(chunk)})
        for item in data.get("poiEntries") or []:
            categories = [
                (ptype or {}).get("title")
                for ptype in (item.get("poiType") or [])
                if (ptype or {}).get("title")
            ]
            found[str(item["id"])] = {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "address": (item.get("address") or "").strip(),
                "categories": categories,
                "category": " | ".join(categories),
            }
        if start + chunk_size < len(ids):
            time.sleep(REQUEST_GAP_SEC)
    return found


def classify_poi(poi: dict[str, Any], nearby: list[tuple[float, dict[str, Any]]]) -> dict[str, Any]:
    """Match CMS overnight POI to OSM lodging.

    Priority:
      1. Compatible lodging within MATCH_RADIUS_M (prefer name hits)
      2. Address match on lodging within NAME_MATCH_RADIUS_M
      3. Strong name match on lodging within NAME_MATCH_RADIUS_M
      4. Legacy possible match within POSSIBLE_RADIUS_M
    """
    title = poi.get("title") or ""
    parsed_address = parse_norwegian_address(poi.get("address") or "")

    def hit(status: str, dist: float, el: dict[str, Any], extra: str = "") -> dict[str, Any]:
        tags = el.get("tags") or {}
        tag_extra = tag_diff(poi.get("our_tags") or {}, tags)
        if extra:
            tag_extra = f"{extra}" + (f"; {tag_extra}" if tag_extra else "")
        return {
            "match_status": status,
            "matched_osm_id": f"{el['type']}/{el['id']}",
            "matched_osm_url": osm_url(el),
            "distance_m": round(dist, 1),
            "tag_diff": tag_extra,
            "matched_osm_name": osm_display_name(tags),
            "matched_osm_tags": tags,
            "matched_osm_lat": el.get("_lat"),
            "matched_osm_lon": el.get("_lon"),
        }

    compatible = [
        (dist, el)
        for dist, el in nearby
        if dist <= MATCH_RADIUS_M and compatible_for_poi(poi, el.get("tags") or {})
    ]
    if compatible:
        compatible.sort(
            key=lambda item: (
                0
                if names_similar(title, osm_display_name(item[1].get("tags") or {}))
                else 1,
                0 if address_matches_tags(parsed_address, item[1].get("tags") or {}) else 1,
                item[0],
            )
        )
        dist, el = compatible[0]
        return hit("matched", dist, el)

    address_hits = [
        (dist, el)
        for dist, el in nearby
        if dist <= NAME_MATCH_RADIUS_M
        and compatible_for_poi(poi, el.get("tags") or {})
        and address_matches_tags(parsed_address, el.get("tags") or {})
    ]
    if address_hits:
        address_hits.sort(key=lambda item: item[0])
        dist, el = address_hits[0]
        reason = "address_match"
        if dist > MATCH_RADIUS_M:
            reason = "address_match_beyond_100m"
        return hit("matched", dist, el, reason)

    name_hits = [
        (dist, el)
        for dist, el in nearby
        if dist <= NAME_MATCH_RADIUS_M
        and compatible_for_poi(poi, el.get("tags") or {})
        and names_similar(title, osm_display_name(el.get("tags") or {}))
    ]
    if name_hits:
        name_hits.sort(key=lambda item: item[0])
        dist, el = name_hits[0]
        reason = "name_match"
        if dist > MATCH_RADIUS_M:
            reason = "name_match_beyond_100m"
        status = "matched" if dist <= POSSIBLE_RADIUS_M else "possible"
        return hit(status, dist, el, reason)

    possible_candidates = [(dist, el) for dist, el in nearby if dist <= POSSIBLE_RADIUS_M]
    if possible_candidates:
        def score(item: tuple[float, dict[str, Any]]) -> tuple[int, float]:
            dist, el = item
            tags = el.get("tags") or {}
            name_hit = names_similar(title, osm_display_name(tags))
            compat = compatible_for_poi(poi, tags)
            weak = is_weak_poi(tags)
            addr_hit = address_matches_tags(parsed_address, tags)
            if name_hit and compat:
                rank = 0
            elif addr_hit and compat:
                rank = 0
            elif compat:
                rank = 1
            elif name_hit:
                rank = 2
            elif weak:
                rank = 3
            else:
                rank = 4
            return rank, dist

        possible_candidates.sort(key=score)
        dist, el = possible_candidates[0]
        tags = el.get("tags") or {}
        reason_bits = []
        if dist > MATCH_RADIUS_M and compatible_for_poi(poi, tags):
            reason_bits.append("compatible_tag_beyond_100m")
        elif not compatible_for_poi(poi, tags):
            reason_bits.append("incompatible_or_weak_tags")
        if address_matches_tags(parsed_address, tags):
            reason_bits.append("address_nearby")
        return hit("possible", dist, el, ",".join(reason_bits))

    return {
        "match_status": "gap",
        "matched_osm_id": "",
        "matched_osm_url": "",
        "distance_m": "",
        "tag_diff": "",
        "matched_osm_name": "",
        "matched_osm_tags": {},
        "matched_osm_lat": None,
        "matched_osm_lon": None,
    }


def build_grid(elements: list[dict[str, Any]], cell: float = 0.02) -> dict[tuple[int, int], list[dict[str, Any]]]:
    grid: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    usable = []
    for el in elements:
        coords = element_coords(el)
        if coords is None:
            continue
        el = dict(el)
        el["_lat"], el["_lon"] = coords
        el["tags"] = el.get("tags") or {}
        usable.append(el)
        grid[(int(coords[0] / cell), int(coords[1] / cell))].append(el)
    return grid


def nearby_elements(
    lat: float,
    lon: float,
    grid: dict[tuple[int, int], list[dict[str, Any]]],
    radius_m: float,
    cell: float = 0.02,
) -> list[tuple[float, dict[str, Any]]]:
    gi, gj = int(lat / cell), int(lon / cell)
    found: list[tuple[float, dict[str, Any]]] = []
    span = 2
    for di in range(-span, span + 1):
        for dj in range(-span, span + 1):
            for el in grid.get((gi + di, gj + dj), []):
                dist = haversine_m(lat, lon, el["_lat"], el["_lon"])
                if dist <= radius_m:
                    found.append((dist, el))
    found.sort(key=lambda item: item[0])
    return found


def status_tables(results: list[dict[str, Any]]) -> str:
    trail_names = TRAIL_ORDER + ["unassigned"]
    categories = CATEGORY_PRIORITY[:]
    counts: dict[str, dict[str, Counter[str]]] = {
        trail: {status: Counter() for status in ("matched", "possible", "gap")}
        for trail in trail_names
    }
    unique: dict[str, Counter[str]] = {trail: Counter() for trail in trail_names}
    overall = Counter()
    seen_ids: dict[str, set[str]] = {trail: set() for trail in trail_names}

    for row in results:
        overall[row["match_status"]] += 1
        trails = row["trails"] or ["unassigned"]
        cats = row["shelter_categories"] or [row["category"]]
        for trail in trails:
            if row["id"] not in seen_ids[trail]:
                unique[trail][row["match_status"]] += 1
                seen_ids[trail].add(row["id"])
            for category in cats:
                counts[trail][row["match_status"]][category] += 1

    def fmt_table(status: str) -> str:
        header = ["trail", "total"] + categories
        col_w = {name: len(name) for name in header}
        body: list[list[str]] = []
        for trail in trail_names:
            row = [trail, str(unique[trail][status])]
            for category in categories:
                row.append(str(counts[trail][status][category]))
            body.append(row)
            for index, cell in enumerate(row):
                col_w[header[index]] = max(col_w[header[index]], len(cell))

        def fmt(row: list[str]) -> str:
            return "  ".join(cell.ljust(col_w[header[i]]) for i, cell in enumerate(row))

        lines = [fmt(header), fmt(["-" * col_w[name] for name in header])]
        lines.extend(fmt(row) for row in body)
        return "\n".join(lines)

    blocks = [
        f"Overall unique POIs: {len(results)}",
        f"matched: {overall['matched']}  possible: {overall['possible']}  gap: {overall['gap']}",
        "",
        "### matched (unique POIs per trail; multi-type counted in each type column)",
        fmt_table("matched"),
        "",
        "### possible",
        fmt_table("possible"),
        "",
        "### gap",
        fmt_table("gap"),
    ]
    return "\n".join(blocks)


def markdown_report(
    results: list[dict[str, Any]],
    pilgrim_centers_osm: list[dict[str, Any]],
    pilgrim_unmatched: list[dict[str, Any]],
    scheme: dict[str, Any],
) -> str:
    tables = status_tables(results)
    lines = [
        "# OSM comparison of Pilegrimsleden shelter/cabin POIs",
        "",
        "Read-only comparison. Nothing was uploaded to OpenStreetMap.",
        "",
        "Existing OSM objects were filtered from Geofabrik extracts "
        "`norway-latest.osm.pbf` and `sweden-latest.osm.pbf` (Norway plus the "
        "Swedish stretch of St. Olavsleden).",
        "",
        "## Reference tagging (changeset 187258738)",
        "",
        scheme["description"],
        "",
        "Canonical combination:",
        "",
        "- `tourism=information`",
        "- `information=office`",
        "- `pilgrimage=stamp_office`",
        "",
        f"Changeset comment: {scheme.get('changeset_comment', '')}",
        f"Changeset source: {scheme.get('changeset_source', '')}",
        "",
        "## Totals",
        "",
        tables,
        "",
        "## Priority gap spots",
        "",
        "These reuse the thin spots from the CMS extract. "
        "A CMS count of zero means the official map has no such POI; "
        "OSM gaps below are CMS POIs with no nearby compatible OSM object.",
        "",
    ]
    by_trail_cat: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        if row["match_status"] != "gap":
            continue
        for trail in row["trails"] or ["unassigned"]:
            for category in row["shelter_categories"]:
                by_trail_cat[(trail, category)].append(row)

    for trail, category in PRIORITY_GAPS:
        if category is None:
            gaps = [
                row
                for row in results
                if row["match_status"] == "gap" and trail in (row["trails"] or [])
            ]
            lines.append(f"### {trail} (all categories)")
            lines.append("")
            if not gaps:
                lines.append("No OSM gaps among the CMS shelter POIs on this trail.")
            else:
                for row in sorted(gaps, key=lambda item: item["title"].lower()):
                    lines.append(
                        f"- {row['title']} ({row['category']}) "
                        f"{row['lat']:.5f},{row['lon']:.5f} {row['url']}"
                    )
            lines.append("")
            continue
        lines.append(f"### {trail} / {category}")
        lines.append("")
        items = by_trail_cat.get((trail, category), [])
        if not items:
            lines.append(
                "No CMS POIs of this type are unmatched in OSM "
                "(either none exist in the CMS extract, or all have a nearby OSM object)."
            )
        else:
            for row in sorted(items, key=lambda item: item["title"].lower()):
                lines.append(
                    f"- {row['title']} {row['lat']:.5f},{row['lon']:.5f} {row['url']}"
                )
        lines.append("")

    lines.extend(
        [
            "## Gap list per trail",
            "",
        ]
    )
    for trail in TRAIL_ORDER:
        gaps = [
            row
            for row in results
            if row["match_status"] == "gap" and trail in (row["trails"] or [])
        ]
        lines.append(f"### {trail} ({len(gaps)} gaps)")
        lines.append("")
        if not gaps:
            lines.append("None.")
            lines.append("")
            continue
        for row in sorted(gaps, key=lambda item: (row_sort_category(row), item["title"].lower())):
            lines.append(
                f"- {row['title']} — {row['category']} — "
                f"{row['lat']:.5f},{row['lon']:.5f} — {row['url']}"
            )
        lines.append("")

    lines.extend(
        [
            "## Pilgrim centers already in OSM",
            "",
            "Queried from Geofabrik Norway and Sweden extracts using the changeset 187258738 scheme "
            "(`pilgrimage=stamp_office`, plus `tourism=information` + `information=office` "
            "when the name refers to a pilgrim center, and `network=Pilegrimsleden`).",
            "",
            f"OSM pilgrim-center objects found: {len(pilgrim_centers_osm)}",
            "",
        ]
    )
    for el in sorted(pilgrim_centers_osm, key=lambda item: (item.get("tags") or {}).get("name", "").lower()):
        tags = el.get("tags") or {}
        coords = element_coords(el)
        coord_s = f"{coords[0]:.5f},{coords[1]:.5f}" if coords else "no-coords"
        lines.append(
            f"- {tags.get('name', '(unnamed)')} — {el['type']}/{el['id']} — {coord_s} — {osm_url(el)}"
        )
    lines.append("")
    lines.extend(
        [
            "## OSM pilgrim centers with no corresponding Pilegrimsleden CMS entry",
            "",
            "Matched to CMS `Pilegrimssenter` entries (not the shelter extract) by 250 m or similar name. "
            "Shelter-only extract is expected not to contain these offices.",
            "",
        ]
    )
    if not pilgrim_unmatched:
        lines.append(
            "Every OSM pilgrim-center object in the Geofabrik extracts has a corresponding CMS pilgrim-center entry."
        )
    else:
        for item in pilgrim_unmatched:
            lines.append(
                f"- {item['name']} — {item['osm_id']} — {item['url']}"
                + (f" — nearest CMS: {item['nearest_cms']}" if item.get("nearest_cms") else "")
            )
    lines.append("")
    return "\n".join(lines)


def row_sort_category(row: dict[str, Any]) -> int:
    primary = primary_category(row.get("shelter_categories") or [])
    try:
        return CATEGORY_PRIORITY.index(primary)
    except ValueError:
        return 99


def nearest_cms(
    lat: float, lon: float, cms_pois: list[dict[str, Any]]
) -> tuple[float, dict[str, Any]] | None:
    best: tuple[float, dict[str, Any]] | None = None
    for cms in cms_pois:
        dist = haversine_m(lat, lon, cms["lat"], cms["lon"])
        if best is None or dist < best[0]:
            best = (dist, cms)
    return best


def nearby_pilgrimage_osm(
    lat: float,
    lon: float,
    osm_centers: list[dict[str, Any]],
    radius_m: float = POSSIBLE_RADIUS_M,
) -> list[tuple[float, dict[str, Any]]]:
    """Return pilgrimage=* OSM objects within radius, closest first.

    Tie-breaker: when several stamp-office objects fall inside the search
    radius of a CMS point, the closest one wins (not an arbitrary peer).
    """
    found: list[tuple[float, dict[str, Any]]] = []
    for el in osm_centers:
        coords = element_coords(el)
        if coords is None:
            continue
        dist = haversine_m(lat, lon, coords[0], coords[1])
        if dist <= radius_m:
            found.append((dist, el))
    found.sort(key=lambda item: (item[0], item[1]["type"], int(item[1]["id"])))
    return found


def closest_pilgrimage_osm(
    lat: float,
    lon: float,
    osm_centers: list[dict[str, Any]],
    radius_m: float = POSSIBLE_RADIUS_M,
) -> tuple[float, dict[str, Any]] | None:
    """Pick the nearest pilgrimage=* object within radius, or None."""
    nearby = nearby_pilgrimage_osm(lat, lon, osm_centers, radius_m=radius_m)
    return nearby[0] if nearby else None


def match_osm_center(
    el: dict[str, Any], cms_pois: list[dict[str, Any]]
) -> dict[str, Any]:
    coords = element_coords(el)
    tags = el.get("tags") or {}
    name = tags.get("name") or ""
    result = {
        "osm": el,
        "osm_id": f"{el['type']}/{el['id']}",
        "osm_url": osm_url(el),
        "osm_name": name,
        "osm_tag_scheme": osm_tag_scheme(tags),
        "lat": coords[0] if coords else None,
        "lon": coords[1] if coords else None,
        "cms": None,
        "distance_m": None,
        "match_status": "gap",
        "nearest_cms": None,
        "nearest_distance_m": None,
    }
    if coords is None:
        return result
    best = nearest_cms(coords[0], coords[1], cms_pois)
    if best is None:
        return result
    dist, cms = best
    result["nearest_cms"] = cms
    result["nearest_distance_m"] = round(dist, 1)
    if dist <= POSSIBLE_RADIUS_M:
        result["cms"] = cms
        result["distance_m"] = round(dist, 1)
        result["match_status"] = "matched"
    return result


def match_osm_centers_to_cms(
    osm_centers: list[dict[str, Any]], cms_pois: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    unmatched = []
    for el in osm_centers:
        match = match_osm_center(el, cms_pois)
        if match["match_status"] == "matched":
            continue
        cms = match.get("nearest_cms")
        nearest = ""
        if cms:
            nearest = (
                f"{cms['title']} at {round(match['nearest_distance_m'] or 0)} m "
                f"({cms.get('url') or ''})"
            )
        unmatched.append(
            {
                "name": match["osm_name"] or "(unnamed)",
                "osm_id": match["osm_id"],
                "url": match["osm_url"],
                "nearest_cms": nearest,
            }
        )
    return unmatched


def enrich_cms_match_titles(
    matches: list[dict[str, Any]], cms_titles: dict[str, dict[str, Any]]
) -> None:
    for match in matches:
        for key in ("cms", "nearest_cms"):
            cms = match.get(key)
            if not cms:
                continue
            extra = cms_titles.get(str(cms.get("id")))
            if not extra:
                continue
            if extra.get("title"):
                cms["title"] = extra["title"]
            if extra.get("url"):
                cms["url"] = extra["url"]
            if extra.get("categories"):
                cms["categories"] = extra["categories"]
                cms["category"] = extra["category"]


def trails_for_point(
    lat: float, lon: float, bboxes: dict[str, tuple[float, float, float, float]]
) -> list[str]:
    found = [trail for trail, box in bboxes.items() if in_bbox(lat, lon, box)]
    return [trail for trail in TRAIL_ORDER if trail in found]


def recheck_named_centers(
    osm_elements: list[dict[str, Any]],
    osm_centers: list[dict[str, Any]],
    cms_pois: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key = {(el["type"], int(el["id"])): el for el in osm_elements}
    reports = []
    for spec in RECHECK_OSM:
        el = by_key.get((spec["type"], spec["id"]))
        cited = None
        cited_id = spec.get("cited_way_id")
        if cited_id:
            cited = by_key.get(("way", int(cited_id)))
        nearby_osm = []
        coords = element_coords(el) if el else None
        if coords:
            nearby_osm = nearby_pilgrimage_osm(coords[0], coords[1], osm_centers)
        match = match_osm_center(el, cms_pois) if el else None
        reports.append(
            {
                "spec": spec,
                "osm": el,
                "cited_way": cited,
                "match": match,
                "nearby_pilgrimage_osm": nearby_osm,
            }
        )
    return reports


def format_recheck_report(
    reports: list[dict[str, Any]], pilgrimage_values: Counter[str]
) -> str:
    lines = [
        "Pilgrim-center match is any node or way with pilgrimage=* "
        "(nodes and way centroids). CMS match uses every map POI, not only "
        "category Pilegrimssenter.",
        "",
        "Distinct pilgrimage=* values in the Geofabrik extract used for matching:",
    ]
    if pilgrimage_values:
        for value, count in pilgrimage_values.most_common():
            lines.append(f"  pilgrimage={value}: {count}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Full PBF tag scan (nodes/ways/relations, no bbox filter):")
    for extract_name, counts in PBF_PILGRIMAGE_VALUES.items():
        rendered = ", ".join(f"{value}={count}" for value, count in counts.items())
        lines.append(f"  {extract_name}: {rendered}")
    lines.append(
        "pilgrimage=yes is almost entirely route ways/relations named Pilegrimsleden; "
        "kvite kyrkjer is five route relations. Those are logged only; matching uses "
        "pilgrimage=stamp_office (and other pilgrimage=* on POI-like nodes/ways, not highways)."
    )
    lines.append("")
    for report in reports:
        spec = report["spec"]
        el = report["osm"]
        match = report["match"]
        lines.append(f"### {spec['label']}")
        lines.append(f"Old status: {spec['old_status']}")
        if spec.get("cited_way_id"):
            cited = report.get("cited_way")
            lines.append(
                f"Cited way {spec['cited_way_id']} is not Nidaros Pilgrimsgard "
                "in current OSM / Geofabrik; live OSM tags it building=warehouse "
                "with no pilgrimage=* key. The mapped building is "
                f"way/{spec['id']}."
            )
            if cited:
                lines.append(
                    f"Geofabrik also contains way/{spec['cited_way_id']}: "
                    f"{osm_tag_scheme(cited.get('tags') or {})}"
                )
        if el is None:
            lines.append("New status: OSM element not present in the local extract.")
            lines.append("")
            continue
        tags = el.get("tags") or {}
        coords = element_coords(el)
        coord_s = f"{coords[0]:.5f},{coords[1]:.5f}" if coords else "no-coords"
        lines.append(
            f"OSM: {el['type']}/{el['id']} — {coord_s} — {osm_url(el)}"
        )
        lines.append(f"OSM tag scheme: {osm_tag_scheme(tags) or '(none)'}")
        if match and match["match_status"] == "matched":
            cms = match["cms"]
            lines.append(
                f"New status: matched CMS '{cms['title']}' at {match['distance_m']} m "
                f"({cms.get('category') or ''}) {cms.get('url') or ''}"
            )
        else:
            nearest = match.get("nearest_cms") if match else None
            dist = match.get("nearest_distance_m") if match else None
            lines.append("New status: still no CMS entry within 250 m")
            if nearest:
                lines.append(
                    f"Nearest CMS: {nearest['title']} at {dist} m "
                    f"({nearest.get('category') or ''}) {nearest.get('url') or ''}"
                )
            nearby = report.get("nearby_pilgrimage_osm") or []
            other = [
                item
                for item in nearby
                if not (
                    item[1]["type"] == el["type"] and int(item[1]["id"]) == int(el["id"])
                )
            ]
            if other:
                lines.append(
                    "Reason: (b) other nearby OSM elements carry pilgrimage=* "
                    "(worth a human look):"
                )
                for dist_m, other_el in other:
                    otags = other_el.get("tags") or {}
                    lines.append(
                        f"  {dist_m:.1f} m {other_el['type']}/{other_el['id']} "
                        f"{otags.get('name', '(unnamed)')} "
                        f"{osm_tag_scheme(otags)}"
                    )
            else:
                lines.append(
                    "Reason: (a) no other OSM node/way within 250 m carries "
                    "pilgrimage=*; this object itself is the pilgrimage=* element "
                    "and has no CMS POI in that radius."
                )
        lines.append("")
    return "\n".join(lines)


def pilgrim_center_rows(
    cms_centers: list[dict[str, Any]],
    osm_centers: list[dict[str, Any]],
    osm_matches: list[dict[str, Any]],
    bboxes: dict[str, tuple[float, float, float, float]],
    shelter_trails_by_cms_id: dict[str, list[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_row(row: dict[str, Any]) -> None:
        key = (
            row["trail"],
            row.get("cms_id") or row.get("matched_osm_id") or row["poi_name"],
        )
        if key in seen:
            return
        seen.add(key)
        rows.append(row)

    for cms in cms_centers:
        # Closest pilgrimage=* object within 250 m wins when several exist.
        closest = closest_pilgrimage_osm(cms["lat"], cms["lon"], osm_centers)
        if closest:
            dist, el = closest
            tags = el.get("tags") or {}
            status = "matched"
            osm_id = f"{el['type']}/{el['id']}"
            osm_link = osm_url(el)
            distance: float | str = round(dist, 1)
            diff = osm_tag_scheme(tags)
        else:
            status = "gap"
            osm_id = ""
            osm_link = ""
            distance = ""
            diff = ""
        trails = cms.get("trails") or trails_for_point(cms["lat"], cms["lon"], bboxes)
        if not trails:
            trails = ["unassigned"]
        for trail in trails:
            add_row(
                {
                    "trail": trail,
                    "poi_name": cms["title"],
                    "category": cms.get("category") or "Pilegrimssenter",
                    "lat": f"{cms['lat']:.7f}",
                    "lon": f"{cms['lon']:.7f}",
                    "match_status": status,
                    "matched_osm_id": osm_id,
                    "matched_osm_url": osm_link,
                    "distance_m": distance,
                    "tag_diff": diff,
                    "cms_id": cms["id"],
                }
            )

    for match in osm_matches:
        el = match["osm"]
        tags = el.get("tags") or {}
        if not tags.get("name"):
            continue
        coords = element_coords(el)
        if coords is None:
            continue
        cms = match.get("cms")
        trails: list[str] = []
        if cms:
            trails.extend(cms.get("trails") or [])
            trails.extend(shelter_trails_by_cms_id.get(str(cms.get("id")), []))
        trails.extend(trails_for_point(coords[0], coords[1], bboxes))
        ordered = [trail for trail in TRAIL_ORDER if trail in set(trails)]
        if not ordered:
            ordered = ["unassigned"]
        if match["match_status"] == "matched" and cms:
            poi_name = cms["title"]
            category = cms.get("category") or ""
            lat = f"{cms['lat']:.7f}"
            lon = f"{cms['lon']:.7f}"
            cms_id = str(cms.get("id") or "")
        else:
            poi_name = tags.get("name") or "(unnamed)"
            category = "OSM pilgrimage=*"
            lat = f"{coords[0]:.7f}"
            lon = f"{coords[1]:.7f}"
            cms_id = ""
        for trail in ordered:
            add_row(
                {
                    "trail": trail,
                    "poi_name": poi_name,
                    "category": category,
                    "lat": lat,
                    "lon": lon,
                    "match_status": match["match_status"],
                    "matched_osm_id": match["osm_id"],
                    "matched_osm_url": match["osm_url"],
                    "distance_m": match["distance_m"]
                    if match["distance_m"] is not None
                    else "",
                    "tag_diff": match["osm_tag_scheme"],
                    "cms_id": cms_id,
                }
            )

    rows.sort(
        key=lambda row: (
            TRAIL_ORDER.index(row["trail"]) if row["trail"] in TRAIL_ORDER else 99,
            row["match_status"],
            row["poi_name"].lower(),
        )
    )
    return rows


def write_pilgrim_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=SHELTER_CSV_FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_by_trail_outputs(
    data_dir: Path,
    shelter_rows: list[dict[str, Any]],
    shelter_records: list[dict[str, Any]],
    pilgrim_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    from extract_pilegrimsleden_shelters import write_osm

    root = data_dir / "by_trail"
    summaries: list[dict[str, Any]] = []
    for trail in TRAIL_ORDER:
        folder = root / trail_dirname(trail)
        folder.mkdir(parents=True, exist_ok=True)
        trail_shelters = [row for row in shelter_rows if row["trail"] == trail]
        trail_pilgrim = [row for row in pilgrim_rows if row["trail"] == trail]
        write_pilgrim_csv(folder / "shelters.csv", trail_shelters)
        records = []
        for record in shelter_records:
            if trail not in (record.get("trails") or []):
                continue
            copy = dict(record)
            copy["trails"] = [trail]
            records.append(copy)
        write_osm(folder / "shelters.osm", records)
        write_pilgrim_csv(folder / "pilgrim_centers.csv", trail_pilgrim)
        summaries.append(
            {
                "trail": trail,
                "folder": trail_dirname(trail),
                "shelters": len(records),
                "shelter_rows": len(trail_shelters),
                "pilgrim_centers": len(trail_pilgrim),
                "shelter_gaps": sum(
                    1 for row in trail_shelters if row["match_status"] == "gap"
                ),
                "pilgrim_gaps": sum(
                    1 for row in trail_pilgrim if row["match_status"] == "gap"
                ),
            }
        )
    readme = [
        "# Outputs by trail",
        "",
        "One folder per Pilegrimsleden trail. Folder names map ae/o/a from",
        "Norwegian special letters and drop the dot in St. Olavsleden for",
        "filesystem safety; Norwegian routes under `Norway/`, Swedish St. Olavsleden under `Sweden/`.",
        "The original trail name is in the `trail` CSV column",
        "and in `note:trail` on OSM nodes.",
        "",
        "Combined national files under `data/` are unchanged. Multi-trail POIs",
        "are copied into every relevant trail folder.",
        "",
        "Pilgrim-center matching uses any OSM node or way with `pilgrimage=*`",
        "(way centroids included), not only the changeset 187258738",
        "information-office combination.",
        "",
        "| folder | trail | shelters | pilgrim centers | shelter gaps | pilgrim gaps |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in summaries:
        readme.append(
            f"| {item['folder']} | {item['trail']} | {item['shelters']} | "
            f"{item['pilgrim_centers']} | {item['shelter_gaps']} | {item['pilgrim_gaps']} |"
        )
    readme.append("")
    (root / "README.md").write_text("\n".join(readme), encoding="utf-8")
    return summaries


def write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for poi in results:
        trails = poi["trails"] or [""]
        for trail in trails:
            rows.append(
                {
                    "trail": trail,
                    "poi_name": poi["title"],
                    "category": poi["category"],
                    "lat": f"{poi['lat']:.7f}",
                    "lon": f"{poi['lon']:.7f}",
                    "address": poi.get("address") or "",
                    "match_status": poi["match_status"],
                    "matched_osm_id": poi["matched_osm_id"],
                    "matched_osm_url": poi["matched_osm_url"],
                    "matched_osm_name": poi.get("matched_osm_name") or "",
                    "distance_m": poi["distance_m"],
                    "tag_diff": poi["tag_diff"],
                }
            )
    rows.sort(
        key=lambda row: (
            TRAIL_ORDER.index(row["trail"]) if row["trail"] in TRAIL_ORDER else 99,
            row["match_status"],
            row["poi_name"].lower(),
        )
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "trail",
                "poi_name",
                "category",
                "lat",
                "lon",
                "address",
                "match_status",
                "matched_osm_id",
                "matched_osm_url",
                "matched_osm_name",
                "distance_m",
                "tag_diff",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
    )
    parser.add_argument(
        "--pilgrim-centers-only",
        action="store_true",
        help=(
            "Reuse the existing Geofabrik extract JSON and skip the 387-POI "
            "shelter/cabin rematch."
        ),
    )
    parser.add_argument(
        "--split-by-trail",
        action="store_true",
        help="Write data/by_trail/<TrailName>/ copies; keep national files.",
    )
    return parser.parse_args()


def load_existing_osm_elements(raw_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    return list(payload.get("elements") or [])


def load_shelter_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def attach_trails_to_cms(
    cms_pois: list[dict[str, Any]],
    extra_trails: dict[str, list[str]],
    shelter_trails: dict[str, list[str]],
) -> None:
    for cms in cms_pois:
        trails: list[str] = []
        for source in (
            cms.get("trails") or [],
            extra_trails.get(str(cms["id"]), []),
            shelter_trails.get(str(cms["id"]), []),
        ):
            for trail in source:
                if trail not in trails:
                    trails.append(trail)
        cms["trails"] = [trail for trail in TRAIL_ORDER if trail in trails]


def compare_pilgrim_centers(
    data_dir: Path,
    pois: list[dict[str, Any]],
    osm_elements: list[dict[str, Any]],
    shelter_rows: list[dict[str, Any]],
    shelter_records: list[dict[str, Any]],
    split_by_trail: bool,
) -> dict[str, Any]:
    bboxes = trail_bboxes(pois)
    pilgrimage_values = collect_pilgrimage_values(osm_elements)
    log(
        "Distinct pilgrimage=* values: "
        + (", ".join(f"{value}={count}" for value, count in pilgrimage_values.most_common()) or "(none)")
    )
    osm_centers = [el for el in osm_elements if is_pilgrim_center_osm(el.get("tags") or {})]
    log(
        f"OSM pilgrim-center objects (any pilgrimage=* on nodes/ways): {len(osm_centers)}"
    )
    node_n = sum(1 for el in osm_centers if el["type"] == "node")
    way_n = sum(1 for el in osm_centers if el["type"] == "way")
    log(f"  nodes={node_n} ways={way_n}")

    log("Fetching CMS map POIs and Pilegrimssenter trail relations")
    cms_all = fetch_cms_maplist()
    time.sleep(REQUEST_GAP_SEC)
    cms_centers = fetch_cms_pilgrim_centers()
    extra_trails = fetch_related_trails(search="Pilegrimsmottak")
    shelter_trails = {poi["id"]: list(poi.get("trails") or []) for poi in pois}
    by_id: dict[str, dict[str, Any]] = {cms["id"]: dict(cms) for cms in cms_all}
    for cms in cms_centers:
        current = by_id.get(cms["id"], {})
        current.update(cms)
        by_id[cms["id"]] = current
    cms_pois = list(by_id.values())
    attach_trails_to_cms(cms_pois, extra_trails, shelter_trails)
    attach_trails_to_cms(cms_centers, extra_trails, shelter_trails)
    log(f"CMS map POIs with coordinates: {len(cms_pois)}")
    log(f"CMS Pilegrimssenter with coordinates: {len(cms_centers)}")

    osm_matches = [match_osm_center(el, cms_pois) for el in osm_centers]
    match_ids = [
        str(match["cms"]["id"])
        for match in osm_matches
        if match.get("cms") and match["cms"].get("id")
    ]
    nearest_ids = [
        str(match["nearest_cms"]["id"])
        for match in osm_matches
        if match.get("nearest_cms") and match["nearest_cms"].get("id")
    ]
    cms_titles = fetch_cms_titles(sorted(set(match_ids + nearest_ids)))
    enrich_cms_match_titles(osm_matches, cms_titles)
    for cms in cms_pois + cms_centers:
        extra = cms_titles.get(str(cms.get("id")))
        if extra and extra.get("title"):
            cms["title"] = extra["title"]
            if extra.get("url"):
                cms["url"] = extra["url"]
            if extra.get("categories"):
                cms["categories"] = extra["categories"]
                cms["category"] = extra["category"]

    pilgrim_unmatched = [
        {
            "name": match["osm_name"] or "(unnamed)",
            "osm_id": match["osm_id"],
            "url": match["osm_url"],
            "nearest_cms": (
                f"{match['nearest_cms']['title']} at "
                f"{round(match['nearest_distance_m'] or 0)} m "
                f"({match['nearest_cms'].get('url') or ''})"
                if match.get("nearest_cms")
                else ""
            ),
        }
        for match in osm_matches
        if match["match_status"] != "matched" and (match.get("osm") or {}).get("tags", {}).get("name")
    ]

    reports = recheck_named_centers(osm_elements, osm_centers, cms_pois)
    recheck_text = format_recheck_report(reports, pilgrimage_values)

    pilgrim_rows = pilgrim_center_rows(
        cms_centers,
        osm_centers,
        osm_matches,
        bboxes,
        shelter_trails,
    )
    write_pilgrim_csv(data_dir / "pilgrim_centers.csv", pilgrim_rows)
    log(f"Wrote {data_dir / 'pilgrim_centers.csv'}")

    summaries = []
    if split_by_trail:
        summaries = write_by_trail_outputs(
            data_dir, shelter_rows, shelter_records, pilgrim_rows
        )
        log(f"Wrote {data_dir / 'by_trail'}")

    return {
        "osm_centers": osm_centers,
        "pilgrim_unmatched": pilgrim_unmatched,
        "recheck_text": recheck_text,
        "summaries": summaries,
        "pilgrim_rows": pilgrim_rows,
        "pilgrimage_values": pilgrimage_values,
    }


def main() -> int:
    args = parse_args()
    data_dir: Path = args.data_dir
    started = datetime.now(timezone.utc)

    ref_path = data_dir / "changeset_187258738_reference.json"
    if ref_path.exists():
        log(f"Reusing {ref_path}")
        reference = json.loads(ref_path.read_text(encoding="utf-8"))
        scheme = reference["tag_scheme_used"]
    else:
        log("Fetching changeset 187258738 metadata")
        meta_xml = http_get(OSM_CHANGESET_META, accept="application/xml")
        time.sleep(REQUEST_GAP_SEC)
        log("Fetching changeset 187258738 osmChange")
        change_xml = http_get(OSM_CHANGESET_DOWNLOAD, accept="application/xml")
        meta = parse_changeset_meta(meta_xml)
        elements = parse_osmchange(change_xml)
        scheme = tag_scheme_from_changeset(elements)
        scheme["changeset_comment"] = meta["comment"]
        scheme["changeset_source"] = meta["source"]
        reference = {
            "changeset_id": 187258738,
            "downloaded_at": started.isoformat(),
            "metadata_url": OSM_CHANGESET_META,
            "download_url": OSM_CHANGESET_DOWNLOAD,
            "metadata": meta,
            "tag_scheme_used": scheme,
            "element_ids": [f"{el['type']}/{el['id']}" for el in elements],
            "bounding_box": {
                "min_lat": meta["min_lat"],
                "min_lon": meta["min_lon"],
                "max_lat": meta["max_lat"],
                "max_lon": meta["max_lon"],
            },
            "elements": elements,
            "note": (
                "osmChange modify payloads contain the tags on each element after this "
                "changeset. Pilgrim-center objects use tourism=information, "
                "information=office, pilgrimage=stamp_office. Some nearby nodes in the "
                "same changeset only have opening_hours and are not the center objects."
            ),
        }
        ref_path.write_text(json.dumps(reference, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"Wrote {ref_path}")

    pois = load_pois(
        data_dir / "pilegrimsleden_shelters_raw.json",
        data_dir / "pilegrimsleden_shelters.osm",
    )
    shelter_records = json.loads(
        (data_dir / "pilegrimsleden_shelters_raw.json").read_text(encoding="utf-8")
    )["pois"]
    log(f"Loaded {len(pois)} CMS shelter POIs")

    if args.pilgrim_centers_only:
        raw_path = data_dir / "osm_existing_shelters_raw.json"
        if not raw_path.exists():
            raise RuntimeError(f"Missing {raw_path}; run a full comparison first")
        log(f"Reusing {raw_path} (no PBF rescan, no 387-POI rematch)")
        osm_elements = load_existing_osm_elements(raw_path)
        shelter_rows = load_shelter_csv(data_dir / "osm_comparison_results.csv")
        result = compare_pilgrim_centers(
            data_dir,
            pois,
            osm_elements,
            shelter_rows,
            shelter_records,
            split_by_trail=True if args.split_by_trail or args.pilgrim_centers_only else False,
        )
        print(result["recheck_text"])
        print("By-trail split:")
        for item in result["summaries"]:
            print(
                f"{item['trail']}: shelters: {item['shelters']}, "
                f"pilgrim centers: {item['pilgrim_centers']}, "
                f"gaps: {item['shelter_gaps']}"
            )
        return 0

    bboxes = trail_bboxes(pois)
    bbox = overall_bbox(pois)
    log(
        "POI bbox with 5 km buffer: "
        f"{bbox[0]:.4f},{bbox[1]:.4f} {bbox[2]:.4f},{bbox[3]:.4f}"
    )

    pbf_paths = download_geofabrik(data_dir / "geofabrik")
    merged: dict[tuple[str, int], dict[str, Any]] = {}
    for pbf_path in pbf_paths:
        for el in extract_from_pbf(pbf_path, bbox):
            merged[(el["type"], el["id"])] = el

    osm_elements = list(merged.values())
    raw_path = data_dir / "osm_existing_shelters_raw.json"
    raw_payload = {
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "source": "geofabrik",
        "extracts": [item["url"] for item in GEOFABRIK_EXTRACTS],
        "strategy": (
            "Download Geofabrik Norway and Sweden PBF extracts, then keep nodes/ways "
            "tagged as pilgrim centers (any pilgrimage=* on nodes or way centroids) "
            "or overnight/shelter/picnic features inside the CMS POI bounding box "
            "plus 5 km."
        ),
        "bbox": {
            "min_lat": bbox[0],
            "min_lon": bbox[1],
            "max_lat": bbox[2],
            "max_lon": bbox[3],
        },
        "trail_bboxes": {
            trail: {"min_lat": b[0], "min_lon": b[1], "max_lat": b[2], "max_lon": b[3]}
            for trail, b in bboxes.items()
        },
        "element_count": len(osm_elements),
        "elements": osm_elements,
    }
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"Geofabrik filter kept {len(osm_elements)} unique elements; wrote {raw_path}")

    grid = build_grid(osm_elements)
    results: list[dict[str, Any]] = []
    for poi in pois:
        nearby = nearby_elements(poi["lat"], poi["lon"], grid, NAME_MATCH_RADIUS_M)
        classified = classify_poi(poi, nearby)
        results.append({**poi, **classified})

    time.sleep(REQUEST_GAP_SEC)
    csv_path = data_dir / "osm_comparison_results.csv"
    md_path = data_dir / "osm_comparison_summary.md"
    write_csv(csv_path, results)
    shelter_rows = load_shelter_csv(csv_path)
    result = compare_pilgrim_centers(
        data_dir,
        pois,
        osm_elements,
        shelter_rows,
        shelter_records,
        split_by_trail=args.split_by_trail,
    )
    report = markdown_report(
        results, result["osm_centers"], result["pilgrim_unmatched"], scheme
    )
    md_path.write_text(report, encoding="utf-8")
    log(f"Wrote {csv_path}")
    log(f"Wrote {md_path}")

    print(status_tables(results))
    print()
    print(result["recheck_text"])
    print(f"OSM pilgrim-center objects: {len(result['osm_centers'])}")
    print(
        "OSM named pilgrim centers with no CMS match within 250 m: "
        f"{len(result['pilgrim_unmatched'])}"
    )
    if result["summaries"]:
        print("By-trail split:")
        for item in result["summaries"]:
            print(
                f"{item['trail']}: shelters: {item['shelters']}, "
                f"pilgrim centers: {item['pilgrim_centers']}, "
                f"gaps: {item['shelter_gaps']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
