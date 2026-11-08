"""삭제된 재무 API의 재유입·직접 HTTP 호출 차단. 호출 함수는 제공하지 않는다."""
from urllib.parse import unquote, urlsplit
from broker.kis import KisApiError

REMOVED_FINANCE_NAMES = frozenset(['domestic_stock.finance_balance_sheet', 'domestic_stock.finance_financial_ratio', 'domestic_stock.finance_growth_ratio', 'domestic_stock.finance_income_statement', 'domestic_stock.finance_other_major_ratios', 'domestic_stock.finance_profit_ratio', 'domestic_stock.finance_stability_ratio'])
REMOVED_FINANCE_PATHS = frozenset(['/uapi/domestic-stock/v1/finance/balance-sheet', '/uapi/domestic-stock/v1/finance/financial-ratio', '/uapi/domestic-stock/v1/finance/growth-ratio', '/uapi/domestic-stock/v1/finance/income-statement', '/uapi/domestic-stock/v1/finance/other-major-ratios', '/uapi/domestic-stock/v1/finance/profit-ratio', '/uapi/domestic-stock/v1/finance/stability-ratio'])


def reject_removed_finance(operation='', path=''):
    """사용자 요청으로 종료 시각 전에 제거했다. 캐시와 낮은 전송 경로에서도 차단한다."""
    normalized = unquote(urlsplit(path).path).rstrip('/').lower()
    if operation in REMOVED_FINANCE_NAMES or normalized in REMOVED_FINANCE_PATHS:
        raise KisApiError('제공 종료 대상으로 삭제한 국내주식 재무분석 API입니다.')
