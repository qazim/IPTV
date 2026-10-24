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

CANLITV_CHA = {
    "Turk": [
            {"name": "TR: ATV HD",  "tvg-id": "atv-canli"},
            {"name": "TR: Show HD",  "tvg-id": "show-tv-izle-1"},
            {"name": "TR: Star TV HD",  "tvg-id": "star-tv-canli"},
            {"name": "TR: Kanal D HD",  "tvg-id": "kanal-d-canli-yayin"},
            {"name": "TR: TV8 HD",  "tvg-id": "tv8-izle-4"},
            {"name": "TR: TLC HD",  "tvg-id": "tlc"},
            {"name": "TR: Dmax HD",  "tvg-id": "dmax-canli-yayin"},
            {"name": "TR: Beyaz TV HD",  "tvg-id": "beyaz-tv"},
            {"name": "Cine1 HD",  "tvg-id": "cine-1"},
            {"name": "TR: Tivi6 HD",  "tvg-id": "tivi6"},
            {"name": "TR: 360 HD",  "tvg-id": "360-tv"},
            {"name": "TR: Cine5",  "tvg-id": "cine-5"},
            {"name": "TR: Teve2 HD",  "tvg-id": "tv2"},
            {"name": "TR: Tele1 HD",  "tvg-id": "tele1-tv"}
            ]}
    # "Azeri":[
            # {"name": "Space TV HD",  "tvg-id": "space-tv"},
            # {"name": "ATV AZ",  "tvg-id": "azad-tv"},
            # {"name": "Xazar TV HD",  "tvg-id": "xezer-tv"},
            # {"name": "AzTV HD",  "tvg-id": "az-tv"},
            # {"name": "ARB HD",  "tvg-id": "arb-tv"},
            # {"name": "ARB24 HD",  "tvg-id": "arb-24-tv"},
            # {"name": "Medeniyyet TV HD",  "tvg-id": "medeniyet-tv"},
            # {"name": "Kanal S Az",  "tvg-id": "kanal-s-azerbaycan"},
            # {"name": "Dunya TV",  "tvg-id": "dunyatv-az"},
            # {"name": "AzStar TV",  "tvg-id": "azstar-tv"},
            # {"name": "Baku TV",  "tvg-id": "baku-tv"},
            # {"name": "Gunaz TV",  "tvg-id": "gunaz-tv"}
            # ]            
# }
# name, group, canlitv.com slug
CANLITV_CHANNELS = [
    ("Space TV HD",      "Milli", "space-tv"),
    ("ATV AZ",   "Milli", "azad-tv"),
    ("Xazar TV HD",      "Milli", "xezer-tv"),
    ("AzTV HD",         "Milli", "az-tv"),
    ("ARB HD",        "Milli", "arb-tv"),
    ("ARB Gunes",  "Milli", "arb-gunes-tv"),
    ("ARB24 HD",     "Milli", "arb-24-tv"),
    ("Medeniyyet TV HD",  "Milli", "medeniyet-tv"),
    ("Kanal S Az",    "Milli", "kanal-s-azerbaycan"),
    ("Gunaz Tv",      "Milli", "gunaz-tv"),
    ("CBC",        "Milli", "cbc-tv"),
    ("Dunya TV",      "Milli", "dunyatv-az"),
    ("AzStar TV",    "Milli", "azstar-tv"),
    ("Baku TV",       "Milli", "baku-tv"),
    ("TR: ATV HD",          "Turk", "atv-canli"),
    ("TR: Show HD",          "Turk", "show-tv-izle-1"),
    ("TR: Star TV HD",       "Turk", "star-tv-canli"), 
    ("TR: Kanal D HD",       "Turk", "kanal-d-canli-yayin"),
    ("TR: TV8 HD",           "Turk", "tv8-izle-4"),
    ("TR: TLC HD",           "Turk", "tlc"),  
    ("TR: Dmax HD",          "Turk", "dmax-canli-yayin"),
    ("TR: Beyaz TV HD",      "Turk", "beyaz-tv"),
    ("TR: Cine1 HD",         "Turk", "cine-1"),
    ("TR: Tivi6 HD",         "Turk", "tivi6"),    
    ("TR: 360 HD",           "Turk", "360-tv"),
    ("TR: Cine5",            "Turk", "cine-5"),
    ("TR: Teve2 HD",         "Turk", "tv2"),
    ("TR: Tele1 HD",         "Turk", "tele1-tv"),
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

def build_m3u_new() -> str:
    lines = ['#EXTM3U']
    for name, channels  in CANLITV_CHA.items():
        lines.append(f"######### {name} ##########")
        for ch in channels:
            try:
                url = get_stream_url(ch['tvg-id'])
            except requests.RequestException as e:
                print(f"[canlitv] HATA ({ch['name']}): {e}")
                url = None
            if url:
                lines.append(f"#EXTINF:-1 group-title=\"{name}\" tvg-id=\"{ch['tvg-id']}\",{ch['name']}")
                lines.append(url)
                print('Bulunan: ', url)
            else:
                print(f"[canlitv] SKIP (bulunamadi): {name} -> {ch['tvg-id']}")
    return "\n".join(lines)
    
def build_m3u_entries() -> str:
    lines = ['#EXTM3U']
    for name, group, slug in CANLITV_CHANNELS:
        try:
            url = get_stream_url(slug)
        except requests.RequestException as e:
            print(f"[canlitv] HATA ({name}): {e}")
            url = None
        if url:
            lines.append(f"#EXTINF:-1 group-title=\"{group}\",{name}")
            lines.append(url)
            print('Bulunan: ', url)
        else:
            print(f"[canlitv] SKIP (bulunamadi): {name} -> {slug}")
    return "\n".join(lines)


OUTPUT_FILE = "canlitv.m3u"



if __name__ == "__main__":
    entries = build_m3u_new()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(entries + "\n")
    print(f"[canlitv] {OUTPUT_FILE} yazildi ({entries.count(chr(10)) // 2 + 1} kanal denendi)")
