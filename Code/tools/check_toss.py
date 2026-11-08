"""토스 인증·거래 시간·시세 수집만 한 번 확인한다. 계좌·주문 API는 호출하지 않는다."""
from app.runtime import load_run_settings
from broker.toss import TossApiError, TossMarketClient, collect_snapshot, read_credentials


def main():
    settings = load_run_settings()
    print("토스 연결만 확인합니다. 같은 키를 쓰는 지속 실행 프로그램은 먼저 종료하세요.")
    try:
        client_id, secret = read_credentials(False, settings["env_file"])
        client = TossMarketClient(client_id, secret)
        client.authenticate()
        print("토스 인증 성공")
        for market, symbol in settings["symbols"]:
            snapshot = collect_snapshot(client, market, symbol)
            if not snapshot["regular_session_open"]:
                print(f"{market}:{symbol}: 휴장·정규장 외 시간 — 장중 호가·봉 확인은 대기")
                continue
            quote = snapshot["quote"]
            print(f"{market}:{symbol}: bid={quote['bid']}, ask={quote['ask']}, 완성 5분봉={len(snapshot['bars'])}")
    except TossApiError as error:
        print(str(error))  # 토스 모듈에서 인증값·원문 응답을 제거한 메시지만 출력한다.
        raise SystemExit(1)


if __name__ == "__main__":
    main()
