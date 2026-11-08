"""선택한 증권사의 인증·시세를 한 번 확인한다. 계좌·주문은 호출하지 않는다."""
from app.runtime import load_run_settings
from broker.kis import KisApiError
from broker.kis_setup import create_kis_client, load_kis_settings
from broker.kis_market import collect_snapshot


def main():
    settings = load_run_settings()
    if settings.get("broker", "toss") == "toss":
        from tools.check_toss import main as check_toss
        return check_toss()
    options = load_kis_settings(settings["broker_config"])
    print("KIS 읽기 전용 연결 확인 — 시세만 조회하며 주문하지 않습니다.")
    try:
        client = create_kis_client(settings["env_file"], options)
        client.authenticate()
        print("KIS 인증 성공")
        for market, symbol in settings["symbols"]:
            try:
                snapshot = collect_snapshot(client, market, symbol, options)
                if not snapshot["regular_session_open"]:
                    print(f"{market}:{symbol}: 휴장·정규장 외 시간")
                elif snapshot.get("quote"):
                    quote = snapshot["quote"]
                    print(f"{market}:{symbol}: bid={quote['bid']}, ask={quote['ask']}, 완성 5분봉={len(snapshot['bars'])}")
                else:
                    print(f"{market}:{symbol}: 호가·원본 시각 미제공 — 대기")
            except (KisApiError, ValueError, KeyError, TypeError) as error:
                message = str(error) if isinstance(error, KisApiError) else "시세 응답 형식을 확인하세요."
                print(f"{market}:{symbol}: {message}")
    except KisApiError as error:
        print(str(error))
        raise SystemExit(1)
