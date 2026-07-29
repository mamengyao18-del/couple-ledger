import json, os, base64, re, requests

GH_TOKEN = os.environ.get('GH_TOKEN', '')
REPO = os.environ.get('GH_REPO', 'mamengyao18-del/couple-ledger')
DATA_DIR = 'data'

def default_data():
    return {'tx':[],'rules':[],'fixed':[],'alerts':{'balance_threshold':3000,'ratio_threshold':0.8},'accts':{'pool':0,'fund':0,'stock':0},'cats':[],'goal':5000,'seen':True}

def gh_path(room):
    safe = ''.join(c for c in room if c.isalnum() or c in '-_')[:40] or 'default'
    return f"{DATA_DIR}/{safe}.json"

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

def handler(request):
    method = request.get('method', 'GET')
    path = request.get('path', '/')

    if method == 'OPTIONS':
        return {"statusCode": 204, "headers": cors_headers(), "body": ""}

    m = re.match(r'^/api/room/([^/]+)(?:/([^/]+))?$', path)
    if not m:
        return json_resp(404, {"error": "not found"})

    room = m.group(1)
    key = m.group(2)

    if method == 'GET':
        data, _ = load_room(room)
        if data is None:
            data = default_data()
            save_room(room, data)
        return json_resp(200, {key: data.get(key)} if key else data)

    if method in ('POST', 'PUT'):
        try:
            body = json.loads(request.get('body') or '{}')
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
        return json_resp(200, data)

    return json_resp(405, {"error": "method not allowed"})

def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

def json_resp(code, obj):
    headers = cors_headers()
    headers['Content-Type'] = 'application/json; charset=utf-8'
    return {"statusCode": code, "headers": headers, "body": json.dumps(obj, ensure_ascii=False)}
