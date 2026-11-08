"""합성 입력으로 매수 제한과 보호 매도 유지를 확인한다."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from paths import RESULTS_ROOT, FIXTURES_ROOT
from trading.paper import PaperAccount
from strategy.engine import parse_timestamp


def main():
    import copy
    from datetime import timedelta
    snapshots = json.loads((FIXTURES_ROOT / "demo_replay.json").read_text(encoding="utf-8"))
    source = next(row for row in snapshots if row["market"] == "US")
    records = []
    with TemporaryDirectory(prefix="safety-paper-") as directory:
        account = PaperAccount(Path(directory) / "account.json")
        # 가격·안전장치만 격리해서 검사한다. 실행 중인 실적 검증 설정은 바꾸지 않는다.
        config = {"news_enabled": False, "earnings_enabled": False}
        first = account.evaluate_snapshot(source, config)
        records.append({"scenario": "synthetic_normal_buy", "decision": first})
        (account.path.parent / "PAUSE_BUYS").touch()
        other = copy.deepcopy(source)
        other["symbol"] = "OTHER"
        records.append({"scenario": "manual_buy_pause", "decision": account.evaluate_snapshot(other, config)})
        stopping = copy.deepcopy(source)
        stopping["now"] = (parse_timestamp(source["now"]) + timedelta(seconds=60)).isoformat()
        stopping["quote"].update(available_at=stopping["now"], bid=95, ask=95.1)
        records.append({"scenario": "protective_sell_while_paused", "decision": account.evaluate_snapshot(stopping, config)})
    for record in records:
        decision = record["decision"]
        print(record["scenario"], decision["action"], decision["reason"])
    output = RESULTS_ROOT / "safety-demo.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("합성 입력 안전장치 결과:", output)
