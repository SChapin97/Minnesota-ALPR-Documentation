#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# --------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------
TARGET_URL = "https://dps.mn.gov/divisions/bca/data-and-reports/agencies-use-lprs-lpr"
OUTPUT_JSON = Path("lpr_agencies.json")   # Change or set to None to skip saving


# --------------------------------------------------------------
# PLAYWRIGHT – fetch the fully‑rendered HTML
# --------------------------------------------------------------
async def fetch_rendered_html(url: str) -> str:
    """
    Open a headless Chromium instance, navigate to `url`,
    wait for network idle (all XHR/fetch calls settled),
    then return the complete page source (including the generated
    __NEXT_DATA__ script).
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        # `wait_until="networkidle"` waits until there are no network
        # connections for at least 500 ms – enough for the JSON to be injected.
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        content = await page.content()
        await browser.close()
        return content


# --------------------------------------------------------------
# JSON extraction helpers
# --------------------------------------------------------------
def get_next_data_json(html: str) -> dict:
    """
    Find the <script id="__NEXT_DATA__"> tag and decode its JSON.
    The search is tolerant – it looks for any <script> whose id contains
    the substring “NEXT_DATA”.
    """
    soup = BeautifulSoup(html, "html.parser")
    script_tag = None
    for tag in soup.find_all("script"):
        sid = tag.get("id", "")
        if "NEXT_DATA" in sid:          # matches "__NEXT_DATA__", "NEXT_DATA", etc.
            script_tag = tag
            break

    if not script_tag:
        sys.exit("ERROR: Could not locate the __NEXT_DATA__ script block.")

    json_text = script_tag.get_text(strip=True)
    if not json_text:
        sys.exit("ERROR: __NEXT_DATA__ script exists but contains no JSON.")

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: Failed to parse JSON from __NEXT_DATA__: {exc}")


def extract_accordion_items(data: dict) -> List[dict]:
    """
    Walk the JSON hierarchy to the list of accordion entries.
    Current path (as of the live page):
    props.pageProps.nodeResource.content[] → ParagraphAccordions → textItems[]
    """
    try:
        content_blocks = data["props"]["pageProps"]["nodeResource"]["content"]
    except KeyError as exc:
        sys.exit(f"ERROR: Unexpected JSON layout – missing key {exc}")

    items = []
    for block in content_blocks:
        if block.get("__typename") == "ParagraphAccordions":
            items.extend(block.get("textItems", []))
    return items


def parse_locations_from_fragment(fragment_html: str) -> List[str]:
    """
    Each accordion’s body is stored as escaped HTML (field `body.processed`).
    It contains a <ul> with <li> entries for each LPR location.
    """
    soup = BeautifulSoup(fragment_html, "html.parser")
    ul = soup.find("ul")
    if not ul:
        return []                     # Agencies that report “N/A” have no list.
    locations = []
    for li in ul.find_all("li"):
        txt = li.get_text(" ", strip=True)   # Normalise whitespace.
        if txt:
            locations.append(txt)
    return locations


def build_agency_mapping(items: List[dict]) -> Dict[str, dict]:
    """
    Convert raw accordion items into the final mapping:

        {
            "Agency Name": {"locations": ["addr 1", "addr 2", …]},
            …
        }
    """
    result = {}
    for itm in items:
        agency_name = itm.get("title", "").strip()
        body_html = itm.get("body", {}).get("processed", "")
        if not agency_name:
            continue
        locations = parse_locations_from_fragment(body_html)
        result[agency_name] = {"locations": locations}
    return result


# --------------------------------------------------------------
# MAIN ASYNC ENTRY POINT
# --------------------------------------------------------------
async def main_async() -> None:
#    print("Fetching the live page…")
    rendered_html = await fetch_rendered_html(TARGET_URL)

#    print("Extracting the __NEXT_DATA__ JSON payload…")
    next_data = get_next_data_json(rendered_html)

#    print(" Pulling accordion items (one per agency)…")
    accordion_items = extract_accordion_items(next_data)

    if not accordion_items:
        sys.exit("ERROR: No accordion data found – the page structure may have changed.")

#    print("Building the agency -> locations dictionary…")
    agencies = build_agency_mapping(accordion_items)

    pretty = json.dumps(agencies, indent=2, ensure_ascii=False)
#    print("\n=== LPR AGENCIES ===")
#    print(pretty)

    if OUTPUT_JSON:
        try:
            OUTPUT_JSON.write_text(pretty, encoding="utf-8")
#            print(f"\nResults also saved to {OUTPUT_JSON}")
        except Exception as exc:
            print(f"\nWARNING: Could not write JSON file: {exc}")


# --------------------------------------------------------------
# Run the async main
# --------------------------------------------------------------
if __name__ == "__main__":
    import asyncio

    asyncio.run(main_async())
