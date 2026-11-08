"""매매 판단 기능만 실행한다. 합성 입력을 사용하며 계좌·인증·주문을 변경하지 않는다."""
import copy
import json

from app.runtime import load_run_settings
from paths import RESULTS_ROOT, FIXTURES_ROOT
from strategy.engine import evaluate, load_config, validate_config


def build_scenarios(snapshot):
    """조건 하나씩 바꿔 판단이 달라지는 과정을 보여준다. 입력은 직접 수정할 수 있다."""
    entry = copy.deepcopy(snapshot)
    weak_volume = copy.deepcopy(snapshot)
    weak_volume["bars"][-1]["volume"] = 100
    holding = copy.deepcopy(snapshot)
    holding["position"] = {"quantity": 1, "average_cost": snapshot["quote"]["ask"],
                           "peak_bid_since_entry": snapshot["quote"]["bid"]}
    stopping = copy.deepcopy(holding)
    stopping["quote"]["bid"] = holding["position"]["average_cost"] * 0.94
    stopping["quote"]["ask"] = stopping["quote"]["bid"] * 1.001
    return [("돌파·거래량 조건 사례", entry), ("거래량 부족 사례", weak_volume),
            ("보유 중 가격 유지 사례", holding), ("보유 중 가격 하락 사례", stopping)]


def main():
    settings = load_run_settings()
    overrides = json.loads(settings["strategy_config"].read_text(encoding="utf-8-sig")) if settings["strategy_config"] else None
    strategy = load_config(overrides)
    validate_config(strategy)
    source = FIXTURES_ROOT / "demo_replay.json"
    snapshots = json.loads(source.read_text(encoding="utf-8"))
    first_by_market = {}
    for snapshot in snapshots:
        first_by_market.setdefault(snapshot["market"], snapshot)
    records = []
    print("매매 판단 기능 실행 — 합성 시세·합성 뉴스 사용. 실제 계좌·주문 변경 없음.")
    print(f"입력 파일: {source}")
    for snapshot in first_by_market.values():
        for name, changed in build_scenarios(snapshot):
            decision = evaluate(changed, strategy)
            print(f"\n{changed['market']}:{changed['symbol']} / {name}")
            print(f"  bid={changed['quote']['bid']:.4f}, ask={changed['quote']['ask']:.4f}")
            print(f"  {decision['action']} / {decision['reason']}")
            for condition in decision["checks"]:
                print(f"    {condition['rule']}: {'통과' if condition['passed'] else '미통과'}")
            if decision["metrics"]:
                print("  계산값: " + json.dumps(decision["metrics"], ensure_ascii=False))
            records.append({"scenario": name, "snapshot": changed, "decision": decision})
    output = RESULTS_ROOT / "strategy.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n입력·판단 저장: {output}")


if __name__ == "__main__":
    main()
