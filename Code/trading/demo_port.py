"""KIS 실제 조회를 실행부·위험 원장·비용 대기 기록에 연결한다.

현재 현금 공급기가 없는 경우에도 원격 보유/주문 관측은 수행한다. 그 결과를
가짜 위험 승인으로 바꾸지 않는다. 시세 인증은 계좌 인증과 별도 클라이언트다.
"""
import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from broker.kis_market import US_QUOTE, normalize_quote, wait_for_quote_time
from broker.sessions import regular_session
from trading.demo_account import select_buying_power, observe_settlement
from trading.demo_readiness import assess_readonly_inputs, resolve_available_sources, ingest_available_sources
from trading.order_contract import context
from trading.reconciliation import normalize_orders, normalize_inventory, normalize_snapshot


class DemoExecutionPort:
    def __init__(self, manager, adapter, profile, contracts, recovery_file, *, quote_client=None):
        self.manager, self.adapter, self.profile = manager, adapter, profile
        self.contracts = contracts
        self.recovery_file = Path(recovery_file)
        self.quote_client = quote_client
        self.latest = None

    def set_deadline(self, deadline, stop_requested):
        """페이지를 도는 중에도 다음 HTTP 전에 중단한다. 진행 중 요청은 기존15초 상한이다."""
        self.adapter.api.execution_deadline = deadline
        self.adapter.api.execution_stop_requested = stop_requested

    def recovery(self):
        """확인 시각은 원본 그대로 사용한다. 읽었다는 이유로 최신 시각을 만들어내지 않는다."""
        value = json.loads(self.recovery_file.read_text(encoding="utf-8"))
        if value.get("observation_folder"):
            from paths import DATA_ROOT
            from tools.verify_quote_recovery import evaluate
            folder=Path(value["observation_folder"]).resolve()
            if not folder.is_relative_to(DATA_ROOT.resolve()):raise ValueError("recovery_folder_outside_data")
            return evaluate(folder)
        return value.get("recovery", value)

    def wait(self, seconds):
        time.sleep(seconds)

    def quote(self):
        if self.quote_client is None:
            raise ValueError("separate_quote_client_required")
        now = datetime.now(timezone.utc)
        session = regular_session("US", now)
        if session is None:
            raise ValueError("regular_session_required")
        symbol = self.profile["symbol"]
        exchange = {"NASD": "NAS", "NYSE": "NYS", "AMEX": "AMS"}[self.adapter.exchanges[symbol]]
        response = self.quote_client.get(US_QUOTE, {"AUTH": "", "EXCD": exchange, "SYMB": symbol})
        quote = normalize_quote(response, "US", session)
        now = wait_for_quote_time(quote, datetime.now(timezone.utc))
        if not quote or not 0 <= (now - datetime.fromisoformat(quote["available_at"])).total_seconds() <= 30:
            raise ValueError("trial_quote_missing_or_stale")
        if not regular_session("US", now):
            raise ValueError("regular_session_ended_during_quote")
        # 기존 정상화가 실수형을 반환하므로 주문 경계에서는 십진 문자열로 바꾼다.
        return {"at": quote["available_at"], "bid": str(quote["bid"]), "ask": str(quote["ask"])}

    def _stage(self,stage):
        """실패가 난 단계의 시작 시각을 갱신한다. 이전 요청의 시간을 재사용하지 않는다."""
        self._processing_stage=stage
        self._step_started=time.monotonic()

    def refresh(self):
        """계좌 조회/검산 단계의 실패를 안전하게 기록한 뒤 원래 예외를 유지한다."""
        from trading.broker_diagnostics import failure_details,record_failure
        started=time.monotonic()
        self._refresh_started=started
        self._stage('account_refresh')
        self.manager._broker_failure=None
        try:
            return self._refresh()
        except (ValueError,OSError,RuntimeError,KeyError,TypeError,sqlite3.Error) as error:
            self.manager._execution_observation_valid=False
            record_failure(self.manager,failure_details(error,self._processing_stage,started,self._step_started))
            raise

    def _refresh(self):
        """이력→3거래소 잔고→여력→이력 순으로 전체 페이지와 관측 시각을 검산한다."""
        manager, adapter, api = self.manager, self.adapter, self.adapter.api
        manager.ready = False
        manager._execution_observation_valid = False
        manager.state["requested_cash_service"] = self.profile["buying_power_service"]
        start_index = len(api.records)
        now = datetime.now(timezone.utc)
        end = now.astimezone(ZoneInfo("America/New_York")).date()
        start = end - timedelta(days=90)
        proof_context = {**context(manager.state), "limit_only": False}
        from trading.demo_user_basis import normalize_owned_history
        self._stage('history_query_initial')
        first_raw=adapter.query_history(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
        self._stage('history_normalization')
        first=normalize_owned_history(manager,first_raw)
        self._stage('balances_query')
        balances = adapter.query_balances()
        self._stage('buying_power_query')
        capacity = adapter.query_buying_power(self.profile["symbol"], self.profile["maximum_gross_buy_commitments_usd"])
        # 모의에서 지원되는 output3 집계만 관측한다. output2를 USD 현금으로 쓰지 않는다.
        self._stage('present_balance_query')
        adapter.query_present_balance()
        self._stage('history_query_final')
        second_raw=adapter.query_history(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
        self._stage('history_normalization')
        second=normalize_owned_history(manager,second_raw)
        self._stage('snapshot_validation')
        if sorted(row["event_id"] for row in first) != sorted(row["event_id"] for row in second):
            raise ValueError("history_changed_during_snapshot")
        inventory = normalize_inventory(balances, second)
        known, issues = manager._verified_events(second)
        contract_issues = list(issues)
        selection = select_buying_power(capacity, self.profile["buying_power_service"], manager=manager)
        captured = api.records[start_index:]
        if not captured or any(row.get("environment") != "vps" for row in captured):
            raise ValueError("actual_demo_capture_missing")
        import hashlib
        for record in captured:
            expected = hashlib.sha256(json.dumps(record["payload"], sort_keys=True).encode()).hexdigest()
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(record["at"])).total_seconds()
            if expected != record["sha256"] or not 0 <= age <= 30:
                raise ValueError("captured_snapshot_hash_or_freshness_invalid")
        observed_at = captured[-1]["at"]
        from trading.buying_power import bind_api_buying_power, assess_buying_power
        capacity_records = [row for row in captured if row["operation"] == "overseas_stock.inquire_psamount"]
        if len(capacity_records) != 1:
            raise ValueError("buying_power_capture_missing_or_duplicated")
        budget_account = bind_api_buying_power(manager, capacity_records[0], inventory)
        purchase_budget = assess_buying_power(budget_account, manager.state["orders"].values())
        hashes = {str(index): row["sha256"] for index, row in enumerate(captured)}
        self._stage('settlement_observation')
        if not contract_issues:
            settlement = observe_settlement(manager, second, inventory, observed_at=observed_at, source_hashes=hashes)
        else:
            manager.verify_cancellations(second, complete=True)
            from trading.broker_diagnostics import failure_details,record_failure
            manager.state['last_reconcile_error']={'code':'account_observation_requires_review','at':datetime.now(timezone.utc).isoformat()}
            record_failure(manager,failure_details(ValueError(contract_issues[0] if contract_issues else 'account_observation_requires_review'),
                'account_contract',self._refresh_started,self._step_started))
            settlement = {"final_costs_complete": False}
        report = {"kind": "kis_demo_readonly", "inventory": inventory,
                  "history_complete": True, "history_stable": True, "inventory_verified": True,
                  "order_rows": len(second), "filled_quantity": sum(row["filled"] for row in second),
                  "buying_power": selection["amount"], "account_enrollment_status_checked": False,
                  "capacity_indicators_usd": {key: capacity["output"].get(key) for key in
                      ("ord_psbl_frcr_amt", "ovrs_ord_psbl_amt", "frcr_ord_psbl_amt1")}, "buying_power_selection": selection,
                  "issues": issues, "history_window": {"start": start.isoformat(), "end": end.isoformat()},
                  "remote_reservations_included": True, "order_requests_sent": 0}
        normalized = assess_readonly_inputs(report, captured, self.contracts)
        normalized["initial_capital_reference"] = manager.state.get("initial_capital_reference")
        reference = normalized["initial_capital_reference"]
        if reference:
            normalized["statuses"]["initial_virtual_cash_reference"] = {
                "status": "확인됨", "source": "user_confirmation", "amount_usd": reference["amount"],
                "scope": "사용자 확인 초기 가상 현금; 현재 현금/NAV와 구분"}
            normalized["statuses"]["initial_usd_capital_nav"]["reason"] = (
                "초기 가상 현금은 사용자 확인으로 기록됨. 현재 USD 현금/NAV의 독립 검산은 아직 미완료")
        from trading.risk_ledger import RiskLedger
        pending_id = RiskLedger(manager).record_unsettled_observation({
            "account_fingerprint": manager.state["broker_identity"], "mode": "kis_demo",
            "source_kind": "kis_vps_observation", "as_of": observed_at,
            "source_hashes": hashes, "inventory": inventory, "capacity_selection": selection,
            "initial_reference": manager.state.get("initial_capital_reference"),
            "queried_period": report["history_window"], "complete_order_pages": True,
            "history_stable": True, "missing_evidence": normalized["issues"],
        })
        from trading.demo_balance import connect_balance_observation
        self._stage('balance_linkage')
        balance_link = connect_balance_observation(manager, captured)
        from trading.user_cash import update_user_cash
        from paths import CONFIG_ROOT
        cash_basis = json.loads((CONFIG_ROOT / "kis-demo-cash.json").read_text(encoding="utf-8"))
        from trading.strategy_posttrade import refresh_from_provider
        settlement_link = {'connected': False, 'reason': 'not_strategy_profile'}
        if self.profile.get('risk_basis') == 'user_designated_strategy_demo' and not contract_issues:
            self._stage('settlement_source_validation')
            provider_started=time.monotonic()
            try:
                settlement_link = refresh_from_provider(manager, api, normalized)
            except (ValueError, KeyError, TypeError) as error:
                from trading.broker_diagnostics import failure_details,record_failure
                details=record_failure(manager,failure_details(error,'settlement_source_validation',provider_started))
                manager._strategy_settlement_binding = None
                settlement_link = {'connected': False, 'reason': 'settlement_source_validation_failed','broker_error':details}
        self._stage('cash_model_update')
        cash_model = update_user_cash(manager, balance_link, second, cash_basis)
        from trading.demo_cash_review import review_cash
        self._stage('risk_review')
        cash_review = review_cash(manager, balance_link, second, budget_account, captured, report["history_window"])
        risk_assessment = RiskLedger(manager).assess_observation(cash_review)
        resolution = resolve_available_sources(manager, api, normalized, self.contracts, self.profile)
        risk_proof = None
        self._stage('risk_ingest')
        if not issues and not settlement_link.get("broker_error"):
            try:
                risk_proof = ingest_available_sources(manager, normalized, resolution["sources"])
            except ValueError:
                manager.ready = False
            else:
                if not risk_proof.eligible:
                    manager.ready = False
                else:
                    snapshot = normalize_snapshot(balances, capacity, risk_proof, second,
                                                  buying_power_service=self.profile["buying_power_service"],
                                                  buying_power_evidence=budget_account)
                    self._stage('account_reconciliation')
                    manager.reconcile(snapshot, second, complete=True)
        from trading.demo_accounting_cycle import apply_verified_costs, observe_posttrade, readonly_plan
        self._stage('cost_import')
        cost_import = apply_verified_costs(manager)
        if cost_import["applied_orders"]:
            cash_model = update_user_cash(manager, balance_link, second, cash_basis)
            settlement = manager.state["demo_settlement"]
            cash_review = review_cash(manager,balance_link,second,budget_account,captured,report["history_window"])
            risk_assessment = RiskLedger(manager).assess_observation(cash_review)
            if risk_proof is not None and risk_proof.eligible:
                snapshot = normalize_snapshot(balances,capacity,risk_proof,second,
                    buying_power_service=self.profile["buying_power_service"],buying_power_evidence=budget_account)
                manager.reconcile(snapshot,second,complete=True)
        self._stage('posttrade_recording')
        posttrade = (observe_posttrade(manager,second,inventory,observed_at,hashes)
                     if not contract_issues else {"phase":"REVIEW","new_orders_allowed":False})
        plan = readonly_plan(manager,cash_review,risk_assessment)
        from trading.strategy_posttrade import settlement_status
        strategy_posttrade = settlement_status(manager)
        manager.state['settlement_provider_observation']={
            'configured':callable(getattr(api,'settlement_source_provider',None)),
            'connected':bool(settlement_link.get('connected')),'as_of':observed_at,
            'reason':settlement_link.get('reason','verified_settlement_connected')}
        self._stage('posttrade_recording')
        manager._save()
        self.latest = {"strategy_posttrade":strategy_posttrade,"settlement_source":settlement_link,"order_accounting_plan":plan,"posttrade":posttrade,"cost_import":cost_import,"risk_assessment": risk_assessment, "cash_risk_review": cash_review, "purchase_budget": purchase_budget, "report": report, "risk_inputs": normalized, "balance_observation_id": balance_link["observation_id"], "user_cash_account": cash_model,
                       "resolution": {key: value for key, value in resolution.items() if key != "sources"},
                       "new_orders_allowed": manager.ready and risk_proof is not None and risk_proof.eligible,
                       "risk_ingested": risk_proof is not None, "risk_observation_id": pending_id, "settlement_complete": settlement["final_costs_complete"],
                       "observed_at": observed_at, "raw_orders": second}
        return self.latest
