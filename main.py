from flask import Flask, Response, request
import requests

app = Flask(__name__)

# 1. Главная страница (чтобы не было 404)
@app.route('/')
def home():
    return "Tiger IPTV Proxy is Running! Use /playlist.m3u to get channels.", 200

# 2. Выдача обработанного плейлиста
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
                # Перенаправляем поток через наш прокси
                new_lines.append(f"{domain}/stream?url={line}")
            else:
                new_lines.append(line)
                
        return Response("\n".join(new_lines), mimetype="text/plain")
    except Exception as e:
        return Response(f"Error loading playlist: {str(e)}", status_code=500)

# 3. Проксирование самого видеопотока
@app.route('/stream')
def proxy_stream():
    url = request.args.get('url')
    if not url:
        return "No URL provided", 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        req = requests.get(url, headers=headers, stream=True, timeout=10)
        return Response(
            req.iter_content(chunk_size=1024 * 64),
            content_type=req.headers.get('content-type', 'video/mp2t'),
            status=req.status_code
        )
    except Exception as e:
        return Response(f"Stream Error: {str(e)}", status_code=500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
