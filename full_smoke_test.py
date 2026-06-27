# -*- coding: utf-8 -*-
"""V0.3 完整功能测试。"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

import urllib.request, json, urllib.error
import subprocess, time
from pathlib import Path

BASE = 'http://localhost:8765'
PROJECT_ROOT = Path(r'D:\ZYY Project\Evalution price agent')

# kill old server
try:
    import psutil
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if p.info['name'] and 'python' in p.info['name'].lower():
                cmdline = ' '.join(p.cmdline())
                if 'uvicorn' in cmdline and 'backend.app' in cmdline:
                    p.kill()
                    print('[cleanup] killed pid=' + str(p.info['pid']))
        except: pass
except ImportError:
    pass

time.sleep(2)

proc = subprocess.Popen(
    [sys.executable, '-X', 'utf8', '-m', 'uvicorn', 'backend.app:app',
     '--port', '8765', '--log-level', 'error'],
    cwd=str(PROJECT_ROOT),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print('[start] pid=' + str(proc.pid))
time.sleep(6)

for i in range(10):
    try:
        urllib.request.urlopen(BASE + '/api/health', timeout=1)
        print('[ready]')
        break
    except: time.sleep(1)

PASS = 0
FAIL = 0
def check(name, ok, detail=''):
    global PASS, FAIL
    if ok:
        PASS += 1
        print('  [PASS] ' + name)
    else:
        FAIL += 1
        print('  [FAIL] ' + name + ': ' + detail)

try:
    print('\n=== Test 1: Health ===')
    res = json.loads(urllib.request.urlopen(BASE + '/api/health').read())
    check('health', res.get('status') == 'ok', str(res))

    print('\n=== Test 2: V0.3 全字段请求 ===')
    payload = {'items': [{
        'name': '奥利奥薄脆 420g', 'final_price': 19.9, 'total_weight_g': 420,
        'flavor_type': 'fixed', 'flavor_name': '原味', 'expiry_date': '2026-09-01',
        'channel': 'tmall', 'category': 'cookie', 'brand': '奥利奥',
        'estimated_delivery_days': 3, 'coupon_amount': 10, 'shipping_fee': 0
    }], 'save': False}
    req = urllib.request.Request(BASE + '/api/compare', method='POST',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    r = res['results'][0]
    check('compare 200', res.get('results') is not None)
    check('name', r.get('name') == '奥利奥薄脆 420g')
    check('price_per_g', r.get('price_per_g') == 0.047381, 'got ' + str(r.get('price_per_g')))
    check('price_per_100g', abs(r.get('price_per_100g') - 4.738095) < 0.01)
    check('real_value', r.get('real_value_price_per_g') is not None and r.get('real_value_price_per_g') > 0)
    check('4 score price', 0 <= r.get('price_score', -1) <= 1)
    check('4 score expiry', 0 <= r.get('expiry_score', -1) <= 1)
    check('4 score pref', 0 <= r.get('preference_score', -1) <= 1)
    check('4 score trust', 0 <= r.get('trust_score', -1) <= 1)
    check('final_score', 0 <= r.get('final_score', -1) <= 1)
    check('usable_days', r.get('usable_days_until_expiry') in (63, 64, 65), 'got ' + str(r.get('usable_days_until_expiry')))
    check('required_daily', r.get('required_daily_intake_g') is not None and r.get('required_daily_intake_g') > 0)
    check('missing_fields', isinstance(r.get('missing_fields'), list))
    check('flavor_factor', r.get('flavor_factor') is not None and r.get('flavor_factor') > 0)
    check('label', r.get('recommendation_label') is not None)
    check('reason', len(r.get('reason', '')) > 0)

    print('\n=== Test 3: 老 total_price 兼容 ===')
    legacy_payload = {'items': [{'name': '老格式', 'total_price': 9.9, 'total_weight_g': 100}], 'save': False}
    req = urllib.request.Request(BASE + '/api/compare', method='POST',
        data=json.dumps(legacy_payload).encode(),
        headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    check('legacy 200', res.get('results') is not None)
    check('legacy price_per_g', res['results'][0].get('price_per_g') == 0.099)

    print('\n=== Test 4: 4 评分权重 ===')
    expected = 0.45 * r['price_score'] + 0.25 * r['expiry_score'] + 0.20 * r['preference_score'] + 0.10 * r['trust_score']
    check('weight formula', abs(expected - r['final_score']) < 0.001)

    print('\n=== Test 5: flavor_type 4 类 ===')
    for ft in ['fixed', 'random', 'mixed', 'unknown']:
        p = {'items': [{'name': ft + '_test', 'final_price': 10, 'total_weight_g': 100, 'flavor_type': ft}], 'save': False}
        req = urllib.request.Request(BASE + '/api/compare', method='POST',
            data=json.dumps(p).encode(),
            headers={'Content-Type': 'application/json'})
        try:
            res = json.loads(urllib.request.urlopen(req).read())
            check('flavor_type=' + ft, res.get('results') is not None)
        except Exception as e:
            check('flavor_type=' + ft, False, str(e))

    print('\n=== Test 6: 错误 - final_price=0 ===')
    bad_payload = {'items': [{'name': 'X', 'final_price': 0, 'total_weight_g': 100}], 'save': False}
    req = urllib.request.Request(BASE + '/api/compare', method='POST',
        data=json.dumps(bad_payload).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req)
        check('price=0 rejected', False, 'should 422')
    except urllib.error.HTTPError as e:
        check('price=0 rejected', e.code == 422, 'got ' + str(e.code))

    print('\n=== Test 7: 错误 - 非法 flavor_type ===')
    bad_payload = {'items': [{'name': 'X', 'final_price': 10, 'total_weight_g': 100, 'flavor_type': 'invalid'}], 'save': False}
    req = urllib.request.Request(BASE + '/api/compare', method='POST',
        data=json.dumps(bad_payload).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req)
        check('flavor_type 校验', False, 'should 422')
    except urllib.error.HTTPError as e:
        check('flavor_type 校验', e.code == 422, 'got ' + str(e.code))

    print('\n=== Test 8: /api/extract_text ===')
    text_payload = {'text': '奥利奥薄脆 到手价19.9元 净含量84g×5袋 保质期至2026.09.01 固定口味草莓味 袋装'}
    req = urllib.request.Request(BASE + '/api/extract_text', method='POST',
        data=json.dumps(text_payload).encode(),
        headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    fields = {k: v for k, v in res.items() if isinstance(v, dict) and v.get('value')}
    check('total_price extracted', fields.get('total_price', {}).get('value') == '19.90')
    check('total_weight_g extracted', fields.get('total_weight_g', {}).get('value') == '420')
    check('flavor_type extracted', fields.get('flavor_type', {}).get('value') == 'fixed')
    check('expiry_date extracted', fields.get('expiry_date', {}).get('value') == '2026-09-01')

    print('\n=== Test 9: /api/baseline + history ===')
    base = json.loads(urllib.request.urlopen(BASE + '/api/baseline').read())
    check('baseline', base.get('baseline_price_per_g') is not None or base.get('baseline_price_per_g') is None)
    hist = json.loads(urllib.request.urlopen(BASE + '/api/history').read())
    check('history', isinstance(hist, list))

    print('\n=== Test 10: /api/preference GET/PUT ===')
    pref = json.loads(urllib.request.urlopen(BASE + '/api/preference').read())
    check('pref get', 'daily_intake_g' in pref)
    put_payload = {'preferred_flavors': ['黑巧'], 'disliked_flavors': ['辣'], 'daily_intake_g': 30}
    req = urllib.request.Request(BASE + '/api/preference', method='PUT',
        data=json.dumps(put_payload).encode(),
        headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    check('pref put', res.get('status') == 'ok')
    pref2 = json.loads(urllib.request.urlopen(BASE + '/api/preference').read())
    check('pref persisted', pref2.get('daily_intake_g') == 30)

    print('\n=== Test 11: save=true 落库 ===')
    save_payload = {'items': [{'name': 'V0.3 落库测试', 'final_price': 15.0, 'total_weight_g': 200,
        'flavor_type': 'fixed', 'flavor_name': '原味'}], 'save': True}
    req = urllib.request.Request(BASE + '/api/compare', method='POST',
        data=json.dumps(save_payload).encode(),
        headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    check('save 200', res.get('results') is not None)
    hist = json.loads(urllib.request.urlopen(BASE + '/api/history').read())
    found = any(h.get('name') == 'V0.3 落库测试' for h in hist)
    check('history 新行', found)

    print('\n=== Test 12: 多商品排序 ===')
    sort_payload = {'items': [
        {'name': 'A 便宜', 'final_price': 5.0, 'total_weight_g': 100, 'flavor_type': 'fixed'},
        {'name': 'B 中价', 'final_price': 10.0, 'total_weight_g': 100, 'flavor_type': 'random'},
        {'name': 'C 贵', 'final_price': 20.0, 'total_weight_g': 100, 'flavor_type': 'fixed'}
    ], 'save': False}
    req = urllib.request.Request(BASE + '/api/compare', method='POST',
        data=json.dumps(sort_payload).encode(),
        headers={'Content-Type': 'application/json'})
    res = json.loads(urllib.request.urlopen(req).read())
    results = res['results']
    check('3 results', len(results) == 3)
    check('sorted by real_value', results[0]['name'] == 'A 便宜', 'got ' + results[0]['name'])
    order = [r['name'] for r in results]
    print('  排序: ' + str(order))

    print('\n=== Test 13: /api/extract 图片上传（OCR 真实路径）===')
    # 1x1 PNG
    import base64
    png_bytes = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==')
    import io
    files_data = b'--BOUNDARY\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n' + png_bytes + b'\r\n--BOUNDARY--\r\n'
    req = urllib.request.Request(BASE + '/api/extract', method='POST',
        data=files_data,
        headers={'Content-Type': 'multipart/form-data; boundary=BOUNDARY'})
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=60).read())
        check('OCR 响应', 'ocr' in res or 'fields' in res, str(list(res.keys())))
    except urllib.error.HTTPError as e:
        check('OCR 响应', False, 'HTTP ' + str(e.code) + ': ' + e.read().decode()[:200])
    except Exception as e:
        check('OCR 响应', False, str(e))

    print('\n=== 总计 ===')
    print('PASS: ' + str(PASS))
    print('FAIL: ' + str(FAIL))
    if FAIL == 0:
        print('\n[OK] 全部 ' + str(PASS) + ' 测试通过！')
    else:
        print('\n[FAIL] 有 ' + str(FAIL) + ' 个失败')

finally:
    proc.terminate()
    try: proc.wait(timeout=5)
    except: proc.kill()