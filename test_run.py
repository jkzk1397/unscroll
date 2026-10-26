# -*- coding: utf-8 -*-
"""시험 세트 전체를 한 번에 돌려 결과표를 만든다.
사용법: python test_run.py --ai gemini   (키가 없으면 --ai mock)"""
import argparse, csv, json, re, time
from datetime import datetime
from pathlib import Path
import core, llm

BASE = Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument('--ai', default='mock', choices=list(llm.PROVIDERS))
ap.add_argument('--model', default=None)
ap.add_argument('--repeat', type=int, default=1, help='같은 사례를 몇 번 돌릴지 (일관성 확인)')
args = ap.parse_args()

cases = json.loads((BASE / 'data/test_cases.json').read_text(encoding='utf-8'))
rows = []
for case in cases:
    for k in range(args.repeat):
        R = core.reflect(case['기록'], args.ai, args.model)
        got = sorted(g['계기'] for g in R.get('추측', []))
        want = sorted(case['기대_추측'])
        used = {n for g in R.get('추측', []) for n in g['근거']}
        tries = R['log']['시도']
        raw_problems = sum(len(t['문제']) for t in tries)
        rows.append({
            '사례': case['이름'], '회차': k + 1, '상태': R['상태'],
            '추측': ', '.join(got) or '없음', '기대': ', '.join(want) or '없음',
            '추측 일치': '✓' if got == want else '✕',
            '헛지적': len(set(got) - set(want)), '놓침': len(set(want) - set(got)),
            '제외할 근거 사용': '✕' if used & set(case['근거_제외']) else '✓',
            '형식(첫 답)': '✓' if tries and not any('형식' in p or '빠진' in p for p in tries[0]['문제']) else ('-' if not tries else '✕'),
            'AI 원답 문제 수': raw_problems, '요청 횟수': len(tries),
            '초': round(sum(t['초'] for t in tries), 1),
        })

out = BASE / 'results'
out.mkdir(exist_ok=True)
stamp = datetime.now().strftime('%Y%m%d_%H%M')
path = out / f'test_{args.ai}_{stamp}.csv'
with open(path, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

cols = ['사례', '회차', '상태', '추측', '기대', '추측 일치', '헛지적', '놓침', '요청 횟수', '초']
print(' | '.join(cols))
for r in rows:
    print(' | '.join(str(r[c]) for c in cols))
n = len(rows)
print(f"\n추측 일치 {sum(r['추측 일치'] == '✓' for r in rows)}/{n} · 헛지적 {sum(r['헛지적'] for r in rows)}건 · 놓침 {sum(r['놓침'] for r in rows)}건")
print(f'저장: {path}')
