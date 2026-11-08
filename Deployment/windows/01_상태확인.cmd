@echo off
chcp 65001 >nul
setlocal
where ssh >nul 2>nul
if errorlevel 1 (
    echo Windows OpenSSH 클라이언트를 찾을 수 없습니다.
    pause
    exit /b 1
)
title PyTrading - 상태 확인
echo 라즈베리파이의 현재 모의 운용 상태를 확인합니다.
echo.
if not defined PYTRADING_PI_HOST set "PYTRADING_PI_HOST=pytrading-pi"
ssh -T -o BatchMode=yes -o ConnectTimeout=10 "%PYTRADING_PI_HOST%" "systemctl status pytrading-daily-validation --no-pager --full"
if errorlevel 4 echo 접속 또는 서비스 조회에 실패했습니다. 위 메시지를 확인하세요.
echo.
echo active: 실행 중 / inactive: 중지됨 / failed: 오류 종료
pause
endlocal
