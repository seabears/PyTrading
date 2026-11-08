"""프로젝트 루트에서 python -m unittest로 실행해도 Code를 찾는다."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
code_root = Path(__file__).resolve().parent.parent / "Code"
if str(code_root) not in sys.path:
    sys.path.insert(0, str(code_root))
