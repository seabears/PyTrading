"""실행: python main.py / 기능별 테스트: python main.py --test

평소에는 ../Config/settings.json을 읽어 계속 판단한다.
--test는 기능을 독립 실행한다. 자동 검증은 --test all 또는 --test unit-기능명이다.
"""
import argparse
import sys
from pathlib import Path

# Code 밖의 Test 패키지를 기능별 테스트 메뉴에서 불러올 수 있게 한다.
repository_root = Path(__file__).resolve().parent.parent
if str(repository_root) not in sys.path:
    sys.path.insert(0, str(repository_root))

# 별도 -B 인자를 요구하지 않고 실행·테스트 중 바이트코드 캐시 생성을 막는다.
sys.dont_write_bytecode = True


def main(argv=None) -> int:
    # CMD 실행 도우미 없이도 한국어·화살표·판단 구분 기호를 출력할 수 있게 한다.
    # Windows 기본 cp949에서는 일부 기호가 UnicodeEncodeError를 일으킨다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)
    from tools.test_features import TEST_CHOICES, run_feature, select_feature

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", nargs="?", const="menu", choices=TEST_CHOICES,
                        help="값 없이 기능 실행 메뉴. news=뉴스 실행, unit-news=뉴스 자동 검증")
    arguments = parser.parse_args(argv)
    if arguments.test is not None:
        feature = select_feature() if arguments.test == "menu" else arguments.test
        return run_feature(feature) if feature is not None else 0

    from app.runner import main as run_continuously
    run_continuously()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
