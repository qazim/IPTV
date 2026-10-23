import re
import requests
import sys
import io
import json
import os
from urllib.parse import urljoin
from tqdm import tqdm


M3U_LIST = [
    "tr.m3u"
]
       
def get_stream_url(url, pattern, method="GET", headers={}, body={}):
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
            print(f"  [{r.status_code}] len={len(r.text)} {url[:60]}")
        elif method == "POST":
            r = requests.post(url, json=body, headers=headers, timeout=15)
        else:
            return None

        # Сначала пробуем обычный паттерн
        results = re.findall(pattern, r.text)
        if results:
            first = results[0]
            if isinstance(first, tuple):
                return next((g for g in first if g), None)
            return first

    except Exception as e:
        print(f"  {url[:60]}: {type(e).__name__}: {e}")
        return None
        
def get_catcast_stream(channel_id):
    url = f"https://api.catcast.tv/api/channels/{channel_id}/getcurrentprogram"
    for send in (requests.post, requests.get):
        try:
            r = send(url, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if data.get("status") != 1:
                continue
            d = data.get("data", {})
            if not d.get("is_online"):
                return None
            base, tok = d.get("full_url"), d.get("token")
            if base:
                return f"{base}?token={tok}" if tok else base
            return d.get("full_mobile_url")
        except Exception as e:
            print(f"  Catcast {channel_id}: {type(e).__name__}: {e}")
    return None
    
def get_catcast_channel(channel_id):
    url = channel_id
    try:
        r = requests.post(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == 1:
                return data.get("data", {}).get("full_mobile_url")
    except:
        return None
    return None

def main():
    final_playlist = ['#EXTM3U url-tvg="https://iptvx.one/EPG"\n']
    for file in M3U_LIST:
        with open(file, "r", encoding="utf-8") as f:
            for line in f:               
                # чтобы они не дублировались в середине общего файла
                if line.startswith("#EXTM3U"):
                    continue
                    
                final_playlist.append(line)

    # Заголовок плейлиста
    # --- 1. Обработка ОСНОВНОГО конфига (Группа: Azeri-yerli) ---
    # group_1 = "Turk ulusal"
    # print(f">>> Обработка основного конфига (Группа: {group_1})...")
    # try:
        # with open('config.json', "r", encoding="utf-8") as f:
            # main_config = json.load(f)
        
        # for site in main_config:  # ← эта строка пропущена!
            # group_1 = site['name']
            # final_playlist.append(f"############   {group_1}   #############\n")
            # for channel in site["channels"]:
                # url = site["url"]
                # for var in channel["variables"]:
                    # url = url.replace(var["name"], var["value"])
                
                    # stream = get_stream_url(
                        # url,
                        # site["pattern"],
                        # method=site.get("method", "GET"),
                        # headers=site.get("headers", {})
                    # )
                    
                    # if stream and site["output_filter"] in stream:
                        # final_playlist.append(f'#EXTINF:-1 group-title="{group_1}",{channel["name"]}\n')
                        # final_playlist.append(f"{stream}\n")
                        # print(f'Bulundu: {channel.get("name")}')
                    # else:
                        # print(f'Bulunmadı..{channel.get("name")}')
    # except Exception as e:
        # print(f"Ошибка в основном конфиге: {e}")
    
    # --- 2. Обработка CATCAST конфига (Группа: Music) ---
    group_2 = "Music"
    
    catcast_config_path = "catcast_config.json"
    if os.path.exists(catcast_config_path):
        print(f"\n>>> Processing Catcast config (Group: {group_2})...")
        try:
            with open(catcast_config_path, "r", encoding="utf-8") as f:
                cat_config = json.load(f)
            for site in cat_config:
                group_2 = site['name']  
                final_playlist.append(f"############   {group_2}   #############\n")
                for channel in site["channels"]:
                    stream = get_catcast_stream(channel["id"])
                    if stream:
                        final_playlist.append(f'#EXTINF:-1 group-title="{group_2}",{channel["slug"]}\n')
                        final_playlist.append(f"{stream}\n")
                        print(f'Bulundu: {channel["slug"]}')
                    else:
                        print(f'Bulunmadı: {channel["slug"]}')
        except Exception as e:
            print(f"Error Catcast config: {e}")
    else:
        print(f"\nFile {catcast_config_path} Not found.")

    with open('region.m3u', "r", encoding="utf-8") as f:
        f.readline()
        for line in f:
            final_playlist.append(line)
            
    # --- 3. ЗАПИСЬ В ЕДИНЫЙ ФАЙЛ ---
    with open("all_channels.m3u", "w", encoding="utf-8") as f:
        f.writelines(final_playlist)
    
    print(f"\n Ready! File 'all_channels.m3u' Created.")
    #print(f"Channels are divided into groups: '{group_1}' и '{group_2}'")

if __name__ == "__main__":
    main()