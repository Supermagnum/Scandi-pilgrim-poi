#!/usr/bin/env python3
"""Extract overnight/shelter POIs from pilegrimsleden.no and emit JSON, CSV, and JOSM OSM XML.

Data source (discovered from https://www.pilegrimsleden.no/kart):
  GraphQL POST https://www.pilegrimsleden.no/actions/graphql/api
    query poiEntries / entryCount on section "poi" (poi_Entry)
    fields: id, title, slug, url, intro, location { lat lng }, poiType { id title slug }
    trail relation field handle on poi_Entry is "trail", but the public schema returns
    empty lists for that field. Inverse relations work via relatedTo: [trailEntryId].

  Map front-end also uses:
    POST /actions/pilegrimsleden/poi/maplist  (FormData: accomodationType[], trail, lang)
    GET  /actions/pilegrimsleden/poi/trailpoints?trailId=<id>

Respectful use: descriptive User-Agent, delay between requests. robots.txt currently 404.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_URL = "https://www.pilegrimsleden.no"
GRAPHQL_URL = f"{BASE_URL}/actions/graphql/api"
MAPLIST_URL = f"{BASE_URL}/actions/pilegrimsleden/poi/maplist"
TRAILPOINTS_URL = f"{BASE_URL}/actions/pilegrimsleden/poi/trailpoints"
USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(OSM mapping research; shelter/cabin POIs along Pilegrimsleden; "
    "+https://www.openstreetmap.org/)"
)
REQUEST_DELAY_SEC = 0.6
GRAPHQL_PAGE_SIZE = 100

TRAILS: list[dict[str, Any]] = [
    {"id": 212, "title": "Gudbrandsdalsleden", "slug": "gudbrandsdalsleden"},
    {"id": 190, "title": "St. Olavsleden", "slug": "st-olavsleden"},
    {"id": 175, "title": "Borgleden", "slug": "borgleden"},
    {"id": 97, "title": "Kystpilegrimsleia", "slug": "kystpilegrimsleia"},
    {"id": 6418, "title": "Tunsbergleden", "slug": "tunsbergleden"},
    {"id": 182, "title": "Østerdalsleden", "slug": "osterdalsleden"},
    {"id": 132, "title": "Valldalsleden", "slug": "valldalsleden"},
    {"id": 202, "title": "Romboleden", "slug": "romboleden"},
    {"id": 194, "title": "Nordleden", "slug": "nordleden"},
]

# Filter-panel values plus closely related overnight/shelter types present in poiType.
CORE_SHELTER_CATEGORIES = {
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
}
RASTEPLASS = "Rasteplass"
INCLUDE_POI_TYPE_IDS = [
    12,  # Pilegrimsherberge
    8,  # Vandrerhjem
    40692,  # Campingplass
    9,  # Rom og hytter
    7,  # Teltplass
    10,  # Gapahuk
    88388,  # Rasteplass (further filtered for built shelter)
    359812,  # Glamping
    359833,  # Rorbu
    439509,  # Pilegrimsbu
    341118,  # Dagsturhytte
]
EXCLUDED_UNLESS_ALSO_SHELTER = {
    "Hotell",
    "Kirke",
    "Transport",
    "Spisested",
    "Matbutikk",
    "Kulturminne",
    "Pilegrimssenter",
}

# Used only for Rasteplass entries that do not already carry a core shelter type.
RASTEPLASS_SHELTER_RE = re.compile(
    r"gapahuk|leskur|rastebu|grillhytte|grillbu|b[åa]lbu|b[åa]lhus|"
    r"lean[-\s]?to|wilderness\s+hut|overbygg|rastehytte|dagsturhytte|"
    r"pilegrimsbu|vedbu|lavvo|gapahuker|tak over",
    re.IGNORECASE,
)

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

POI_QUERY = """
query PoiPage($types: [QueryArgument], $limit: Int, $offset: Int) {
  poiEntries(poiType: $types, limit: $limit, offset: $offset) {
    ... on poi_Entry {
      id
      title
      slug
      url
      intro
      location { lat lng }
      poiType { id title slug }
    }
  }
}
"""

TRAIL_POI_IDS_QUERY = """
query TrailPoiIds($types: [QueryArgument], $trailId: [QueryArgument], $limit: Int, $offset: Int) {
  poiEntries(poiType: $types, relatedTo: $trailId, limit: $limit, offset: $offset) {
    ... on poi_Entry {
      id
    }
  }
}
"""


def log(message: str) -> None:
    print(message, file=sys.stderr)


def http_json(
    url: str,
    payload: dict[str, Any] | None = None,
    method: str | None = None,
    form: dict[str, str] | None = None,
) -> Any:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, application/graphql-response+json, */*",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
        method = method or "POST"
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        from urllib.parse import urlencode

        data = urlencode(form).encode("utf-8")
        method = method or "POST"
    req = urllib.request.Request(url, data=data, headers=headers, method=method or "GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:500]}") from exc
    text = raw.decode("utf-8")
    if not text:
        return None
    return json.loads(text)


def graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    result = http_json(GRAPHQL_URL, payload={"query": query, "variables": variables or {}})
    if result.get("errors"):
        raise RuntimeError(f"GraphQL errors: {result['errors']}")
    return result["data"]


def paginate_pois() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    offset = 0
    while True:
        log(f"Fetching poiEntries offset={offset} limit={GRAPHQL_PAGE_SIZE}")
        data = graphql(
            POI_QUERY,
            {"types": INCLUDE_POI_TYPE_IDS, "limit": GRAPHQL_PAGE_SIZE, "offset": offset},
        )
        page = data.get("poiEntries") or []
        items.extend(page)
        if len(page) < GRAPHQL_PAGE_SIZE:
            break
        offset += GRAPHQL_PAGE_SIZE
        time.sleep(REQUEST_DELAY_SEC)
    return items


def paginate_trail_ids(trail_id: int) -> set[str]:
    ids: set[str] = set()
    offset = 0
    while True:
        data = graphql(
            TRAIL_POI_IDS_QUERY,
            {
                "types": INCLUDE_POI_TYPE_IDS,
                "trailId": [trail_id],
                "limit": GRAPHQL_PAGE_SIZE,
                "offset": offset,
            },
        )
        page = data.get("poiEntries") or []
        ids.update(str(item["id"]) for item in page)
        if len(page) < GRAPHQL_PAGE_SIZE:
            break
        offset += GRAPHQL_PAGE_SIZE
        time.sleep(REQUEST_DELAY_SEC)
    return ids


def category_titles(poi: dict[str, Any]) -> list[str]:
    titles: list[str] = []
    for item in poi.get("poiType") or []:
        title = (item or {}).get("title")
        if title and title not in titles:
            titles.append(title)
    return titles


def shelter_text(poi: dict[str, Any]) -> str:
    parts = [poi.get("title") or "", poi.get("intro") or "", poi.get("slug") or ""]
    return "\n".join(parts)


def rasteplass_has_built_shelter(poi: dict[str, Any], titles: set[str]) -> tuple[bool, str]:
    if titles & CORE_SHELTER_CATEGORIES:
        return True, "also_tagged_core_shelter_type"
    if "Overnatting" in titles and "Hotell" not in titles:
        return True, "rasteplass_and_overnatting"
    if RASTEPLASS_SHELTER_RE.search(shelter_text(poi)):
        return True, "description_or_title_mentions_shelter"
    return False, ""


def is_included(poi: dict[str, Any]) -> tuple[bool, str]:
    titles = set(category_titles(poi))
    if titles & CORE_SHELTER_CATEGORIES:
        return True, "core_shelter_category"
    if RASTEPLASS in titles:
        ok, reason = rasteplass_has_built_shelter(poi, titles)
        if ok:
            return True, f"rasteplass:{reason}"
        return False, "rasteplass_without_built_shelter_evidence"
    return False, "no_shelter_category"


def primary_category(titles: list[str]) -> str:
    rank = {name: index for index, name in enumerate(CATEGORY_PRIORITY)}
    matching = [title for title in titles if title in rank]
    if not matching:
        return titles[0] if titles else ""
    return min(matching, key=lambda title: rank[title])


def osm_tags_for_category(category: str) -> tuple[list[tuple[str, str]], bool]:
    """Return OSM tags and whether the mapping is uncertain."""
    if category == "Gapahuk":
        return [("amenity", "shelter"), ("shelter_type", "lean_to")], False
    if category == "Rom og hytter":
        return [("tourism", "chalet")], False
    if category == "Vandrerhjem":
        return [("tourism", "hostel")], False
    if category == "Campingplass":
        return [("tourism", "camp_site")], False
    if category == "Teltplass":
        return [("tourism", "camp_site"), ("tents", "yes")], False
    if category == "Pilegrimsherberge":
        return [("tourism", "hostel"), ("hostel:type", "pilgrim")], True
    if category == "Rasteplass":
        return [("amenity", "shelter"), ("shelter_type", "lean_to")], True
    if category == "Dagsturhytte":
        return [("tourism", "wilderness_hut")], True
    if category == "Pilegrimsbu":
        return [("tourism", "wilderness_hut")], True
    if category == "Rorbu":
        return [("tourism", "chalet")], True
    if category == "Glamping":
        return [("tourism", "camp_site"), ("tents", "yes")], True
    return [], True


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def compact_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def coords(poi: dict[str, Any]) -> tuple[float, float] | None:
    location = poi.get("location") or {}
    lat = location.get("lat")
    lon = location.get("lng")
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
        return None
    if lat_f == 0 and lon_f == 0:
        return None
    return lat_f, lon_f


def build_records(
    raw_pois: list[dict[str, Any]], trail_membership: dict[str, list[str]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for poi in raw_pois:
        titles = category_titles(poi)
        ok, reason = is_included(poi)
        point = coords(poi)
        record = {
            "id": str(poi.get("id")),
            "title": compact_text(poi.get("title")),
            "slug": poi.get("slug") or "",
            "url": poi.get("url") or "",
            "intro": compact_text(poi.get("intro")),
            "categories": titles,
            "poi_type": poi.get("poiType") or [],
            "lat": point[0] if point else None,
            "lon": point[1] if point else None,
            "trails": trail_membership.get(str(poi.get("id")), []),
            "include_reason": reason,
        }
        if not ok:
            excluded.append(record)
            continue
        if point is None:
            record["include_reason"] = "missing_coordinates"
            excluded.append(record)
            continue
        included.append(record)
    included.sort(key=lambda item: (item["title"].lower(), item["id"]))
    return included, excluded


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for record in records:
        shelter_cats = [
            title
            for title in record["categories"]
            if title in CORE_SHELTER_CATEGORIES or title == RASTEPLASS
        ]
        category = " | ".join(shelter_cats) or primary_category(record["categories"])
        trails = record["trails"] or [""]
        for trail in trails:
            rows.append(
                {
                    "trail": trail,
                    "poi_name": record["title"],
                    "category": category,
                    "lat": f"{record['lat']:.7f}",
                    "lon": f"{record['lon']:.7f}",
                    "url": record["url"],
                }
            )
    rows.sort(key=lambda row: (row["trail"] or "~", row["poi_name"].lower(), row["url"]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["trail", "poi_name", "category", "lat", "lon", "url"]
        )
        writer.writeheader()
        writer.writerows(rows)


def write_osm(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    node_ids: list[int] = []
    trail_names: list[str] = []
    for index, record in enumerate(records, start=1):
        node_id = -index
        node_ids.append(node_id)
        lat = f"{record['lat']:.7f}"
        lon = f"{record['lon']:.7f}"
        lines.append(
            f"  <node id='{node_id}' version='0' action='modify' visible='true' "
            f"lat='{lat}' lon='{lon}'>"
        )
        primary = primary_category(record["categories"])
        mapping, uncertain = osm_tags_for_category(primary)
        tags: list[tuple[str, str]] = [
            ("name", record["title"]),
            ("source", "pilegrimsleden.no"),
            ("url", record["url"]),
            ("network", "Pilegrimsleden"),
        ]
        if record["trails"]:
            trail_note = "; ".join(record["trails"])
            tags.append(("note:trail", trail_note))
            trail_names.extend(record["trails"])
        else:
            tags.append(("note:trail", "unassigned"))
        tags.append(
            (
                "pilegrimsleden:poi_type",
                ";".join(
                    title
                    for title in record["categories"]
                    if title in CORE_SHELTER_CATEGORIES or title == RASTEPLASS
                )
                or primary,
            )
        )
        tags.append(("pilegrimsleden:id", record["id"]))
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
    if node_ids:
        # Local JOSM research relation grouping this file's overnight POIs.
        from collections import Counter

        rel_id = min(node_ids) - 1
        dominant = ""
        if trail_names:
            dominant = Counter(trail_names).most_common(1)[0][0]
        lines.append(
            f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>"
        )
        for node_id in node_ids:
            lines.append(f"    <member type='node' ref='{node_id}' role='shelter'/>")
        rel_tags = [
            ("type", "site"),
            ("name", f"{dominant or 'Pilegrimsleden'} overnight POIs"),
            ("network", "Pilegrimsleden"),
            (
                "note",
                "Local JOSM research relation grouping overnight POIs for this trail; "
                "not an OSM import",
            ),
        ]
        if dominant:
            rel_tags.append(("note:trail", dominant))
        for key, value in rel_tags:
            lines.append(f"    <tag k='{xml_escape(key)}' v='{xml_escape(value)}'/>")
        lines.append("  </relation>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_osm(path: Path, expected_count: int) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "osm":
        raise RuntimeError("OSM root element is not <osm>")
    if root.attrib.get("version") != "0.6":
        raise RuntimeError("OSM version attribute is not 0.6")
    nodes = list(root.findall("node"))
    if len(nodes) != expected_count:
        raise RuntimeError(f"OSM node count {len(nodes)} != {expected_count}")
    ids: set[str] = set()
    for node in nodes:
        node_id = node.attrib.get("id", "")
        if not node_id.startswith("-"):
            raise RuntimeError(f"Node id is not negative: {node_id}")
        if node_id in ids:
            raise RuntimeError(f"Duplicate node id {node_id}")
        ids.add(node_id)
        lat = float(node.attrib["lat"])
        lon = float(node.attrib["lon"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise RuntimeError(f"Out-of-range coordinates on {node_id}")
        keys = [tag.attrib["k"] for tag in node.findall("tag")]
        if "name" not in keys or "source" not in keys:
            raise RuntimeError(f"Missing required tags on {node_id}")
        for tag in node.findall("tag"):
            if "k" not in tag.attrib or "v" not in tag.attrib:
                raise RuntimeError(f"Tag missing k/v on {node_id}")
    ET.fromstring(path.read_text(encoding="utf-8"))


def validate_with_josm(path: Path) -> None:
    josm = shutil.which("josm")
    if not josm:
        log("josm not on PATH; skipped JOSM validator (XML well-formedness already checked)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "validate.geojson"
        command = [josm, "validate", "--input", str(path), "--output", str(output)]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        combined = (result.stdout or "") + (result.stderr or "")
        opened = "Open file:" in combined or "fullført" in combined or "completed" in combined
        if result.returncode != 0 and not opened:
            raise RuntimeError(f"JOSM validate failed:\n{combined[-2000:]}")
        log("JOSM opened and validated the OSM file (exit %s)" % result.returncode)


def summary_table(records: list[dict[str, Any]]) -> str:
    trail_names = [trail["title"] for trail in TRAILS] + ["unassigned"]
    categories = CATEGORY_PRIORITY[:]
    counts: dict[str, Counter[str]] = {name: Counter() for name in trail_names}
    unique: Counter[str] = Counter()

    for record in records:
        shelter_cats = [
            title
            for title in record["categories"]
            if title in CORE_SHELTER_CATEGORIES or title == RASTEPLASS
        ]
        trails = record["trails"] or ["unassigned"]
        for trail in trails:
            unique[trail] += 1
            for category in shelter_cats:
                counts[trail][category] += 1

    header = ["trail", "total"] + categories
    col_w = {name: len(name) for name in header}
    rows: list[list[str]] = []
    for trail in trail_names:
        row = [trail, str(unique[trail])]
        for category in categories:
            row.append(str(counts[trail][category]))
        rows.append(row)
        for index, cell in enumerate(row):
            col_w[header[index]] = max(col_w[header[index]], len(cell))

    def fmt(row: list[str]) -> str:
        return "  ".join(cell.ljust(col_w[header[index]]) for index, cell in enumerate(row))

    lines = [fmt(header), fmt(["-" * col_w[name] for name in header])]
    lines.extend(fmt(row) for row in rows)
    lines.append("")
    lines.append(f"Unique shelter/cabin POIs: {len(records)}")
    lines.append(
        "Counts are unique POIs per trail; a POI with several types is counted in each type column."
    )
    lines.append("Zeros mark trails with no entries of that category.")
    return "\n".join(lines)


def exclusion_summary(excluded: list[dict[str, Any]]) -> str:
    counts = Counter(item["include_reason"] for item in excluded)
    lines = ["Excluded from OSM/CSV (kept in raw JSON):"]
    for reason, count in counts.most_common():
        lines.append(f"  {count:4d}  {reason}")
    missing = [item for item in excluded if item["include_reason"] == "missing_coordinates"]
    for item in missing:
        lines.append(f"    no coords: {item['title']} ({item['url']})")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
        help="Output directory (default: ./data)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY_SEC,
        help="Delay in seconds between HTTP requests",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global REQUEST_DELAY_SEC
    REQUEST_DELAY_SEC = args.delay

    started = datetime.now(timezone.utc)
    log("Checking GraphQL endpoint")
    probe = http_json(GRAPHQL_URL)
    if not probe or "errors" not in probe:
        log(f"Unexpected GraphQL probe response: {probe}")

    raw_pois = paginate_pois()
    log(f"Fetched {len(raw_pois)} POIs matching shelter-related poiType ids")

    trail_membership: dict[str, list[str]] = defaultdict(list)
    for trail in TRAILS:
        time.sleep(REQUEST_DELAY_SEC)
        log(f"Fetching trail relations for {trail['title']} (id={trail['id']})")
        poi_ids = paginate_trail_ids(int(trail["id"]))
        log(f"  {len(poi_ids)} related shelter-type POIs")
        for poi_id in sorted(poi_ids, key=lambda value: int(value)):
            trail_membership[poi_id].append(trail["title"])

    included, excluded = build_records(raw_pois, dict(trail_membership))
    log(f"Included {len(included)}; excluded {len(excluded)}")

    data_dir: Path = args.data_dir
    raw_path = data_dir / "pilegrimsleden_shelters_raw.json"
    csv_path = data_dir / "pilegrimsleden_shelters_by_trail.csv"
    osm_path = data_dir / "pilegrimsleden_shelters.osm"

    payload = {
        "source": {
            "site": f"{BASE_URL}/kart",
            "graphql": GRAPHQL_URL,
            "maplist": MAPLIST_URL,
            "trailpoints": TRAILPOINTS_URL,
            "user_agent": USER_AGENT,
            "extracted_at": started.isoformat(),
            "poi_entry_trail_field": "trail",
            "trail_relation_note": (
                "poi_Entry.trail is the Craft relation field handle, but the public "
                "GraphQL schema returns empty lists. Trail membership is resolved with "
                "relatedTo: [trailEntryId] (same relation the map uses via trailpoints)."
            ),
            "include_categories": sorted(CORE_SHELTER_CATEGORIES | {RASTEPLASS}),
            "rasteplass_rule": (
                "Rasteplass is included only when also tagged with a core shelter type, "
                "tagged Overnatting (and not Hotell-only), or the title/intro matches "
                "built-shelter keywords (gapahuk, leskur, rastebu, ...)."
            ),
        },
        "trails": TRAILS,
        "pois": included,
        "excluded": excluded,
    }
    write_json(raw_path, payload)
    write_csv(csv_path, included)
    write_osm(osm_path, included)
    validate_osm(osm_path, len(included))
    validate_with_josm(osm_path)

    table = summary_table(included)
    print(table)
    print()
    print(exclusion_summary(excluded))
    log(f"Wrote {raw_path}")
    log(f"Wrote {csv_path}")
    log(f"Wrote {osm_path} ({len(included)} nodes, OSM XML parsed OK)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
