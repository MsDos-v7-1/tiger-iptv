import os
import requests
from flask import Flask, Response, request, stream_with_context

app = Flask(__name__)

# Заголовки, притворяемся VLC-плеером на Windows
HEADERS = {
    "User-Agent": "VLC/3.0.18 LibVLC/3.0.18",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

@app.route('/playlist.m3u')
def get_playlist():
    """Читает локальный файл playlist.m3u и перенаправляет ссылки через прокси"""
    try:
        if not os.path.exists('playlist.m3u'):
            return "Файл playlist.m3u не найден!", 404

        with open('playlist.m3u', 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        host_url = request.host_url.rstrip('/')
        new_playlist = []

        for line in lines:
            clean_line = line.strip()
            if clean_line.startswith("http://") or clean_line.startswith("https://"):
                new_playlist.append(f"{host_url}/stream?url={clean_line}")
            else:
                new_playlist.append(clean_line)
                
        return Response("\n".join(new_playlist), content_type="text/plain; charset=utf-8")
    except Exception as e:
        return f"Ошибка обработки: {e}", 500

@app.route('/stream')
def proxy_stream():
    """Проксирует поток с нужными заголовками"""
    stream_url = request.args.get('url')
    if not stream_url:
        return "URL не указан", 400

    def generate():
        try:
            with requests.get(stream_url, headers=HEADERS, stream=True, timeout=15) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
        except Exception as e:
            print(f"Ошибка потока: {e}")

    return Response(stream_with_context(generate()), content_type="video/mp2t")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
