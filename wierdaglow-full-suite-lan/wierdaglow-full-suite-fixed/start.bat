@echo off
cd /d %~dp0

if not exist .venv (
    py -m venv .venv
)

call .venv\Scripts\activate.bat
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

echo.
echo Starting Wierdaglow Full Suite on your local network...
echo Local computer: http://127.0.0.1:5000
echo.
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } ^| Select-Object -ExpandProperty IPAddress"`) do (
    echo Network access URL: http://%%I:5000
)
echo.
echo If other devices cannot connect, allow Python through Windows Firewall or open TCP port 5000 on this PC.
echo.
start "" http://127.0.0.1:5000
py app.py

if errorlevel 1 (
    echo.
    echo The application stopped because of an error.
    pause
)
