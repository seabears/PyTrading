"""설정 기능만 실행해 적용되는 종목·주기·경로를 보여준다. 인증값은 읽지 않는다."""
import json

from app.runtime import SETTINGS_PATH, load_run_settings


def main():
    settings = load_run_settings()
    print(f"설정 파일: {SETTINGS_PATH}")
    print("상대 경로를 프로젝트 기준으로 해석한 실제 적용값:")
    print(json.dumps(settings, ensure_ascii=False, indent=2, default=str))
    print(f"인증 파일 존재: {settings['env_file'].is_file()} (파일 내용은 읽지 않습니다)")


if __name__ == "__main__":
    main()
