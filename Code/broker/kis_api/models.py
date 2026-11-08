"""요청·응답 자료형. 요청 생성 자체는 인증·조회·주문을 실행하지 않는다."""
from dataclasses import dataclass, field
from copy import deepcopy
from .policy import validate_no_borrowing


@dataclass(frozen=True)
class ApiRequest:
    name: str
    path: str
    transaction_id: str
    parameters: dict = field(repr=False)
    method: str = "GET"
    environment: str = "real"
    continuation: str = ""

    def __post_init__(self):
        if self.method not in {"GET", "POST"} or self.environment not in {"real", "demo"}:
            raise ValueError("KIS 요청 방식·환경을 확인하세요.")
        if self.continuation not in {"", "N"} or not isinstance(self.parameters, dict):
            raise ValueError("KIS 연속조회 값은 빈 문자열 또는 N이어야 합니다.")
        validate_no_borrowing(self.name, self.path, self.parameters)
        object.__setattr__(self, "parameters", deepcopy(self.parameters))

    @property
    def changes_account(self):
        """현재 공식 상품 POST API는 주문·예약·취소다. 기본 실행에서 차단한다."""
        return self.method == "POST"


@dataclass(frozen=True)
class ApiResponse:
    payload: dict = field(repr=False)
    continuation: str = ""

    @property
    def has_more(self):
        return self.continuation in {"M", "F"}

    def rows(self, output="output"):
        """객체·객체 배열을 공통 목록으로 반환한다. 없는 출력은 조용히 빈 결과로 바꾸지 않는다."""
        if output not in self.payload:
            raise ValueError(f"KIS 응답에 {output} 항목이 없습니다.")
        value = self.payload[output]
        if isinstance(value, dict):
            return [deepcopy(value)]
        if isinstance(value, list) and all(isinstance(row, dict) for row in value):
            return deepcopy(value)
        raise ValueError("KIS 출력이 객체 또는 객체 배열이 아닙니다.")


@dataclass(frozen=True)
class Subscription:
    name: str
    transaction_id: str
    action: str
    parameters: dict = field(repr=False)
    columns: tuple[str, ...] = ()
    environment: str = "real"

    def __post_init__(self):
        if self.action not in {"1", "2"} or not self.parameters.get("tr_key"):
            raise ValueError("실시간 등록은 1, 해제는 2이며 tr_key가 필요합니다.")
        if self.environment not in {"real", "demo"} or not self.columns:
            raise ValueError("실시간 환경·출력 필드가 잘못됐습니다.")
        object.__setattr__(self, "parameters", deepcopy(self.parameters))

    def message(self, approval_key):
        return {"header": {"approval_key": approval_key, "custtype": "P", "tr_type": self.action,
                           "content-type": "utf-8"},
                "body": {"input": {"tr_id": self.transaction_id, **self.parameters}}}
