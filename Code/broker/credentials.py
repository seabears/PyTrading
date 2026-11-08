"""KIS 인증 파일. 파일 내용을 실행하거나 인증값을 출력하지 않는다."""
from pathlib import Path


def read_credentials_file(path: Path) -> tuple[str, str]:
    required = {"KIS_APP_KEY", "KIS_APP_SECRET"}
    # 기존 파일에서 흔히 쓰는 APP_KEY/APP_SECRET 표기도 같은 이름으로 해석한다.
    aliases = {"APP_KEY": "KIS_APP_KEY", "APP_SECRET": "KIS_APP_SECRET",
               "KIS_APPKEY": "KIS_APP_KEY", "KIS_APPSECRET": "KIS_APP_SECRET"}
    values = {}
    try:
        lines = path.expanduser().read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        raise ValueError("KIS 인증 파일을 읽을 수 없습니다. 설정에서 지정한 파일 경로와 UTF-8 인코딩을 확인하세요.") from None
    for number, original in enumerate(lines, 1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        name, value = name.strip(), value.strip()
        name = aliases.get(name, name)
        if not separator:
            raise ValueError(f"KIS 인증 파일 {number}행은 KEY=VALUE 형식이어야 합니다.")
        if name not in required:
            continue
        if name in values:
            raise ValueError(f"KIS 인증 파일에서 {name}이 중복됐습니다.")
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"KIS 인증 파일 {number}행의 따옴표를 확인하세요.")
            value = value[1:-1]
        if not value.strip():
            raise ValueError(f"KIS 인증 파일의 {name}이 비어 있습니다.")
        values[name] = value
    if required - values.keys():
        raise ValueError("kis.env에 KIS_APP_KEY와 KIS_APP_SECRET이 모두 필요합니다.")
    return values["KIS_APP_KEY"], values["KIS_APP_SECRET"]
