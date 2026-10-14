#!/usr/bin/env python3
"""
make_epg.py - build a small XMLTV guide containing only the channels
listed (by tvg-id) in your m3u playlist.

The source EPG address is NOT stored in this file. Provide it via the
EPG_URL environment variable (or --epg for a URL / local file).

Windows (PowerShell):
    $env:EPG_URL = "<your link>"
    python make_epg.py

Windows (cmd):
    set EPG_URL=<your link>
    python make_epg.py

Output: epg_small.xml and epg_small.xml.gz (UTF-8)
No third-party packages needed (Python 3.7+).
"""
import argparse
import gzip
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def is_url(s):
    return re.match(r"https?://", s) is not None


def read_m3u_ids(path_or_url):
    """Return the set of tvg-id values found in the playlist."""
    if is_url(path_or_url):
        req = urllib.request.Request(path_or_url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8", errors="replace")
    else:
        with open(path_or_url, encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
    return set(re.findall(r'tvg-id="([^"]+)"', text))


def fetch_to_file(src, dst):
    """Download (or copy) src into dst, streaming. Never prints the address."""
    if is_url(src):
        req = urllib.request.Request(src, headers=UA)
        with urllib.request.urlopen(req, timeout=180) as r, open(dst, "wb") as f:
            shutil.copyfileobj(r, f, length=1024 * 1024)
    else:
        shutil.copyfile(src, dst)


def open_xml(path):
    """Open the file, transparently handling gzip (checked by magic bytes)."""
    with open(path, "rb") as f:
        magic = f.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(path, "rb")
    return open(path, "rb")


def filter_epg(epg_path, ids, out_path):
    ids_lower = {}
    for i in ids:
        ids_lower.setdefault(i.lower(), i)

    found_channels = set()
    seen_epg_ids = set()
    n_prog = 0
    n_prog_total = 0
    case_hints = {}

    with open_xml(epg_path) as src, open(out_path, "w", encoding="utf-8", newline="\n") as out:
        out.write('<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n')
        context = ET.iterparse(src, events=("start", "end"))
        root = None
        for event, elem in context:
            if event == "start":
                if root is None:
                    root = elem
                continue
            tag = elem.tag
            if tag == "channel":
                cid = elem.get("id", "")
                seen_epg_ids.add(cid)
                if cid in ids:
                    found_channels.add(cid)
                    elem.tail = None
                    out.write(ET.tostring(elem, encoding="unicode") + "\n")
                elif cid.lower() in ids_lower:
                    case_hints[ids_lower[cid.lower()]] = cid
                elem.clear()
            elif tag == "programme":
                n_prog_total += 1
                if elem.get("channel", "") in ids:
                    n_prog += 1
                    elem.tail = None
                    out.write(ET.tostring(elem, encoding="unicode") + "\n")
                elem.clear()
            if root is not None and tag in ("channel", "programme"):
                root.clear()
        out.write("</tv>\n")

    return found_channels, n_prog, n_prog_total, len(seen_epg_ids), case_hints


def gzip_file(src, dst):
    with open(src, "rb") as fi, gzip.open(dst, "wb", compresslevel=9) as fo:
        shutil.copyfileobj(fi, fo, length=1024 * 1024)


def main():
    ap = argparse.ArgumentParser(description="Filter an XMLTV guide by tvg-id from an m3u playlist")
    ap.add_argument("--m3u", default="regional.m3u", help="playlist file or URL (default: regional.m3u)")
    ap.add_argument("--epg", default=os.environ.get("EPG_URL"),
                    help="full EPG URL or local file (.xml/.gz); default: env EPG_URL")
    ap.add_argument("--out", default="epg_small.xml", help="output XML file (default: epg_small.xml)")
    ap.add_argument("--no-gz", action="store_true", help="do not create the .gz copy")
    args = ap.parse_args()

    if not args.epg:
        sys.exit("EPG source not set: define the EPG_URL environment variable or pass --epg.")

    ids = read_m3u_ids(args.m3u)
    if not ids:
        sys.exit("No tvg-id found in the playlist: check the --m3u path.")
    print(f"Playlist: {len(ids)} unique tvg-id")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".epg")
    tmp.close()
    try:
        print("Downloading EPG ...")
        try:
            fetch_to_file(args.epg, tmp.name)
        except Exception as e:
            # do not print the exception text: it may contain the source address
            sys.exit(f"Download failed ({type(e).__name__}).")
        print(f"Downloaded: {os.path.getsize(tmp.name) / 1048576:.1f} MB")

        print("Filtering ...")
        found, n_prog, n_total, n_epg_ch, hints = filter_epg(tmp.name, ids, args.out)
    finally:
        os.unlink(tmp.name)

    print(f"EPG has {n_epg_ch} channels, {n_total} programmes in total")
    print(f"Kept {len(found)} channels, {n_prog} programmes -> {args.out} "
          f"({os.path.getsize(args.out) / 1048576:.2f} MB)")

    # Safety: never publish an empty guide (e.g. provider returned an error page)
    if not found or n_prog == 0:
        sys.exit("Result is empty: not writing a gz file. Check the source and tvg-id values.")

    if not args.no_gz:
        gz = args.out + ".gz"
        gzip_file(args.out, gz)
        print(f"Compressed -> {gz} ({os.path.getsize(gz) / 1048576:.2f} MB)")

    missing = sorted(ids - found)
    if missing:
        print(f"\nNo guide for {len(missing)} tvg-id (not in EPG, exact match):")
        for m in missing:
            hint = f"   <- EPG has '{hints[m]}' (case differs)" if m in hints else ""
            print(f"  {m}{hint}")


if __name__ == "__main__":
    main()
