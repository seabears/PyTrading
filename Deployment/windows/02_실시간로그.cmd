@echo off
chcp 65001 >nul
setlocal
where ssh >nul 2>nul
if errorlevel 1 (
    echo Windows OpenSSH 클라이언트를 찾을 수 없습니다.
    pause
    exit /b 1
)
title PyTrading - 실시간 로그
echo 최근 로그 50줄부터 계속 표시합니다.
echo 창을 닫거나 Ctrl+C를 누르면 로그 보기만 종료됩니다. 모의 운용은 계속됩니다.
echo.
if not defined PYTRADING_PI_HOST set "PYTRADING_PI_HOST=pytrading-pi"
ssh -T -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 "%PYTRADING_PI_HOST%" "journalctl -u pytrading-daily-validation -n 50 -f --no-pager"
echo.
echo 로그 연결이 종료됐습니다. 서비스 상태는 변경하지 않았습니다.
pause
endlocal
