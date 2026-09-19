#!/usr/bin/env python3
"""Extract missing Swedish pilgrim trails into data/by_trail/Sweden/.

Preference order for path geometry:
  1. OSM hiking/foot route or superroute (member ways from sweden-latest.osm.pbf)
  2. OSRM foot routing between catalog from/to endpoints

Already extracted (skipped): St-Olavsleden, Pilgrimsleden Västra Värmland.
Romboleden lives under Norway/Romboleden.
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

import osmium

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from propose_relation_additions import (  # noqa: E402
    densify_for_index,
    expand_membership,
    haversine_m,
    stitch_points,
)
from build_josm_review import xml_escape, write_gpx  # noqa: E402

USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(Sweden pilgrim trail extracts; "
    "+https://github.com/Supermagnum/Scandi-pilgrim-poi)"
)
PBF = ROOT / "data/geofabrik/sweden-latest.osm.pbf"
CATALOG = ROOT / "data/sweden/trails_catalog.json"
BY_TRAIL = ROOT / "data/by_trail/Sweden"

SKIP_NAMES = {
    "Pilgrimsleden Västra Värmland",
    "S:t Olavsleden",
    "Romboleden",
}

# Catalog trail name -> primary OSM relation id(s) (route or superroute).
OSM_RELATIONS: dict[str, list[int]] = {
    "Dag Hammarskjöldsleden": [8344292],
    "Franciskusleden": [12203269],
    "Fryksdalsleden": [10712798],
    "Hedemora Pilgrimsled": [7320525],
    "Ingegerdsleden": [8436154],
    "Jämt-Norgevägen": [9686095],
    "Katarinaleden": [20517282],
    "Kårböleleden": [7392417],
    "Marialeden": [11053382],
    "Munkaleden / Munkagårdsleden": [10641722],
    "Munkastigen": [3876331],
    "Nydalaleden": [12562477],
    "Pilgrimsleden Dalsland": [6796203],
    "Pilgrimsleden Falköping - Varnhem": [7329382],
    "Pilgrimsleden Skara - Husaby": [6425786],
    "Pilgrimsled Hjo - Kungslena": [8393555],
    "Pilgrimsleden Orust": [6497110],
    "Pilgrimsleden Göta Älv": [8235330],
    "Sigfridsleden": [11075053],
    "Västra Sigfridsleden": [11108991],
    "Östra Sigfridsleden": [11061726],
    "S:t Birgitta Ways Vårdnäs - Vadstena": [9514230],
    "Stråsjöleden": [12702331],
}

# Override catalog from/to when missing, misspelled, or incomplete.
ENDPOINT_OVERRIDES: dict[str, tuple[str, str]] = {
    "Den heliga vägen": ("Pjätteryd", "Åhus"),
    "Nutida pilgrimer": ("Grinneröd, Ljungskile", "Hjärtum"),
    "Pilgrim Halland": ("Örkelljunga", "Kållered"),
    "Pilgrimsleder i Tyresö": ("Tyresö kyrka", "Ällmora, Tyresö"),
    "Pilgrimsvägen Skåne Blekinge": ("Ystad", "Karlskrona"),
    "Sankta Annaleden": ("Frötuna kyrka, Norrtälje", "Östanbäcks kloster"),
    "S:t Olofsleden, Gotland": ("Sankt Olofsholm, Gotland", "Visby"),
    "Sankta Thoras pilgrimsled": ("Ausås", "Torekov"),
    "Pilgrimsleden Orust": ("Ellös, Orust", "Henån, Orust"),
    "Vikingaleden": ("Grisslehamn", "Älvkarleby"),
}

# Multi-stop OSRM for winding trails where endpoint routing is far too short.
WAYPOINT_ROUTES: dict[str, list[str]] = {
    "Sankta Thoras pilgrimsled": [
        "Ausås kyrka",
        "Starby kyrka, Ängelholm",
        "Össjö kyrka",
        "Tåstarps kyrka",
        "Rebbelberga kyrka, Ängelholm",
        "Vejbystrand",
        "Grevie kyrka, Båstad",
        "Mariakyrkan Båstad",
        "Hovs kyrka",
        "Torekovs kyrka",
    ],
    "Nutida pilgrimer": [
        "Resteröds kyrka",
        "Ljungskile",
        "Grinneröd, Uddevalla",
        "Hjärtum",
    ],
}


def log(msg: str) -> None:
    print(msg, flush=True)


def slugify(name: str) -> str:
    s = name.strip()
    s = s.replace("Å", "A").replace("Ä", "A").replace("Ö", "O")
    s = s.replace("å", "a").replace("ä", "a").replace("ö", "o")
    s = s.replace("é", "e").replace("ü", "u")
    s = re.sub(r"[^A-Za-z0-9]+", "-", s)
    return s.strip("-")


def http_get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def nominatim(query: str) -> tuple[float, float] | None:
    params = urllib.parse.urlencode(
        {"q": query + ", Sweden", "format": "jsonv2", "limit": 1, "countrycodes": "se"}
    )
    hits = json.loads(
        http_get("https://nominatim.openstreetmap.org/search?" + params).decode()
    )
    if not hits:
        return None
    return float(hits[0]["lat"]), float(hits[0]["lon"])


def path_km(pts: list[tuple[float, float]]) -> float:
    return sum(haversine_m(a, b, c, d) / 1000 for (a, b), (c, d) in zip(pts, pts[1:]))


def load_ways_from_pbf(way_ids: set[int]) -> dict[int, list[tuple[float, float]]]:
    if not way_ids or not PBF.exists():
        return {}

    class H(osmium.SimpleHandler):
        def __init__(self) -> None:
            super().__init__()
            self.ways: dict[int, list[tuple[float, float]]] = {}

        def way(self, w: osmium.Way) -> None:
            if w.id not in way_ids:
                return
            try:
                coords = [(n.lat, n.lon) for n in w.nodes]
            except osmium.InvalidLocationError:
                return
            if len(coords) >= 2:
                self.ways[w.id] = coords

    h = H()
    h.apply_file(str(PBF), locations=True)
    return h.ways


def collect_way_refs(relation_ids: list[int]) -> list[int]:
    way_ids: set[int] = set()
    ordered_refs: list[int] = []
    for rid in relation_ids:
        log(f"  expand relation/{rid}")
        _tags, members, visited = expand_membership(rid, max_depth=3)
        log(f"    visited relations: {visited}")
        for kind, mid in members:
            if kind == "way":
                if mid not in way_ids:
                    ordered_refs.append(mid)
                way_ids.add(mid)
        time.sleep(0.25)
    return ordered_refs


def greedy_stitch(
    segments: list[list[tuple[float, float]]], max_gap_m: float = 2000.0
) -> list[tuple[float, float]]:
    """Connect unordered relation members by nearest free endpoint.

    OSM hiking relations often list members out of geographic order; naive
    concatenation then densifies huge fake jumps. Keep the longest chain.
    """
    segs = [list(s) for s in segments if len(s) >= 2]
    if not segs:
        return []
    segs.sort(key=path_km, reverse=True)
    used = [False] * len(segs)
    chains: list[list[tuple[float, float]]] = []
    while not all(used):
        i = next(idx for idx, u in enumerate(used) if not u)
        used[i] = True
        chain = list(segs[i])
        while True:
            best: tuple[float, int, bool, bool] | None = None
            end, start = chain[-1], chain[0]
            for j, taken in enumerate(used):
                if taken:
                    continue
                s = segs[j]
                for dist, rev, to_end in (
                    (haversine_m(end[0], end[1], s[0][0], s[0][1]), False, True),
                    (haversine_m(end[0], end[1], s[-1][0], s[-1][1]), True, True),
                    (haversine_m(start[0], start[1], s[-1][0], s[-1][1]), False, False),
                    (haversine_m(start[0], start[1], s[0][0], s[0][1]), True, False),
                ):
                    if dist <= max_gap_m and (best is None or dist < best[0]):
                        best = (dist, j, rev, to_end)
            if best is None:
                break
            _dist, j, rev, to_end = best
            used[j] = True
            s = list(reversed(segs[j])) if rev else list(segs[j])
            if to_end:
                chain.extend(s[1:] if chain[-1] == s[0] else s)
            else:
                chain = (s[:-1] if s[-1] == chain[0] else s) + chain
        chains.append(chain)
    chains.sort(key=path_km, reverse=True)
    return chains[0] if chains else []


def geometry_from_way_refs(
    ordered_refs: list[int], ways: dict[int, list[tuple[float, float]]]
) -> list[tuple[float, float]]:
    segments: list[list[tuple[float, float]]] = []
    for wid in ordered_refs:
        pts = ways.get(wid)
        if pts:
            segments.append(pts)
    track = greedy_stitch(segments)
    if len(track) < 2:
        # Fall back to order-preserving stitch if greedy found nothing useful
        track = stitch_points(segments)
    if len(track) < 2:
        return []
    return densify_for_index(track, step_m=100.0)


def catalog_km_number(km: object) -> float | None:
    if isinstance(km, (int, float)):
        return float(km)
    if isinstance(km, str):
        m = re.match(r"(\d+(?:\.\d+)?)", km.strip())
        if m:
            return float(m.group(1))
    return None


def endpoints_for(entry: dict) -> tuple[str | None, str | None]:
    name = entry["name"]
    if name in ENDPOINT_OVERRIDES:
        return ENDPOINT_OVERRIDES[name]
    return entry.get("from"), entry.get("to")


def osrm_between(a: tuple[float, float], b: tuple[float, float]) -> list[tuple[float, float]]:
    coord = f"{a[1]},{a[0]};{b[1]},{b[0]}"
    url = (
        "https://router.project-osrm.org/route/v1/foot/"
        f"{coord}?overview=full&geometries=geojson"
    )
    for attempt in range(4):
        try:
            data = json.loads(http_get(url, timeout=90))
            route = (data.get("routes") or [None])[0]
            if not route:
                break
            return [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
        except Exception as exc:
            log(f"    OSRM retry {attempt+1}: {exc}")
            time.sleep(1.5 * (attempt + 1))
    return densify_for_index([a, b], step_m=100.0)


def osrm_waypoints(labels: list[str]) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    for lab in labels:
        log(f"  geocode via={lab!r}")
        pt = nominatim(lab)
        time.sleep(1.1)
        if not pt:
            log(f"    miss {lab!r}")
            continue
        coords.append(pt)
    if len(coords) < 2:
        return []
    track: list[tuple[float, float]] = []
    for a, b in zip(coords, coords[1:]):
        seg = osrm_between(a, b)
        if track and seg and track[-1] == seg[0]:
            track.extend(seg[1:])
        else:
            track.extend(seg)
        time.sleep(0.3)
    return densify_for_index(track, step_m=100.0) if track else []


def osrm_endpoints(frm: str | None, to: str | None) -> list[tuple[float, float]]:
    if not frm or not to:
        return []
    log(f"  geocode from={frm!r}")
    a = nominatim(frm)
    time.sleep(1.1)
    log(f"  geocode to={to!r}")
    b = nominatim(to)
    time.sleep(1.1)
    if not a or not b:
        return []
    log("  OSRM foot…")
    return densify_for_index(osrm_between(a, b), step_m=100.0)


def write_trail_osm(
    path: Path,
    trail_name: str,
    source_url: str | None,
    points: list[tuple[float, float]],
    path_source: str,
    pois: list[dict[str, str | float]] | None = None,
) -> None:
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        "<osm version='0.6' generator='pilegrimsleden-osm-extractor 1.0'>",
    ]
    next_id = -1
    members: list[tuple[str, int, str]] = []
    if len(points) >= 2:
        node_ids: list[int] = []
        for lat, lon in points:
            lines.append(
                f"  <node id='{next_id}' version='0' action='modify' visible='true' "
                f"lat='{lat:.7f}' lon='{lon:.7f}'/>"
            )
            node_ids.append(next_id)
            next_id -= 1
        way_id = next_id
        next_id -= 1
        lines.append(f"  <way id='{way_id}' version='0' action='modify' visible='true'>")
        for nid in node_ids:
            lines.append(f"    <nd ref='{nid}'/>")
        for k, v in (
            ("highway", "path"),
            ("name", trail_name),
            ("network", "Pilgrimsleder Sverige"),
            ("note:trail", trail_name),
            ("note:path_source", path_source),
        ):
            lines.append(f"    <tag k='{xml_escape(k)}' v='{xml_escape(v)}'/>")
        lines.append("  </way>")
        members.append(("way", way_id, "path"))

    for poi in pois or []:
        nid = next_id
        next_id -= 1
        lines.append(
            f"  <node id='{nid}' version='0' action='modify' visible='true' "
            f"lat='{float(poi['lat']):.7f}' lon='{float(poi['lon']):.7f}'>"
        )
        lines.append(f"    <tag k='name' v='{xml_escape(str(poi['name']))}'/>")
        lines.append("    <tag k='tourism' v='yes'/>")
        lines.append("  </node>")
        members.append(("node", nid, "poi"))

    rel_id = next_id
    lines.append(f"  <relation id='{rel_id}' version='0' action='modify' visible='true'>")
    for typ, ref, role in members:
        lines.append(f"    <member type='{typ}' ref='{ref}' role='{role}'/>")
    lines.append(f"    <tag k='type' v='site'/>")
    lines.append(f"    <tag k='name' v='{xml_escape(trail_name)}'/>")
    lines.append("    <tag k='network' v='Pilgrimsleder Sverige'/>")
    lines.append(f"    <tag k='note:trail' v='{xml_escape(trail_name)}'/>")
    if source_url:
        lines.append(f"    <tag k='url' v='{xml_escape(source_url)}'/>")
    lines.append(
        "    <tag k='note' v='Local JOSM research file for Swedish pilgrim trail mapping.'/>"
    )
    lines.append("  </relation>")
    lines.append("</osm>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(
    path: Path,
    trail_name: str,
    folder: str,
    source_url: str | None,
    n_path: int,
    path_source: str,
    osm_rels: list[int],
    km: object,
) -> None:
    lines = [
        f"# {trail_name}",
        "",
        f"Folder: `{folder}`",
        "",
        "## Open in JOSM",
        "",
        "Open `trail.osm` in this folder.",
        "",
        "## Path source",
        "",
        f"- {path_source}",
    ]
    if osm_rels:
        lines.append(
            "- OSM: "
            + ", ".join(f"https://www.openstreetmap.org/relation/{r}" for r in osm_rels)
        )
    if source_url:
        lines.extend(["", f"Official / info: {source_url}"])
    lines.extend(
        [
            "",
            "## Counts",
            "",
            "| item | count |",
            "| --- | ---: |",
            f"| Path points (densified) | {n_path} |",
            f"| Catalog km | {km if km is not None else '—'} |",
            "",
            "## Files",
            "",
            "- `trail.osm`",
            "- `hiking_path.gpx`",
            "- `README.md`",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def thin(points: list[tuple[float, float]], max_points: int = 8000) -> list[tuple[float, float]]:
    if len(points) <= max_points:
        return points
    step = math.ceil(len(points) / max_points)
    out = points[::step]
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def write_one(
    entry: dict,
    points: list[tuple[float, float]],
    path_source: str,
    rels: list[int],
) -> dict:
    name = entry["name"]
    slug = slugify(name)
    trail_dir = BY_TRAIL / slug
    trail_dir.mkdir(parents=True, exist_ok=True)
    if len(points) < 2:
        log(f"  SKIP {name}: no usable path")
        return {
            **entry,
            "folder": f"Sweden/{slug}",
            "status": "failed",
            "path_points": 0,
        }
    points = thin(points, 8000)
    log(f"  path: {len(points)} pts, ~{path_km(points):.1f} km")
    write_gpx(trail_dir / "hiking_path.gpx", points, name)
    write_trail_osm(
        trail_dir / "trail.osm",
        name,
        entry.get("url"),
        points,
        path_source,
    )
    write_readme(
        trail_dir / "README.md",
        name,
        f"Sweden/{slug}",
        entry.get("url"),
        len(points),
        path_source,
        rels,
        entry.get("km"),
    )
    return {
        **entry,
        "folder": f"Sweden/{slug}",
        "status": "extracted",
        "path_source": "osm_relation" if rels and "OSRM" not in path_source else "osrm_or_mixed",
        "path_points": len(points),
        "osm_relations": rels,
    }


def main() -> int:
    if not PBF.exists():
        raise SystemExit(f"Missing {PBF}")
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))

    # Phase 1: expand all OSM memberships, then one PBF load.
    pending: list[tuple[dict, list[int], list[int]]] = []
    all_way_ids: set[int] = set()
    for entry in cat["trails"]:
        name = entry["name"]
        if name in SKIP_NAMES:
            continue
        rels = OSM_RELATIONS.get(name, [])
        if not rels:
            continue
        try:
            refs = collect_way_refs(rels)
        except Exception as exc:
            log(f"expand failed for {name}: {exc}")
            refs = []
        pending.append((entry, rels, refs))
        all_way_ids.update(refs)

    log(f"Loading {len(all_way_ids)} unique ways from PBF once…")
    ways_cache = load_ways_from_pbf(all_way_ids)
    log(f"PBF returned {len(ways_cache)} ways with coords")

    by_name_points: dict[str, tuple[list[tuple[float, float]], str, list[int]]] = {}
    for entry, rels, refs in pending:
        pts = geometry_from_way_refs(refs, ways_cache)
        src = (
            f"OSM relation(s) {', '.join(str(r) for r in rels)} "
            "via Geofabrik Sweden PBF"
        )
        by_name_points[entry["name"]] = (pts, src, rels)
        log(f"  OSM geom {entry['name']}: {len(pts)} pts")

    results = []
    for entry in cat["trails"]:
        name = entry["name"]
        if name in SKIP_NAMES or (entry.get("folder") and name == "Romboleden"):
            if name == "Pilgrimsleden Västra Värmland":
                entry = {
                    **entry,
                    "folder": "Sweden/Pilgrimsleden-Vastra-Varmland",
                    "status": "extracted",
                }
            elif name == "S:t Olavsleden":
                entry = {
                    **entry,
                    "folder": "Sweden/St-Olavsleden",
                    "status": "extracted",
                }
            results.append(entry)
            continue

        log(f"=== {name}")
        pts, src, rels = by_name_points.get(name, ([], "", []))
        cat_km = catalog_km_number(entry.get("km"))
        osm_bad = False
        if pts and cat_km and cat_km > 0:
            ratio = path_km(pts) / cat_km
            if ratio > 2.5 or path_km(pts) < cat_km * 0.55:
                log(
                    f"  OSM path length ~{path_km(pts):.0f} km vs catalog {cat_km} "
                    f"(ratio {ratio:.2f}) — trying OSRM"
                )
                osm_bad = True
        need_osrm = len(pts) < 50 or osm_bad
        if need_osrm:
            if name in WAYPOINT_ROUTES:
                fallback = osrm_waypoints(WAYPOINT_ROUTES[name])
                frm, to = WAYPOINT_ROUTES[name][0], WAYPOINT_ROUTES[name][-1]
            else:
                frm, to = endpoints_for(entry)
                fallback = osrm_endpoints(frm, to)
            use_fallback = False
            if len(fallback) >= 2:
                if osm_bad and cat_km:
                    osm_err = abs(path_km(pts) - cat_km) if pts else 1e9
                    osrm_err = abs(path_km(fallback) - cat_km)
                    use_fallback = osrm_err < osm_err
                else:
                    use_fallback = len(fallback) > len(pts)
            if use_fallback:
                pts = fallback
                src = (
                    "OSRM foot routing between endpoints "
                    f"({frm} -> {to}); "
                    "replace with official GPX when available"
                )
                if rels:
                    src += f" (OSM rel {rels} sparse/unusable or length mismatch)"
        # Persist resolved endpoints on catalog entry
        frm, to = endpoints_for(entry)
        if frm:
            entry = {**entry, "from": frm}
        if to:
            entry = {**entry, "to": to}
        results.append(write_one(entry, pts, src, rels))

    payload = {
        "country": "Sweden",
        "label": "SVERIGE",
        "updated": "2026-09-19",
        "notes": [
            "Inventory of Swedish pilgrim trails for Scandi-pilgrim-poi.",
            "Paths prefer OSM hiking relations (Geofabrik Sweden PBF); else OSRM foot between catalog endpoints.",
        ],
        "trails": results,
    }
    CATALOG.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {CATALOG}")

    ok = sum(1 for r in results if r.get("status") == "extracted" and r.get("path_points", 0) > 0)
    fail = [r["name"] for r in results if r.get("status") == "failed"]
    log(f"Done. extracted_with_path≈{ok} failed={fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
