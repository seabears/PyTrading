"""KIS 상품 REST 공통 전송. 기존 시세 전용 클라이언트의 토큰 캐시를 공유한다.

자동매매 main.py에는 연결하지 않는다. 주문 함수 구현과 실계좌 운용은 별도 단계다.
조회 GET만 한도 초과 시 한 번 재시도한다. 주문 POST는 전송 실패 시 재전송하지 않는다.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from broker.kis import BASE_URLS, KisApiError, KisRateLimitError
from paths import CONFIG_ROOT
from .models import ApiRequest, ApiResponse
from .policy import validate_no_borrowing
from .removed_finance import reject_removed_finance
from broker.product_policy import validate_product_request


class KisOrderStateUnknown(KisApiError):
    """응답 유실 시 같은 주문을 자동 재전송하지 않고 주문·체결 내역부터 확인한다."""


class KisPreflightError(KisApiError):
    """주문 HTTP 전송 전에 실패했다. 응답 유실과 구분한다."""


class KisOrderRejected(KisApiError):
    """명시적으로 거절된 주문. 응답 유실과 구별한다."""


def load_catalog():
    value = json.loads((CONFIG_ROOT / "kis-api-catalog.json").read_text(encoding="utf-8"))
    return {row["name"]: row for row in value["operations"]}


def validate_operation(specification, kind, environment, catalog=None):
    reject_removed_finance(specification.name, getattr(specification, "path", ""))
    if kind == "rest":
        validate_no_borrowing(specification.name, specification.path, specification.parameters)
    catalog = load_catalog() if catalog is None else catalog
    operation = catalog.get(specification.name)
    # 기존 클라이언트가 카탈로그를 캐시했어도 최신 사용 불허 상태는 즉시 적용한다.
    current_operation = load_catalog().get(specification.name)
    if (operation and operation.get("enabled", True) is not True) or (current_operation and current_operation.get("enabled", True) is not True):
        raise KisApiError("선물·옵션·ELW 등 사용 불허 상태의 API입니다. 전송·구독할 수 없습니다.")
    expected = "real" if environment == "prod" else "demo"
    if not operation or operation["kind"] != kind or specification.environment != expected:
        raise KisApiError("KIS API 이름·상품 종류·실전/모의 환경이 일치하지 않습니다.")
    if specification.transaction_id not in operation["transaction_ids"]:
        raise KisApiError("공식 목록에 없는 KIS TR ID입니다.")
    if kind == "rest" and (specification.path not in operation["paths"] or specification.method not in operation["methods"]):
        raise KisApiError("공식 목록에 없는 KIS 경로·요청 방식입니다.")
    validate_product_request(getattr(specification, "path", ""), specification.parameters, operation=specification.name, subscription=kind == "websocket")
    return operation


class KisApiClient:
    def __init__(self, market_client, *, allow_trading=False):
        if type(allow_trading) is not bool:
            raise ValueError("allow_trading은 bool이어야 합니다.")
        self.market_client = market_client
        self.allow_trading = allow_trading
        self._managed_permission = False
        self.catalog = load_catalog()
        self.http_audit = []
        self.market_client.request_interval = max(self.market_client.request_interval, 0.2)

    @classmethod
    def from_settings(cls, *, allow_trading=False):
        from app.runtime import load_run_settings
        from broker.kis_setup import create_kis_client, load_kis_settings
        settings = load_run_settings()
        if settings["broker"] != "kis":
            raise KisApiError("현재 기본 증권사가 KIS가 아닙니다.")
        options = load_kis_settings(settings["broker_config"])
        return cls(create_kis_client(settings["env_file"], options), allow_trading=allow_trading)

    def _http(self, path, parameters, method, headers=None, *, order=False):
        """인증값·HTTP 본문·계좌 응답을 오류 문자열이나 로그에 넣지 않는다."""
        reject_removed_finance(path=path)
        if order or (method != "GET" and "/trading/" in path):
            from broker.diagnostic import require_broker_orders_allowed
            require_broker_orders_allowed()
        # 낮은 수준의 전송 함수를 직접 호출해도 미허용 상품 경로는 전송하지 않는다.
        if method != "GET" and "/trading/" in path:
            if self.market_client.environment != "vps" or not self._managed_permission:
                raise KisApiError("관리되지 않은 주문·실계좌 전송은 금지합니다.")
        operations = load_catalog().values()
        if any(path in operation["paths"] and operation.get("enabled", True) is not True for operation in operations):
            raise KisApiError("사용 불허 상품의 API 경로입니다.")
        validate_no_borrowing("", path, parameters)
        validate_product_request(path, parameters)
        client = self.market_client
        request_headers = {"Content-Type": "application/json; charset=utf-8", **(headers or {})}
        url = BASE_URLS[client.environment] + path
        data = None
        if method == "GET":
            url += "?" + urllib.parse.urlencode(parameters)
        else:
            data = json.dumps(parameters, allow_nan=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
        if method != "GET" and "/trading/" in path:
            self._enforce_managed_policy(path, parameters)
        client._wait()
        if method != "GET" and "/trading/" in path:
            self._enforce_managed_policy(path, parameters)
        audit = {"at": datetime.now(timezone.utc).isoformat(), "method": method,
                 "path": urllib.parse.urlsplit(path).path, "environment": client.environment,
                 "kind": "account_read" if method == "GET" else "managed_account_change",
                 "outcome": "started"}
        self.http_audit.append(audit)
        try:
            if order:
                self._order_http_started = True
            with urllib.request.urlopen(request, timeout=15) as response:
                status_value = getattr(response, "status", None)
                audit["http_status"] = status_value if type(status_value) is int else None
                payload = json.load(response)
                audit["outcome"] = "http_response_received"
                continuation = response.headers.get("tr_cont", "")
        except urllib.error.HTTPError as error:
            status = error.code
            try:
                payload = json.loads(error.read(16384))
            except (ValueError, UnicodeError):
                payload = {}
            finally:
                error.close()
            code = payload.get("msg_cd", payload.get("error_code")) if isinstance(payload, dict) else None
            audit.update(http_status=status, outcome="http_error",
                         provider_code=code if code in {"EGW00201", "EGW00103", "EGW00121", "EGW00123", "EGW00133"} else None)
            if status == 429 or (isinstance(payload, dict) and payload.get("msg_cd") == "EGW00201"):
                raise KisRateLimitError("KIS 호출 한도 초과",stage="account_http",category="rate_limit",http_status=status,provider_code=code) from None
            if order and status >= 500:
                raise KisOrderStateUnknown("KIS 주문 응답 확인 실패. 재주문 전에 체결·미체결 내역을 확인하세요.",stage="account_http",category="http_error",http_status=status,provider_code=code) from None
            raise KisApiError(f"KIS HTTP {status}: 권한·환경·입력값을 확인하세요.",stage="account_http",category="http_error",http_status=status,provider_code=code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            audit["outcome"] = "transport_or_json_error"
            if order:
                raise KisOrderStateUnknown("KIS 주문 응답 유실. 재주문 전에 체결·미체결 내역을 확인하세요.",stage="account_http",category="connection_error") from None
            raise KisApiError("KIS 연결 또는 JSON 응답 확인 실패",stage="account_http",category="connection_error") from None
        except (ValueError, UnicodeError):
            audit['outcome']='response_decode_error'
            if order:
                raise KisOrderStateUnknown("KIS 주문 응답 형식 확인 실패",stage="account_http",category="response_decode_error") from None
            raise KisApiError("KIS 계좌 응답 형식 확인 실패",stage="account_http",category="response_decode_error") from None
        if not isinstance(payload, dict):
            if order:
                raise KisOrderStateUnknown("KIS 주문 응답 형식 오류. 주문 상태를 먼저 확인하세요.")
            raise KisApiError("KIS 응답이 객체가 아닙니다.",stage="account_http",category="response_decode_error")
        if payload.get("msg_cd") == "EGW00201":
            audit.update(outcome="business_rate_limit", provider_code="EGW00201")
            raise KisRateLimitError("KIS 호출 한도 초과")
        audit["outcome"] = "success" if payload.get("rt_cd") == "0" else "business_error"
        if payload.get("msg_cd") == "EGW00201":
            audit["provider_code"] = "EGW00201"
        return ApiResponse(payload, continuation)

    def execute(self, specification):
        """한 페이지를 전송한다. 다음 페이지의 커서는 API별 응답을 보고 호출자가 지정한다."""
        if not isinstance(specification, ApiRequest):
            raise TypeError("상품 함수가 반환한 ApiRequest가 필요합니다.")
        if specification.changes_account:
            from broker.diagnostic import require_broker_orders_allowed
            require_broker_orders_allowed()
        validate_operation(specification, "rest", self.market_client.environment, self.catalog)
        if specification.changes_account and (self.market_client.environment != "vps" or not self._managed_permission):
            raise KisApiError("실계좌·원장 없는 직접 주문 전송은 금지합니다.")
        if specification.changes_account:
            self._enforce_managed_policy(specification.path, specification.parameters)
        if specification.changes_account and not self.allow_trading:
            raise KisApiError("주문 전송이 꺼져 있습니다. 요청 명세만 확인할 수 있습니다.")
        # 인증 호출보다 먼저 입력과 주문 차단 여부를 확인한다.
        if any(not isinstance(key, str) or not isinstance(value, (str, int, float)) or isinstance(value, bool)
               for key, value in specification.parameters.items()):
            raise ValueError("KIS 입력값은 문자열 또는 숫자여야 합니다.")
        json.dumps(specification.parameters, allow_nan=False)
        client = self.market_client
        transaction_id = specification.transaction_id
        # 공식 공통 전송부의 모의 TR 변환 규칙. 함수가 이미 V로 만들었으면 그대로 사용한다.
        if client.environment == "vps" and transaction_id.startswith(("T", "J", "C")):
            transaction_id = "V" + transaction_id[1:]
        for attempt in range(2 if specification.method == "GET" else 1):
            try:
                client.authenticate()
            except KisApiError as error:
                error.stage='authentication'
                raise
            except OSError:
                raise KisApiError("KIS 인증 캐시 저장을 확인하세요.",stage="authentication",category="token_storage_error") from None
            audit_start = len(self.http_audit)
            try:
                result = self._http(specification.path, specification.parameters, specification.method,
                    {"authorization": "Bearer " + client.access_token, "appkey": client.app_key,
                     "appsecret": client.app_secret, "tr_id": transaction_id, "custtype": "P",
                     "tr_cont": specification.continuation}, order=specification.changes_account)
            except KisRateLimitError:
                for row in self.http_audit[audit_start:]:
                    row.update(operation=specification.name, attempt=attempt + 1,
                               retry_scheduled=specification.method == "GET" and attempt == 0)
                client.next_request_at = max(client.next_request_at, time.monotonic() + 2)
                if specification.method != "GET" or attempt == 1:
                    raise
                continue
            for row in self.http_audit[audit_start:]:
                row.update(operation=specification.name, attempt=attempt + 1, retry_scheduled=False)
            if specification.changes_account and result.payload.get("rt_cd") not in {"0", "1"}:
                raise KisOrderStateUnknown("KIS 주문 처리 결과 누락. 주문 상태를 먼저 확인하세요.")
            if result.payload.get("rt_cd") != "0":
                code = str(result.payload.get("msg_cd", ""))
                code = code if re.fullmatch(r"[A-Z0-9_-]{1,32}", code) else "UNKNOWN"
                error_class = KisOrderRejected if specification.changes_account else KisApiError
                raise error_class(f"KIS API 처리 거절 ({code}). 권한·입력값·실전/모의 지원을 확인하세요.",stage="account_http",category="business_error",provider_code=code)
            return result

    def validate_managed(self, specification, manager, intent_id):
        """신규 주문 권한과 취소 권한을 분리한다. 실제 HTTP를 보내지 않는다."""
        try:
            from broker.diagnostic import require_broker_orders_allowed
            require_broker_orders_allowed()
            validate_operation(specification, "rest", self.market_client.environment, self.catalog)
            if manager.state.get('replay_only'):
                raise ValueError('replay_store_never_sends_orders')
            order = manager.state["orders"].get(intent_id)
            cancel = specification.name == "overseas_stock.order_rvsecncl"
            if self.market_client.environment != "vps" or manager.state["mode"] != "kis_demo" or not order:
                raise ValueError("mode_or_order_unverified")
            if cancel:
                if not manager.can_cancel(intent_id, allow_sending=True):
                    raise ValueError("cancel_identity_unverified")
            elif order["status"] != "SENDING":
                raise ValueError("order_not_sending")
            elif not manager.ready:
                from trading.execution_observation import validate_reduction
                validate_reduction(manager, order)
            if not cancel and order['side'] == 'BUY':
                if order.get("strategy_owner"):
                    from app.universe import current_entry_allowed
                    if not current_entry_allowed(order["symbol"], datetime.now(timezone.utc)):
                        raise ValueError("universe_no_longer_eligible")
                from trading.cash_service_policy import require_cash_only
                require_cash_only(manager)
                from trading.buying_power import assess_buying_power
                from decimal import Decimal
                budget = assess_buying_power(manager.state["account"], manager.state["orders"].values(),
                    current_id=intent_id,
                    order_cost=str(Decimal(order["quantity"]-order.get("filled",0)) * Decimal(order["price"]) * Decimal("1.003")))
                if not budget["within_buying_power"]:
                    raise ValueError("broker_buying_power_exceeded")
                from trading.risk_ledger import RiskLedger
                from trading.cash_service_policy import require_usd_funding
                require_usd_funding(manager, order)
                from trading.demo_user_basis import require_execution_basis
                require_execution_basis(manager,order=order)
                if intent_id in manager.state.get('limited_demo_session', {}).get('order_ids', []):
                    from trading.demo_accounting_cycle import validate_pretrade
                    validate_pretrade(manager, intent_id)
            parameters = specification.parameters
            import hashlib
            identity = hashlib.sha256((self.market_client.environment + "\0" + str(self.market_client.app_key) + "\0" + str(parameters.get("CANO")) + "\0" + str(parameters.get("ACNT_PRDT_CD"))).encode()).hexdigest()
            if manager.state.get("broker_identity") != identity:
                raise ValueError("account_identity_mismatch")
            if str(parameters.get("PDNO")) != order["symbol"]:
                raise ValueError("symbol_mismatch")
            expected = manager.cancellation_quantity(intent_id) if cancel else order["quantity"]
            if str(parameters.get("ORD_QTY")) != str(expected):
                raise ValueError("quantity_mismatch")
            if cancel:
                if (parameters.get("ORGN_ODNO") != order["broker_id"].split(":")[-1]
                        or parameters.get("RVSE_CNCL_DVSN_CD") != "02" or str(parameters.get("OVRS_ORD_UNPR")) != "0"):
                    raise ValueError("cancel_original_mismatch")
            else:
                from decimal import Decimal
                if specification.name != "overseas_stock.order" or Decimal(str(parameters.get("OVRS_ORD_UNPR"))) != Decimal(order["price"]):
                    raise ValueError("price_or_type_mismatch")
                expected_tr = "VTTT1002U" if order["side"] == "BUY" else "VTTT1001U"
                if specification.transaction_id != expected_tr or parameters.get("ORD_DVSN") != "00":
                    raise ValueError("limit_order_required")
        except Exception:
            raise KisPreflightError("managed_order_preflight_failed") from None

    def _enforce_managed_policy(self, path, parameters):
        """부울 허가만으로 전송하지 않는다. 현재 계좌·상품·현금 정책을 재검사한다."""
        context = getattr(self, "_managed_policy_context", None)
        if context is None:
            raise KisPreflightError("managed_policy_context_required")
        specification, manager, intent_id = context
        if specification.path != path or specification.parameters != parameters:
            raise KisPreflightError("managed_policy_request_changed")
        self.validate_managed(specification, manager, intent_id)

    def execute_managed(self, specification, manager, intent_id):
        self.validate_managed(specification, manager, intent_id)
        self._order_http_started = False
        self._managed_permission = True
        self._managed_policy_context = (specification, manager, intent_id)
        try:
            return self.execute(specification)
        except (KisOrderStateUnknown, KisOrderRejected):
            raise
        except Exception:
            if not self._order_http_started:
                raise KisPreflightError("managed_order_not_transmitted") from None
            raise KisOrderStateUnknown("managed_order_response_unknown") from None
        finally:
            self._managed_permission = False
            self._managed_policy_context = None

    def approval_key(self):
        """실시간 접속키 발급. REST 토큰을 재발급하거나 파일에 접속키를 노출하지 않는다."""
        client = self.market_client
        result = self._http("/oauth2/Approval", {"grant_type": "client_credentials", "appkey": client.app_key,
                            "secretkey": client.app_secret}, "POST")
        key = result.payload.get("approval_key")
        if not isinstance(key, str) or not key:
            raise KisApiError("KIS 실시간 접속키 응답 오류")
        return key

    def authenticate(self):
        """기존 발급 시각·서버 만료·24시간 제한과 파일 잠금을 그대로 사용한다."""
        self.market_client.authenticate()

    def hash_key(self, parameters):
        client = self.market_client
        result = self._http("/uapi/hashkey", parameters, "POST", {"appkey": client.app_key, "appsecret": client.app_secret})
        value = result.payload.get("HASH")
        if not isinstance(value, str) or not value:
            raise KisApiError("KIS 해시키 응답 오류")
        return value

    def revoke_token(self):
        """명시적으로 호출할 때만 토큰을 폐기한다. 정상 종료 시 자동 호출하지 않는다."""
        client = self.market_client
        if not self.allow_trading:
            raise KisApiError("다른 실행의 토큰을 폐기할 수 있어 기본 모드에서는 차단합니다.")
        client.authenticate()
        result = self._http("/oauth2/revokeP", {"appkey": client.app_key, "appsecret": client.app_secret,
                            "token": client.access_token}, "POST")
        if str(result.payload.get("code")) != "200":
            raise KisApiError("KIS 토큰 폐기 응답을 확인하세요.")
        client.access_token = ""
        client.token_valid_until = 0
        client.token_issued_at = 0
        if client.token_cache and Path(client.token_cache).exists():
            Path(client.token_cache).unlink()
        return result
