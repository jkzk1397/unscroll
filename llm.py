# -*- coding: utf-8 -*-
"""AI 호출 모음. 키는 코드에 쓰지 않고 .env 파일이나 환경변수에서 읽는다."""
import os, json, re, time
from pathlib import Path
import requests

BASE = Path(__file__).parent

def load_env():
    p = BASE / '.env'
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()

PROVIDERS = {
    'mock':      {'이름': '모의 AI (키 없이 화면 흐름 확인용)', 'key': None, 'model': '-'},
    'gemini':    {'이름': 'Google Gemini', 'key': 'GEMINI_API_KEY', 'model': os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')},
    'openai':    {'이름': 'OpenAI', 'key': 'OPENAI_API_KEY', 'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini')},
    'anthropic': {'이름': 'Anthropic Claude', 'key': 'ANTHROPIC_API_KEY', 'model': os.getenv('ANTHROPIC_MODEL', 'claude-haiku-4-5')},
}

def has_key(provider):
    k = PROVIDERS[provider]['key']
    return k is None or bool(os.getenv(k))

def ask(provider, prompt, model=None, timeout=40):
    """프롬프트를 보내고 (답 글자, 걸린 초)를 돌려준다."""
    model = model or PROVIDERS[provider]['model']
    t0 = time.time()
    if provider == 'gemini':
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        r = requests.post(url, params={'key': os.getenv('GEMINI_API_KEY')}, timeout=timeout, json={
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.3}})
        r.raise_for_status()
        text = r.json()['candidates'][0]['content']['parts'][0]['text']
    elif provider == 'openai':
        r = requests.post('https://api.openai.com/v1/chat/completions', timeout=timeout,
                          headers={'Authorization': f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                          json={'model': model, 'temperature': 0.3, 'response_format': {'type': 'json_object'},
                                'messages': [{'role': 'user', 'content': prompt}]})
        r.raise_for_status()
        text = r.json()['choices'][0]['message']['content']
    elif provider == 'anthropic':
        r = requests.post('https://api.anthropic.com/v1/messages', timeout=timeout,
                          headers={'x-api-key': os.getenv('ANTHROPIC_API_KEY'), 'anthropic-version': '2023-06-01'},
                          json={'model': model, 'max_tokens': 1024, 'temperature': 0.3,
                                'messages': [{'role': 'user', 'content': prompt}]})
        r.raise_for_status()
        text = r.json()['content'][0]['text']
    else:
        raise ValueError('mock은 core.py에서 처리')
    return text, round(time.time() - t0, 1)

def parse_json(text):
    """답에서 JSON 부분만 꺼낸다. 앞뒤에 다른 말이 붙어도 괜찮게."""
    m = re.search(r'\{.*\}', text, re.S)
    if not m:
        raise ValueError('JSON을 찾지 못함')
    return json.loads(m.group(0))
