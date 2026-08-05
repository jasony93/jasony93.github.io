@echo off
rem Daily data update + static page rebuild (local runner, SEO D5 local alternative)
rem Usage: run directly, or register with Windows Task Scheduler via register_task.ps1
rem Log:   src\scripts\update_data.log (appended)
rem Note:  keep this file CRLF-terminated and ASCII-only
rem        (cmd.exe misparses LF-only batch files - QA report 2026-08-04 FAIL #4)

setlocal
cd /d "%~dp0..\.."
echo ==== start %date% %time% ==== >> src\scripts\update_data.log
python src\fetch_data.py >> src\scripts\update_data.log 2>&1
if errorlevel 1 echo [WARN] fetch_data reported failures (previous data kept) >> src\scripts\update_data.log
python src\build_pages.py >> src\scripts\update_data.log 2>&1
if errorlevel 1 echo [ERROR] build_pages failed >> src\scripts\update_data.log
echo ==== done %date% %time% ==== >> src\scripts\update_data.log
endlocal
