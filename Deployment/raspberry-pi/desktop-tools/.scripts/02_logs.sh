#!/bin/sh
# 조회 전용: 서비스 시작·중지·부팅 설정 변경을 하지 않는다.
printf '%s\n\n' '실시간 로그'
printf '%s\n' 'Ctrl+C 또는 창 닫기는 로그 보기만 종료합니다.'
trap 'exit 0' INT TERM
journalctl -u pytrading-daily-validation -n 50 -f --no-pager
printf '\n%s\n' '로그 연결을 종료해도 모의 운용은 계속됩니다.'
printf '%s' 'Enter를 누르면 창을 닫습니다. '
read -r answer || true
