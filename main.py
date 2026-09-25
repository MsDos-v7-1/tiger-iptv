from flask import Flask, Response, request
import requests
from urllib.parse import urljoin, quote, unquote
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

@app.route('/')
def home():
    return "Tiger IPTV Proxy is Running!", 200

@app.route('/playlist.m3u')
def get_playlist():
    try:
        with open("playlist.m3u", "r", encoding="utf-8") as f:
            content = f.read()
        
        domain = request.host_url.rstrip('/')
        lines = content.splitlines()
        new_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("http://") or line.startswith("https://"):
                # Кодируем URL, чтобы спецсимволы не ломали запросы
                encoded_url = quote(line, safe='')
                new_lines.append(f"{domain}/stream?url={encoded_url}")
            else:
                new_lines.append(line)
                
        return Response("\n".join(new_lines), mimetype="text/plain")
    except Exception as e:
        return Response(f"Error loading playlist: {str(e)}", status_code=500)

@app.route('/stream')
def proxy_stream():
    raw_url = request.args.get('url')
    if not raw_url:
        return "No URL provided", 400

    target_url = unquote(raw_url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }

    try:
        req = requests.get(target_url, headers=headers, stream=True, timeout=10, verify=False)
        content_type = req.headers.get('Content-Type', '')

        # Если это m3u8 плейлист — переписываем внутри него пути к сегментам
        if 'mpegurl' in content_type or 'apple' in content_type or target_url.endswith('.m3u8'):
            text_content = req.text
            domain = request.host_url.rstrip('/')
            
            new_lines = []
            for line in text_content.splitlines():
                line_str = line.strip()
                if line_str and not line_str.startswith('#'):
                    # Преобразуем относительную ссылку в абсолютную
                    abs_url = urljoin(target_url, line_str)
                    encoded_segment = quote(abs_url, safe='')
                    new_lines.append(f"{domain}/stream?url={encoded_segment}")
                else:
                    new_lines.append(line)
            
            return Response("\n".join(new_lines), mimetype="application/vnd.apple.mpegurl")

        # Если это бинарный видеосегмент (.ts / .aac и т.д.) — проксируем как есть
        return Response(
            req.iter_content(chunk_size=1024 * 64),
            content_type=content_type or 'video/mp2t',
            status=req.status_code
        )
    except Exception as e:
        return Response(f"Stream Error: {str(e)}", status_code=500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
