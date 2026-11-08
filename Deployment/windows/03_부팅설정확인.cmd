@echo off
chcp 65001 >nul
setlocal
where ssh >nul 2>nul
if errorlevel 1 (
    echo Windows OpenSSH 클라이언트를 찾을 수 없습니다.
    pause
    exit /b 1
)
title PyTrading - 부팅 자동 시작 설정 확인
echo 부팅 자동 시작 설정을 조회합니다. 설정을 변경하지 않습니다.
echo.
if not defined PYTRADING_PI_HOST set "PYTRADING_PI_HOST=pytrading-pi"
ssh -T -o BatchMode=yes -o ConnectTimeout=10 "%PYTRADING_PI_HOST%" "systemctl is-enabled pytrading-daily-validation"
if errorlevel 2 echo 접속 또는 설정 조회에 실패했습니다. 위 메시지를 확인하세요.
echo.
echo disabled: 부팅 자동 시작 꺼짐 / enabled: 부팅 자동 시작 켜짐
pause
endlocal
