r"""KIS/토스 시세와 기존 룰 판단·공통 체결 경로를 연결한다.

실시간: python main.py (../Config/settings.json을 읽고 계속 판단한다)
오프라인 기능 확인: python main.py --test paper 또는 python main.py --test replay
오프라인 재생은 인증·네트워크·주문을 호출하지 않는다. 체결 방식은 Config/execution.json을 따르며 실계좌 전송은 잠금 상태다.
"""
from __future__ import annotations

import argparse
import json
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from broker.kis import KisApiError
from broker.kis_setup import create_kis_client, load_kis_settings
from broker.kis_market import collect_snapshot as collect_kis_snapshot
from strategy.engine import load_config, validate_config
from news.collector import NEWS_QUERIES, collect_news, load_confirmed_events, update_news_cache
from news.earnings_service import EarningsService
from trading.paper import PaperAccount
from app.operations import OperationMonitor
from app.stateio import rotate_log
from app.runtime import AlreadyRunningError, acquire_run_lock, load_run_settings, release_run_lock
from broker.toss import TossRateLimitError, TossApiError, TossMarketClient, collect_snapshot, parse_symbol, read_credentials


def write_summary(account: PaperAccount, folder: Path) -> None:
    """수익률과 보유·거래 수를 사람이 읽을 수 있는 한국어 Markdown으로 저장한다."""
    if getattr(account, 'execution_mode', 'internal_paper') != 'internal_paper':
        (folder / 'summary.md').write_text('# 체결 경로 상태\n\n'+json.dumps(account.summary(),ensure_ascii=False,indent=2)+'\n\n주문 접수는 체결이 아니며 전략 계산용 추정값을 실제 손익으로 표시하지 않습니다.\n',encoding='utf-8')
        return
    lines = ["# 모의매매 현황", "", "실제 계좌·실제 주문과 무관한 모의 결과입니다.", "",
             "평가액은 마지막 유효 호가 기준입니다. 휴장·수집 지연 시 현재 가치와 다를 수 있습니다.", "",
             "| 시장 | 통화 | 현금 | 평가액 | 평가 손익 | 수익률 | 보유 종목 | 실현 손익 |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for market, row in account.summary().items():
        lines.append(f"| {market} | {row['currency']} | {row['cash']:,.2f} | {row['equity_at_last_quote']:,.2f} | "
                     f"{row['pnl_at_last_quote']:,.2f} | {row['return_at_last_quote']:.2%} | "
                     f"{row['position_count']} | {row['realized_pnl']:,.2f} |")
    lines += ["", f"누적 모의 거래: {len(account.state['trades'])}건", "",
              "비용·슬리피지 가정은 account.json의 settings에 기록됩니다. 수익성 검증 결과가 아닙니다.", ""]
    (folder / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def record_decision(account: PaperAccount, snapshot: dict, strategy: dict, folder: Path):
    """한 입력을 평가하고 판단·가상 체결·현황을 저장한다."""
    decision = account.evaluate_snapshot(snapshot, strategy)
    record = {"snapshot": snapshot, "decision": decision, "account_summary": account.summary()}
    # 날짜가 아닌 단일 일지 파일로 기록해 오프라인 재생과 실시간 기록 형식을 맞춘다.
    rotate_log(folder / "decisions.jsonl")
    with (folder / "decisions.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    fill = decision.get("paper_fill")
    explanation = ""
    if fill:
        explanation = f" / 모의 {fill['quantity']}주 @ {fill['price']:.4f}"
    print(f"{snapshot['market']}:{snapshot['symbol']} {decision['action']} — {decision['reason']}{explanation}")
    write_summary(account, folder)
    return decision


def refresh_news(symbols: list[tuple[str, str]], queries: dict, folder: Path) -> None:
    """뉴스 오류는 시세 손절 검사를 중단하지 않는다. 원문 자동 확정은 하지 않는다."""
    for market, symbol in symbols:
        query = queries.get(market + ":" + symbol)
        if not query:
            print(f"{market}:{symbol} 뉴스 검색어 미설정 — 설정의 news_queries 파일에서 추가할 수 있습니다.")
            continue
        try:
            report = collect_news(market, symbol, query)
            update_news_cache(folder / "news-candidates.json", report["selected"], selected_only=True)
            # 종목마다 이번 수집의 제외 이유도 별도 보존한다. 매매 후보 목록과 섞지 않는다.
            report_path = folder / f"news-filter-{market}-{symbol}.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{market}:{symbol} 뉴스 수집 {report['fetched_count']}건 / 선정 {len(report['selected'])}건 / 제외 {len(report['excluded'])}건")
        except (ValueError, OSError):
            print(f"{market}:{symbol} 뉴스 수집 실패 — 기존 검토 사건만 사용합니다.")


def interleave_holdings(symbols, account):
    """최대 3개 비보유 종목 조회 사이에 보유를 다시 본다. 실제 지연은 별도로 계측한다."""
    ordered = sorted(symbols, key=lambda item: (item[0] + ":" + item[1]) not in account.state["positions"])
    for index, item in enumerate(ordered):
        if index and index % 3 == 0:
            for position in list(account.state["positions"].values()):
                yield position["market"], position["symbol"]
        yield item


def stop_on_service_signal(signum, frame) -> None:
    """systemctl stop의 SIGTERM도 Ctrl+C와 같은 정리 경로를 사용한다."""
    raise KeyboardInterrupt


def main(argv=None, settings_override=None, decision_observer=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        defaults = load_run_settings()
        if settings_override:
            defaults.update(settings_override)
    except (ValueError, TypeError, OSError) as error:
        parser.exit(1, "../Config/settings.json의 내용과 경로를 확인하세요.\n")
    # 기존 옵션은 테스트·재생용이다. 평소에는 ../Config/settings.json만 수정한다.
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--symbols", nargs="+", type=parse_symbol)
    parser.add_argument("--watch", action="store_true", default=None)
    parser.add_argument("--interval", type=int)
    parser.add_argument("--collect-news", action="store_true", default=None, help="뉴스 후보를 함께 수집")
    parser.add_argument("--news-interval", type=int, help="뉴스 수집 간격: 초, 최소 300")
    parser.add_argument("--news-queries", type=Path, help="시장:종목 → 검색어 JSON")
    parser.add_argument("--events-file", type=Path)
    parser.add_argument("--paper-settings", type=Path)
    parser.add_argument("--strategy-config", type=Path)
    parser.add_argument("--replay", type=Path, help="입력 스냅샷 JSON 배열 또는 기록 JSONL의 순서대로 재생")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    if args.replay and args.watch:
        parser.error("오프라인 재생과 --watch는 함께 사용할 수 없습니다.")
    # 증권사 선택은 설정 파일에서만 한다. 실행 인자를 추가하지 않는다.
    broker_name = defaults.pop("broker", "toss")
    broker_config = defaults.pop("broker_config", None)
    for name, value in defaults.items():
        if getattr(args, name) is None:
            setattr(args, name, value)
    if args.replay:
        args.watch = False  # 오프라인 재생은 항상 파일 끝에서 종료한다.
    if args.interval < 30 or args.news_interval < 300:
        parser.error("시세 간격은 30초 이상, 뉴스 간격은 300초 이상이어야 합니다.")

    from trading.execution import load_execution, strategy_path, configure_account
    selection = load_execution()
    from broker.diagnostic import diagnostic_active
    if args.replay or diagnostic_active():
        selection = dict(selection, mode='internal_paper')
    if selection['mode']=='live':
        parser.exit(1, '실계좌 체결 경로는 선택됐지만 실계좌 전송은 잠겨 있습니다. 인증·주문을 호출하지 않습니다.\n')
    args.output_dir = strategy_path(args.output_dir / 'account.json', selection).parent
    print('체결 방식: '+selection['mode'], flush=True)
    # 계좌 하나를 두 프로세스가 동시에 변경하지 않도록 독점 실행 잠금을 만든다.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = args.output_dir / "run.lock"
    try:
        lock_file = acquire_run_lock(lock_path)
    except AlreadyRunningError as error:
        parser.exit(1, str(error) + "\n")
    earnings_service = None
    universe_service = None
    previous_signal_handler = signal.signal(signal.SIGTERM, stop_on_service_signal)
    try:
        paper_settings = json.loads(args.paper_settings.read_text(encoding="utf-8-sig")) if args.paper_settings else None
        strategy_overrides = json.loads(args.strategy_config.read_text(encoding="utf-8-sig")) if args.strategy_config else None
        strategy = load_config(strategy_overrides)
        validate_config(strategy)
        # 현재 시세 어댑터는 5분봉 합성 전용. 다른 간격 설정은 묵시적으로 사용하지 않는다.
        if not args.replay and strategy["bar_minutes"] != 5:
            raise ValueError("현재 실시간 연결은 5분봉만 지원합니다.")
        account = configure_account(PaperAccount(args.output_dir / "account.json", paper_settings), selection)

        if args.replay:
            if args.replay.suffix.lower() == ".jsonl":
                rows = [json.loads(line) for line in args.replay.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
                snapshots = [row.get("snapshot", row) for row in rows]
            else:
                snapshots = json.loads(args.replay.read_text(encoding="utf-8-sig"))
            if not isinstance(snapshots, list):
                raise ValueError("재생 입력은 스냅샷 목록이어야 합니다.")
            print("오프라인 모의 재생 시작. 실제 시세·인증·주문을 호출하지 않습니다.")
            for snapshot in snapshots:
                decision = record_decision(account, snapshot, strategy, args.output_dir)
                if decision_observer is not None:
                    observation = dict(snapshot, research_decision_reason=decision["reason"])
                    decision_observer(account, observation, args.output_dir)
            write_summary(account, args.output_dir)
            return

        # 서비스는 터미널 입력을 기다리면 안 된다. 지정한 파일에서만 인증 정보를 읽는다.
        if broker_name == "kis":
            options = load_kis_settings(broker_config)
            # 인증 전에 달력 설치와 지원 범위를 확인한다.
            from broker.sessions import regular_session
            regular_session("KR", datetime.now(timezone.utc))
            regular_session("US", datetime.now(timezone.utc))
            client = create_kis_client(args.env_file, options)
        else:
            client_id, client_secret = read_credentials(False, args.env_file)
            client = TossMarketClient(client_id, client_secret)
        while True:
            try:
                client.authenticate()
                break
            except (TossApiError, KisApiError) as error:
                if not args.watch:
                    raise
                if isinstance(error, TossRateLimitError):
                    print(f"{error} / 서버 대기 안내에 맞춰 인증을 재시도합니다.", flush=True)
                    client.rate_limiter.wait("/oauth2/token")
                else:
                    print(f"{error} / {args.interval}초 후 인증을 재시도합니다.", flush=True)
                    time.sleep(args.interval)
        broker_label = "KIS" if broker_name == "kis" else "토스"
        mode_label = "뉴스·가격·거래량" if strategy["news_enabled"] else "가격·거래량 (뉴스 기능 끔)"
        if strategy["earnings_enabled"]:
            mode_label = "가격·거래량·실적 뉴스"
        print(f"{broker_label} 인증 성공. {mode_label} 전략 실행. 체결 방식은 시작 시 선택한 execution 설정을 따릅니다.")
        queries = dict(NEWS_QUERIES)
        if strategy["news_enabled"] and args.collect_news and args.news_queries:
            queries.update(json.loads(args.news_queries.read_text(encoding="utf-8-sig")))
        # 보유 종목이 관찰 목록에서 빠져도 손절 시세 검사는 계속한다.
        held_symbols = [(position["market"], position["symbol"]) for position in account.state["positions"].values()]
        symbols = list(dict.fromkeys([*args.symbols, *held_symbols]))
        if strategy["earnings_enabled"]:
            earnings_service = EarningsService(symbols, args.output_dir / "earnings-news.json")
            if args.watch:
                earnings_service.start()
            print("실적 뉴스 사용: 호재+가격·거래량 충족 시 모의 매수, 악재 시 진입 제한·모의 매도. 초기 수집 중에는 신규 매수를 대기합니다.")
        monitor = OperationMonitor(args.output_dir)
        from app.universe import selection_view
        from app.universe_service import UniverseService
        if broker_name == 'kis' and args.watch:
            universe_service = UniverseService(dict(defaults, symbols=args.symbols), options).start()
        next_news_refresh = 0.0
        while True:
            monitor.begin_cycle()
            if broker_name == 'kis':
                port = getattr(account, 'port', None)
                orders = list(port.manager.state['orders'].values()) if port is not None else []
                view = selection_view(args.symbols, account.state, datetime.now(timezone.utc), broker_orders=orders)
                symbols = view['observed_symbols']
                if view['automatic']:
                    options['us_exchanges'].update(view['automatic'])
                entry_symbols = set(view['entry_symbols'])
            else:
                entry_symbols = set(args.symbols)
            # 보유 종목부터 매 주기 다시 정렬한다. 신규 보유도 다음 주기부터 우선한다.
            for market, symbol in interleave_holdings(symbols, account):
                request_started = time.monotonic()
                try:
                    snapshot = (collect_kis_snapshot(client, market, symbol, options) if broker_name == "kis"
                                else collect_snapshot(client, market, symbol))
                except (TossApiError, KisApiError) as error:
                    monitor.error(market + ":" + symbol, type(error).__name__)
                    print(f"{market}:{symbol} 시세 수집 실패 — {error}")
                    continue  # 한 종목의 오류로 다른 보유 종목의 검사를 멈추지 않는다.
                except (ValueError, KeyError, TypeError):
                    monitor.error(market + ":" + symbol, "invalid_response")
                    print(f"{market}:{symbol} 시세 응답 형식 오류 — 해당 종목 판단을 보류합니다.")
                    continue
                snapshot["data_mode"] = "live_observation"
                snapshot["universe_entry_allowed"] = (market, symbol) in entry_symbols
                monitor.observe(snapshot, time.monotonic() - request_started)
                # 끈 상태에서는 뉴스 파일을 읽지 않는다. 오래된 확정 악재도 판단에 넣지 않는다.
                snapshot["news_events"] = []
                if strategy["news_enabled"]:
                    try:
                        snapshot["news_events"] = load_confirmed_events(args.events_file, datetime.now(timezone.utc))
                    except (ValueError, KeyError, TypeError, OSError):
                        print("확정 뉴스 파일 오류 — 신규 매수 판단을 보류하고 가격 손절부터 검사합니다.")
                        # 빈 목록은 '악재 없음'으로 오해될 수 있다. 오류 입력을 명시한다.
                        # 엔진은 가격 손절을 먼저 검사하며, 나머지 판단은 invalid_input으로 대기한다.
                        snapshot["news_events"] = [{}]
                if earnings_service is not None:
                    snapshot.update(earnings_service.snapshot(market, symbol, datetime.now(timezone.utc)))
                decision = record_decision(account, snapshot, strategy, args.output_dir)
                if decision_observer is not None:
                    observation = dict(snapshot, research_decision_reason=decision["reason"])
                    decision_observer(account, observation, args.output_dir)
            if strategy["news_enabled"] and args.collect_news and time.monotonic() >= next_news_refresh:
                refresh_news(symbols, queries, args.output_dir)
                next_news_refresh = time.monotonic() + args.news_interval
            monitor.end_cycle(account, args.interval if args.watch else 0)
            if not args.watch:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n모의매매를 종료했습니다. 다음 실행에서 기존 계좌 상태를 이어갑니다.")
    except (TossApiError, KisApiError, ValueError, KeyError, TypeError, OSError) as error:
        # API 오류는 이미 비밀값이 제거돼 있다. 파일 오류의 전체 내용은 출력하지 않는다.
        if isinstance(error, (TossApiError, KisApiError)):
            parser.exit(1, str(error) + "\n")
        parser.exit(1, "입력·설정·저장 파일을 확인하세요. 기존 계좌를 삭제하지 않고 실행을 중단합니다.\n")
    finally:
        if "account" in locals() and hasattr(account, "close"):
            account.close()
        if universe_service is not None:
            universe_service.close()
        if earnings_service is not None:
            earnings_service.stop()
        signal.signal(signal.SIGTERM, previous_signal_handler)
        release_run_lock(lock_file)


if __name__ == "__main__":
    main()
