"""상품 사용 정책: 주식·채권·ETF만 허용. ETN·파생상품·미확인 종목은 전송하지 않는다.

공용 시세·주문 API는 URL만으로 ETF와 ETN을 구별할 수 없다.
그래서 전송 전에 확인된 종목 목록의 상품 종류를 검사한다. 새 종목은 종류 확인 후 등록한다.
"""
import json
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit

from paths import CONFIG_ROOT

ALLOWED_PATH_PREFIXES = (
    "/uapi/domestic-stock/", "/uapi/overseas-stock/", "/uapi/overseas-price/",
    "/uapi/domestic-bond/", "/uapi/etfetn/",
)
COMMON_PATHS = frozenset({"/oauth2/tokenP", "/oauth2/Approval", "/oauth2/revokeP", "/uapi/hashkey"})
SYMBOL_FIELDS = frozenset({"PDNO", "SYMB", "MKSC_SHRN_ISCD", "SHRN_ISCD", "FID_INPUT_ISCD"})
MARKET_FILTERS = frozenset({"", "0", "0000", "00000", "000000", "ALL", "%"})


def reject(message):
    from broker.kis import KisApiError
    raise KisApiError(message)


def load_product_rules():
    rules = json.loads((CONFIG_ROOT / "product-policy.json").read_text(encoding="utf-8"))
    if set(rules["allowed_asset_types"]) != {"stock", "bond", "etf"}:
        reject("상품 정책은 주식·채권·ETF만 허용해야 합니다.")
    # 공식 KIS 마스터로 확인한 추가 USD 주식만 합친다. 기존 불허 판정은 그대로 둔다.
    from broker.universe_data import verified_stocks
    try:
        discovered = verified_stocks()
    except (OSError, ValueError, KeyError, TypeError):
        discovered = {}
    for symbol, item in discovered.items():
        rules["verified_instruments"].setdefault(symbol, item)
    return rules


def validate_etf_evidence(symbol, item):
    """ETF 분류만으로 허용하지 않는다. 선물 여부·해당 종목·공식 근거를 확인한다."""
    review = item.get("futures_review")
    if item.get("futures_based") is True or (isinstance(review, dict) and review.get("status") == "futures"):
        reject("선물 기반 ETF 및 선물 기반 레버리지·인버스 ETF는 사용 불허입니다.")
    # 2026-11-01 사용자 요청: KODEX200의 근거 미확인 조건만 종목 한정 예외로 둔다.
    # 선물 미사용을 증명한 것이 아니다. 다른 ETF로 복사하거나 확정 선물 상품에 쓰지 않는다.
    exception = item.get("policy_exception", {})
    if (symbol == "069500" and exception.get("id") == "kodex200-user-allow-20261101"
            and exception.get("symbol") == symbol
            and exception.get("authority") == "user_explicit_instruction"
            and exception.get("authorized_on") == "2026-11-01"
            and exception.get("scope") == "unconfirmed_futures_evidence_only"
            and exception.get("reason")):
        return
    if item.get("futures_based") is not False or not isinstance(review, dict) or review.get("status") != "non_futures":
        reject("ETF의 선물 기반 여부가 확인되지 않아 사용할 수 없습니다.")
    if review.get("symbol") != symbol or not review.get("basis"):
        reject("ETF 선물 판정 근거의 종목 연결이 불명확합니다.")
    source = review.get("source", {})
    parsed = urlsplit(source.get("url", ""))
    checksum = source.get("sha256", "")
    try:
        checked = date.fromisoformat(review["checked_on"])
        if checked > datetime.now(ZoneInfo("Asia/Seoul")).date():
            raise ValueError("future_review_date")
    except (KeyError, TypeError, ValueError):
        reject("ETF 선물 판정 확인일이 올바르지 않습니다.")
    if (source.get("kind") != "issuer_official_document" or parsed.scheme != "https"
            or not parsed.hostname or not isinstance(checksum, str)
            or not re.fullmatch(r"[0-9a-f]{64}", checksum)):
        reject("ETF 선물 판정의 공식 자료 출처·해시가 없습니다.")


def validate_symbol(symbol, rules):
    """코드 모양만 보고 ETF라고 추측하지 않는다. Q 접두사 ETN과 등록되지 않은 종목도 차단한다."""
    value = str(symbol).strip().upper()
    if value in MARKET_FILTERS:
        return
    if re.fullmatch(r"Q\d{6}", value):
        reject("ETN은 사용 불허 상품입니다.")
    item = rules["verified_instruments"].get(value)
    if not item:
        reject("상품 종류가 확인되지 않은 종목입니다. 주식·채권·ETF 여부를 확인해 등록하세요.")
    if item.get("asset_type") not in rules["allowed_asset_types"]:
        reject("사용 불허 상품입니다. 주식·채권·ETF만 허용합니다.")
    if item.get("asset_type") == "etf":
        validate_etf_evidence(value, item)


def validate_product_request(path, parameters, *, operation="", subscription=False):
    """요청 생성은 보존하고 실제 REST 전송·실시간 구독 직전에만 검사한다."""
    rules = load_product_rules()
    if path and path not in COMMON_PATHS:
        if not path.startswith(ALLOWED_PATH_PREFIXES) or "elw" in path.lower():
            reject("사용 불허 상품 API입니다. 주식·채권·ETF만 허용합니다.")
    if path in COMMON_PATHS:
        return
    if subscription:
        # 체결통보의 키는 종목이 아닌 HTS ID, 장 상태·지수 구독은 상품 주문과 무관하다.
        if any(word in operation for word in ("notice", "market_status", "index_", "vi_")):
            return
        value = str(parameters.get("tr_key", "")).upper()
        if value.startswith(("DNAS", "DNYS", "DAMS", "RNAS", "RNYS", "RAMS", "RBAQ", "RBAY", "RBAA")):
            value = value[4:]
        validate_symbol(value, rules)
        return
    # 시장·업종 지수와 순위 검색의 시장코드는 개별 증권 코드가 아니다.
    market_query = any(word in path for word in ("/ranking/", "index", "industry", "market-time"))
    for key, value in parameters.items():
        upper = str(key).upper()
        if upper in SYMBOL_FIELDS or re.fullmatch(r"SYMB_\d{2}", upper):
            if upper == "FID_INPUT_ISCD" and market_query:
                if re.fullmatch(r"Q\d{6}", str(value).upper()):
                    reject("ETN은 사용 불허 상품입니다.")
                continue
            validate_symbol(value, rules)
