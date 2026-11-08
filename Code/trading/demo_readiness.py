"""조회 결과·공식 계약·정산 시점을 구분한 위험 자료 변환.

빈 체결 이력은 과거 체결 비용 '해당 없음'이다. 미래 비용을 0으로 확정하지 않는다.
모의 미지원 출력의 숫자나 매수 한도를 USD 현금/NAV로 대입하지 않는다.
"""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal

from strategy.engine import parse_timestamp

CONFIRMED = "확인됨"
UNKNOWN = "미확인"
UNSUPPORTED = "공식적으로 미지원"


def support(contract):
    """미지원이라는 명시적 공식 필드가 있을 때만 미지원으로 판정한다."""
    value = (contract or {}).get("virtualTrId", "")
    if value == "모의투자 미지원":
        return UNSUPPORTED
    return CONFIRMED if value.startswith("V") else UNKNOWN


def assess_readonly_inputs(report, records, contracts=None, now=None):
    """확인된 실제 값과 공식 미지원/미확인을 분리한다. 이 함수는 승인하지 않는다."""
    contracts = contracts or {}
    now = now or datetime.now(timezone.utc)
    pages, times, problems = {}, [], set()
    for record in records:
        pages[record["operation"]] = pages.get(record["operation"], 0) + 1
        times.append(record["at"])
        if record.get("sha256"):
            calculated = hashlib.sha256(json.dumps(record["payload"], sort_keys=True).encode()).hexdigest()
            if calculated != record["sha256"]:
                problems.add("source_payload_hash_mismatch")
        if not 0 <= (now - parse_timestamp(record["at"])).total_seconds() <= 30:
            problems.add("source_observations_not_current")
    history_complete = report.get("history_complete") is True and report.get("history_stable") is True
    filled_quantity = report.get("filled_quantity")
    historical_costs_not_applicable = history_complete and type(filled_quantity) is int and filled_quantity == 0
    present = contracts.get("inquire-present-balance", {})
    output2_unsupported = "output3" in present.get("apiSummary", "") and "만 정상 출력" in present.get("apiSummary", "")
    deposit = report.get("reported_usd_deposit_settlement_basis")
    power = report.get("buying_power")
    observed = {"buying_power_usd": power, "reported_foreign_deposit_usd": deposit,
                "execution_cash_usd": None, "initial_nav_usd": None, "initial_basis_at": None,
                "final_execution_fees": None, "cash_movements_complete": False}
    statuses = {
        "initial_usd_capital_nav": {"status": UNKNOWN, "reason": "USD 기준 자금/순자산 원본 없음; 주문가능액과 총자산 집계값은 대체 근거가 아님"},
        "execution_cash": {"status": UNKNOWN, "cash_api_support": support(contracts.get("foreign-margin")),
                           "reason": "통화별 증거금 현금 경로의 모의 지원 및 체결 기준 정의 필요"},
        "buying_power": {"status": CONFIRMED if power is not None else UNKNOWN,
                         "field": "inquire_psamount.output.ord_psbl_frcr_amt / ovrs_ord_psbl_amt", "currency": "USD"},
        "reported_deposit": {"status": UNSUPPORTED if output2_unsupported else UNKNOWN,
                             "field": "inquire_present_balance.output2[USD].frcr_dncl_amt_2",
                             "reason": "모의 output2는 정상 출력 보장 대상 아님" if output2_unsupported else "출력의 모의 유효 범위 확인 필요"},
        "holdings_cost_reservations": {"status": CONFIRMED if report.get("inventory_verified") is True else UNKNOWN,
                                       "reason": "보유/매도가능/원격 예약은 기존 정상화로 대조; 보유 원가는 실제 보유가 있을 때 별도 검산"},
        "order_and_cumulative_execution": {"status": CONFIRMED if history_complete else UNKNOWN,
                                          "reason": "ord_dt/odno와 누적 ft_ccld_qty/ft_ccld_amt3; 전체 페이지 양끝 조회"},
        "individual_fill_id_and_time": {"status": UNKNOWN,
                                        "reason": "ord_tmd는 주문 접수 시각; 개별 체결 ID/시각으로 간주하지 않음"},
        "historical_execution_costs": {"status": CONFIRMED if historical_costs_not_applicable else UNKNOWN,
                                       "applicability": "not_applicable_no_fills_in_queried_window" if historical_costs_not_applicable else "requires_final_cost_evidence",
                                       "reason": "조회 범위 내 체결0이면 기존 체결 비용은 해당 없음; 이전 기간을 검증했다는 뜻이 아님"},
        "future_final_cost_channel": {"status": support(contracts.get("inquire-period-trans")),
                                      "reason": "주문 전에는 예약 한도 검사; 체결 뒤 확정 비용과 정산 시각을 확인하며 그 전 손익을 확정하지 않음"},
        "cash_movements": {"status": UNKNOWN,
                           "candidate_api_support": support(contracts.get("inquire-period-trans")),
                           "reason": "입출금/배당/환전 전체 사건을 검증하는 모의 자료 원본 필요"},
    }
    issues = set(report.get("issues", []))
    # 기존 위험 평가 없음은 결과이지 자료 누락의 원인은 아니다. 각각의 필수 원본으로 설명한다.
    issues.discard("risk_evidence_unavailable_or_stale")
    issues.discard("execution_fee_and_cash_movement_history_not_proven")
    issues.update({"execution_cash_basis_unproven", "initial_nav_basis_unproven", "cash_movement_source_unproven"})
    if not historical_costs_not_applicable:
        issues.add("final_fee_source_unproven")
    if output2_unsupported:
        issues.add("vps_present_balance_output2_not_supported")
    issues.update(problems)
    return {"source_kind": "kis_vps_readonly_observations", "observed_inputs": observed,
            "buying_power_minus_reported_deposit": str(Decimal(power) - Decimal(deposit)) if power is not None and deposit is not None else None,
            "pages_by_operation": pages, "query_started_at": min(times) if times else None,
            "query_ended_at": max(times) if times else None,
            "reported_deposit_source": "inquire_present_balance.output2[USD].frcr_dncl_amt_2",
            "deposit_basis": "unsupported_for_vps" if output2_unsupported else "unproven",
            "initial_basis_established": False, "risk_ingested": False, "new_orders_allowed": False,
            "historical_costs_not_applicable": historical_costs_not_applicable,
            "pretrade_cost_policy": {"reservation_multiplier": "1.003", "final_fee_assumed": False,
                                     "after_fill": "block_new_buys_until_actual_costs_and_cash_reconciled"},
            "statuses": statuses, "issues": sorted(issues),
            "inventory": report.get("inventory"), "history_window": report.get("history_window")}


def assemble_risk_evidence(manager, normalized, sources):
    """검산 가능한 정규화 원본을 RiskLedger 계약으로 조립한다.

    sources는 획득 경로에서 파싱된 현금/NAV/체결/자금 사건 원본이다. 임의의
    verified 플래그·주문가능액 복사·미지원 output2는 받지 않는다. 현재 실제
    모의 경로는 현금 원본이 없어 이 함수에서 차단된다.
    """
    required = {"cash", "nav", "as_of", "window_start", "source_times", "source_hashes",
                "fills", "cash_events", "quotes", "provenance", "source_kind", "coverage", "account_fingerprint", "mode"}
    if set(sources) != required:
        raise ValueError("risk_source_components_missing")
    if sources["account_fingerprint"] != manager.state["broker_identity"] or sources["mode"] != manager.state["mode"]:
        raise ValueError("risk_source_account_or_mode_mismatch")
    provenance = sources["provenance"]
    if not isinstance(provenance, dict) or not {"cash", "nav", "fills", "cash_events"} <= provenance.keys():
        raise ValueError("risk_source_provenance_missing")
    for name in ("cash", "nav", "fills", "cash_events"):
        entry = provenance[name]
        if set(entry) != {"origin", "sha256", "currency", "basis"} or entry["currency"] != "USD":
            raise ValueError("risk_source_currency_or_schema_invalid")
        if entry["origin"] in {"buying_power", "vps_present_output2", "aggregate_krw_assets", "manual_verified_flag"}:
            raise ValueError("risk_source_not_authoritative")
        if len(entry["sha256"]) != 64 or entry["sha256"] not in sources["source_hashes"].values():
            raise ValueError("risk_source_hash_not_linked")
    if provenance["cash"]["basis"] != "execution_cash" or provenance["nav"]["basis"] != "usd_net_assets":
        raise ValueError("risk_cash_nav_basis_not_established")
    if sources["source_kind"] not in {"kis_vps", "synthetic"}:
        raise ValueError("risk_source_kind_invalid")
    if sources["source_kind"] == "kis_vps":
        # 실제 현금 공급기는 실제 캡처에서 생성돼야 한다. 외부 JSON의 origin/basis
        # 문자열만으로 실제 계좌 근거를 인증하지 않는다. 현재 모의 현금 API는 미지원이다.
        captured = getattr(manager, "_captured_execution_cash_sources", None)
        if not isinstance(captured, dict) or captured.get("source_hashes") != sources["source_hashes"]:
            raise ValueError("live_cash_source_capture_required")
        if captured.get("cash") != sources["cash"] or captured.get("nav") != sources["nav"]:
            raise ValueError("live_cash_source_value_mismatch")
    if sources["source_kind"] == "synthetic" and not manager.state.get("replay_only"):
        raise ValueError("synthetic_source_requires_replay_store")
    if any(value is None for value in (sources["cash"], sources["nav"])):
        raise ValueError("risk_cash_or_nav_missing")
    coverage = sources["coverage"]
    for field in ("cash", "balances", "fills", "cash_events", "quotes"):
        row = coverage.get(field, {})
        if set(row) != {"from", "through", "complete"} or row["complete"] is not True:
            raise ValueError("risk_source_coverage_incomplete")
        if (parse_timestamp(row["from"]) > parse_timestamp(sources["window_start"])
                or parse_timestamp(row["through"]) < parse_timestamp(sources["as_of"])):
            raise ValueError("risk_source_coverage_gap")
    for fill in sources["fills"]:
        if fill.get("fees_final") is not True:
            raise ValueError("execution_cost_pending_not_zero")
    inventory = normalized.get("inventory")
    if not inventory:
        raise ValueError("risk_inventory_evidence_missing")
    return {"account_fingerprint": manager.state["broker_identity"], "mode": "kis_demo",
            "source_kind": sources["source_kind"], "as_of": sources["as_of"],
            "window_start": sources["window_start"], "source_times": sources["source_times"],
            "source_hashes": sources["source_hashes"], "code_version": "risk-source-adapter-v1",
            "config_version": manager.state.get("limited_demo_session", {}).get("limits_hash", "unversioned"),
            "complete": {field: coverage[field]["complete"] for field in coverage},
            "cash": sources["cash"], "buying_power": normalized["observed_inputs"]["buying_power_usd"],
            "net_asset_value": sources["nav"], "positions": inventory["positions"],
            "position_costs": inventory["position_costs"], "fills": sources["fills"],
            "cash_events": sources["cash_events"], "quotes": sources["quotes"]}


def ingest_available_sources(manager, normalized, sources):
    """조립 → 기존 RiskLedger 검산. 실제 원본이 없으면 승인이나 가짜 초기값을 저장하지 않는다."""
    from trading.risk_ledger import RiskLedger
    if sources is None:
        manager.record_reconcile_failure("official_vps_cash_and_flow_sources_unavailable")
        raise ValueError("official_vps_cash_and_flow_sources_unavailable")
    if sources.get("source_kind") == "user_designated_demo_trial":
        from trading.demo_user_basis import ingest_sources
        return ingest_sources(manager,sources)
    if sources.get('source_kind')=='user_designated_strategy_demo':
        from trading.strategy_model_basis import ingest
        return ingest(manager,sources)
    evidence = assemble_risk_evidence(manager, normalized, sources)
    return RiskLedger(manager).ingest(evidence)


def resolve_available_sources(manager, api, normalized, contracts, profile=None):
    """지원 계약·필드 의미·실제 캡처가 모두 있는 원본만 조립한다.

    현재 공식 계약은 foreign-margin의 모의 지원을 거절하므로 현금 공급기로
    선택되지 않는다. 단순히 금액이 있다는 이유로 통과시키지 않으며, 가상의
    API 이름이나 V 치환도 생성하지 않는다.
    """
    from trading.demo_profile import load_demo_profile
    profile = profile or load_demo_profile()
    if manager is not None and profile.get('risk_basis')=='user_designated_strategy_demo':
        from trading.strategy_model_basis import build_sources
        try:
            sources=build_sources(manager,api,normalized)
        except (ValueError,KeyError,TypeError) as error:
            import re
            reason=str(error)
            safe=reason if re.fullmatch(r'strategy_[a-z_]{1,100}',reason) else 'strategy_actual_capture_or_posttrade_review_required'
            return {'sources':None,'status':UNKNOWN,'reason':safe}
        return {'sources':sources,'status':CONFIRMED,'reason':'user_designated_forward_strategy_model',
                'broker_cash_verified':False,'past_cash_movements_verified':False}
    if manager is not None and profile.get("risk_basis") == "user_designated_demo_trial":
        from trading.demo_user_basis import build_sources
        try:
            sources = build_sources(manager,api,normalized,profile)
        except (ValueError,KeyError) as error:
            import re
            code = str(error)
            safe = code if re.fullmatch(r"user_trial_[a-z_]+",code) else "user_trial_source_incomplete"
            return {"sources":None,"status":UNKNOWN,"reason":safe}
        return {"sources":sources,"status":CONFIRMED,"reason":"user_authorized_bounded_demo_basis",
                "broker_cash_verified":False,"past_cash_movements_verified":False}
    cash_contract = contracts.get("foreign-margin", {})
    if support(cash_contract) != CONFIRMED:
        return {"sources": None, "status": support(cash_contract),
                "reason": "official_foreign_margin_vps_unsupported_or_unknown",
                "needed": "KIS가 확인한 모의 USD 체결현금/순자산 원본 또는 공식 대체 조회 경로"}
    # 외화예수금이라는 이름만으로 체결현금이라고 가정하지 않는다.
    cash_fields = [row for row in cash_contract.get("apiPropertys", []) if row.get("propertyCd") == "frcr_dncl_amt1"]
    if not any("체결" in row.get("description", "") and "현금" in row.get("description", "") for row in cash_fields):
        return {"sources": None, "status": UNKNOWN, "reason": "execution_cash_definition_not_in_contract"}
    # 지원 계약이 향후 바뀌더라도 현재 파서로 기준 시점·자금 사건 범위를
    # 추정하지 않는다. 실제 응답과 정산 계약을 검증한 공급기를 먼저 구현한다.
    return {"sources": None, "status": UNKNOWN,
            "reason": "supported_cash_contract_requires_validated_capture_and_settlement_provider"}
