"""V0.3 端到端实测脚本（GBK-safe）。"""
import urllib.request, json, urllib.error
import subprocess, time, os
from pathlib import Path

BASE = 'http://localhost:8765'
PROJECT_ROOT = Path(r'D:\ZYY Project\Evalution price agent')

# 用 psutil 杀旧 server
try:
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if p.info['name'] and 'python' in p.info['name'].lower():
                cmdline = ' '.join(p.cmdline())
                if 'uvicorn' in cmdline and 'backend.app' in cmdline:
                    print(f'killing pid={p.info["pid"]}')
                    p.kill()
        except: pass
except ImportError:
    os.system('taskkill /F /IM python.exe /FI "WINDOWTITLE eq uvicorn*" 2>nul')

time.sleep(2)

# 启动新 server
proc = subprocess.Popen(
    ['powershell', '-Command', 'C:/python实验/python.exe -X utf8 -m uvicorn backend.app:app --port 8765 --log-level error'],
    cwd=str(PROJECT_ROOT),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f'started pid={proc.pid}')
time.sleep(8)

try:
    # 1. V0.3 新格式
    print('\n=== 1. V0.3 新格式请求 ===')
    req = urllib.request.Request(f'{BASE}/api/compare', method='POST',
        data=json.dumps({'items': [{
            'name': '奥利奥薄脆 420g', 'final_price': 19.9, 'total_weight_g': 420,
            'flavor_type': 'fixed', 'flavor_name': '原味', 'expiry_date': '2026-09-01',
            'channel': 'tmall', 'category': 'cookie', 'brand': '奥利奥',
            'estimated_delivery_days': 3
        }], 'save': False}).encode(),
        headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    r = res['results'][0]
    print(f"  name: {r['name']}")
    print(f"  label: {r['recommendation_label']}")
    print(f"  reason: {r['reason']}")
    print(f"  4 score: price={r['price_score']} expiry={r['expiry_score']} pref={r['preference_score']} trust={r['trust_score']}")
    print(f"  final_score: {r['final_score']}")
    print(f"  real_value: {r['real_value_price_per_g']}")
    print(f"  price_100g: {r['price_per_100g']}")
    print(f"  usable_days: {r['usable_days_until_expiry']}")
    print(f"  required_daily: {r['required_daily_intake_g']}g/day")
    print(f"  missing: {r['missing_fields']}")

    # 2. 老 total_price 兼容
    print('\n=== 2. 老 total_price 格式 ===')
    req = urllib.request.Request(f'{BASE}/api/compare', method='POST',
        data=json.dumps({'items': [{
            'name': '老格式薯片', 'total_price': 9.9, 'total_weight_g': 100
        }], 'save': False}).encode(),
        headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    r = res['results'][0]
    print(f"  name: {r['name']} | price_per_g: {r['price_per_g']}")

    # 3. extract_text
    print('\n=== 3. extract_text ===')
    req = urllib.request.Request(f'{BASE}/api/extract_text', method='POST',
        data=json.dumps({'text': '奥利奥薄脆 到手价19.9元 净含量84g×5袋 保质期至2026.09.01 固定口味草莓味 袋装'}).encode(),
        headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    for k, v in res.items():
        if isinstance(v, dict) and v.get('value'):
            print(f"  {k}: {v['value']} ({v['confidence']})")

    # 4. baseline
    print('\n=== 4. baseline + history ===')
    base = json.loads(urllib.request.urlopen(f'{BASE}/api/baseline').read())
    print(f"  baseline: {base}")
    hist = json.loads(urllib.request.urlopen(f'{BASE}/api/history').read())
    print(f"  history: {len(hist)} 条")

    print('\n[OK] V0.3 端到端实测通过')
finally:
    proc.terminate()
    try: proc.wait(timeout=5)
    except: proc.kill()
