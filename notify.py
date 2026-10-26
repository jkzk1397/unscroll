# -*- coding: utf-8 -*-
"""통계 기반 알림 만들기 (규칙). 폰을 켤 때마다가 아니라, 사용자가 정한 시간에만 보낸다.
숫자는 코드가 계산하고, 문구는 혼내지 않고 사실과 응원만 담는다."""
DAYS = list('월화수목금토일')
MAX_PER_DAY = 2

def week_summary(regret_this, regret_last, goal):
    diff = regret_last - regret_this
    if regret_last == 0:
        trend = f'이번 주 후회한 사용은 {regret_this}번이었어요.'
    elif diff > 0:
        trend = f'이번 주 후회한 사용 {regret_this}번, 지난주보다 {diff}번 줄었어요.'
    elif diff < 0:
        trend = f'이번 주 후회한 사용 {regret_this}번, 지난주보다 {-diff}번 많았어요. 같이 이유를 볼까요?'
    else:
        trend = f'이번 주 후회한 사용 {regret_this}번, 지난주와 같아요.'
    goal_txt = f' 목표({goal}번 이하)를 지켰어요!' if regret_this <= goal else ''
    return trend + goal_txt

def build_schedule(settings, state):
    """settings: 사용자가 정한 알림 설정 / state: 현재 기록 상태.
    돌려주는 값: 다음 7일 동안의 알림 목록 [(요일, 시각, 종류, 문구)]"""
    out = []
    streak = state['연속일']
    for i, day in enumerate(DAYS):
        today = []
        if settings['돌아보기 알림'] and day in settings['요일']:
            s = streak + i
            msg = f'{s}일째 돌아보고 있어요. 오늘도 1분만 돌아볼까요?' if s >= 2 else '오늘 쓴 앱, 1분만 돌아볼까요?'
            today.append((day, settings['돌아보기 시각'], '오늘 돌아보기', msg))
        if settings['계획 알림'] and state.get('계획') and day in settings['요일']:
            kept = state['계획 지킴']
            tail = ' 어제는 지켰어요!' if kept.get('어제') else ''
            today.append((day, settings['계획 시각'], '내 계획', f"오늘 계획: {state['계획']}.{tail}"))
        if settings['주간 성찰 알림'] and day == '일':
            today.append((day, '20:00', '주간 성찰',
                          week_summary(state['이번 주 후회'], state['지난주 후회'], settings['목표'])))
        out += today[:MAX_PER_DAY]          # 하루 최대 2개
    return out
