"""매수→보유→손절을 합성 입력으로 확인한다. 실행마다 별도 결과 폴더를 쓴다."""
import json
from datetime import datetime, timezone

from app.runner import record_decision, write_summary
from app.runtime import load_run_settings
from paths import RESULTS_ROOT, FIXTURES_ROOT
from strategy.engine import load_config, validate_config
from trading.paper import PaperAccount


def main():
    settings = load_run_settings()
    paper_settings = json.loads(settings["paper_settings"].read_text(encoding="utf-8-sig")) if settings["paper_settings"] else None
    strategy_overrides = json.loads(settings["strategy_config"].read_text(encoding="utf-8-sig")) if settings["strategy_config"] else None
    strategy = load_config(strategy_overrides)
    validate_config(strategy)
    output = RESULTS_ROOT / ("replay-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
    output.mkdir(parents=True)
    account = PaperAccount(output / "account.json", paper_settings)
    snapshots = json.loads((FIXTURES_ROOT / "demo_replay.json").read_text(encoding="utf-8"))
    print("가상 입력 재생. 실제 데이터·인증·주문은 사용하지 않습니다.")
    print("가상 자금·비용·전략은 현재 설정을 적용합니다.")
    for snapshot in snapshots:
        record_decision(account, snapshot, strategy, output)
        summary = account.summary()[snapshot["market"]]
        print(f"  모의 현금={summary['cash']:,.2f} {summary['currency']}, "
              f"평가액={summary['equity_at_last_quote']:,.2f}, 보유 종목={summary['position_count']}, "
              f"실현 손익={summary['realized_pnl']:,.2f}")
    write_summary(account, output)
    restored = PaperAccount(output / "account.json", paper_settings)
    print(f"파일에서 복원한 거래 수: {len(restored.state['trades'])}")
    print(f"재생 결과: {output}")


if __name__ == "__main__":
    main()
