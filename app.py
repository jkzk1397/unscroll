# -*- coding: utf-8 -*-
"""언스크롤 1차 프로토타입: 하루 돌아보기(Input) → 성찰(Processing) → 결과와 계획(Output)"""
import json
from pathlib import Path
import pandas as pd
import streamlit as st
import core, llm

BASE = Path(__file__).parent
SAMPLES = json.loads((BASE / 'data/samples.json').read_text(encoding='utf-8'))
st.set_page_config(page_title='언스크롤 1차 프로토타입', page_icon='🔁', layout='centered')
S = st.session_state
S.setdefault('step', 'input')

# ---------- 옆 메뉴: AI 선택 ----------
with st.sidebar:
    st.subheader('설정')
    names = {k: v['이름'] for k, v in llm.PROVIDERS.items()}
    provider = st.selectbox('AI', list(names), format_func=lambda k: names[k])
    model = st.text_input('모델 이름', llm.PROVIDERS[provider]['model'], disabled=provider == 'mock')
    if not llm.has_key(provider):
        st.error(f"{llm.PROVIDERS[provider]['key']}가 없어요. .env 파일에 넣어 주세요.")
    st.caption(f'프롬프트: {core.PROMPT_VERSION}')
    if st.button('처음으로'):
        S.clear(); st.rerun()

def go(step):
    S.step = step; st.rerun()

def show_stats(stt):
    c1, c2, c3 = st.columns(3)
    c1.metric('돌아본 사용', f"{stt['전체']}번")
    c2.metric('후회한 사용', f"{stt['후회']}번")
    c3.metric('가장 많은 앱', stt['앱별'][0][0] if stt['앱별'] else '-')

# ---------- ① Input: 하루 돌아보기 ----------
if S.step == 'input':
    st.title('오늘 돌아보기')
    st.caption('10분 넘게 쓴 사용 목록이에요. 만족/보통/후회를 고르고, 후회했다면 이유를 한마디 적어 주세요.')
    st.info('1차 프로토타입에서는 휴대폰 사용 기록 대신 예시 기록을 불러와요. (안드로이드 연동은 다음 단계)')
    pick = st.selectbox('예시 기록 불러오기', list(SAMPLES) + ['빈 기록'])
    if S.get('pick') != pick:
        S.pick = pick
        S.rows = pd.DataFrame(SAMPLES.get(pick, []), columns=['요일', '시간대', '앱', '분', '평가', '이유'])
    rows = st.data_editor(
        S.rows, num_rows='dynamic', use_container_width=True, hide_index=True,
        column_config={
            '요일': st.column_config.SelectboxColumn(options=list('월화수목금토일'), required=True),
            '시간대': st.column_config.SelectboxColumn(options=['새벽', '오전', '오후', '저녁', '밤'], required=True),
            '분': st.column_config.NumberColumn(min_value=10, max_value=600, step=1),
            '평가': st.column_config.SelectboxColumn(options=['만족', '보통', '후회'], required=True),
            '이유': st.column_config.TextColumn(max_chars=20, help='후회했을 때만, 20자 이내'),
        })
    if st.button('이번 주 돌아보기', type='primary'):
        data = rows.fillna('').to_dict('records')
        if not llm.has_key(provider):
            st.stop()
        with st.status('기록을 정리하고 있어요 (1/2)', expanded=False) as status:
            S.result = core.reflect(data, provider, model)
            status.update(label='같이 돌아볼 준비가 됐어요 (2/2)', state='complete')
        go('result')

# ---------- ② Output: 성찰 결과 (다섯 얼굴) ----------
elif S.step == 'result':
    R = S.result
    st.title('이번 주 돌아보기')
    if R['위기']:
        st.warning('힘든 일이 있으셨던 것 같아요. 그 기록은 AI에게 보내지 않았어요. '
                   '이야기할 곳이 필요하면 109(자살예방상담) 또는 학교 학생상담센터에 연락할 수 있어요.')
    if R['상태'] == '빈 상태':
        st.write('아직 돌아본 기록이 없어요.')
        if st.button('오늘 돌아보기 하러 가기'): go('input')
    elif R['상태'] == '적음':
        show_stats(R['통계'])
        st.write('이번 주는 후회 기록이 적어서 같이 돌아보기엔 일러요. 기록이 더 모이면 같이 돌아봐요.')
        if st.button('알림 시간 바꾸기 (다음 단계에서 구현)'): st.toast('1차 프로토타입에서는 아직 준비 중이에요')
    elif R['상태'] == '오류':
        st.error('지금은 돌아보기를 만들지 못했어요. 잠시 후 다시 시도해 주세요.')
        show_stats(R['통계'])
        if st.button('다시 시도'): go('input')
    else:
        show_stats(R['통계'])
        if R['상태'] == '보통':
            for g in R['추측']:
                with st.container(border=True):
                    st.markdown(f"**{g['문장']}**")
                    st.caption('근거가 된 기록')
                    for n in g['근거']:
                        r = R['기록'][n - 1]
                        st.write(f"· {r['요일']}요일 {r['시간대']}, {r['앱']} {r['분']}분 — \"{r['이유'] or '이유 없음'}\"")
            st.caption('AI가 기록을 보고 짐작한 내용이에요.')
            st.subheader(R['질문'])
            c1, c2 = st.columns(2)
            if c1.button('맞아요', type='primary', use_container_width=True):
                S.trigger = R['추측'][0]['계기']; go('plan')
            if c2.button('아니에요, 다른 이유예요', use_container_width=True):
                S.choose = True; st.rerun()
        else:
            st.write('아직 공통된 계기를 찾지 못했어요. 직접 골라 볼까요?')
            S.choose = True
        if S.get('choose'):
            t = st.radio('이번 주 후회한 사용은 주로 언제였나요?', core.CATS[:-1])
            if st.button('이 계기로 계획 받기'):
                S.trigger = t; go('plan')
    with st.expander('AI 처리 기록 (시험용)'):
        st.json(R['log'])

# ---------- ③ Output: 계획 고르기 ----------
elif S.step == 'plan':
    st.title('다음 주 계획 고르기')
    st.caption(f"확인한 계기: {S.trigger}")
    if 'plans' not in S:
        with st.spinner('계획을 만들고 있어요'):
            S.plans, S.plan_log = core.make_plans(S.trigger, S.result['기록'], provider, model)
    choice = st.radio('마음에 드는 계획을 하나 고르세요', [p['문장'] for p in S.plans])
    text = st.text_input('계획 고치기', choice)
    when = st.time_input('하루 한 번 알려 드릴 시간', value=pd.Timestamp('21:00').time())
    if st.button('이 계획으로 시작', type='primary'):
        S.final = (text, when); go('done')
    with st.expander('AI 처리 기록 (시험용)'):
        st.json(S.plan_log)

# ---------- ④ 홈: 연속 기록, 내 목표, 알림 설정 ----------
elif S.step == 'done':
    import notify
    text, when = S.final
    R = S.result
    S.setdefault('kept', {})
    S.setdefault('goal', max(R['통계']['후회'] - 1, 1))
    st.title('홈')
    c1, c2 = st.columns(2)
    c1.metric('연속 돌아보기', f"{S.get('streak', 5)}일")
    c2.metric('이번 주 후회한 사용', f"{R['통계']['후회']}번", delta=f"{R['통계']['후회'] - S.get('last_week', 7)}번 (지난주 대비)", delta_color='inverse')

    with st.container(border=True):
        st.caption('내 계획')
        st.markdown(f'### {text}')
        k1, k2 = st.columns(2)
        if k1.button('오늘 지켰어요', use_container_width=True):
            S.kept['오늘'] = True; st.toast('좋아요! 기록했어요')
        if k2.button('오늘은 못 했어요', use_container_width=True):
            S.kept['오늘'] = False; st.toast('괜찮아요. 내일 다시 해 봐요')

    st.subheader('내 목표')
    S.goal = st.slider('이번 주 후회한 사용을 몇 번 이하로 줄여 볼까요? (직접 정해요)', 1, 15, S.goal)
    st.progress(min(R['통계']['후회'] / S.goal, 1.0), text=f"{R['통계']['후회']} / {S.goal}번")

    st.subheader('알림 설정')
    st.caption('폰을 켤 때마다 알림이 오지 않아요. 정한 시간에만, 하루 최대 2개까지 와요.')
    a1, a2 = st.columns(2)
    review_on = a1.toggle('오늘 돌아보기 알림', value=True)
    review_t = a2.time_input('돌아보기 시각', value=pd.Timestamp('22:00').time(), disabled=not review_on)
    b1, b2 = st.columns(2)
    plan_on = b1.toggle('내 계획 알림', value=True)
    plan_t = b2.time_input('계획 알림 시각', value=when, disabled=not plan_on)
    week_on = st.toggle('일요일 주간 성찰 알림 (오후 8시)', value=True)
    days = st.multiselect('알림 받을 요일', list('월화수목금토일'), default=list('월화수목금토일'))

    settings = {'돌아보기 알림': review_on, '돌아보기 시각': review_t.strftime('%H:%M'),
                '계획 알림': plan_on, '계획 시각': plan_t.strftime('%H:%M'),
                '주간 성찰 알림': week_on, '요일': days, '목표': S.goal}
    state = {'연속일': S.get('streak', 5), '계획': text, '계획 지킴': {'어제': True},
             '이번 주 후회': R['통계']['후회'], '지난주 후회': S.get('last_week', 7)}
    st.subheader('이번 주 알림 미리보기')
    sched = notify.build_schedule(settings, state)
    if not sched:
        st.write('받을 알림이 없어요. 위에서 알림을 켜 주세요.')
    for day, t, kind, msg in sched:
        st.write(f"**{day} {t}** · {kind} — {msg}")
    if st.button('처음으로'):
        S.clear(); st.rerun()
