"""KIS 실시간 접속·등록/해제·PINGPONG·복수 레코드·암호화 체결통보 처리.

연결이 끊기면 예외를 전달한다. 재연결 중 누락 시세·체결을 받은 것처럼 이어붙이지 않는다.
재접속 후에는 REST 잔고·미체결 조회로 상태를 맞춘 뒤 새 세션을 시작해야 한다.
"""
import base64
import json
from contextlib import contextmanager
from dataclasses import dataclass, field

from broker.kis import KisApiError
from .client import validate_operation
from .models import Subscription

WEBSOCKET_URLS = {"prod": "ws://ops.koreainvestment.com:21000/tryitout",
                  "vps": "ws://ops.koreainvestment.com:31000/tryitout"}


@dataclass(frozen=True)
class StreamEvent:
    kind: str
    transaction_id: str
    rows: tuple[dict, ...] = field(default=(), repr=False)


def decrypt_notice(ciphertext, key, initialization_vector):
    """공식 체결통보의 AES-CBC + PKCS7 형식. 키는 파일·이벤트·로그에 넣지 않는다."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.padding import PKCS7
    try:
        decoder = Cipher(algorithms.AES(key.encode()), modes.CBC(initialization_vector.encode())).decryptor()
        padded = decoder.update(base64.b64decode(ciphertext, validate=True)) + decoder.finalize()
        unpadder = PKCS7(128).unpadder()
        return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")
    except (ValueError, UnicodeError):
        raise KisApiError("KIS 암호화 체결통보를 해석할 수 없습니다.") from None


class KisStreamSession:
    def __init__(self, api_client, socket, approval_key):
        self.api_client, self.socket = api_client, socket
        self._approval_key = approval_key
        self._subscriptions = {}
        self._cipher_keys = {}
        self._pending = {}

    def send(self, subscription):
        """등록·해제를 명시적으로 전송한다. 한 세션에서 같은 TR의 출력 구조는 같아야 한다."""
        if not isinstance(subscription, Subscription):
            raise TypeError("상품별 실시간 함수의 Subscription이 필요합니다.")
        validate_operation(subscription, "websocket", self.api_client.market_client.environment, self.api_client.catalog)
        identifier = subscription.transaction_id
        key = subscription.parameters["tr_key"]
        previous = self._subscriptions.get(identifier)
        if previous and previous.columns != subscription.columns:
            raise KisApiError("동일 TR의 실시간 출력 필드가 다릅니다.")
        # 암호화 통보는 프레임에 계정 키가 없어 서로 다른 HTS ID를 한 세션에 섞지 않는다.
        if previous and "CUST_ID" in subscription.columns and previous.parameters["tr_key"] != key:
            raise KisApiError("암호화 체결통보는 한 세션에 한 HTS ID만 등록하세요.")
        self._subscriptions[identifier] = subscription
        self._pending[(identifier, key)] = subscription.action
        self.socket.send(json.dumps(subscription.message(self._approval_key)))

    def parse(self, raw):
        """열 개수·레코드 수가 맞지 않으면 해석을 중단한다. 잘못된 체결 필드를 만들지 않는다."""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if raw.startswith("{"):
            try:
                payload = json.loads(raw)
                header = payload["header"]
                identifier = header["tr_id"]
                if identifier == "PINGPONG":
                    self.socket.pong(raw.encode("utf-8"))
                    return StreamEvent("ping", identifier)
                body = payload["body"]
                if body.get("rt_cd") != "0":
                    raise KisApiError("KIS 실시간 등록·해제 거절. TR·이용 권한·구독 한도를 확인하세요.")
                key = header.get("tr_key", "")
                action = self._pending.pop((identifier, key), None)
                output = body.get("output", {})
                if "key" in output and "iv" in output:
                    self._cipher_keys[identifier] = (output["key"], output["iv"])
                if action == "2":
                    # 같은 TR의 다른 종목 구독은 유지한다. 다음 데이터는 동일 필드로 해석한다.
                    return StreamEvent("unsubscribed", identifier)
                return StreamEvent("subscribed", identifier)
            except (KeyError, TypeError, ValueError):
                raise KisApiError("KIS 실시간 제어 응답 형식 오류") from None
        try:
            encryption, identifier, record_count, values = raw.split("|", 3)
            count = int(record_count)
            if encryption not in {"0", "1"} or not 1 <= count <= 10000:
                raise ValueError("프레임 구분·건수 오류")
            subscription = self._subscriptions[identifier]
            if encryption == "1":
                values = decrypt_notice(values, *self._cipher_keys[identifier])
            fields = values.split("^")
            width = len(subscription.columns)
            if len(fields) != count * width:
                raise ValueError("필드 개수 오류")
            # 공식 필드명이 중복된 경우 두 번째부터 번호를 붙여 값 소실을 방지한다.
            names, occurrences = [], {}
            for column in subscription.columns:
                occurrences[column] = occurrences.get(column, 0) + 1
                names.append(column if occurrences[column] == 1 else f"{column}_{occurrences[column]}")
            rows = tuple(dict(zip(names, fields[index:index + width])) for index in range(0, len(fields), width))
            return StreamEvent("data", identifier, rows)
        except (ValueError, KeyError, TypeError):
            raise KisApiError("KIS 실시간 프레임·구독·암호화 키·필드 개수를 확인하세요.") from None

    def events(self, maximum_messages=100, timeout=15):
        """유한한 메시지 수·대기 시간으로 실행한다. 연결 오류는 호출자에게 전달한다."""
        if type(maximum_messages) is not int or maximum_messages < 1 or timeout <= 0:
            raise ValueError("메시지 상한·대기 시간은 양수여야 합니다.")
        for _ in range(maximum_messages):
            try:
                raw = self.socket.recv(timeout=timeout)
            except TimeoutError:
                return
            event = self.parse(raw)
            if event.kind != "ping":
                yield event


@contextmanager
def open_stream(api_client):
    """읽기 전용 실시간 구독도 사용자가 명시적으로 이 함수를 호출할 때만 연결한다."""
    from websockets.sync.client import connect
    approval = api_client.approval_key()
    url = WEBSOCKET_URLS[api_client.market_client.environment]
    with connect(url, proxy=None, open_timeout=15, close_timeout=5) as socket:
        yield KisStreamSession(api_client, socket, approval)
