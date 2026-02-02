import re
import requests
import sys
import json
import os
from urllib.parse import urljoin
from tqdm import tqdm

# --- Функции из первого скрипта (Regex) ---
def get_stream_url(url, pattern, method="GET", headers={}, body={}):
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            r = requests.post(url, json=body, headers=headers, timeout=15)
        else: return None
        
        results = re.findall(pattern, r.text)
        return results[0] if results else None
    except:
        return None

# --- Функции из второго скрипта (Catcast API) ---
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
    if len(sys.argv) < 2:
        print("Ошибка! Запуск: python main.py config.json")
        return

    # Заголовок плейлиста
    final_playlist = ["#EXTM3U\n"]
    
    # --- 1. Обработка ОСНОВНОГО конфига (Группа: Azeri-yerli) ---
    group_1 = "Azeri-yerli"
    print(f">>> Обработка основного конфига (Группа: {group_1})...")
    try:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            main_config = json.load(f)
        
        for site in main_config:
            group_1 = site['name'] 
            for channel in tqdm(site["channels"], desc=f"Сайт: {site['slug']}"):
                url = site["url"]
                for var in channel["variables"]:
                    url = url.replace(var["name"], var["value"])
                
                stream = get_stream_url(url, site["pattern"])
                if stream and site["output_filter"] in stream:
                    # Добавляем group-title="Azeri-yerli"
                    final_playlist.append(f'#EXTINF:-1 group-title="{group_1}",{channel["name"]}\n')
                    final_playlist.append(f"{stream}\n")
    except Exception as e:
        print(f"Ошибка в основном конфиге: {e}")

    # --- 2. Обработка CATCAST конфига (Группа: Music) ---
    group_2 = "Music"
    catcast_config_path = "catcast-config.json"
    if os.path.exists(catcast_config_path):
        print(f"\n>>> Обработка Catcast конфига (Группа: {group_2})...")
        try:
            with open(catcast_config_path, "r", encoding="utf-8") as f:
                cat_config = json.load(f)
            
            for channel in tqdm(cat_config, desc="Catcast"):
                stream = get_catcast_stream(channel.get("id"))
                if stream:
                    # Добавляем group-title="Music"
                    final_playlist.append(f'#EXTINF:-1 group-title="{group_2}",{channel.get("slug")}\n')
                    final_playlist.append(f"{stream}\n")
        except Exception as e:
            print(f"Ошибка в Catcast конфиге: {e}")
    else:
        print(f"\nФайл {catcast_config_path} не найден.")

    # --- 3. ЗАПИСЬ В ЕДИНЫЙ ФАЙЛ ---
    with open("all_channels.m3u", "w", encoding="utf-8") as f:
        f.writelines(final_playlist)
    
    print(f"\n✅ Готово! Файл 'all_channels.m3u' создан.")
    print(f"Каналы распределены по группам: '{group_1}' и '{group_2}'")

if __name__ == "__main__":

    main()

