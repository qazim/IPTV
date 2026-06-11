import re
import requests
import json
import os
import yt_dlp
import tempfile
from tqdm import tqdm

def get_stream_url(url, pattern, method="GET", headers={}, body={}):
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            r = requests.post(url, json=body, headers=headers, timeout=15)
        else:
            return None

        results = re.findall(pattern, r.text)
        if results:
            first = results[0]
            if isinstance(first, tuple):
                return next((g for g in first if g), None)
            return first

        return None
    except:
        return None

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

def main():
    final_playlist = ["#EXTM3U \n"]
    
    with open('TurkAzeri.m3u', "r", encoding="utf-8") as f:
        for line in f:
            final_playlist.append(line)

    # --- 1. Основной конфиг ---
    group_1 = "Turk ulusal"
    print(f">>> Обработка основного конфига (Группа: {group_1})...")
    try:
        with open('config.json', "r", encoding="utf-8") as f:
            main_config = json.load(f)
        
        for site in main_config:
            group_1 = site['name']
            for channel in tqdm(site["channels"], desc=f"Сайт: {site['slug']}"):
                url = site["url"]
                for var in channel["variables"]:
                    url = url.replace(var["name"], var["value"])
                
                stream = get_stream_url(
                    url,
                    site["pattern"],
                    method=site.get("method", "GET"),
                    headers=site.get("headers", {})
                )
                
                if stream and site["output_filter"] in stream:
                    print('Add channel:', channel['name'])
                    final_playlist.append(f'#EXTINF:-1 group-title="{group_1}",{channel["name"]}\n')
                    final_playlist.append(f"{stream}\n")
    except Exception as e:
        print(f"Ошибка в основном конфиге: {e}")

    # --- 2. Catcast конфиг ---
    group_2 = "Music"
    catcast_config_path = "catcast_config.json"
    if os.path.exists(catcast_config_path):
        print(f"\n>>> Processing Catcast config (Group: {group_2})...")
        try:
            with open(catcast_config_path, "r", encoding="utf-8") as f:
                cat_config = json.load(f)
            for site in cat_config:
                group_2 = site['name']
                for channel in tqdm(site["channels"], desc="Catcast: " + site['name']):
                    stream = get_catcast_stream(channel.get("id"))
                    if stream:
                        final_playlist.append(f'#EXTINF:-1 group-title="{group_2}",{channel.get("slug")}\n')
                        final_playlist.append(f"{stream}\n")
        except Exception as e:
            print(f"Error Catcast config: {e}")
    else:
        print(f"\nFile {catcast_config_path} Not found.")

    # --- 3. Запись файла ---
    with open("all_channels.m3u", "w", encoding="utf-8") as f:
        f.writelines(final_playlist)

    print(f"\nReady! File 'all_channels.m3u' Created.")

if __name__ == "__main__":
    main()