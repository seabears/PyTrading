# 주문·위험 원장 백업과 새 경로 복구

PaperAccount 복구와 다른 기능이다. Code/order_store.py와 trading/order_backup.py는 SQLite 주문 원장 전용이다. 원래 파일은 덮어쓰지 않는다. 계좌 원문 대신 manifest의 비밀을 제거한 지문을 사용한다.

## 백업

```cmd
cd /d C:\Projects\PyTrading
python Code\order_store.py backup --source Data\execution\kis-demo-readonly\orders.sqlite --destination Data\order-backups\backup-001
```

실제로 존재하는 원장을 지정한다. SQLite backup API로 WAL의 커밋 내용까지 읽어 orders.sqlite를 만들고 integrity_check·JSON 구조·계좌 지문을 확인한다. 주문과 위험은 한 journal 행에 있어 같은 커밋 시점이다. 평가가 갱신되고 주문 대조가 아직 끝나지 않은 상태도 그대로 보존하며, 이를 주문 허가 상태로 간주하지 않는다.

manifest.json에는 생성 시각·모드·별칭·계좌 지문·스키마·위험 체크포인트·파일 SHA256·도구 코드/설정 지문을 기록한다. 실행 프로세스의 모든 메모리 버전까지 확인한 기록은 아니다. 기존 위험 원본의 코드/설정 버전도 체크포인트 안에 보존된다. 임시 .partial 폴더에 쓴 뒤 파일 flush/fsync와 검사를 끝낸 전체 묶음만 최종 이름으로 등록한다. 실패한 partial은 정상 백업이 아니며 자동 선택하지 않는다. 기존 이름을 덮어쓰지 않는다.

운영 중 읽기 백업은 가능하다. .sqlite 파일만 파일 탐색기로 복사하거나 WAL 파일을 임의로 지우지 않는다. 보관 기간·별도 저장 장치 복사는 사용자가 결정한다. 백업 파일의 개인 거래 내역은 공개하지 않는다.

## 별도 경로에서 복원

```cmd
python Code\order_store.py restore --backup Data\order-backups\backup-001 --destination Data\execution\recovered-001\orders.sqlite --mode kis_demo --alias kis-demo-readonly --fingerprint 지문문자열
```

지문문자열은 해당 계좌에 기대하는 지문이며 계좌번호가 아니다. manifest만 믿고 다른 계좌로 전환하지 않는다. bundle의 해시·무결성·스키마·계좌/모드/별칭을 검사하고, 새로운 대상의 OS 잠금을 획득한다. 대상이 이미 있으면 활성/비활성 여부와 무관하게 덮어쓰지 않는다. 원본은 보존하고 임시 DB가 검사를 통과했을 때 새 이름으로 이동한다. 중간 종료 시 partial 파일만 남고 기존 원본은 바뀌지 않는다.

복원 직후 account 스냅샷을 비우고 restore_gate를 저장한다. INTENT/SENDING은 UNKNOWN·검토 필요로 바꾸고 불명 취소도 유지한다. INTENT가 오래 남아 있었다는 이유로 다시 전송하지 않는다. 취소 접수는 최종 취소가 아니다. 부분 체결 수량·비용은 원장에 남고 새 조회와 대조한다.

## 복원 후 대조

1. 복구 경로를 기존 운용 원장 대신 자동 연결하지 않는다. 먼저 읽기 전용 계좌 검사를 한다.
2. 백업 생성일의 미국 현지 날짜 이전부터 모든 페이지의 주문·체결·취소와 현금·잔고·예약·자금 변동을 조회한다.
3. 백업 이후 체결·수동 거래·누락 주문과 원장 차이를 검토한다. UNKNOWN은 유일한 원격 계약을 확인한 경우에만 기존 bind_unknown 경로로 연결한다. 단순 부재를 미접수로 간주하지 않는다.
4. 복원 시각 이후의 신선한 실제 KIS 위험 평가와 전체 원격 이력을 함께 검산해야 restore_gate를 해제할 수 있다. 오래된 평가나 합성 파일은 해제 근거가 아니다. 미확인 주문이 남으면 자동 해제되지 않는다.

이 단계는 주문을 전송하는 복구 명령을 제공하지 않는다. 실제 모의투자 응답 계약·위험 원본이 없으면 UNKNOWN/검토 필요로 남는 것이 정상이다. 복원했다고 외부 주문 가능 상태가 되지 않는다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
