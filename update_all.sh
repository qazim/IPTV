#!/data/data/com.termux/files/usr/bin/bash
# update_all.sh — обновляет canlitv.m3u и/или regional.m3u и пушит в GitHub
# Использование:
#   ./update_all.sh canlitv     — обновить только canlitv.m3u
#   ./update_all.sh regional    — обновить только regional.m3u
#   ./update_all.sh all         — обновить оба файла
#   ./update_all.sh             — по умолчанию тоже "all"

set -e   # остановиться при первой ошибке

MODE="${1:-all}"

echo ">>> git pull..."
git pull

if [ "$MODE" = "canlitv" ] || [ "$MODE" = "all" ]; then
    echo ">>> Запуск canlitv_source.py..."
    python canlitv_source.py
    git add canlitv.m3u
fi

if [ "$MODE" = "regional" ] || [ "$MODE" = "all" ]; then
    echo ">>> Запуск build_playlist.py..."
    python build_playlist.py
    git add regional.m3u
fi

# Коммитим только если реально что-то изменилось
if git diff --cached --quiet; then
    echo ">>> Изменений нет, коммит не нужен."
else
    echo ">>> Коммит и push..."
    git commit -m "update playlists ($(date '+%Y-%m-%d %H:%M'))"
    git push
    echo ">>> Готово! Изменения запушены."
    echo ">>> Теперь открой приложение GitHub -> qazim/IPTV -> Actions -> main.yml -> Run workflow"
fi
fi
