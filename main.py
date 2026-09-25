from flask import Flask, Response, request
import requests
from urllib.parse import urljoin, quote, unquote
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

def parse_playlist():
    """Считывает playlist.m3u и возвращает список всех прямых ссылок по порядку"""
    urls = []
    try:
        with open("playlist.m3u", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("http://") or line.startswith("https://"):
                    urls.append(line)
    except Exception as e:
        print(f"Error reading playlist: {e}")
    return urls

@app.route('/')
def home():
    return "Tiger IPTV Proxy is Running!", 200

@app.route('/playlist.m3u')
def get_playlist():
    try:
        with open("playlist.m3u", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Формируем короткий HTTP-домен для микроконтроллера/тюнера
        domain = f"http://{request.host}"
        lines = content.splitlines()
        new_lines = []
        
        ch_id = 1
        for line in lines:
            line = line.strip()
            if line.startswith("http://") or line.startswith("https://"):
                # Автоматически превращаем любую длинную ссылку в ультракороткую: /s/1, /s/2 и т.д.
                new_lines.append(f"{domain}/s/{ch_id}")
                ch_id += 1
            else:
                new_lines.append(line)
                
        return Response("\n".join(new_lines), mimetype="text/plain")
    except Exception as e:
        return Response(f"Error loading playlist: {str(e)}", status_code=500)

@app.route('/s/<int:channel_id>')
def proxy_channel(channel_id):
    urls = parse_playlist()
    # Выбираем нужный URL по порядковому номеру из плейлиста
    if 1 <= channel_id <= len(urls):
        target_url = urls[channel_id - 1]
        return fetch_and_proxy(target_url)
    return "Channel Not Found", 404

@app.route('/stream')
def proxy_stream():
    raw_url = request.args.get('url')
    if not raw_url:
        return "No URL provided", 400
    return fetch_and_proxy(unquote(raw_url))

def fetch_and_proxy(target_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": "https://smotrim.ru/"
    }

    try:
        session = requests.Session()
        req = session.get(target_url, headers=headers, stream=True, timeout=10, verify=False)
        content_type = req.headers.get('Content-Type', '')

        if 'mpegurl' in content_type or 'apple' in content_type or target_url.endswith('.m3u8'):
            text_content = req.text
            domain = f"http://{request.host}"
            
            new_lines = []
            for line in text_content.splitlines():
                line_str = line.strip()
                if line_str and not line_str.startswith('#'):
                    abs_url = urljoin(target_url, line_str)
                    encoded_segment = quote(abs_url, safe='')
                    new_lines.append(f"{domain}/stream?url={encoded_segment}")
                else:
                    new_lines.append(line)
            
            return Response("\n".join(new_lines), mimetype="application/vnd.apple.mpegurl")

        return Response(
            req.iter_content(chunk_size=1024 * 64),
            content_type=content_type or 'video/mp2t',
            status=req.status_code
        )
    except Exception as e:
        return Response(f"Stream Error: {str(e)}", status_code=500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
