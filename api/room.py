import json, os, re, requests

UP_URL = os.environ.get('UPSTASH_REDIS_REST_URL','')
UP_TOKEN = os.environ.get('UPSTASH_REDIS_REST_TOKEN','')

def redis_get(key):
    if not UP_URL or not UP_TOKEN:
        return None
    try:
        r = requests.get(f"{UP_URL}/get/{key}", headers={"Authorization": f"Bearer {UP_TOKEN}"}, timeout=5)
        data = r.json()
        if data.get('result'):
            return json.loads(data['result'])
    except Exception:
        pass
    return None

def redis_set(key, value):
    if not UP_URL or not UP_TOKEN:
        return
    try:
        payload = {"value": json.dumps(value, ensure_ascii=False)}
        requests.post(f"{UP_URL}/set/{key}", headers={"Authorization": f"Bearer {UP_TOKEN}", "Content-Type": "application/json"}, json=payload, timeout=5)
    except Exception:
        pass

def default_data():
    return {'tx':[],'rules':[],'fixed':[],'alerts':{'balance_threshold':3000,'ratio_threshold':0.8},'accts':{'pool':0,'fund':0,'stock':0},'cats':[],'goal':5000,'seen':True}

def load_room(room):
    safe = re.sub(r'[^a-zA-Z0-9_-]', '', room)[:40] or 'default'
    data = redis_get(f"room:{safe}")
    if data is None:
        data = default_data()
        redis_set(f"room:{safe}", data)
    return data

def save_room(room, data):
    safe = re.sub(r'[^a-zA-Z0-9_-]', '', room)[:40] or 'default'
    redis_set(f"room:{safe}", data)

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
        data = load_room(room)
        return json_resp(200, {key: data.get(key)} if key else data)

    if method in ('POST', 'PUT'):
        try:
            body = json.loads(request.get('body') or '{}')
        except Exception:
            body = {}
        data = load_room(room)
        if key:
            data[key] = body.get(key, body)
        else:
            for k, v in body.items():
                data[k] = v
        save_room(room, data)
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
