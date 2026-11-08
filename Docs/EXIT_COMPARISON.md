# 일봉 매수 고정·보호 매도 연구

운용 Code·Config·계좌를 수정하지 않는 시험 전용 실행이다. 프로젝트 루트의 CMD에서:

```cmd
python Test/research/exit_comparison_experiment.py
python Test/research/test_exit_comparison.py
```

매수·매도 계산은 `Test/research/exit_comparison_core.py`, 기간·자금·선정 기준과 보고서는 `Test/research/exit_comparison_experiment.py`에 있다. 한국어 설명과 함수별 책임을 기준으로 수정한다.

최신 결과는 `Data/reports/exit-comparison/report.md`, 실행 보존은 `Data/tests/results/exit-comparison/`이다. 각 실행의 declaration.json에 실제 시세·코드 해시·조건을 저장하며, runs에는 48개 계좌의 일별 평가·거래·진입·누락 진단을 남긴다.

기본은 같은 돌파 매수 기회·수량 공식에 20거래일 보유 만기와 여섯 보호 매도를 비교한다. 매매 손익의 비용 분해, 기간별·전체 연속 계좌, 기본·두 배 비용, 개발·검증 사전 선정과 이후 평가를 모두 보존한다. 운용으로 자동 연결하지 않는다.

forward-plan.json은 새 자료에서 검증할 후보의 유무를 기록한 계획이다. 새 미래 성과가 이미 검증되었다거나 자동 실행 중이라는 뜻이 아니다. 사전 기준 미통과 시 후보를 바꾸지 않고 미선정으로 남긴다.
