#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


BASE_URL = "https://raw.githubusercontent.com/iptv-org/iptv/master/streams"

SOURCES = {
    "az": f"{BASE_URL}/az.m3u",
    "tr": f"{BASE_URL}/tr.m3u",
    "ru": f"{BASE_URL}/ru.m3u",
}

GROUP_NAMES = {
    "az": "Azeri",
    "tr": "Turk",
    "ru": "Rus",
}

CONFIG_FILE = Path("channels.json")
OUTPUT_FILE = Path("regional.m3u")


def download_text(url: str) -> str:
    """Download text from URL."""
    print(f"Downloading: {url}")

    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    try:
        with urlopen(request, timeout=30) as response:
            data = response.read()

        return data.decode("utf-8-sig")

    except HTTPError as e:
        raise RuntimeError(f"HTTP error {e.code}: {url}") from e

    except URLError as e:
        raise RuntimeError(f"Connection error: {url}\n{e}") from e


def parse_m3u(text: str):
    """
    Parse M3U into records.

    Each record:
    {
        "country": "...",
        "extinf": "...",
        "url": "..."
    }
    """

    lines = [line.strip() for line in text.splitlines()]

    records = []

    current_extinf = None

    for line in lines:

        if not line:
            continue

        if line.startswith("#EXTINF:"):
            current_extinf = line

        elif current_extinf and not line.startswith("#"):
            records.append({
                "extinf": current_extinf,
                "url": line,
            })

            current_extinf = None

    return records


def get_tvg_id(extinf: str):
    """Extract tvg-id from EXTINF line."""

    marker = 'tvg-id="'

    start = extinf.find(marker)

    if start == -1:
        return None

    start += len(marker)

    end = extinf.find('"', start)

    if end == -1:
        return None

    return extinf[start:end]


def load_config():
    """Load channels.json."""

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {CONFIG_FILE}"
        )

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            config = json.load(f)

    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Invalid JSON in {CONFIG_FILE}: {e}"
        ) from e

    return config


def main():

    print("===================================")
    print(" IPTV Regional Playlist Generator")
    print("===================================")
    print()

    config = load_config()

    all_records = []

    # Download sources in fixed order:
    # AZ -> TR -> RU
    for country, url in SOURCES.items():

        selected_ids = config.get(country, [])

        if not selected_ids:
            print(f"{country.upper()}: no channels selected")
            continue

        print(f"\n[{country.upper()}]")

        text = download_text(url)

        records = parse_m3u(text)

        print(f"Downloaded streams: {len(records)}")

        selected_set = set(selected_ids)

        found_ids = set()

        count = 0

        for record in records:

            tvg_id = get_tvg_id(record["extinf"])

            if tvg_id in selected_set:

                all_records.append({
                    "country": country,
                    "tvg_id": tvg_id,
                    "extinf": record["extinf"],
                    "url": record["url"],
                })

                found_ids.add(tvg_id)
                count += 1

        print(f"Selected streams: {count}")

        # Show missing tvg-id
        missing = selected_set - found_ids

        if missing:
            print("NOT FOUND:")

            for tvg_id in sorted(missing):
                print(f"  - {tvg_id}")

    # -----------------------------------------
    # Create playlist
    # -----------------------------------------

    output = []

    output.append("#EXTM3U")

    output.append(
        "# Generated automatically by build_playlist.py"
    )

    output.append(
        "# Source: https://github.com/iptv-org/iptv"
    )

    output.append("")

    current_country = None

    for record in all_records:

        country = record["country"]

        if country != current_country:

            current_country = country

            country_names = {
                "az": "AZERBAIJAN",
                "tr": "TURKEY",
                "ru": "RUSSIA",
            }

            output.append(
                f"# ===== {country_names[country]} ====="
            )

        extinf = record["extinf"]

        group = GROUP_NAMES[record["country"]]

        if 'group-title="' in extinf:
            import re

            extinf = re.sub(
                r'group-title="[^"]*"',
                f'group-title="{group}"',
                extinf,
                count=1
            )
        else:
            extinf = extinf.replace(
                '#EXTINF:-1',
                f'#EXTINF:-1 group-title="{group}"',
                1
            )

        output.append(extinf)
        output.append(record["url"])

    output.append("")

    OUTPUT_FILE.write_text(
        "\n".join(output),
        encoding="utf-8"
    )

    print()
    print("===================================")
    print(f"Created: {OUTPUT_FILE}")
    print(f"Streams: {len(all_records)}")
    print("===================================")


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)