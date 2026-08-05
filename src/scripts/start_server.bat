@echo off
rem Start local preview server for ADR premium site (double-click to run)
rem Keep this file ASCII + CRLF (see update_data.bat header note)
cd /d "%~dp0..\.."
echo Starting server at http://localhost:8765 (close this window to stop)
python -m http.server 8765 -d src\web
