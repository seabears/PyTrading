"""실행: python Code/price_paper.py — 가격 연구 전용 지속 모의 운용."""
import sys
sys.dont_write_bytecode = True
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

if __name__ == "__main__":
    from tools.price_forward import main
    main()
