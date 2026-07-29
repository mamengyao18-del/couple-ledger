from flask import Flask, request, jsonify
import json, os, base64, re, requests

app = Flask(__name__)

GH_TOKEN = os.environ.get('GH_TOKEN', '')
REPO = os.environ.get('GH_REPO', 'mamengyao18-del/couple-ledger')
DATA_DIR = 'data'

def default_data():
    return {'cou_tx':[],'cou_rules':[],'cou_fixed':[],'cou_alerts':{'balance_threshold':3000,'ratio_threshold':0.8},'cou_accounts':{'pool':0,'fund':0,'stock':0},'cou_cats':[],'cou_goal':5000,'cou_seen':True}

def gh_path(room):
    safe = ''.join(c for c in room if c.isalnum() or c in '-_')[:40] or 'default'
    return f"{DATA_DIR}/{safe}.json"

def cors_headers(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp

def load_room(room):
    path = gh_path(room)
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            d = r.json()
            content = base64.b64decode(d['content']).decode('utf-8')
            return json.loads(content), d.get('sha')
    except Exception:
        pass
    return None, None

def save_room(room, data, sha=None):
    path = gh_path(room)
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}
    payload = {
        "message": f"update {path}",
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('utf-8')
    }
    if sha:
        payload["sha"] = sha
    try:
        r = requests.put(url, headers=headers, json=payload, timeout=8)
        return r.status_code in (200, 201)
    except Exception:
        return False

@app.route('/api/room/<room>', methods=['GET', 'POST', 'PUT', 'OPTIONS'])
@app.route('/api/room/<room>/<key>', methods=['GET', 'POST', 'PUT', 'OPTIONS'])
def room_handler(room, key=None):
    if request.method == 'OPTIONS':
        resp = jsonify({})
        return cors_headers(resp), 204

    if request.method == 'GET':
        data, _ = load_room(room)
        if data is None:
            data = default_data()
            save_room(room, data)
        resp = jsonify({key: data.get(key)} if key else data)
        return cors_headers(resp), 200

    if request.method in ('POST', 'PUT'):
        try:
            body = request.get_json(silent=True) or {}
        except Exception:
            body = {}
        data, sha = load_room(room)
        if data is None:
            data = default_data()
        if key:
            data[key] = body.get(key, body)
        else:
            for k, v in body.items():
                data[k] = v
        save_room(room, data, sha)
        resp = jsonify(data)
        return cors_headers(resp), 200

    resp = jsonify({"error": "method not allowed"})
    return cors_headers(resp), 405
