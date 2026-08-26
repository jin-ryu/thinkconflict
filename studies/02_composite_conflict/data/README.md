# Data

복합 충돌 연구에서 생성한 파생 데이터만 둔다.

- `samples/`: 원 데이터셋에서 고정한 파일럿 표본과 manifest
- `annotations/`: 주석자별 sidecar JSONL
- `adjudicated/`: 합의·판정이 끝난 `K/H` 정본
- `splits/`: 평가 split 및 matched-pair 정의

원 데이터셋 전체를 추가할 때는 라이선스와 버전 정보를 함께 기록한다. AIR 연구의 `studies/01_air_trace/data/`를 직접 수정하지 않는다.
