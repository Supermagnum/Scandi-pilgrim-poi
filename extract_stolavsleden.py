#!/usr/bin/env python3
"""Extract St. Olavsleden POIs and GPX routes from stolavsleden.com / Naturkartan.

Read-only against trail sources and OSM. Writes local files under data/.
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
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(OSM mapping research; St. Olavsleden Sweden + horseback POIs; "
    "+https://www.openstreetmap.org/)"
)
REQUEST_GAP_SEC = 1.0
NATURKARTAN_API = "https://api.naturkartan.se/v2"
GUIDE_ID = 154
ORG_ID = 139

# Naturkartan category ids used on the embedded map quick filters.
CAT_HOSTEL = 55
CAT_CAMPING = 56
CAT_TENT = 89
CAT_SHELTER = 61
CAT_RESTING_CABIN = 68
CAT_PILGRIM_WELCOME = 123
CAT_HIKER_FRIENDLY = 122
CAT_RESTING = 60
CAT_SERVICE = 72
CAT_PILGRIM_SERVICE = 96
CAT_HIKING = 33
CAT_BIKING = 31
CAT_RIDING = 34

OVERNIGHT_CATS = {
    CAT_HOSTEL,
    CAT_CAMPING,
    CAT_TENT,
    CAT_SHELTER,
    CAT_RESTING_CABIN,
    CAT_PILGRIM_WELCOME,
    CAT_HIKER_FRIENDLY,
}
VET_RE = re.compile(
    r"veterin|djurklin|djursjuk|vetzervice|djurklinik|distriktsveterin",
    re.I,
)
FARRIER_RE = re.compile(r"hovslag|farrier|hästsk|hastsk", re.I)

GPX_URLS = {
    "hiking": "https://stolavsleden.com/wp-content/uploads/2022/06/st-olavsleden-hiking-2022.gpx",
    "biking": "https://stolavsleden.com/wp-content/uploads/2021/06/StOlavsleden_Sundsvall_Trondheim_bike.gpx",
    "horseback": "https://stolavsleden.com/wp-content/uploads/2020/04/s-t-olavsleden-ridning.gpx",
}
PAGES = {
    "hiking": "https://stolavsleden.com/hiking/",
    "biking": "https://stolavsleden.com/biking/",
    "horseback": "https://stolavsleden.com/horse-back-riding/",
}

# Approximate Sweden/Norway split along this corridor (Skalstugan / riksgräns).
SWEDEN_LON_MIN = 12.05
MATCH_RADIUS_M = 100.0
POSSIBLE_RADIUS_M = 250.0

CSV_FIELDS = [
    "trail",
    "country",
    "poi_name",
    "category",
    "lat",
    "lon",
    "match_status",
    "matched_osm_id",
    "matched_osm_url",
    "distance_m",
    "tag_diff",
    "source",
    "path_types",
    "naturkartan_id",
]


def log(message: str) -> None:
    print(message, file=sys.stderr)


def http_json(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def http_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=180) as response:
        return response.read()


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def country_for(lat: float, lon: float) -> str:
    if lon >= SWEDEN_LON_MIN:
        return "Sweden"
    return "Norway"


def site_categories(site: dict[str, Any]) -> list[dict[str, Any]]:
    return list(site.get("categories") or [])


def category_ids(site: dict[str, Any]) -> set[int]:
    return {int(c["id"]) for c in site_categories(site) if c.get("id") is not None}


def category_labels(site: dict[str, Any]) -> list[str]:
    labels = []
    for cat in site_categories(site):
        label = cat.get("label") or cat.get("name") or ""
        if label and label not in labels:
            labels.append(label)
    return labels


def site_text(site: dict[str, Any]) -> str:
    parts = [
        site.get("name") or "",
        site.get("description") or "",
        site.get("short_description") or "",
        " ".join(category_labels(site)),
    ]
    return "\n".join(parts)


def is_trail_geometry(site: dict[str, Any]) -> bool:
    return (site.get("type") or "").lower() == "trail"


def classify_site(site: dict[str, Any]) -> str | None:
    if is_trail_geometry(site):
        return None
    text = site_text(site)
    cids = category_ids(site)
    if FARRIER_RE.search(text):
        return "Farrier"
    if VET_RE.search(text) or (
        CAT_SERVICE in cids and re.search(r"veterin|djur", text, re.I)
    ):
        return "Veterinarian"
    if cids & OVERNIGHT_CATS:
        if CAT_SHELTER in cids:
            return "Vindskydd"
        if CAT_CAMPING in cids:
            return "Campingplass"
        if CAT_TENT in cids:
            return "Teltplass"
        if CAT_RESTING_CABIN in cids:
            return "Raststuga"
        return "Boende"
    return None


def path_types_for_site(
    site_id: int,
    hiking_ids: set[int],
    biking_ids: set[int],
    riding_ids: set[int],
    cids: set[int],
) -> list[str]:
    types: list[str] = []
    if site_id in hiking_ids or CAT_HIKING in cids:
        types.append("hiking")
    if site_id in biking_ids or CAT_BIKING in cids:
        types.append("biking")
    if site_id in riding_ids or CAT_RIDING in cids:
        types.append("horseback")
    if not types:
        types.append("all")
    return types


def discover_reference(data_dir: Path) -> dict[str, Any]:
    log("Discovering stolavsleden.com / Naturkartan endpoints")
    page_embeds: dict[str, Any] = {}
    for key, url in PAGES.items():
        time.sleep(REQUEST_GAP_SEC)
        html = http_bytes(url).decode("utf-8", errors="replace")
        embed = {}
        for attr in (
            "data-naturkartan-client",
            "data-naturkartan-guide",
            "data-naturkartan-query",
            "data-naturkartan-quick-categories",
            "data-naturkartan-strict",
        ):
            match = re.search(rf'{attr}="([^"]+)"', html)
            if match:
                embed[attr] = match.group(1).replace("&amp;", "&")
        gpx = re.findall(r'https://stolavsleden\.com/wp-content/uploads/[^"\']+\.gpx', html)
        page_embeds[key] = {"url": url, "embed": embed, "gpx_links": sorted(set(gpx))}
        log(f"  {key}: guide={embed.get('data-naturkartan-guide')} gpx={len(set(gpx))}")

    time.sleep(REQUEST_GAP_SEC)
    guide = http_json(f"{NATURKARTAN_API}/guides/{GUIDE_ID}")
    time.sleep(REQUEST_GAP_SEC)
    sites_payload = http_json(f"{NATURKARTAN_API}/sites.json?guide_ids={GUIDE_ID}")
    sample = (sites_payload.get("sites") or [None])[0]

    reference = {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "cms": "WordPress (stolavsleden.com) + Naturkartan map embed",
        "user_agent": USER_AGENT,
        "wordpress": {
            "evidence": "Link: <https://stolavsleden.com/wp-json/>; rel=https://api.w.org/",
            "wp_json": "https://stolavsleden.com/wp-json/",
            "note": (
                "WP REST has no public POI custom post type; map POIs come from Naturkartan."
            ),
        },
        "naturkartan": {
            "embed_script": "https://map-embed.naturkartan.se/embed.js",
            "api_base": NATURKARTAN_API,
            "guide_id": GUIDE_ID,
            "organization_id": ORG_ID,
            "endpoints": {
                "guide": f"{NATURKARTAN_API}/guides/{GUIDE_ID}",
                "sites_by_guide": f"{NATURKARTAN_API}/sites.json?guide_ids={GUIDE_ID}",
                "sites_by_ids": f"{NATURKARTAN_API}/sites.json?site_ids={{comma_separated}}",
                "categories": f"{NATURKARTAN_API}/categories",
                "trip": f"{NATURKARTAN_API}/trips/{{id}}",
            },
            "path_category_ids": {
                "hiking": CAT_HIKING,
                "biking": CAT_BIKING,
                "horseback": CAT_RIDING,
            },
            "quick_category_ids_hiking": [55, 54, 31, 34, 63, 72, 19, 86, 60, 53, 73, 97],
            "sample_site_keys": sorted(sample.keys()) if isinstance(sample, dict) else [],
            "sample_site": sample,
            "sites_returned": len(sites_payload.get("sites") or []),
        },
        "pages": page_embeds,
        "gpx_urls": GPX_URLS,
        "osm_tag_notes": {
            "horse_route": (
                "Taginfo: route=horse is used on thousands of relations; "
                "horse=designated is common on ways. horseback_path.osm uses both."
            ),
            "veterinary": "amenity=veterinary (~65k uses).",
            "farrier": (
                "craft=farrier is rare (~7 uses); shop=farrier unused. "
                "No farrier POIs were present in Naturkartan guide 154 at extraction time."
            ),
        },
    }
    path = data_dir / "stolavsleden_api_reference.json"
    path.write_text(json.dumps(reference, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {path}")
    return reference


def fetch_trip_path_site_ids() -> dict[str, set[int]]:
    mapping = {
        "hiking": {61, 53, 72, 71, 73, 97, 75},
        "horseback": {227},
        "biking": {228},
    }
    out: dict[str, set[int]] = {key: set() for key in mapping}
    for path_type, trip_ids in mapping.items():
        for trip_id in trip_ids:
            time.sleep(REQUEST_GAP_SEC)
            trip = http_json(f"{NATURKARTAN_API}/trips/{trip_id}")
            for item in trip.get("trip_items") or []:
                sid = item.get("site_id")
                if sid:
                    out[path_type].add(int(sid))
            log(f"  trip {trip_id} ({trip.get('name')}): {len(trip.get('trip_items') or [])} segments")
    return out


def fetch_all_sites(cache_path: Path) -> list[dict[str, Any]]:
    if cache_path.exists() and cache_path.stat().st_size > 100_000:
        log(f"Reusing {cache_path}")
        return json.loads(cache_path.read_text(encoding="utf-8"))["sites"]
    time.sleep(REQUEST_GAP_SEC)
    payload = http_json(f"{NATURKARTAN_API}/sites.json?guide_ids={GUIDE_ID}")
    sites = payload.get("sites") or []
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "guide_id": GUIDE_ID,
                "count": len(sites),
                "sites": sites,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    log(f"Fetched {len(sites)} Naturkartan sites for guide {GUIDE_ID}")
    return sites


def download_gpx(data_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for key, url in GPX_URLS.items():
        dest = data_dir / f"{key}.gpx"
        time.sleep(REQUEST_GAP_SEC)
        try:
            body = http_bytes(url)
        except urllib.error.HTTPError as exc:
            log(f"GPX download failed for {key}: HTTP {exc.code}")
            continue
        if b"<gpx" not in body[:500].lower() and b"<GPX" not in body[:500]:
            log(f"GPX download for {key} does not look like GPX ({len(body)} bytes)")
            continue
        dest.write_bytes(body)
        out[key] = dest
        log(f"Downloaded {dest.name} ({len(body)} bytes)")
    return out


def gpx_track_points(path: Path) -> list[tuple[float, float]]:
    root = ET.parse(path).getroot()
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
    points: list[tuple[float, float]] = []
    for trkpt in root.findall(f".//{ns}trkpt"):
        points.append((float(trkpt.attrib["lat"]), float(trkpt.attrib["lon"])))
    if not points:
        for wpt in root.findall(f".//{ns}wpt"):
            points.append((float(wpt.attrib["lat"]), float(wpt.attrib["lon"])))
    return points


def simplify_points(
    points: list[tuple[float, float]], max_points: int = 2000
) -> list[tuple[float, float]]:
    if len(points) <= max_points:
        return points
    step = math.ceil(len(points) / max_points)
    simplified = points[::step]
    if simplified[-1] != points[-1]:
        simplified.append(points[-1])
    return simplified


def deviation_summary(
    hiking: list[tuple[float, float]], horseback: list[tuple[float, float]], threshold_m: float = 150.0
) -> dict[str, Any]:
    """Sample horseback points and measure distance to nearest hiking point."""
    if not hiking or not horseback:
        return {"compared": 0, "deviating": 0, "max_m": None, "samples": []}
    sample = horseback[:: max(1, len(horseback) // 200)]
    deviations = []
    for lat, lon in sample:
        best = min(haversine_m(lat, lon, hlat, hlon) for hlat, hlon in hiking[:: max(1, len(hiking) // 500)])
        if best >= threshold_m:
            deviations.append({"lat": lat, "lon": lon, "distance_to_hiking_m": round(best, 1)})
    deviations.sort(key=lambda item: item["distance_to_hiking_m"], reverse=True)
    return {
        "threshold_m": threshold_m,
        "compared": len(sample),
        "deviating": len(deviations),
        "max_m": deviations[0]["distance_to_hiking_m"] if deviations else 0.0,
        "samples": deviations[:15],
    }


def write_horseback_path_osm(path: Path, points: list[tuple[float, float]]) -> None:
    points = simplify_points(points, max_points=2500)
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    node_ids = []
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
        ("name", "St. Olavsleden (horseback riding)"),
        ("route", "horse"),
        ("horse", "designated"),
        ("network", "St. Olavsleden"),
        ("source", "stolavsleden.com"),
        ("note", "Derived from official horseback GPX; research aid, not an OSM import"),
    ]
    for key, value in tags:
        lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
    lines.append("  </way>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def osm_tags_for_category(category: str) -> list[tuple[str, str]]:
    if category == "Vindskydd":
        return [("amenity", "shelter"), ("shelter_type", "lean_to")]
    if category == "Campingplass":
        return [("tourism", "camp_site")]
    if category == "Teltplass":
        return [("tourism", "camp_site"), ("tents", "yes")]
    if category == "Raststuga":
        return [("tourism", "wilderness_hut")]
    if category == "Boende":
        return [("tourism", "hostel")]
    if category == "Veterinarian":
        return [("amenity", "veterinary")]
    if category == "Farrier":
        return [("craft", "farrier")]
    return []


def write_shelters_osm(path: Path, records: list[dict[str, Any]]) -> None:
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    node_ids: list[int] = []
    for index, record in enumerate(records, start=1):
        node_id = -index
        node_ids.append(node_id)
        lines.append(
            f"  <node id='{node_id}' version='0' action='modify' visible='true' "
            f"lat='{record['lat']:.7f}' lon='{record['lon']:.7f}'>"
        )
        tags = [
            ("name", record["title"]),
            ("source", record.get("source") or "stolavsleden.com"),
            ("network", "St. Olavsleden"),
            ("note:trail", "St. Olavsleden"),
            ("note:country", record.get("country") or ""),
            ("note:osm_route_relation", "10524322"),
            ("pilegrimsleden:poi_type", record.get("category") or ""),
        ]
        if record.get("url"):
            tags.append(("url", record["url"]))
        if record.get("id"):
            tags.append(("stolavsleden:id", str(record["id"])))
        tags.extend(osm_tags_for_category(record.get("category") or ""))
        for key, value in tags:
            if not value:
                continue
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </node>")
    if node_ids:
        rel_id = min(node_ids) - 1
        lines.append(
            f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>"
        )
        for node_id in node_ids:
            lines.append(f"    <member type='node' ref='{node_id}' role='shelter'/>")
        for key, value in [
            ("type", "site"),
            ("name", "St. Olavsleden overnight POIs"),
            ("network", "Pilegrimsleden"),
            ("note:trail", "St. Olavsleden"),
            ("note:osm_route_relation", "10524322"),
            ("source", "openstreetmap.org/relation/10524322"),
            (
                "note",
                "Local JOSM research relation grouping overnight POIs for this trail; "
                "not an OSM import",
            ),
        ]:
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </relation>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_existing_st_olav(data_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    trail_dir = data_dir / "by_trail" / "St-Olavsleden"
    shelters: list[dict[str, str]] = []
    centers: list[dict[str, str]] = []
    shelters_path = trail_dir / "shelters.csv"
    centers_path = trail_dir / "pilgrim_centers.csv"
    if shelters_path.exists():
        with shelters_path.open(encoding="utf-8", newline="") as handle:
            shelters = list(csv.DictReader(handle))
    if centers_path.exists():
        with centers_path.open(encoding="utf-8", newline="") as handle:
            centers = list(csv.DictReader(handle))
    return shelters, centers


def compare_to_osm(
    pois: list[dict[str, Any]],
    pbf_path: Path,
) -> list[dict[str, Any]]:
    """Match POIs against Geofabrik Sweden extract (nodes/ways, closest within 250 m)."""
    import osmium

    keep_tourism = {
        "wilderness_hut",
        "hostel",
        "camp_site",
        "chalet",
        "guest_house",
        "alpine_hut",
        "apartment",
        "cabin",
        "hotel",
    }

    def is_strong_lodging(tags: dict[str, str]) -> bool:
        if tags.get("amenity") in {"shelter", "veterinary"}:
            return True
        if tags.get("tourism") in keep_tourism:
            return True
        if tags.get("craft") == "farrier" or tags.get("shop") == "farrier":
            return True
        return False

    def is_hut_only(tags: dict[str, str]) -> bool:
        """building=hut with no supporting tourism/amenity lodging tag."""
        if tags.get("building") != "hut":
            return False
        if tags.get("tourism") or tags.get("amenity"):
            return False
        return True

    class Handler(osmium.SimpleHandler):
        def __init__(self) -> None:
            super().__init__()
            self.elements: list[dict[str, Any]] = []

        def _wanted(self, tags: Any) -> bool:
            if is_strong_lodging({tag.k: tag.v for tag in tags}):
                return True
            if tags.get("building") == "hut":
                return True
            return False

        def _add(self, kind: str, obj: Any, lat: float, lon: float) -> None:
            self.elements.append(
                {
                    "type": kind,
                    "id": int(obj.id),
                    "lat": lat,
                    "lon": lon,
                    "tags": {tag.k: tag.v for tag in obj.tags},
                }
            )

        def node(self, node: Any) -> None:
            if not node.location.valid() or not self._wanted(node.tags):
                return
            self._add("node", node, float(node.location.lat), float(node.location.lon))

        def way(self, way: Any) -> None:
            if not self._wanted(way.tags):
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
            self._add("way", way, sum(lats) / len(lats), sum(lons) / len(lons))

    if not pois:
        return []
    log(f"Scanning {pbf_path.name} for shelter/vet/farrier/hut tags")
    handler = Handler()
    handler.apply_file(str(pbf_path), locations=True, idx="flex_mem")
    log(f"  kept {len(handler.elements)} OSM elements")

    results = []
    for poi in pois:
        nearby: list[tuple[float, dict[str, Any]]] = []
        for el in handler.elements:
            dist = haversine_m(poi["lat"], poi["lon"], el["lat"], el["lon"])
            if dist <= POSSIBLE_RADIUS_M:
                nearby.append((dist, el))
        nearby.sort(
            key=lambda item: (
                0 if is_strong_lodging(item[1].get("tags") or {}) else 1,
                item[0],
                item[1]["type"],
                int(item[1]["id"]),
            )
        )
        best = nearby[0] if nearby else None
        if best is None:
            status = "gap"
            matched = None
        else:
            dist, el = best
            tags = el.get("tags") or {}
            if is_hut_only(tags):
                # Ambiguous without tourism/amenity; never "matched".
                status = "possible"
            elif dist <= MATCH_RADIUS_M:
                status = "matched"
            else:
                status = "possible"
            matched = el
        tags = (matched or {}).get("tags") or {}
        tag_diff = ""
        if matched:
            tag_diff = "; ".join(
                f"{key}={tags[key]}"
                for key in ("tourism", "amenity", "building", "craft", "shop", "name")
                if tags.get(key)
            )
        results.append(
            {
                **poi,
                "match_status": status,
                "matched_osm_id": f"{matched['type']}/{matched['id']}" if matched else "",
                "matched_osm_url": (
                    f"https://www.openstreetmap.org/{matched['type']}/{matched['id']}"
                    if matched
                    else ""
                ),
                "distance_m": round(best[0], 1) if matched and best else "",
                "tag_diff": tag_diff,
            }
        )
    return results


def merge_shelter_rows(
    existing: list[dict[str, str]], swedish: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    for row in existing:
        rows.append(
            {
                "trail": row.get("trail") or "St. Olavsleden",
                "country": row.get("country") or "Norway",
                "poi_name": row["poi_name"],
                "category": row["category"],
                "lat": row["lat"],
                "lon": row["lon"],
                "match_status": row["match_status"],
                "matched_osm_id": row.get("matched_osm_id") or "",
                "matched_osm_url": row.get("matched_osm_url") or "",
                "distance_m": row.get("distance_m") or "",
                "tag_diff": row.get("tag_diff") or "",
                "source": row.get("source") or "pilegrimsleden.no",
                "path_types": row.get("path_types") or "hiking",
                "naturkartan_id": row.get("naturkartan_id") or "",
            }
        )

    def near_existing(lat: float, lon: float) -> bool:
        for row in rows:
            try:
                dist = haversine_m(lat, lon, float(row["lat"]), float(row["lon"]))
            except (TypeError, ValueError):
                continue
            if dist <= 80:
                return True
        return False

    added = 0
    for poi in swedish:
        if near_existing(poi["lat"], poi["lon"]):
            continue
        rows.append(
            {
                "trail": "St. Olavsleden",
                "country": poi.get("country") or "Sweden",
                "poi_name": poi["title"],
                "category": poi["category"],
                "lat": f"{poi['lat']:.7f}",
                "lon": f"{poi['lon']:.7f}",
                "match_status": poi.get("match_status") or "",
                "matched_osm_id": poi.get("matched_osm_id") or "",
                "matched_osm_url": poi.get("matched_osm_url") or "",
                "distance_m": poi.get("distance_m") or "",
                "tag_diff": poi.get("tag_diff") or "",
                "source": "stolavsleden.com",
                "path_types": ";".join(poi.get("path_types") or ["all"]),
                "naturkartan_id": str(poi.get("id") or ""),
            }
        )
        added += 1
    rows.sort(key=lambda row: (row["country"], row["match_status"], row["poi_name"].lower()))
    return rows, added


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
    )
    parser.add_argument(
        "--skip-osm-compare",
        action="store_true",
        help="Skip Geofabrik Sweden PBF scan",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir: Path = args.data_dir
    stolav_dir = data_dir / "stolavsleden"
    stolav_dir.mkdir(parents=True, exist_ok=True)
    trail_dir = data_dir / "by_trail" / "St-Olavsleden"
    trail_dir.mkdir(parents=True, exist_ok=True)

    discover_reference(data_dir)
    path_site_ids = fetch_trip_path_site_ids()
    sites = fetch_all_sites(stolav_dir / "sites_guide_154.json")
    gpx_paths = download_gpx(stolav_dir)

    overnight: list[dict[str, Any]] = []
    horse_services: list[dict[str, Any]] = []
    for site in sites:
        if site.get("latitude") is None or site.get("longitude") is None:
            continue
        category = classify_site(site)
        if not category:
            continue
        lat = float(site["latitude"])
        lon = float(site["longitude"])
        record = {
            "id": site.get("id"),
            "title": site.get("name") or "",
            "slug": site.get("slug") or "",
            "url": site.get("url") or "",
            "description": (site.get("short_description") or site.get("description") or "")[:500],
            "category": category,
            "lat": lat,
            "lon": lon,
            "country": country_for(lat, lon),
            "path_types": path_types_for_site(
                int(site["id"]),
                path_site_ids["hiking"],
                path_site_ids["biking"],
                path_site_ids["horseback"],
                category_ids(site),
            ),
            "categories": category_labels(site),
            "source": "stolavsleden.com",
        }
        if category in {"Farrier", "Veterinarian"}:
            horse_services.append(record)
        else:
            overnight.append(record)

    log(f"Overnight/shelter POIs: {len(overnight)}")
    log(f"Horse service POIs: {len(horse_services)} (farriers={sum(1 for p in horse_services if p['category']=='Farrier')}, vets={sum(1 for p in horse_services if p['category']=='Veterinarian')})")

    swedish_overnight = [p for p in overnight if p["country"] == "Sweden"]
    log(f"Swedish overnight POIs: {len(swedish_overnight)}")

    if not args.skip_osm_compare:
        pbf = data_dir / "geofabrik" / "sweden-latest.osm.pbf"
        if not pbf.exists():
            raise RuntimeError(f"Missing {pbf}")
        swedish_overnight = compare_to_osm(swedish_overnight, pbf)
        horse_services = compare_to_osm(horse_services, pbf)
    else:
        for poi in swedish_overnight + horse_services:
            poi.update(
                {
                    "match_status": "",
                    "matched_osm_id": "",
                    "matched_osm_url": "",
                    "distance_m": "",
                    "tag_diff": "",
                }
            )

    existing_shelters, existing_centers = load_existing_st_olav(data_dir)
    merged_rows, added = merge_shelter_rows(existing_shelters, swedish_overnight)
    write_csv(trail_dir / "shelters.csv", merged_rows, CSV_FIELDS)

    # Rebuild shelters.osm from merged CSV (Norway existing + Sweden new).
    osm_records = []
    for row in merged_rows:
        osm_records.append(
            {
                "id": row.get("naturkartan_id") or "",
                "title": row["poi_name"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "category": row["category"],
                "country": row["country"],
                "source": row["source"],
                "url": "",
            }
        )
    write_shelters_osm(trail_dir / "shelters.osm", osm_records)

    # Keep pilgrim centers; ensure country column present.
    center_rows = []
    for row in existing_centers:
        center_rows.append(
            {
                **row,
                "country": row.get("country") or "Norway",
                "source": row.get("source") or "pilegrimsleden.no",
                "path_types": row.get("path_types") or "",
                "naturkartan_id": row.get("naturkartan_id") or "",
            }
        )
    write_csv(
        trail_dir / "pilgrim_centers.csv",
        center_rows,
        list(dict.fromkeys(list(existing_centers[0].keys()) + ["country", "source", "path_types", "naturkartan_id"]))
        if existing_centers
        else CSV_FIELDS,
    )

    horse_rows = []
    for poi in horse_services:
        horse_rows.append(
            {
                "trail": "St. Olavsleden",
                "country": poi["country"],
                "poi_name": poi["title"],
                "category": poi["category"],
                "lat": f"{poi['lat']:.7f}",
                "lon": f"{poi['lon']:.7f}",
                "match_status": poi.get("match_status") or "",
                "matched_osm_id": poi.get("matched_osm_id") or "",
                "matched_osm_url": poi.get("matched_osm_url") or "",
                "distance_m": poi.get("distance_m") or "",
                "tag_diff": poi.get("tag_diff") or "",
                "source": "stolavsleden.com",
                "path_types": "horseback",
                "naturkartan_id": str(poi.get("id") or ""),
            }
        )
    write_csv(trail_dir / "horseback_service_points.csv", horse_rows, CSV_FIELDS)

    deviation = {}
    if "horseback" in gpx_paths:
        horse_pts = gpx_track_points(gpx_paths["horseback"])
        write_horseback_path_osm(trail_dir / "horseback_path.osm", horse_pts)
        if "hiking" in gpx_paths:
            hike_pts = gpx_track_points(gpx_paths["hiking"])
            deviation = deviation_summary(hike_pts, horse_pts)
            log(
                f"GPX deviation samples >=150m from hiking line: "
                f"{deviation['deviating']} / {deviation['compared']} (max {deviation['max_m']} m)"
            )
        # copy GPX into trail folder too
        (trail_dir / "horseback_path.gpx").write_bytes(gpx_paths["horseback"].read_bytes())
    if "hiking" in gpx_paths:
        (trail_dir / "hiking_path.gpx").write_bytes(gpx_paths["hiking"].read_bytes())

    raw = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "overnight_count": len(overnight),
        "swedish_overnight_count": len(swedish_overnight),
        "swedish_added_after_dedupe": added,
        "horse_services": horse_services,
        "swedish_overnight": swedish_overnight,
        "gpx_deviation": deviation,
        "path_segment_counts": {k: len(v) for k, v in path_site_ids.items()},
    }
    (stolav_dir / "extract_summary.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    horse_counts = Counter(r["match_status"] for r in horse_rows)
    shelter_counts = Counter(r["match_status"] for r in merged_rows if r["country"] == "Sweden")
    print("Swedish overnight POIs added (after NO dedupe):", added)
    print("Horseback service POIs:", len(horse_rows))
    print(
        "Horseback OSM status:",
        f"matched={horse_counts.get('matched', 0)} "
        f"possible={horse_counts.get('possible', 0)} "
        f"gap={horse_counts.get('gap', 0)}",
    )
    print(
        "Swedish shelter OSM status:",
        f"matched={shelter_counts.get('matched', 0)} "
        f"possible={shelter_counts.get('possible', 0)} "
        f"gap={shelter_counts.get('gap', 0)}",
    )
    if deviation:
        print(
            "GPX horseback vs hiking deviations (>=150 m): "
            f"{deviation['deviating']} of {deviation['compared']} samples "
            f"(max {deviation['max_m']} m)"
        )
    print(f"Farriers found: {sum(1 for r in horse_rows if r['category']=='Farrier')}")
    print(f"Veterinarians found: {sum(1 for r in horse_rows if r['category']=='Veterinarian')}")
    print(f"St. Olavsleden shelters.csv rows: {len(merged_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
