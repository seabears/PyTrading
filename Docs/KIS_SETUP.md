# KIS 읽기 전용 시세 연결

기본 실행은 KIS(prod) 실제 시세 + 프로그램 내부 모의매매다.
KIS 증권사 모의주문(vps)이나 실제 계좌 주문을 보내는 기능은 아직 추가하지 않았다.
시세 조회에는 계좌번호·HTS ID를 요구하지 않는다.

## 준비

1. KIS 실전용 App Key, App Secret을 발급받는다.
2. Credentials/kis.env에 다음 이름으로 저장한다. 값은 채팅에 올리지 않는다.

```text
KIS_APP_KEY=발급받은_App_Key
KIS_APP_SECRET=발급받은_App_Secret
```

기존 APP_KEY / APP_SECRET 이름도 지원하므로 현재 인증 파일 내용을 바꿀 필요는 없다.

3. 의존성 설치: `python -m pip install -r Deployment/requirements.txt`
4. 프로젝트 루트에서 `python Code/main.py` 실행.
5. 기능 선택은 `python Code/main.py --test`, 시세 연결만 확인하려면 `python Code/main.py --test broker`.

지금 PC의 Python 3.12에는 의존성을 설치했다. 라즈베리파이에는 별도 설치한다.
Config/settings.json: broker, env_file, symbols. Config/kis.json: 환경, 미국 거래소, 분봉 페이지 한도.
미국 거래소 NAS=나스닥, NYS=뉴욕, AMS=아멕스. 신규 종목은 거래소를 확인해 추가한다.
관찰 중인 미국 14개 종목은 KIS 공식 마스터로 거래소를 대조했다. SPCX도 NAS로 확인해 포함했다. 신규 종목은 실제 거래소를 확인해야 한다.

## 데이터와 인증

- KIS 모의 계좌·판단·뉴스 기록: Data/paper-kis. 기존 토스의 Data/paper는 그대로 보존한다.
- 인증 토큰 재사용 캐시: Data/cache/kis/token.json. 비밀 파일이며 공유하지 않는다. Git의 Data 제외 정책 적용.
- 토큰 파일은 키·환경 지문을 대조하고 만료 전 재사용한다. 인증 갱신에는 별도 OS 잠금을 쓴다.
- API는 인증 POST와 명시한 국내·미국 분봉·호가 GET만 허용한다. 주문·계좌 경로는 차단한다.
- 기본 요청 간격은 실전 시세 0.1초, 모의 0.6초. 실제 계약 한도는 별도로 확인해야 한다.
- HTTP 429와 KIS EGW00201을 처리하며 GET을 한 번만 재시도한다.

## 시세 해석과 검증 범위

국내는 KRX(J), 미국은 정규장만 관찰한다. 거래소 달력의 휴장·조기 종료·서머타임을 반영한다.
달력은 커뮤니티 자료여서 갑작스러운 휴장·거래 정지는 누락될 수 있다. 원본 호가 시각의 신선도를 추가 검사한다.
국내 30개 응답은 과거 시간으로 반복 조회하고, 미국은 NMIN=1·NREC=120으로 수집한다.
KIS 분 시각을 구간 시작으로 해석해 1분을 더한다. 진행 중 분·누락 분은 완성 봉에서 제외한다.
미국 분봉 xymd/xhms는 현지 시각, 호가 dymd/dhms는 한국 시각으로 해석한다. 실제 응답의 분봉 khms와 호가 dhms를 대조해 확인했다. 원본 시각이 없으면 수신 시각으로 대체하지 않고 대기한다.
이 시각 해석과 실제 응답 필드는 실계정 연결 검증이 필요하며, 지연 시세는 기존 30초 신선도 검사로 차단될 수 있다.

뉴스 후보를 자동 확정하지 않는 기존 규칙과 모든 매매 조건은 그대로다. 증권사 전환이 매수 신호·수익을 보장하지 않는다.
기존 장기 연구는 출처가 명시된 저장 토스 자료로만 재현한다. KIS 모드에서 토스 신규 수집은 차단한다.
KIS 장기 과거자료 수집기는 별도 변환이 필요하다. 토스 자료를 KIS 자료로 이름만 바꾸거나 섞지 않는다.

## 공식 참고

- https://github.com/koreainvestment/open-trading-api
- https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock/inquire_time_itemchartprice
- https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/overseas_stock/inquire_time_itemchartprice

호가 원본 시각이 PC보다 최대 2초 앞선 경우 실제 시간이 지날 때까지 기다린 뒤 다시 검사한다. 더 먼 미래의 호가는 허용하지 않는다.

## 토큰 24시간 재사용

Data/cache/kis/token.json에 issued_at(발급 시각), expires_at(서버 만료 시각), reuse_until(재사용 종료 시각)을 한국 시간으로 저장한다.
프로그램을 재시작해도 발급 후 24시간 미만이며 서버 만료 전이면 저장된 토큰을 재사용한다.
24시간이 지났거나 서버가 먼저 만료시키면 재발급하고 발급 시각도 갱신한다. 키·실전/모의 환경이 바뀌어도 재발급한다.
기존 발급 시각 없는 캐시는 서버 만료 시각에서 24시간을 뺀 시각을 보수적으로 사용하고 그 근거를 별도 표시한다.
토큰 파일에는 비밀 토큰이 들어 있으므로 공유하지 않는다. 인증값은 로그에 출력하지 않는다.

이 문서의 장비 이름, 사용자명 및 절대 경로는 공개용 예시다. 실제 환경에서는 로컬 값을 사용한다.
