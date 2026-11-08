"""--test api-live: 미국 시세 REST 3개와 실시간 호가만 실제 연결한다. 계좌·주문 없음."""
import json
from datetime import datetime, timezone

from broker.kis import KisApiError
from broker.kis_api import KisApiClient, overseas_stock, overseas_stock_ws
from broker.kis_api.websocket import open_stream
from paths import DATA_ROOT


def main():
    client = KisApiClient.from_settings()
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "actual_order_sent": False,
              "rest": [], "websocket": {"passed": False, "data_frames": 0},
              "scope": "AAPL market data only; no account or order endpoints"}
    requests = [overseas_stock.price("", "NAS", "AAPL"), overseas_stock.inquire_asking_price("", "NAS", "AAPL"),
                overseas_stock.dailyprice("", "NAS", "AAPL", "0", "", "1")]
    for request in requests:
        try:
            result = client.execute(request)
            counts = {key: len(value) if isinstance(value, list) else 1 for key, value in result.payload.items()
                      if key.startswith("output") and isinstance(value, (dict, list))}
            report["rest"].append({"name": request.name, "passed": True, "output_counts": counts})
            print(f"{request.name}: 실제 조회 성공 / {counts}", flush=True)
        except KisApiError as error:
            report["rest"].append({"name": request.name, "passed": False, "error": str(error)})
            print(f"{request.name}: {error}", flush=True)
    try:
        with open_stream(client) as session:
            session.send(overseas_stock_ws.asking_price("1", "DNASAAPL"))
            for event in session.events(maximum_messages=4, timeout=10):
                if event.kind == "data":
                    report["websocket"] = {"passed": True, "data_frames": 1, "records": len(event.rows),
                                           "columns": len(event.rows[0])}
                    session.send(overseas_stock_ws.asking_price("2", "DNASAAPL"))
                    break
        print("실시간 호가: " + ("실제 수신 성공" if report["websocket"]["passed"] else "시간 내 시세 미수신"), flush=True)
    except Exception as error:
        # 라이브러리 오류에는 연결 내부 정보가 있을 수 있어 원문을 파일·로그에 저장하지 않는다.
        report["websocket"]["error_type"] = type(error).__name__
        print(f"실시간 호가 확인 실패 ({type(error).__name__}). 전 상품 실시간 수신 성공으로 간주하지 않습니다.", flush=True)
    folder = DATA_ROOT / "reports/kis-api"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "live.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"실제 연결 결과: {folder / 'live.json'}")
