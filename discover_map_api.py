#!/usr/bin/env python3
"""Capture XHR/fetch traffic from the Pilegrimsleden map (Playwright).

Loads https://www.pilegrimsleden.no/kart, records network requests, toggles the
Gapahuk filter, and writes request URL/method/payload plus a response sample.

The extractor uses the GraphQL API discovered here and does not need Playwright
on subsequent runs.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse


MAP_URL = "https://www.pilegrimsleden.no/kart"
USER_AGENT = (
    "pilegrimsleden-osm-extractor/1.0 "
    "(OSM mapping research; shelter/cabin POIs along Pilegrimsleden; "
    "+https://www.openstreetmap.org/)"
)


def interesting(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(
        token in path
        for token in ("/actions/", "graphql", "poi", "interesse", "maplist", "trail")
    ) or parsed.netloc.endswith("pilegrimsleden.no") and path.endswith((".json", "/api"))


def summarize_body(body: str | None, limit: int = 1500) -> str | None:
    if body is None:
        return None
    text = body if len(body) <= limit else body[:limit] + "...[truncated]"
    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "map_api_discovery.json",
        help="Where to write the captured request log",
    )
    parser.add_argument("--headed", action="store_true", help="Show the browser window")
    return parser.parse_args()


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright is not installed. Install with:\n"
            "  pip install playwright && playwright install chromium\n"
            "The extractor can run without this step; GraphQL is already identified.",
            file=sys.stderr,
        )
        return 1

    args = parse_args()
    captured: list[dict] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        context = browser.new_context(user_agent=USER_AGENT, locale="nb-NO")
        page = context.new_page()

        def on_request(request) -> None:
            url = request.url
            if "pilegrimsleden.no" not in url and "graphql" not in url:
                return
            if request.resource_type not in {"xhr", "fetch"} and not interesting(url):
                if request.resource_type not in {"xhr", "fetch"}:
                    return
            captured.append(
                {
                    "phase": "request",
                    "url": url,
                    "method": request.method,
                    "resource_type": request.resource_type,
                    "post_data": summarize_body(request.post_data),
                    "headers": {
                        key: value
                        for key, value in request.headers.items()
                        if key.lower() in {"content-type", "accept", "x-requested-with"}
                    },
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )

        def on_response(response) -> None:
            url = response.url
            request = response.request
            if request.resource_type not in {"xhr", "fetch"} and not interesting(url):
                return
            if "pilegrimsleden.no" not in url and "graphql" not in url:
                return
            sample = None
            try:
                sample = summarize_body(response.text())
            except Exception:
                sample = None
            captured.append(
                {
                    "phase": "response",
                    "url": url,
                    "method": request.method,
                    "status": response.status,
                    "content_type": response.headers.get("content-type"),
                    "sample": sample,
                    "query": parse_qs(urlparse(url).query),
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )

        page.on("request", on_request)
        page.on("response", on_response)
        page.goto(MAP_URL, wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)

        filter_button = page.get_by_role("button", name="Vis filter")
        if filter_button.count():
            filter_button.first.click()
            page.wait_for_timeout(500)

        gapahuk = page.locator("label", has_text="Gapahuk")
        if gapahuk.count():
            gapahuk.first.click()
            page.wait_for_timeout(4000)
        else:
            checkbox = page.locator("#10")
            if checkbox.count():
                checkbox.first.check()
                page.wait_for_timeout(4000)

        browser.close()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "map_url": MAP_URL,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "events": captured,
        "xhr_or_fetch_urls": sorted(
            {
                item["url"]
                for item in captured
                if item.get("resource_type") in {"xhr", "fetch"} or item.get("phase") == "response"
            }
        ),
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} ({len(captured)} events)")
    for url in payload["xhr_or_fetch_urls"]:
        print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
