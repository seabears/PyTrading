"""고정 일봉 후보 실행. Config/execution.json으로 체결 경로를 선택하며 실계좌는 잠금 상태다."""
import sys
sys.dont_write_bytecode = True
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)
if __name__ == "__main__":
    from app.daily_service import run
    run()
