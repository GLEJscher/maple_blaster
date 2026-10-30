## 웹 시뮬레이터

브라우저에서 바로 돌려 볼 수 있는 DPM 시뮬레이터입니다. 서버 없이 Pyodide로 `Skills.py`를 그대로 실행하므로, 노트북(`Skills.ipynb`)과 같은 계산 결과가 나옵니다.

- 주소: https://GLEJscher.github.io/maple_blaster/
- `index.html`: 화면(입력 탭과 분석 탭)
- `web_api.py`: 화면 입력을 `Skills.py`의 변수로 바꿔 실행하고 분석 결과를 돌려 주는 연결 코드
- `Skills.py`, `Attribute.py`: 시뮬레이터 본체 (웹은 이 파일들을 수정하지 않고 그대로 읽습니다)
- `pyodide/`: 브라우저용 파이썬 실행 환경

`Skills.py`를 고치면 웹에도 바로 반영됩니다. 입력 항목은 `Skills.py` 위쪽의 변수와 주석에서 자동으로 만들어집니다.
