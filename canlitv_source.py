"""
canlitv.com kaynagi - myvideo.az'in yerine gecen ikinci kaynak.
Space TV, Real TV gibi token korumali kanallar icin.

Nasil calisir:
1. https://canlitv.com/{slug} sayfasini cek, og:image'dan kanal ID'sini cikar
   (og:image: https://canlitv.com/kanal/logo/{ID}.jpg)
2. https://canlitv.com/player/index.php?id={ID}&mobile=0 sayfasini cek
3. jwplayer setup icindeki file: "..." degerini regex ile cikar
   (bu URL her istekte YENIDEN uretilir - hash/token her build'de taze olur)

myvideo-az'in eski regex-scraper mimarisiyle ayni mantik, sadece
kaynak canlitv.com'a, hedef de dogru sayfaya isaret ediyor.
"""
import re
import requests
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://canlitv.com/",
}

# name, group, canlitv.com slug
CANLITV_CHANNELS = [
    ("Space TV",      "Milli", "space-tv"),
    ("Real TV",       "Milli", "real-tv"),
    ("Atv Azad TV",   "Milli", "azad-tv"),
    ("Xezer Tv",      "Milli", "xezer-tv"),
    ("Az TV",         "Milli", "az-tv"),
    ("El Tv",         "Milli", "el-tv"),
    ("ARB TV",        "Milli", "arb-tv"),
    ("ARB Gunes TV",  "Milli", "arb-gunes-tv"),
    ("ARB 24 TV",     "Milli", "arb-24-tv"),
    ("Medeniyet Tv",  "Milli", "medeniyet-tv"),
    ("Kanal S Az",    "Milli", "kanal-s-azerbaycan"),
    ("Gunaz Tv",      "Milli", "gunaz-tv"),
    ("CBC Tv",        "Milli", "cbc-tv"),
    ("Ictimai Tv",    "Milli", "ictimai-tv"),
    ("CBC Sport",     "Milli", "cbc-sport-izle"),
    ("Idman Tv",      "Milli", "idman-tv"),
    ("Dunya TV",      "Milli", "dunyatv-az"),
    ("Az Star TV",    "Milli", "azstar-tv"),
    ("Baku TV",       "Milli", "baku-tv"),
    ("Atv TV",        "Milli", "atv-canli"),
    ("Show TV",       "Milli", "show-tv-izle-1"),
    ("Star TV",       "Milli", "star-tv-canli"), 
    ("Kanal D",       "Milli", "kanal-d-canli-yayin"),
    ("TLC",      "Milli", "tlc"),  
    ("DMAX",      "Milli", "dmax-canli-yayin"),
    ("Trt Belgesel",      "Milli", "trt-belgesel"),
]

ID_RE = re.compile(r'og:image["\']?\s*content=["\']https://canlitv\.com/kanal/logo/(\d+)\.jpg')
FILE_RE = re.compile(r'file:\s*"([^"]+)"')


def get_channel_id(slug: str) -> str | None:
    r = requests.get(f"https://canlitv.com/{slug}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    m = ID_RE.search(r.text)
    return m.group(1) if m else None


def get_stream_url(slug: str) -> str | None:
    channel_id = get_channel_id(slug)
    if not channel_id:
        return None
    player_url = f"https://canlitv.com/player/index.php?id={channel_id}&mobile=0"
    r = requests.get(player_url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    m = FILE_RE.search(r.text)
    return m.group(1) if m else None


def build_m3u_entries() -> str:
    lines = []
    for name, group, slug in CANLITV_CHANNELS:
        try:
            url = get_stream_url(slug)
        except requests.RequestException as e:
            print(f"[canlitv] HATA ({name}): {e}")
            url = None
        if url:
            lines.append(f"#EXTINF:-1 group-title=\"{group}\",{name}")
            lines.append(url)
        else:
            print(f"[canlitv] SKIP (bulunamadi): {name} -> {slug}")
    return "\n".join(lines)


OUTPUT_FILE = "CanliTvAz.m3u"



if __name__ == "__main__":
    entries = build_m3u_entries()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(entries + "\n")
    print(f"[canlitv] {OUTPUT_FILE} yazildi ({entries.count(chr(10)) // 2 + 1} kanal denendi)")