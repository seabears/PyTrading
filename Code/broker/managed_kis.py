"""기존 KIS 요청 생성기를 사용하는 모의투자 전용 실행 어댑터. 실계좌 전송은 금지한다."""

from broker.kis_api import overseas_stock
from broker.kis_api.client import KisOrderStateUnknown, KisPreflightError


class ManagedKisAdapter:
    def __init__(self, api, manager, account_number, product_code, exchanges, *, enabled=False):
        self.api, self.manager = api, manager
        self.account_number, self.product_code, self.exchanges = (
            account_number,
            product_code,
            exchanges,
        )
        self.enabled = enabled
        self._account_fingerprint = None
        # 별칭이 같아도 다른 실제 계좌·앱 키를 같은 원장에 연결하지 않는다.
        import hashlib

        identity = hashlib.sha256(
            (
                api.market_client.environment
                + "\0"
                + str(api.market_client.app_key)
                + "\0"
                + account_number
                + "\0"
                + product_code
            ).encode()
        ).hexdigest()
        if manager.state.get("broker_identity", identity) != identity:
            raise ValueError("주문 원장과 증권사 인증·계좌가 다릅니다.")
        self._account_fingerprint = identity
        manager.state["broker_identity"] = identity
        manager._save()

    def _guard(self, *, read_only=False):
        import hashlib

        if not read_only and self.manager.state.get("replay_only"):
            raise ValueError("replay_store_never_sends_orders")
        current = hashlib.sha256(
            (
                self.api.market_client.environment
                + "\0"
                + str(self.api.market_client.app_key)
                + "\0"
                + self.account_number
                + "\0"
                + self.product_code
            ).encode()
        ).hexdigest()
        if current != self._account_fingerprint or current != self.manager.state.get(
            "broker_identity"
        ):
            raise ValueError("account_binding_changed")
        if (
            (not read_only and not self.enabled)
            or self.manager.state["mode"] != "kis_demo"
            or self.api.market_client.environment != "vps"
        ):
            raise ValueError(
                "KIS 모의투자 명시 활성화와 독립 vps 인증이 필요합니다. 실계좌 전송은 금지합니다."
            )

    def submit(self, order):
        self._guard()
        specification = overseas_stock.order(
            self.account_number,
            self.product_code,
            self.exchanges[order["symbol"]],
            order["symbol"],
            str(order["quantity"]),
            order["price"],
            order["side"].lower(),
            "",
            "",
            "0",
            "00",
            env_dv="demo",
        )
        response = self.api.execute_managed(specification, self.manager, order["id"])
        output = response.payload.get("output")
        if not isinstance(output, dict) or not output.get("ODNO", output.get("odno")):
            raise KisOrderStateUnknown("접수 번호를 확인하지 못했습니다.")
        from datetime import datetime
        from zoneinfo import ZoneInfo

        day = datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d")
        return day + ":" + str(output.get("ODNO", output.get("odno")))

    def _cancel_request(self, order):
        self._guard()
        return overseas_stock.order_rvsecncl(
            self.account_number,
            self.product_code,
            self.exchanges[order["symbol"]],
            order["symbol"],
            order["broker_id"].split(":")[-1],
            "02",
            str(order["cancel_quantity"]),
            "0",
            "",
            "0",
            env_dv="demo",
        )

    def prepare_cancel(self, order):
        specification = self._cancel_request(order)
        self.api.validate_managed(specification, self.manager, order["id"])

    def cancel(self, order):
        # 준비 검사 뒤 설정이 바뀌어도 전송 전 실패를 응답 유실로 기록하지 않는다.
        try:
            specification = self._cancel_request(order)
        except Exception as error:
            raise KisPreflightError("cancel_request_preflight_failed") from error
        response = self.api.execute_managed(specification, self.manager, order["id"])
        output = response.payload.get("output")
        if not isinstance(output, dict) or not output.get("ODNO", output.get("odno")):
            raise KisOrderStateUnknown("cancel_acknowledgement_missing")
        from datetime import datetime
        from zoneinfo import ZoneInfo

        return (
            datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d")
            + ":"
            + str(output.get("ODNO", output.get("odno")))
        )

    def query_history(self, start, end):
        """모의는 주문번호·종목 필터 없이 전종목/전체상태로 모든 페이지를 조회한다."""
        self._guard(read_only=True)
        rows, previous, first, following, continuation = [], None, "", "", ""
        for _ in range(20):
            request = overseas_stock.inquire_ccnl(
                self.account_number,
                self.product_code,
                "",
                start,
                end,
                "00",
                "00",
                "DS",
                "",
                "",
                "",
                ovrs_excg_cd="",
                NK200=following,
                FK200=first,
                env_dv="demo",
                tr_cont=continuation,
            )
            response = self.api.execute(request)
            page_rows = response.rows("output")
            for row in page_rows:
                if ("cano" in row and row["cano"] != self.account_number) or (
                    "acnt_prdt_cd" in row and row["acnt_prdt_cd"] != self.product_code
                ):
                    raise ValueError("response_account_mismatch")
            rows.extend(page_rows)
            if not response.has_more:
                return rows
            first = response.payload.get("ctx_area_fk200", "")
            following = response.payload.get("ctx_area_nk200", "")
            if not following or (first, following) == previous:
                raise ValueError("주문 이력 페이지 커서 반복·누락")
            previous, continuation = (first, following), "N"
        raise ValueError("전체 주문 이력 조회 상한 초과. 대조 완료로 처리하지 않습니다.")

    def query_balances(self):
        """미국 3거래소를 각각 조회하고 중복 종목은 정상화 단계에서 검산한다."""
        self._guard(read_only=True)
        result = []
        for exchange in ("NASD", "NYSE", "AMEX"):
            first, following, previous = "", "", None
            for page in range(20):
                request = overseas_stock.inquire_balance(
                    self.account_number,
                    self.product_code,
                    exchange,
                    "USD",
                    FK200=first,
                    NK200=following,
                    env_dv="demo",
                    tr_cont="" if page == 0 else "N",
                )
                response = self.api.execute(request)
                page_rows = response.rows("output1")
                for row in page_rows:
                    if ("cano" in row and row["cano"] != self.account_number) or (
                        "acnt_prdt_cd" in row and row["acnt_prdt_cd"] != self.product_code
                    ):
                        raise ValueError("balance_account_mismatch")
                result.extend(page_rows)
                if not response.has_more:
                    break
                first, following = response.payload.get("ctx_area_fk200", ""), response.payload.get(
                    "ctx_area_nk200", ""
                )
                if not following or (first, following) == previous:
                    raise ValueError("잔고 페이지 커서 오류")
                previous = first, following
            else:
                raise ValueError("잔고 전체 조회 미완료")
        return result

    def query_buying_power(self, symbol, price):
        self._guard(read_only=True)
        request = overseas_stock.inquire_psamount(
            self.account_number,
            self.product_code,
            self.exchanges[symbol],
            str(price),
            symbol,
            env_dv="demo",
        )
        return self.api.execute(request).payload

    def query_present_balance(self):
        """미국 외화 현재잔고 전체 출력을 읽는다. 반복 페이지·미완료 상태는 거절한다."""
        self._guard(read_only=True)
        output = {"output1": [], "output2": [], "output3": []}
        seen = set()
        continuation = ""
        import hashlib, json

        for _ in range(20):
            request = overseas_stock.inquire_present_balance(
                self.account_number,
                self.product_code,
                "02",
                "840",
                "00",
                "00",
                env_dv="demo",
                tr_cont=continuation,
            )
            response = self.api.execute(request)
            signature = hashlib.sha256(
                json.dumps(response.payload, sort_keys=True).encode()
            ).hexdigest()
            if signature in seen:
                raise ValueError("present_balance_page_repeated")
            seen.add(signature)
            for key in output:
                rows = response.rows(key)
                for row in rows:
                    if ("cano" in row and row["cano"] != self.account_number) or (
                        "acnt_prdt_cd" in row and row["acnt_prdt_cd"] != self.product_code
                    ):
                        raise ValueError("present_balance_account_mismatch")
                output[key].extend(rows)
            if not response.has_more:
                return output
            continuation = "N"
        raise ValueError("present_balance_pages_incomplete")


def create_demo_api(credentials_path, *, allow_trading=False):
    """명시적 모의투자 호출에서만 인증 파일을 읽는다. 시세·실전 토큰과 별도로 저장한다."""
    from broker.credentials import read_credentials_file
    from broker.kis import KisMarketClient
    from broker.kis_api.client import KisApiClient
    from paths import DATA_ROOT

    key, secret = read_credentials_file(credentials_path)
    market = KisMarketClient(key, secret, "vps")
    market.token_cache = DATA_ROOT / "cache/kis/vps" / ("orders-" + market.identity[:16] + ".json")
    return KisApiClient(market, allow_trading=allow_trading)
