import re
import requests
import sys
import io
import json
import os
import yt_dlp 
from urllib.parse import urljoin
from tqdm import tqdm
import tempfile

def get_youtube_m3u8(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    cookies_file = None
    cookies_content = os.environ.get("YOUTUBE_COOKIES")
    if cookies_content:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        tmp.write(cookies_content)
        tmp.close()
        cookies_file = tmp.name
    
    ydl_opts = {
        "quiet": True,
        "format": "best[protocol=m3u8_native]/best",
        "extractor_args": {"youtube": {"js_runtimes": ["nodejs"]}},
    }
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("url")
    except:
        return None
    finally:
        if cookies_file and os.path.exists(cookies_file):
            os.unlink(cookies_file)
        
def get_stream_url(url, pattern, method="GET", headers={}, body={}):
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
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

        # Fallback: ищем YouTube и извлекаем HLS через yt-dlp
        yt = re.findall(r'youtube-nocookie\.com/embed/([a-zA-Z0-9_-]{11})', r.text)
        if yt:
            return get_youtube_m3u8(yt[0])

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
    #final_playlist.append(f"\n")
    with open('TurkAzeri.m3u', "r", encoding="utf-8") as f:
        for line in f:
            final_playlist.append(line)
    # Заголовок плейлиста
    # --- 1. Обработка ОСНОВНОГО конфига (Группа: Azeri-yerli) ---
    group_1 = "Turk ulusal"
    print(f">>> Обработка основного конфига (Группа: {group_1})...")
    try:
        with open('config.json', "r", encoding="utf-8") as f:
            main_config = json.load(f)
        
        for site in main_config:  # ← эта строка пропущена!
            group_1 = site['name']
            final_playlist.append(f"\n")
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
                    #print('Add channel:', channel['name'])
                    final_playlist.append(f'#EXTINF:-1 group-title="{group_1}",{channel["name"]}\n')
                    final_playlist.append(f"{stream}\n")
    except Exception as e:
        print(f"Ошибка в основном конфиге: {e}")
    
    # --- 2. Обработка CATCAST конфига (Группа: Music) ---
    group_2 = "Music"
    
    #catcast_config_path = "catcast-config.json"
    catcast_config_path = "catcast_config.json"
    if os.path.exists(catcast_config_path):
        print(f"\n>>> Processing Catcast config (Group: {group_2})...")
        try:
            with open(catcast_config_path, "r", encoding="utf-8") as f:
                cat_config = json.load(f)
            for site in cat_config:
                group_2 = site['name']  
                final_playlist.append(f"\n")
                for channel in tqdm(site["channels"], desc="Catcast: " + site['name']):
                    stream = get_catcast_stream(channel.get("id"))
                    if stream:
                    # Добавляем group-title="Music"
                        final_playlist.append(f'#EXTINF:-1 group-title="{group_2}",{channel.get("slug")}\n')
                        final_playlist.append(f"{stream}\n")
        except Exception as e:
            print(f"Error Catcast config: {e}")
    else:
        print(f"\nFile {catcast_config_path} Not found.")
    
    # --- 3. ЗАПИСЬ В ЕДИНЫЙ ФАЙЛ ---
    with open("all_channels.m3u", "w", encoding="utf-8") as f:
        f.writelines(final_playlist)
    
    print(f"\n Ready! File 'all_channels.m3u' Created.")
    print(f"Channels are divided into groups: '{group_1}' и '{group_2}'")

if __name__ == "__main__":
    main()
