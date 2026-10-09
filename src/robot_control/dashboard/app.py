#!/usr/bin/env python3
"""
Farmer-facing dashboard — Flask scaffold.
Serves results table + GPS health map from data/results.json.

Later, real data arrives either via:
  - result_logger.py node writing to results.json (current design), or
  - robot POSTing to /api/submit directly
"""
import json, os, threading
from datetime import datetime
from flask import Flask, jsonify, render_template, request, abort, Response, stream_with_context
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data', 'results.json')

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
_lock = threading.Lock()

def load_results():
    with _lock:
        with open(DATA) as f:
            return json.load(f)

def save_results(data):
    with _lock:
        tmp = DATA + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, DATA)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/results')
def api_results():
    return jsonify(load_results())

@app.route('/api/stats')
def api_stats():
    data = load_results()
    rs = data['results']
    diseased = sum(1 for r in rs if r['classification'] != 'healthy')
    return jsonify({
        'mission': data.get('mission_id', '-'),
        'updated': data.get('updated', '-'),
        'total': len(rs),
        'healthy': len(rs) - diseased,
        'diseased': diseased,
        'pct_diseased': round(100 * diseased / len(rs), 1) if rs else 0.0,
    })

@app.route('/api/submit', methods=['POST'])
def api_submit():
    r = request.get_json(force=True)
    for k in ('waypoint', 'lat', 'lon', 'classification', 'confidence'):
        if k not in r:
            abort(400, f'missing field: {k}')
    data = load_results()
    r['id'] = max((x['id'] for x in data['results']), default=0) + 1
    r.setdefault('timestamp', datetime.now().isoformat(timespec='seconds'))
    data['results'].append(r)
    data['updated'] = datetime.now().isoformat(timespec='seconds')
    save_results(data)
    return jsonify({'ok': True, 'id': r['id']})
CAM = 'http://127.0.0.1:5000'

@app.route('/cam')
def cam():
    return ('<html><body style="margin:0;background:#000">'
            '<img src="/cam_feed" style="width:100%;height:100%;object-fit:cover">'
            '</body></html>')

@app.route('/cam_feed')
def cam_feed():
    def gen():
        with requests.get(CAM + '/video_feed', stream=True, timeout=10) as r:
            for chunk in r.iter_content(chunk_size=4096):
                yield chunk
    return Response(stream_with_context(gen()),
                    content_type='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Port 8080 — 5000 is already used by your camera stream
    app.run(host='0.0.0.0', port=8080, threaded=True)
