# -*- coding: utf-8 -*-
"""시연용 가상 스크린타임. 실제 앱에서는 안드로이드 사용 기록(UsageStatsManager)이 이 자리에 들어온다.
세션 길이 비율은 LSApp 공개 데이터 분석 결과를 따름: 1분 미만 30%, 1~10분 50%, 10~30분 17%, 30분 이상 3%."""
import random
from datetime import date, timedelta

DAYNAMES = '월화수목금토일'
APPS = {   # short = 릴스·쇼츠 같은 숏폼
    '인스타그램 릴스': 'short', '유튜브 쇼츠': 'short', '틱톡': 'short', '유튜브': 'video', '인스타그램': 'feed',
    '카카오톡': 'chat', '에브리타임': 'feed', '네이버웹툰': 'video', '크롬': 'tool', '노션': 'tool',
}
SHORT = [a for a, k in APPS.items() if k == 'short']
PERSONAS = {
    '과제가 막히면 폰을 여는 학생': {
        'peak': [14, 15, 16, 22, 23, 0], 'regret': ['과제 막혀서', '레포트 쓰기 싫어서', '시험공부 하다가', '과제하다 지쳐서', '하나만 보려다가'],
        'ok': ['강의 복습', '친구랑 연락', '좋아하는 영상'], 'feed_bias': 0.6},
    '잠들기 전에 오래 보는 학생': {
        'peak': [23, 0, 1, 2], 'regret': ['잠이 안 와서', '자려다가 계속 봄', '누워서 쇼츠 넘기다', '잠 안 옴'],
        'ok': ['노래 들으면서', '친구 스토리', '웹툰 한 편'], 'feed_bias': 0.7},
    '알림에 바로 반응하는 학생': {
        'peak': [10, 13, 18, 21], 'regret': ['단톡 알림', '답장하다가', '알림 보고', '릴스 공유받아서'],
        'ok': ['과제 연락', '가족 연락', '약속 잡기'], 'feed_bias': 0.4},
}

def _length(rng):
    r = rng.random()
    if r < 0.30: return rng.randint(0, 0) + rng.random()        # 1분 미만
    if r < 0.80: return rng.uniform(1, 10)
    if r < 0.97: return rng.uniform(10, 30)
    return rng.uniform(30, 75)

def hour_label(h):
    return '새벽' if h < 6 else '오전' if h < 12 else '오후' if h < 18 else '저녁' if h < 22 else '밤'

def generate(persona='과제가 막히면 폰을 여는 학생', seed=7, today=None):
    rng = random.Random(seed)
    P = PERSONAS[persona]
    today = today or date.today()
    days = []
    sid = 0
    for back in range(6, -1, -1):
        d = today - timedelta(days=back)
        sessions, total, short, pickups = [], 0.0, 0.0, rng.randint(20, 30)
        for _ in range(pickups):
            m = _length(rng)
            h = rng.choice(P['peak']) if rng.random() < 0.45 else rng.randint(8, 23)
            long_ = m >= 10
            if long_:
                app = rng.choice(SHORT) if rng.random() < P['feed_bias'] + 0.15 else rng.choice(list(APPS))
            else:
                app = rng.choice(list(APPS))
            total += m
            if APPS[app] == 'short': short += m
            if not long_:
                continue
            sid += 1
            regret = (h in P['peak'] and APPS[app] in ('short', 'feed', 'video') and rng.random() < 0.65) or rng.random() < 0.12
            mm = rng.randint(0, 59)
            s = {'id': sid, '앱': app, '시': h, '분시각': mm, '시작': f'{h:02d}:{mm:02d}', '분': int(round(m)),
                 '시간대': hour_label(h), '평가': '', '이유': ''}
            if back > 0:                                   # 지난 6일은 이미 돌아본 것으로
                s['평가'] = '후회' if regret else rng.choice(['만족', '만족', '보통'])
                s['이유'] = rng.choice(P['regret']) if regret else (rng.choice(P['ok']) if rng.random() < 0.5 else '')
            sessions.append(s)
        sessions.sort(key=lambda s: ((s['시'] - 6) % 24, s['분시각']))
        end = -1                                           # 겹치는 세션은 앞 세션이 끝난 뒤로 민다
        for s in sessions:
            t = ((s['시'] - 6) % 24) * 60 + s['분시각']
            if t <= end:
                t = min(end + rng.randint(3, 20), 24 * 60 - 1)
                h = (t // 60 + 6) % 24
                s.update({'시': h, '분시각': t % 60, '시작': f'{h:02d}:{t % 60:02d}', '시간대': hour_label(h)})
            end = t + s['분']
        days.append({'날짜': d.isoformat(), '요일': DAYNAMES[d.weekday()], '오늘': back == 0,
                     '총분': int(total), '숏폼분': int(short), '켠 횟수': pickups, '세션': sessions})
    last_week = sum(1 for d in days for s in d['세션'] if s['평가'] == '후회') + rng.randint(1, 3)
    return {'페르소나': persona, '날들': days, '지난주 후회': last_week}

if __name__ == '__main__':
    import json
    g = generate()
    for d in g['날들']:
        print(d['요일'], d['총분'], '분', len(d['세션']), [ (s['시작'], s['앱'], s['분'], s['평가']) for s in d['세션']])
    print(g['지난주 후회'])
