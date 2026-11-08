"""KIS 모의 한정 시험의 명시적 실행 요청. 현금/위험 근거가 없으면 전송 전에 중단한다."""
import argparse
from pathlib import Path
from kis_demo_session import run
from paths import CONFIG_ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-limited-demo",action="store_true",required=True)
    parser.add_argument("--recovery-file",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--profile",type=Path,default=CONFIG_ROOT/"kis-demo-session.json")
    parser.add_argument("--contracts-folder",type=Path,required=True)
    parser.add_argument("--env-file",type=Path,default=CONFIG_ROOT.parent / "Credentials/kis_demo.env")
    args=parser.parse_args()
    try:
        result=run(args.recovery_file,args.env_file,args.output,args.profile,args.contracts_folder,execute_requested=True)
        print("한정 모의 시험 결과:", result["phase"], "자료:", result["result_directory"])
        return 0 if result["phase"] == "completed" else 3
    except (ValueError,OSError,RuntimeError,KeyError):
        print("모의 시험 중단. 생성된 result.json에서 전송 횟수·미체결·보유를 확인하세요. 비밀 원문은 출력하지 않습니다.")
        return 1

if __name__=="__main__":
    raise SystemExit(main())
