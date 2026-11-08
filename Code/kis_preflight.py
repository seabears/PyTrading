"""KIS 모의투자 계좌의 읽기 전용 사전 검사. 주문·정정·취소 경로는 연결하지 않는다."""

import os
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.runtime import load_run_settings
from broker.credentials import read_credentials_file
from broker.kis import KisMarketClient
from broker.kis_setup import load_kis_settings
from broker.managed_kis import ManagedKisAdapter
from broker.kis_readonly import ReadOnlyKisApi, inspect_remote
from paths import CODE_ROOT, CONFIG_ROOT, DATA_ROOT
from trading.orders import OrderManager


def read_demo_identity(path):
    """분리형 또는 ACC_NO 결합형을 읽는다. 모의 전용 도구는 항상 vps로만 접속한다.

    환경 표기가 생략되면 이 도구의 vps 기본값을 사용한다. prod 등 다른 환경이
    명시되면 거절한다. 두 계좌 형식이 함께 있으면 서로 일치해야 한다.
    """
    key, secret = read_credentials_file(path)
    values = {}
    accepted = {'KIS_ENVIRONMENT', 'KIS_ACCOUNT_NUMBER', 'KIS_ACCOUNT_PRODUCT_CODE', 'ACC_NO'}
    for original in path.read_text(encoding='utf-8-sig').splitlines():
        line = original.strip()
        if not line or line.startswith('#'):
            continue
        name, separator, value = line.partition('=')
        name, value = name.strip(), value.strip()
        if name not in accepted:
            continue
        if name in values or not separator:
            raise ValueError('demo_identity_duplicate')
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError('demo_identity_quote_invalid')
            value = value[1:-1]
        values[name] = value
    if values.get('KIS_ENVIRONMENT', 'vps') != 'vps':
        raise ValueError('demo_environment_mismatch')
    account = values.get('KIS_ACCOUNT_NUMBER', '')
    product = values.get('KIS_ACCOUNT_PRODUCT_CODE', '')
    if 'ACC_NO' in values:
        parts = values['ACC_NO'].split('-')
        if len(parts) != 2:
            raise ValueError('demo_account_format_invalid')
        combined_account, combined_product = parts
        if (account and account != combined_account) or (product and product != combined_product):
            raise ValueError('demo_account_fields_conflict')
        account, product = combined_account, combined_product
    if (len(account) != 8 or not account.isascii() or not account.isdecimal()
            or len(product) != 2 or not product.isascii() or not product.isdecimal()):
        raise ValueError('demo_account_format_invalid')
    return key, secret, account, product


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_ROOT / ("kis-preflight.json" if os.name == "nt" else "kis-preflight-linux.json"))
    parser.add_argument("--env-file", type=Path, help="명시한 모의투자 전용 파일만 읽음")
    arguments = parser.parse_args()
    manager = None
    api = None
    try:
        settings = json.loads(arguments.config.read_text(encoding="utf-8"))
        path = arguments.env_file or (CODE_ROOT / settings["credentials_file"]).resolve()
        if path.resolve() == load_run_settings()["env_file"].resolve():
            raise ValueError("market_credentials_path_must_be_separate")
        if not path.is_file():
            parser.exit(
                2,
                "모의투자 전용 인증 파일이 없습니다. Credentials/kis-demo.env.example과 Docs/KIS_READINESS.md를 확인하세요.\n",
            )
        key, secret, account, product = read_demo_identity(path)
        market = KisMarketClient(key, secret, "vps")
        market.token_cache = (
            DATA_ROOT / "cache/kis/vps" / ("readonly-" + market.identity[:16] + ".json")
        )
        api = ReadOnlyKisApi(market, account)
        manager = OrderManager(
            (CODE_ROOT / settings["store"]).resolve(), "kis_demo", settings["alias"]
        )
        exchanges = load_kis_settings(CONFIG_ROOT / "kis.json")["us_exchanges"]
        exchanges = {
            symbol: {"NAS": "NASD", "NYS": "NYSE", "AMS": "AMEX"}.get(value, value)
            for symbol, value in exchanges.items()
        }
        adapter = ManagedKisAdapter(api, manager, account, product, exchanges, enabled=False)
        now = datetime.now(timezone.utc)
        end = now.astimezone(ZoneInfo("America/New_York")).date()
        start = end - timedelta(days=settings["history_days"])
        result = inspect_remote(
            manager,
            adapter,
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d"),
            settings["probe_symbol"],
            settings["probe_price"],
        )
        output = DATA_ROOT / "preflight/actual" / now.strftime("%Y%m%d-%H%M%S-%f")
        output.mkdir(parents=True)
        (output / "responses-redacted.json").write_text(
            json.dumps(api.records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (output / "report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("조회 완료. 주문 요청 0건. 위험 근거와 외부 주문 계약 검증은 별도입니다.")
        print("진단 코드:", ", ".join(result["issues"]))
        print("결과:", output)
        if result["issues"]:
            raise SystemExit(3)
    except (OSError, ValueError, KeyError, RuntimeError):
        # 키·계좌·서버 원문 오류 문자열을 출력하지 않는다.
        parser.exit(
            1,
            "읽기 전용 사전 검사 실패. 모의 환경·권한·입력과 공식 지원 범위를 확인하세요. 주문은 전송하지 않았습니다.\n",
        )
    finally:
        if manager:
            manager.ready = False
            manager.close()


if __name__ == "__main__":
    main()
