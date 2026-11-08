"""관찰 목록 TUI 진입점. Windows CMD와 Linux SSH에서 인자 없이 실행한다."""
import sys
sys.dont_write_bytecode = True
from app.watchlist_tui import main

if __name__ == '__main__':
    raise SystemExit(main())
