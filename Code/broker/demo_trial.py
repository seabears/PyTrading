"""명시 한정 시험의 실제 vps 어댑터. 기본 조회 전용 클래스는 변경하지 않는다."""
import copy
import hashlib
import json
import time
from datetime import datetime, timezone

from broker.kis_readonly import ReadOnlyKisApi, redact_payload
from broker.kis_api.client import KisApiClient, KisApiError

ORDER_PATHS = {"/uapi/overseas-stock/v1/trading/order", "/uapi/overseas-stock/v1/trading/order-rvsecncl"}


class TrialKisApi(ReadOnlyKisApi):
    """원장·프로필·위험 검사 뒤 execute_managed를 거친 vps 지정가만 전송한다."""
    def execute(self, specification):
        self._check_deadline()
        if specification.method == "GET":
            return super().execute(specification)
        if (not self._managed_permission or not self.allow_trading
                or specification.path not in ORDER_PATHS or self.market_client.environment != "vps"):
            raise KisApiError("trial_unmanaged_post_blocked")
        response = KisApiClient.execute(self, specification)
        payload = redact_payload(copy.deepcopy(response.payload), self.secrets)
        self.records.append({"at": datetime.now(timezone.utc).isoformat(), "environment": "vps",
            "method": "POST", "operation": specification.name, "tr_id": specification.transaction_id,
            "payload": payload, "sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()})
        return response

    def _check_deadline(self):
        deadline = getattr(self, "execution_deadline", None)
        stopped = getattr(self, "execution_stop_requested", lambda: False)
        if (deadline is not None and time.monotonic() >= deadline) or stopped():
            raise KisApiError("trial_execution_deadline_or_stop")

    def _http(self, path, parameters, method, headers=None, *, order=False):
        self._check_deadline()
        if method == "GET":
            return super()._http(path, parameters, method, headers, order=order)
        if not self._managed_permission or not self.allow_trading or path not in ORDER_PATHS:
            raise KisApiError("trial_http_permission_blocked")
        return KisApiClient._http(self, path, parameters, method, headers, order=order)

    def execute_managed(self, specification, manager, intent_id):
        session = getattr(self, "trial_session", None)
        if session is None or session.manager is not manager or intent_id not in session.state["order_ids"]:
            raise KisApiError("trial_session_scope_required")
        order = manager.state["orders"][intent_id]
        contract = session.state["contracts"].get(intent_id, {})
        if not contract or any(order.get(key) != value for key, value in contract.items()):
            raise KisApiError("trial_contract_changed")
        if specification.path.endswith("order-rvsecncl"):
            from datetime import timedelta
            from strategy.engine import parse_timestamp
            from broker.sessions import regular_session
            expiry = session.state.get("expires_at")
            now = datetime.now(timezone.utc)
            if (not expiry or now > parse_timestamp(expiry) + timedelta(minutes=2)
                    or not regular_session("US", now)
                    or not 0 < session.state["cancel_attempts"] <= session.limits["maximum_cancel_attempts"]
                    or not order.get("session_cancel_attempted")):
                raise KisApiError("trial_cancel_scope_invalid")
        else:
            session._guard()
            counter = "buy_attempts" if order["side"] == "BUY" else "sell_attempts"
            ceiling = "maximum_buy_attempts" if order["side"] == "BUY" else "maximum_sell_attempts"
            if (not order.get("session_transmission_attempted")
                    or not 0 < session.state[counter] <= session.limits[ceiling]):
                raise KisApiError("trial_transmission_attempt_not_recorded")
        return KisApiClient.execute_managed(self, specification, manager, intent_id)
