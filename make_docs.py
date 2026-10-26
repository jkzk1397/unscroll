# -*- coding: utf-8 -*-
"""static/index.html(서버용)에서 docs/index.html(GitHub Pages 체험판)을 만든다.
실행: python make_docs.py"""
import shutil, pathlib
B = pathlib.Path(__file__).parent
s = (B / 'static/index.html').read_text(encoding='utf-8')
s = s.replace("url('/static/fonts/PretendardVariable.woff2')", "url('fonts/PretendardVariable.woff2')")
s = s.replace('href="/static/', 'href="')
s = s.replace("<script>\n/* ---------- 기본 ---------- */", "<script>\nwindow.STANDALONE = true;   // GitHub Pages 체험판: 서버 없이 브라우저 안에서 동작\n/* ---------- 기본 ---------- */", 1)
s = s.replace('<p>같은 와이파이의 휴대폰에서 이 주소를 열면 실제 폰 화면으로 볼 수 있어요.</p>',
              '<p>휴대폰으로 이 링크를 열면 앱 화면처럼 꽉 차게 보여요. 설정에서 Gemini 키를 넣으면 실제 AI로 바뀌어요.</p>')
assert 'window.STANDALONE = true' in s
(B / 'docs').mkdir(exist_ok=True)
(B / 'docs/index.html').write_text(s, encoding='utf-8')
for f in ['manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png']:
    shutil.copy(B / 'static' / f, B / 'docs' / f)
(B / 'docs/fonts').mkdir(exist_ok=True)
shutil.copy(B / 'static/fonts/PretendardVariable.woff2', B / 'docs/fonts/')
print('docs/index.html 갱신')
