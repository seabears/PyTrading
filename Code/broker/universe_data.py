"""일별 관찰 후보용 읽기 전용 KIS 공급기. 계좌·주문 API는 호출하지 않는다."""
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.stateio import atomic_json
from paths import DATA_ROOT

MASTER_BASE = 'https://new.real.download.dws.co.kr/common/master/'
MASTER_URLS = {exchange: MASTER_BASE+exchange.lower()+'mst.cod.zip' for exchange in ('NAS','NYS','AMS')}


def parse_master(raw, exchange, now):
    """공식 24열 마스터의 type=2, USD만 사용한다. ETP·미확인 분류는 등록하지 않는다."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        matches = [name for name in archive.namelist() if Path(name).name.lower() == exchange.lower()+'mst.cod']
        if len(matches) != 1 or archive.getinfo(matches[0]).file_size > 20_000_000:
            raise ValueError('universe_master_archive_invalid')
        name = matches[0]
        text = archive.read(name).decode('cp949')
    digest = hashlib.sha256(raw).hexdigest()
    found = {}
    seen = set()
    for line in text.splitlines():
        fields = [field.strip() for field in line.split('\t')]
        if len(fields) != 24:
            raise ValueError('universe_master_contract_changed')
        symbol = fields[4].strip()
        if symbol in seen:
            raise ValueError('universe_master_duplicate')
        seen.add(symbol)
        if fields[8] != '2' or fields[9] != 'USD' or fields[22] not in {'', '000'}:
            continue
        if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}', symbol):
            continue
        found[symbol] = {'asset_type':'stock', 'security_type':'2', 'currency':'USD',
                         'exchange':exchange, 'name':fields[7], 'source_url':MASTER_URLS[exchange],
                         'source_sha256':digest, 'checked_at':now.isoformat()}
    if not found:
        raise ValueError('universe_master_empty')
    return found


def save_stock_evidence(folder, stocks):
    """최초 확인 자료를 지우지 않는다. 목록 탈락 후에도 보유·미체결 상품 확인에 필요하다."""
    path = Path(folder)/'verified-stocks.json'
    prior = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    for symbol, row in stocks.items():
        if symbol in prior and prior[symbol]['exchange'] != row['exchange']:
            raise ValueError('universe_exchange_changed_requires_review')
    atomic_json(path, {**prior, **stocks}, backup=True)


def verified_stocks(path=None):
    """전송 정책에서 사용하는 자동 확인 자료. 기존 Config 상품 판정을 덮어쓰지 않는다."""
    path = Path(path or DATA_ROOT/'universe/verified-stocks.json')
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding='utf-8'))
    for symbol, row in raw.items():
        if (not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',symbol) or row['asset_type'] != 'stock'
                or row['security_type'] != '2' or row['currency'] != 'USD'
                or row['source_url'] != MASTER_URLS.get(row['exchange'])
                or not re.fullmatch('[0-9a-f]{64}',row['source_sha256'])):
            raise ValueError('universe_stock_evidence_invalid')
        checked = datetime.fromisoformat(row['checked_at'])
        if checked.tzinfo is None or checked > datetime.now(timezone.utc)+timedelta(seconds=30):
            raise ValueError('universe_stock_evidence_time_invalid')
    return raw


class UniverseData:
    """독립 시세 클라이언트를 천천히 사용한다. 운용 계좌와 인증 환경을 바꾸지 않는다."""
    def __init__(self, runtime, options, policy, folder):
        from broker.kis_setup import create_kis_client
        from broker.kis_api.client import KisApiClient
        if options['environment'] != 'prod':
            raise ValueError('universe_requires_prod_quotes_not_demo_account')
        self.client = create_kis_client(runtime['env_file'], options)
        self.client.request_interval = policy['request_interval_seconds']
        self.api = KisApiClient(self.client, allow_trading=False)
        self.policy, self.folder = policy, Path(folder)

    def masters(self, now, stop):
        stocks = {}
        for exchange, url in MASTER_URLS.items():
            if stop.is_set():
                raise InterruptedError('universe_stopped')
            with urllib.request.urlopen(url, timeout=15) as response:
                raw = response.read(20_000_001)
            if len(raw) > 20_000_000:
                raise ValueError('universe_master_size_limit')
            found = parse_master(raw, exchange, now)
            if set(found) & set(stocks):
                raise ValueError('universe_multiple_exchange_conflict')
            atomic_json(self.folder/'sources'/now.date().isoformat()/('master-'+exchange+'.json'), found)
            # 공식 분류 원본도 보존해 JSON의 출처 해시를 다시 검산할 수 있게 한다.
            from app.stateio import _replace_bytes
            _replace_bytes(self.folder/'sources'/now.date().isoformat()/('master-'+exchange+'.zip'), raw)
            stocks.update(found)
        return stocks

    def shortlist(self, stocks, users, stop):
        """거래소별 거래대금 순위 최대 300개를 탐색한다. 미국 전체 전수조사라고 표시하지 않는다."""
        from broker.kis_api.overseas_stock import trade_pbmn
        selected = {}
        scope = {}
        for exchange in MASTER_URLS:
            key = ''; seen = set(); count = 0; complete = False; stop_reason = 'maximum_pages'
            for page in range(self.policy['maximum_ranking_pages']):
                if stop.is_set():
                    raise InterruptedError('universe_stopped')
                response = self.api.execute(trade_pbmn(exchange, '5', '0', keyb=key, tr_cont='N' if page else ''))
                payload = response.payload
                rows = payload.get('output2')
                if not isinstance(rows, list) or (not rows and page == 0):
                    raise ValueError('universe_ranking_empty_or_invalid')
                fingerprint = hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
                if fingerprint in seen:
                    raise ValueError('universe_ranking_page_repeated')
                seen.add(fingerprint)
                for row in rows:
                    symbol = row['symb'].strip()
                    if symbol in stocks and stocks[symbol]['exchange'] == exchange and symbol not in users:
                        selected[symbol] = stocks[symbol]
                    count += 1
                    if count >= self.policy['ranking_per_exchange']:
                        break
                if count >= self.policy['ranking_per_exchange']:
                    stop_reason = 'configured_rank_limit'
                    break
                if response.continuation not in {'M','F'}:
                    complete = True; stop_reason = 'available_pages_complete'; break
                if page+1 >= self.policy['maximum_ranking_pages']:
                    break
                header = payload.get('output1',{})
                next_key = payload.get('keyb') or (header.get('keyb') if isinstance(header,dict) else None)
                if not next_key:
                    # 실제 KIS 응답(2026-11-05): tr_cont=F여도 응답 KEYB가 없었다.
                    # 키를 추정해 재호출하지 않고 받은 순위 범위만 명시해 선별한다.
                    stop_reason = 'next_cursor_not_provided'; break
                if next_key == key:
                    raise ValueError('universe_ranking_cursor_missing_or_repeated')
                key = next_key
            scope[exchange] = {'rank_rows':count, 'all_pages_reached':complete,
                               'stop_reason':stop_reason,
                               'scope':'top_ranked_available_pages_not_entire_market'}
        # 상품 확인 후에만 개별 종목 API를 읽는다. ETF 허용 범위를 넓히지 않는다.
        save_stock_evidence(self.folder, selected)
        return selected, scope

    def daily(self, symbol, exchange, required):
        from research.kis_history import collect_us_history
        from research.daily import prepare_daily_bars
        from broker.kis_api.overseas_stock import price_detail
        record, raw = collect_us_history(self.client, symbol, exchange, '1d',
            date.fromisoformat(required)-timedelta(days=120), date.fromisoformat(required), maximum_pages=2)
        if not record['collection_complete']:
            raise ValueError('universe_daily_pages_incomplete')
        path = self.folder/'sources'/required/(symbol+'.json')
        atomic_json(path, record)
        detail = self.api.execute(price_detail('',exchange,symbol)).payload['output']
        safe = {name:detail.get(name) for name in ('curr','shar','last','base','e_ordyn')}
        atomic_json(path.with_name(symbol+'-detail.json'), {'at':datetime.now(timezone.utc).isoformat(),
            'source':'KIS price-detail HHDFS76200200', 'values':safe})
        return prepare_daily_bars(record), safe

    def quote(self, symbol, exchange, now):
        from broker.kis_market import US_QUOTE, normalize_quote
        from broker.sessions import regular_session
        session = regular_session('US',now)
        if not session:
            return None
        result = normalize_quote(self.client.get(US_QUOTE, {'AUTH':'','EXCD':exchange,'SYMB':symbol}), 'US', session)
        return {'at':datetime.now(timezone.utc).isoformat(), 'quote_at':result['available_at'],
                'bid':result['bid'], 'ask':result['ask']}
