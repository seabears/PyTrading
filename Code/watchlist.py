"""관찰 목록 TUI. 실행: python Code/watchlist.py. 주문·서비스 제어는 하지 않는다."""
import sys
sys.dont_write_bytecode = True
from app.watchlist_tui import main

if __name__ == '__main__':
    raise SystemExit(main())
