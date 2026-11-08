#!/bin/sh
# 조회 전용: 서비스 시작·중지·부팅 설정 변경을 하지 않는다.
printf '%s\n\n' '부팅 설정 확인'
systemctl is-enabled pytrading-daily-validation
printf '\n%s\n' 'disabled: 부팅 자동 시작 꺼짐 / enabled: 켜짐'
printf '%s' 'Enter를 누르면 창을 닫습니다. '
read -r answer || true
