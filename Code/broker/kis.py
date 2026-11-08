"""KIS 읽기 전용 REST 연결. 인증 POST와 명시한 시세 GET만 허용한다.

실전용 키(prod)는 실제 시세를 읽는 용도다. 계좌번호·주문 API는 받거나 호출하지 않는다.
요청 간격은 보수적 기본값이며 실제 계약 한도를 보장하는 수치가 아니다.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_URLS = {"prod": "https://openapi.koreainvestment.com:9443",
             "vps": "https://openapivts.koreainvestment.com:29443"}
TOKEN_REUSE_SECONDS = 24 * 60 * 60
TOKEN_TIMEZONE = timezone(timedelta(hours=9))

TOKEN_PATH = "/oauth2/tokenP"
READ_OPERATIONS = {
    "/uapi/overseas-price/v1/quotations/dailyprice": "HHDFS76240000",
    "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice": "FHKST03010200",
    "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn": "FHKST01010200",
    "/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice": "HHDFS76950200",
    "/uapi/overseas-price/v1/quotations/inquire-asking-price": "HHDFS76200100",
}


class KisApiError(RuntimeError):
    """자유문 예외와 분리된 허용 목록 기반 진단. 키·본문·헤더는 저장하지 않는다."""
    def __init__(self, message, *, stage="quote_http", category="api_error", http_status=None, provider_code=None):
        super().__init__(message)
        self.stage = stage
        self.category = category
        self.http_status = http_status
        self.provider_code = provider_code if provider_code in {
            "EGW00103", "EGW00121", "EGW00123", "EGW00201", "EGW00133"} else None

    def diagnostic(self):
        return {"stage": self.stage, "category": self.category,
                "http_status": self.http_status, "provider_code": self.provider_code}



class KisAuthenticationExpired(KisApiError):
    pass


class KisRateLimitError(KisApiError):
    pass


class KisMarketClient:
    source_name = "kis"

    def __init__(self, app_key, app_secret, environment="prod", token_cache: Path | None = None):
        if environment not in BASE_URLS or not app_key or not app_secret:
            raise KisApiError("KIS 실행 환경 또는 인증값을 확인하세요.")
        self.app_key, self.app_secret = app_key, app_secret
        self.environment = environment
        self.token_cache = token_cache
        self.access_token = ""
        self.token_valid_until = 0.0
        self.token_issued_at = 0.0
        self.next_request_at = 0.0
        self.next_token_request_at = 0.0
        self.connection_retry_at = 0.0
        self.last_timings = {}
        self._pending_token_event = None
        self.request_interval = 0.1 if environment == "prod" else 0.6
        self.identity = hashlib.sha256((environment + app_key + app_secret).encode()).hexdigest()

    def _wait(self):
        delay = self.next_request_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self.next_request_at = time.monotonic() + self.request_interval

    def _request(self, path, parameters=None, *, token_request=False):
        """인증값·HTTP 오류 본문·msg1을 출력하지 않는다. 알려진 오류 코드만 해석한다."""
        if token_request:
            if path != TOKEN_PATH:
                raise KisApiError("허용되지 않은 인증 경로입니다.")
            payload = json.dumps({"grant_type": "client_credentials", "appkey": self.app_key,
                                  "appsecret": self.app_secret}).encode()
            request = urllib.request.Request(BASE_URLS[self.environment] + path, data=payload,
                                             headers={"Content-Type": "application/json"}, method="POST")
        else:
            if path not in READ_OPERATIONS:
                raise KisApiError("허용되지 않은 KIS API 경로입니다.")
            from broker.product_policy import validate_product_request
            validate_product_request(path, parameters or {})
            query = urllib.parse.urlencode(parameters or {})
            request = urllib.request.Request(BASE_URLS[self.environment] + path + "?" + query, headers={
                "Content-Type": "application/json; charset=utf-8", "authorization": "Bearer " + self.access_token,
                "appkey": self.app_key, "appsecret": self.app_secret,
                "tr_id": READ_OPERATIONS[path], "custtype": "P",
            })
        self._wait()
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.load(response)
        except urllib.error.HTTPError as error:
            status = error.code
            try:
                data = json.loads(error.read(16384))
            except (ValueError, UnicodeError):
                data = {}
            finally:
                error.close()
            metadata = {"stage": "authentication" if token_request else "quote_http",
                        "http_status": status,
                        "provider_code": data.get("msg_cd") if isinstance(data, dict) else None}
            if not token_request and isinstance(data, dict) and data.get("msg_cd") in {"EGW00121", "EGW00123"}:
                raise KisAuthenticationExpired("KIS 인증 만료", category="authentication_expired", **metadata) from None
            if status == 429 or (isinstance(data, dict) and data.get("msg_cd") == "EGW00201"):
                raise KisRateLimitError("KIS 호출 한도 초과. 요청을 잠시 대기합니다.", category="rate_limit", **metadata) from None
            if status == 401 and not token_request:
                raise KisAuthenticationExpired("KIS 인증 만료", category="authentication_expired", **metadata) from None
            if status >= 500:
                self.connection_retry_at = time.monotonic() + 60
            raise KisApiError(f"KIS HTTP {status}: 인증·API 권한·실전/모의 키 구분을 확인하세요.", category="http_error", **metadata) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            self.connection_retry_at = time.monotonic() + 60
            raise KisApiError("KIS 연결 실패: 인터넷·DNS·방화벽을 확인하세요.",
                              category="connection_error", stage="authentication" if token_request else "quote_http") from None
        except (ValueError, UnicodeError):
            raise KisApiError("KIS 응답을 JSON으로 읽을 수 없습니다.") from None
        if not isinstance(data, dict):
            raise KisApiError("KIS 응답이 JSON 객체가 아닙니다.")
        if data.get("msg_cd") == "EGW00201":
            raise KisRateLimitError("KIS 호출 한도 초과. 요청을 잠시 대기합니다.")
        if not token_request and data.get("rt_cd") != "0":
            if data.get("msg_cd") in {"EGW00121", "EGW00123"}:
                raise KisAuthenticationExpired("KIS 토큰이 유효하지 않습니다. 키·토큰 만료·다른 실행을 확인하세요.")
            raise KisApiError("KIS 시세 조회 거절: 종목·거래소 코드·시세 이용 권한을 확인하세요.")
        return data

    def _token_is_reusable(self, issued_at, valid_until):
        """24시간 미만이면서 서버 만료 전인 토큰만 재사용한다. 미래 발급 시각은 거부한다."""
        now = time.time()
        return (math.isfinite(issued_at) and math.isfinite(valid_until)
                and 0 <= now - issued_at < TOKEN_REUSE_SECONDS and now < valid_until)

    def _save_token(self, issued_at_source=None):
        """발급·만료 시각은 한국 시간 ISO 형식으로 저장한다. 토큰 파일은 비밀 파일이다."""
        if self.token_cache is None:
            return
        record = {
            "version": 2, "identity": self.identity, "access_token": self.access_token,
            "issued_at": datetime.fromtimestamp(self.token_issued_at, TOKEN_TIMEZONE).isoformat(),
            "expires_at": datetime.fromtimestamp(self.token_valid_until, TOKEN_TIMEZONE).isoformat(),
            "reuse_until": datetime.fromtimestamp(min(self.token_issued_at + TOKEN_REUSE_SECONDS,
                                                      self.token_valid_until), TOKEN_TIMEZONE).isoformat(),
            "valid_until": self.token_valid_until,
        }
        if issued_at_source is not None:
            record["issued_at_source"] = issued_at_source
        temporary = self.token_cache.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.token_cache)

    def _load_cached_token(self):
        if self.token_cache is None or not self.token_cache.exists():
            return False
        try:
            saved = json.loads(self.token_cache.read_text(encoding="utf-8"))
            expiry = float(saved["valid_until"])
            if "issued_at" in saved:
                moment = datetime.fromisoformat(saved["issued_at"])
                if moment.tzinfo is None:
                    return False
                issued_at = moment.timestamp()
            else:
                # 기존 파일에는 만료 시각만 있었다. 재발급 없이 보수적으로 24시간 전을 사용한다.
                # 실제 발급 시각을 아는 것으로 기록하지 않도록 별도 근거를 남긴다.
                issued_at = expiry - TOKEN_REUSE_SECONDS
            if saved["identity"] != self.identity or not self._token_is_reusable(issued_at, expiry):
                return False
            token = saved["access_token"]
            if not isinstance(token, str) or not token:
                return False
            self.access_token, self.token_valid_until, self.token_issued_at = token, expiry, issued_at
        except (ValueError, KeyError, TypeError, OSError, OverflowError):
            return False
        if "issued_at" not in saved:
            self._save_token(issued_at_source="legacy_expiry_minus_24_hours")
        return True

    def _flush_token_event(self):
        """이력 저장 실패는 다음 호출에서 재시도하되 토큰을 다시 발급하지 않는다."""
        from app.audit_logs import append_token_event, token_event_path
        path = token_event_path(self.token_cache)
        if self._pending_token_event is not None and path is not None:
            append_token_event(path, self._pending_token_event)
            self._pending_token_event = None

    def authenticate(self):
        """만료 전 토큰을 재사용한다. 다른 실행의 캐시도 잠금 안에서 확인한다."""
        self._flush_token_event()
        if self.access_token and self._token_is_reusable(self.token_issued_at, self.token_valid_until):
            return
        lock = None
        issuance_attempted = False
        if self.token_cache is not None:
            from app.runtime import acquire_run_lock
            self.token_cache.parent.mkdir(parents=True, exist_ok=True)
            lock = acquire_run_lock(self.token_cache.with_suffix(".lock"))
        try:
            if self._load_cached_token():
                return
            delay = self.next_token_request_at - time.monotonic()
            if delay > 0:
                # 공통 장애 때 30종목이 각각 60초 대기하지 않는다. 발급 간격 자체는 유지한다.
                raise KisApiError("KIS 인증 재시도 대기 중", stage="authentication", category="authentication_cooldown")
            self.next_token_request_at = time.monotonic() + 60
            issued_at = time.time()
            issuance_attempted = True
            data = self._request(TOKEN_PATH, token_request=True)
            token, lifetime = data.get("access_token"), data.get("expires_in")
            if not isinstance(token, str) or not token or str(data.get("token_type", "")).lower() != "bearer":
                raise KisApiError("KIS 토큰 응답의 access_token·token_type을 확인하세요.")
            if type(lifetime) is not int or lifetime <= 60:
                raise KisApiError("KIS 토큰 응답의 유효 시간이 잘못됐습니다.")
            expiry = time.time() + lifetime
            if data.get("access_token_token_expired"):
                try:
                    absolute = datetime.strptime(data["access_token_token_expired"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(timedelta(hours=9)))
                    expiry = min(expiry, absolute.timestamp())
                except (ValueError, TypeError):
                    raise KisApiError("KIS 토큰 만료 시각 형식을 확인하세요.") from None
            if expiry <= time.time() + 60:
                raise KisApiError("KIS가 만료된 토큰을 반환했습니다.")
            self.access_token, self.token_valid_until, self.token_issued_at = token, expiry, issued_at
            from app.audit_logs import token_event
            self._pending_token_event = token_event(self.environment, issued_at, expiry)
            self._save_token()
            self._flush_token_event()
        except KisApiError as error:
            error.stage = "authentication"
            if issuance_attempted:
                from app.audit_logs import token_event
                self._pending_token_event = token_event(self.environment, error=error.diagnostic())
                try:
                    self._flush_token_event()
                except (OSError, ValueError):
                    # 이력 저장 실패가 원래 인증 실패의 단계·HTTP 코드를 지우지 않는다.
                    print("KIS 인증 이력 저장 실패 — 다음 호출에서 재시도합니다.", flush=True)
            raise
        finally:
            if lock is not None:
                lock.close()

    def get(self, path, parameters=None):
        """실패를 포함한 이번 요청의 인증·시세 소요 시간을 새로 측정한다."""
        started = time.monotonic()
        self.last_timings = {"authentication_seconds": 0.0, "quote_http_seconds": 0.0}
        try:
            if time.monotonic() < self.connection_retry_at:
                raise KisApiError("공통 연결 재시도 대기 중", category="connection_cooldown")
            return self._get_with_retry(path, parameters)
        finally:
            self.last_timings["total_seconds"] = time.monotonic() - started

    def _get_with_retry(self, path, parameters=None):
        if path not in READ_OPERATIONS:
            raise KisApiError("허용되지 않은 KIS API 경로입니다.")
        from broker.product_policy import validate_product_request
        validate_product_request(path, parameters or {})
        for attempt in range(2):
            auth_started = time.monotonic()
            try:
                self.authenticate()
            finally:
                self.last_timings["authentication_seconds"] += time.monotonic() - auth_started
            try:
                quote_started = time.monotonic()
                try:
                    return self._request(path, parameters)
                finally:
                    self.last_timings["quote_http_seconds"] += time.monotonic() - quote_started
            except KisAuthenticationExpired:
                if attempt == 1:
                    raise
                self.access_token = ""
                self.token_valid_until = 0
                if self.token_cache is not None and self.token_cache.exists():
                    self.token_cache.replace(self.token_cache.with_suffix(".invalid"))
            except KisRateLimitError:
                self.next_request_at = max(self.next_request_at, time.monotonic() + 2 ** attempt)
                if attempt == 1:
                    raise
                print("KIS 호출 한도 초과 — 대기 후 시세 조회를 한 번 재시도합니다.", flush=True)
