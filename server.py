# -*- coding: utf-8 -*-
"""언스크롤 시연 서버. 화면(static/index.html)과 AI 처리(core.py)를 잇는다.
실행: python server.py  →  http://localhost:8000  (같은 와이파이의 휴대폰에서는 http://<노트북IP>:8000)"""
import os
from flask import Flask, jsonify, request, send_from_directory
import core, llm, sim

app = Flask(__name__, static_folder='static')

@app.get('/')
def index():
    return send_from_directory('static', 'index.html')

@app.get('/api/config')
def config():
    return jsonify({'providers': [{'id': k, 'name': v['이름'], 'ready': llm.has_key(k)} for k, v in llm.PROVIDERS.items()],
                    'personas': list(sim.PERSONAS), 'prompt': core.PROMPT_VERSION})

@app.get('/api/screentime')
def screentime():
    """가상 스크린타임. 실제 앱에서는 안드로이드 사용 기록을 읽는 자리."""
    persona = request.args.get('persona', list(sim.PERSONAS)[0])
    seed = int(request.args.get('seed', 7))
    return jsonify(sim.generate(persona, seed))

@app.post('/api/reflect')
def reflect():
    body = request.get_json(force=True)
    rows = [{'요일': s['요일'], '시간대': s['시간대'], '앱': s['앱'], '분': s['분'],
             '평가': s.get('평가') or '보통', '이유': s.get('이유', '')} for s in body.get('sessions', [])]
    R = core.reflect(rows, body.get('provider', 'mock'), body.get('model'))
    R['분류'] = {str(k): v for k, v in R.get('분류', {}).items()}
    return jsonify(R)

@app.post('/api/plans')
def plans():
    body = request.get_json(force=True)
    plans, log = core.make_plans(body['trigger'], body.get('records', []), body.get('provider', 'mock'), body.get('model'))
    return jsonify({'plans': plans, 'log': log})

@app.post('/api/llm')
def llm_call():
    """화면에서 만든 프롬프트를 .env의 AI에 그대로 보내고 답 글자를 돌려준다. 답 확인은 화면 쪽 코드가 한다."""
    body = request.get_json(force=True)
    provider = body.get('provider', 'mock')
    if provider == 'mock' or not llm.has_key(provider):
        return jsonify({'error': 'AI 키가 없어요'}), 400
    try:
        text, sec = llm.ask(provider, body['prompt'][:6000], body.get('model'))
        return jsonify({'text': text, 'sec': sec})
    except Exception as e:
        return jsonify({'error': str(e)}), 502

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    print(f'언스크롤 시연 서버: http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
