"""진단 한 주기: 전역 체결 모드와 무관하게 실제 시세+별도 내부 모의 계좌만 사용한다."""
from datetime import datetime, timezone

from app.runner import main as run
from paths import RESULTS_ROOT


def main():
    output = RESULTS_ROOT / ("once-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
    print("전체 연결 1회 실행 — 인증·실제 시세·뉴스 수집, 별도 모의 계좌 사용.")
    print("같은 증권사 키를 쓰는 지속 실행은 먼저 종료하세요. KIS 모의·실계좌 주문/정정/취소를 모두 차단하고 내부 가상체결만 수행합니다.")
    print(f"실행 결과 폴더: {output}")
    from broker.diagnostic import diagnostic_scope
    with diagnostic_scope():
        run(argv=[], settings_override={"watch": False, "output_dir": output})


if __name__ == "__main__":
    main()
