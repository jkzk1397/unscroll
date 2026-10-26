# -*- coding: utf-8 -*-
"""Processing: 기록 정리 → 걸러내기 → AI 호출 → 결과 확인(검증) → 화면에 줄 결과."""
import json, re, time
from collections import Counter
from pathlib import Path
import llm

BASE = Path(__file__).parent
CATS = ['과제·공부 피하기', '심심함', '습관적 확인', '잠이 안 옴', '연락·알림', '기타']
REFLECT_PROMPT = (BASE / 'prompts/reflect_v1.txt').read_text(encoding='utf-8')
PLAN_PROMPT = (BASE / 'prompts/plan_v1.txt').read_text(encoding='utf-8')
METHODS = json.loads((BASE / 'data/methods.json').read_text(encoding='utf-8'))
PROMPT_VERSION = 'reflect_v1 / plan_v1'

# 힘든 감정 표현: 이 단어가 있으면 AI에 보내지 않는다 (목록은 팀이 관리)
CRISIS_WORDS = ['죽고', '죽을', '자해', '살기 싫', '사라지고', '우울해', '다 싫어', '버티기 힘들']
BANNED = ['중독', '우울증', '장애', '한심', '문제가 있', '그만 좀']

# ---------- 입력 정리 ----------
def clean_reason(text):
    t = (text or '').strip()
    t = re.sub(r'\b\d{2,3}[- ]?\d{3,4}[- ]?\d{4}\b', '[번호]', t)          # 전화번호 가리기
    t = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '[메일]', t)                    # 이메일 가리기
    return t[:20]                                                          # 20자 제한

def is_crisis(text):
    return any(w in (text or '') for w in CRISIS_WORDS)

def regretted(rows):
    """평가가 '후회'인 기록만 골라 번호를 붙인다. 평가 칸이 없으면(시험용) 모두 후회로 본다."""
    out = []
    for r in rows:
        if r.get('평가', '후회') != '후회':
            continue
        out.append({**r, '이유': clean_reason(r.get('이유', ''))})
    for i, r in enumerate(out, 1):
        r['번호'] = i
    return out

def records_text(recs):
    return '\n'.join(f"{r['번호']}. {r['요일']}요일 {r['시간대']}, {r['앱']} {r['분']}분, 이유: {r['이유'] or '(없음)'}" for r in recs)

def stats(rows, recs):
    """숫자는 AI가 아니라 코드가 계산한다."""
    return {'전체': len(rows), '후회': len(recs),
            '앱별': Counter(r['앱'] for r in recs).most_common(),
            '시간대별': Counter(r['시간대'] for r in recs).most_common()}

# ---------- 모의 AI (키 없이 흐름 확인용) ----------
MOCK_RULES = [('과제·공부 피하기', ['과제', '레포트', '공부', '시험', '숙제', '막혀', '막힘']),
              ('잠이 안 옴', ['잠', '자려', '졸려']),
              ('연락·알림', ['알림', '단톡', '연락', '답장']),
              ('심심함', ['심심', '지루', '할 게 없', '할 거 없']),
              ('습관적 확인', ['그냥', '습관', '무심코', '스토리', '하나만', '넘기다'])]

MOCK_SENT = {   # 모의 AI가 쓰는 문장 (추측, 확인 질문)
    '과제·공부 피하기': ('과제나 공부가 막힐 때 숏폼을 여신 걸까요?', '이번 주에는 과제가 막힐 때 폰을 오래 본 것 같은데, 맞나요?'),
    '잠이 안 옴': ('잠이 안 올 때 숏폼을 오래 보신 걸까요?', '이번 주에는 잠이 안 올 때 폰을 오래 본 것 같은데, 맞나요?'),
    '연락·알림': ('알림을 보고 들어갔다가 길어진 걸까요?', '이번 주에는 알림을 보고 들어갔다가 길어진 것 같은데, 맞나요?'),
    '심심함': ('할 게 없을 때 숏폼으로 시간을 채우신 걸까요?', '이번 주에는 심심할 때 폰을 오래 본 것 같은데, 맞나요?'),
    '습관적 확인': ('특별한 이유 없이 습관처럼 여신 걸까요?', '이번 주에는 습관처럼 폰을 연 때가 많았던 것 같은데, 맞나요?'),
}

def mock_reflect(recs):
    cls = []
    for r in recs:
        cat = next((c for c, ws in MOCK_RULES if any(w in r['이유'] for w in ws)), '기타')
        cls.append({'번호': r['번호'], '계기': cat})
    cnt = Counter(c['계기'] for c in cls if c['계기'] != '기타')
    guesses = [{'계기': c, '근거': [x['번호'] for x in cls if x['계기'] == c],
                '문장': MOCK_SENT[c][0]} for c, n in cnt.most_common(2) if n >= 3]
    q = MOCK_SENT[guesses[0]['계기']][1] if guesses else ''
    return json.dumps({'분류': cls, '추측': guesses, '질문': q}, ensure_ascii=False)

def mock_plan(trigger):
    pick = {'과제·공부 피하기': [1, 2, 6], '잠이 안 옴': [3, 4, 10], '연락·알림': [7, 8, 6],
            '심심함': [9, 6, 5], '습관적 확인': [5, 6, 7]}.get(trigger, [6, 1, 9])
    return json.dumps({'계획': [{'방법': n, '문장': METHODS[n - 1]['방법']} for n in pick]}, ensure_ascii=False)

# ---------- 결과 확인(검증) ----------
def has_bad_text(s):
    return bool(re.search(r'\d', s or '')) or any(b in (s or '') for b in BANNED)

def check_reflect(data, recs):
    """AI 답을 확인하고, 틀린 부분은 빼고, 무엇이 틀렸는지 기록한다."""
    problems = []
    ids = {r['번호'] for r in recs}
    cls = {}
    for c in data.get('분류', []):
        if c.get('번호') in ids and c.get('계기') in CATS:
            cls[c['번호']] = c['계기']
        else:
            problems.append(f"분류 형식 오류: {c}")
    if set(cls) != ids:
        problems.append('분류가 빠진 기록이 있음')
        return None, problems                          # 형식이 깨지면 다시 요청
    guesses = []
    for g in data.get('추측', []):
        if len(guesses) == 2:
            break
        ev = [n for n in g.get('근거', []) if n in ids]
        if g.get('계기') not in CATS or g.get('계기') == '기타':
            problems.append(f"추측 계기 오류: {g.get('계기')}"); continue
        if len(ev) != len(g.get('근거', [])):
            problems.append(f"없는 기록 번호를 근거로 씀: {g.get('근거')}"); continue
        if sum(1 for n in ev if cls[n] == g['계기']) < 3:
            problems.append(f"같은 계기가 3개 미만인데 추측함: {g['계기']}"); continue
        if has_bad_text(g.get('문장')):
            problems.append(f"추측 문장에 숫자나 금지 표현: {g.get('문장')}"); continue
        guesses.append({'계기': g['계기'], '근거': ev, '문장': g['문장']})
    q = data.get('질문', '') if guesses else ''
    if has_bad_text(q):
        problems.append(f"질문에 숫자나 금지 표현: {q}")
        q = f"이번 주 후회한 사용은 '{guesses[0]['계기']}'일 때가 많았던 것 같아요. 맞나요?" if guesses else ''
    return {'분류': cls, '추측': guesses, '질문': q}, problems

# ---------- 메인 처리 ----------
def reflect(rows, provider='mock', model=None):
    """rows: 하루 돌아보기에서 모은 기록 전체. 화면에 그릴 결과(dict)를 돌려준다."""
    log = {'프롬프트': PROMPT_VERSION, 'AI': provider, '시도': [], '걸러낸 기록': 0}
    recs = regretted(rows)
    crisis = [r for r in recs if is_crisis(r['이유'])]
    recs = [r for r in recs if not is_crisis(r['이유'])]
    for i, r in enumerate(recs, 1):
        r['번호'] = i
    log['걸러낸 기록'] = len(crisis)
    base = {'기록': recs, '통계': stats(rows, recs), '위기': bool(crisis), 'log': log}
    if not rows:
        return {**base, '상태': '빈 상태'}
    if len(recs) < 3:
        return {**base, '상태': '적음'}
    prompt = REFLECT_PROMPT.replace('{records}', records_text(recs))
    log['보낸 프롬프트'] = prompt
    for attempt in range(2):                           # 최대 2번 요청
        try:
            if provider == 'mock':
                text, sec = mock_reflect(recs), 0.0
            else:
                text, sec = llm.ask(provider, prompt, model)
            data = llm.parse_json(text)
            result, problems = check_reflect(data, recs)
            log['시도'].append({'답': text, '초': sec, '문제': problems})
            if result is not None:
                state = '보통' if result['추측'] else '판단 보류'
                return {**base, **result, '상태': state}
        except Exception as e:
            log['시도'].append({'답': '', '초': 0, '문제': [f'오류: {e}']})
    return {**base, '상태': '오류'}

def make_plans(trigger, recs, provider='mock', model=None):
    examples = ' / '.join(r['이유'] for r in recs if r['이유'])[:200]
    methods = '\n'.join(f"{m['번호']}. {m['방법']}" for m in METHODS)
    prompt = PLAN_PROMPT.replace('{trigger}', trigger).replace('{examples}', examples).replace('{methods}', methods)
    log = {'시도': []}
    for attempt in range(2):
        try:
            text, sec = (mock_plan(trigger), 0.0) if provider == 'mock' else llm.ask(provider, prompt, model)
            plans = [p for p in llm.parse_json(text).get('계획', [])
                     if p.get('방법') in range(1, len(METHODS) + 1) and p.get('문장') and not any(b in p['문장'] for b in BANNED)][:3]
            log['시도'].append({'답': text, '초': sec})
            if plans:
                return plans, log
        except Exception as e:
            log['시도'].append({'답': '', '초': 0, '오류': str(e)})
    return [{'방법': n, '문장': METHODS[n - 1]['방법']} for n in (6, 1, 9)], {**log, '기본 계획 사용': True}
