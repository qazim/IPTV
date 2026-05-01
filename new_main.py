import re
import requests
import json
import os
from tqdm import tqdm

# ============================================================
# Funksiya 1: Adi Regex (myvideo-az və s. üçün)
# ============================================================
def get_stream_url(url, pattern, method="GET", headers={}, body={}):
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            r = requests.post(url, json=body, headers=headers, timeout=15)
        else:
            return None
        results = re.findall(pattern, r.text)
        return results[0] if results else None
    except:
        return None


# ============================================================
# Funksiya 2: canlitv.me üçün şifrə açma
# ============================================================
def x34fcag3(encoded):
    """JavaScript-dəki şifrələmə funksiyasının Python versiyası"""
    _443365 = ['€','$','Ă','Ä','Ë','Ģ','Ḩ','Ķ','Ḽ','Ņ','Ň','Š','Ț','Ž','Ә','Є','Б','Җ',
               'Ч','Ж','Д','Ӡ','Ф','Ғ','Ӷ','Ы','И','К','Љ','Ө','Ў','Њ','Һ','Г','Ş']
    _3ad2f0 = ['0','1','2','3','4','5','6','7','8','9','.','&','=','w','?','c','o','m','a',
               'f','l','i','h','t','s',':','/','r','e','d','n','k','p','_','-']
    separator = 'Äx|Xf|x'
    parts = encoded.split(separator)
    if len(parts) < 2:
        return None
    try:
        key_index = int(parts[0])
    except:
        return None
    text = parts[1]
    max_key = len(_443365) - 1
    pos = key_index
    for i in range(len(_3ad2f0)):
        if pos > max_key:
            pos = 0
        text = text.replace(_443365[pos], _3ad2f0[i])
        pos += 1
    return text


def get_canlitv_stream(channel_slug):
    """canlitv.me-dən m3u8 linkini alır"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
    }

    try:
        # Addım 1: Ana səhifədən security token al
        main_url = f'https://www.canlitv.me/live/{channel_slug}'
        r = requests.get(main_url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None

        security_match = re.search(r'security=([a-f0-9]+)', r.text)
        if not security_match:
            return None
        security = security_match.group(1)

        # Addım 2: geolive.php-dən ulke dəyişənini al
        geo_url = f'https://www.canlitv.me/geolive.php?kanal={channel_slug}&security={security}'
        headers['Referer'] = main_url
        r2 = requests.get(geo_url, headers=headers, timeout=15)

        ulke_match = re.search(r'tkslast\s*=\s*"([^"]+)"', r2.text)
        ulke = ulke_match.group(1) if ulke_match else 'AZ'

        # Addım 3: yayin.php-dən şifrəli linki al
        yayin_url = (f'https://www.canlitv.me/yayin.php?kanal={channel_slug}'
                     f'&ulke={ulke}&tkslast={ulke}')
        headers['Referer'] = geo_url
        r3 = requests.get(yayin_url, headers=headers, timeout=15)

        # Addım 4: Şifrəli linki tap
        encoded_match = re.search(r"file\s*:\s*'(\d+Äx\|Xf\|x[^']+)'", r3.text)
        if not encoded_match:
            # Alternativ: birbaşa m3u8 linki ola bilər
            direct = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', r3.text)
            return direct[0] if direct else None

        # Addım 5: Deşifrə et
        encoded = encoded_match.group(1)
        return x34fcag3(encoded)

    except Exception as e:
        return None


# ============================================================
# Funksiya 3: Catcast API
# ============================================================
def get_catcast_stream(channel_id):
    url = f"https://api.catcast.tv/api/channels/{channel_id}/getcurrentprogram"
    try:
        r = requests.post(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == 1:
                return data.get("data", {}).get("full_mobile_url")
    except:
        return None
    return None


# ============================================================
# ƏSAS FUNKSIYA
# ============================================================
def main():
    final_playlist = ["#EXTM3U \n"]

    # Mövcud TurkAzeri.m3u faylını əlavə et
    if os.path.exists('TurkAzeri.m3u'):
        with open('TurkAzeri.m3u', "r", encoding="utf-8") as f:
            for line in f:
                final_playlist.append(line)

    # --- 1. config.json (Azeri-yerli və s.) ---
    print(">>> config_new.json emal edilir...")
    try:
        with open('config_new.json', "r", encoding="utf-8") as f:
            main_config = json.load(f)

        for site in main_config:
            group = site['name']
            slug  = site['slug']

            # canlitv-me xüsusi metod ilə işlənir
            if slug == 'canlitv-me':
                print(f"\n>>> canlitv.me emal edilir (Qrup: {group})...")
                for channel in tqdm(site["channels"], desc="canlitv.me"):
                    channel_slug = channel["variables"][0]["value"]
                    stream = get_canlitv_stream(channel_slug)
                    if stream:
                        final_playlist.append(
                            f'#EXTINF:-1 group-title="{group}",{channel["name"]}\n')
                        final_playlist.append(f"{stream}\n")
                        tqdm.write(f"  ✓ {channel['name']}: {stream[:60]}...")
                    else:
                        tqdm.write(f"  ✗ {channel['name']}: tapılmadı")
            else:
                # Adi regex metodu
                print(f"\n>>> {slug} emal edilir (Qrup: {group})...")
                for channel in tqdm(site["channels"], desc=f"Sayt: {slug}"):
                    url = site["url"]
                    for var in channel["variables"]:
                        url = url.replace(var["name"], var["value"])

                    stream = get_stream_url(
                        url, site["pattern"],
                        method=site.get("method", "GET"),
                        headers=site.get("headers", {})
                    )
                    if stream and site.get("output_filter", "") in stream:
                        final_playlist.append(
                            f'#EXTINF:-1 group-title="{group}",{channel["name"]}\n')
                        final_playlist.append(f"{stream}\n")

    except Exception as e:
        print(f"config.json xətası: {e}")

    # --- 2. config-cat.json (Catcast / Music) ---
    catcast_path = "config-cat.json"
    if os.path.exists(catcast_path):
        print(f"\n>>> Catcast emal edilir...")
        try:
            with open(catcast_path, "r", encoding="utf-8") as f:
                cat_config = json.load(f)
            for site in cat_config:
                group = site['name']
                for channel in tqdm(site["channels"], desc="Catcast"):
                    stream = get_catcast_stream(channel.get("id"))
                    if stream:
                        final_playlist.append(
                            f'#EXTINF:-1 group-title="{group}",{channel.get("slug")}\n')
                        final_playlist.append(f"{stream}\n")
        except Exception as e:
            print(f"Catcast xətası: {e}")
    else:
        print(f"\n{catcast_path} tapılmadı, keçilir.")

    # --- 3. Faylı yaz ---
    with open("New_turk.m3u", "w", encoding="utf-8") as f:
        f.writelines(final_playlist)

    print(f"\n✓ Hazır! 'New_turk.m3u' yaradıldı.")


if __name__ == "__main__":
    main()
