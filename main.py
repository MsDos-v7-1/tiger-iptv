from flask import Flask, Response, request
import requests
from urllib.parse import urljoin, unquote
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

def parse_playlist():
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
        
        host = request.host
        lines = content.splitlines()
        new_lines = []
        
        ch_id = 1
        for line in lines:
            line = line.strip()
            if line.startswith("http://") or line.startswith("https://"):
                # Важно: отдаём http, чтобы тюнер не пытался сразу штурмовать SSL
                new_lines.append(f"http://{host}/s/{ch_id}")
                ch_id += 1
            else:
                new_lines.append(line)
                
        return Response("\n".join(new_lines), mimetype="text/plain")
    except Exception as e:
        return Response(f"Error loading playlist: {str(e)}", status_code=500)

@app.route('/s/<int:channel_id>')
def stream_channel(channel_id):
    urls = parse_playlist()
    if not (1 <= channel_id <= len(urls)):
        return "Channel Not Found", 404
    
    target_url = urls[channel_id - 1]

    def generate_ts_stream():
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://smotrim.ru/"
        }
        session = requests.Session()
        
        try:
            # Получаем HLS манифест
            res = session.get(target_url, headers=headers, timeout=10, verify=False)
            if res.status_code != 200:
                return

            lines = [l.strip() for l in res.text.splitlines() if l.strip() and not l.startswith('#')]
            
            # Если это плейлист с вариантами качества, берем первую ссылку
            if lines and lines[0].endswith('.m3u8'):
                sub_url = urljoin(target_url, lines[0])
                res = session.get(sub_url, headers=headers, timeout=10, verify=False)
                lines = [l.strip() for l in res.text.splitlines() if l.strip() and not l.startswith('#')]

            # Прокачиваем сегменты напрямую в тюнер
            for segment in lines:
                seg_url = urljoin(target_url, segment)
                with session.get(seg_url, headers=headers, stream=True, timeout=10, verify=False) as seg_res:
                    for chunk in seg_res.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
        except Exception as e:
            print(f"Stream Error: {e}")

    # Отдаем как прямой MPEG-TS файл
    return Response(generate_ts_stream(), mimetype='video/mp2t')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
