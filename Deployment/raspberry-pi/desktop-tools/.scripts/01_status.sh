#!/bin/sh
# 조회 전용: 서비스 시작·중지·부팅 설정 변경을 하지 않는다.
printf '%s\n\n' '상태 확인'
systemctl status pytrading-daily-validation --no-pager --full
printf '\n%s\n' 'active: 실행 중 / inactive: 중지됨 / failed: 오류 종료'
printf '%s' 'Enter를 누르면 창을 닫습니다. '
read -r answer || true
