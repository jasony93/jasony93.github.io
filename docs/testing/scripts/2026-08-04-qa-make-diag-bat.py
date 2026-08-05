# -*- coding: utf-8 -*-
"""Diagnostic: same logic as src/scripts/update_data.bat but with
(1) CRLF line endings (2) ASCII-only comments (3) absolute cd path.
Written to scratchpad to prove the root cause without touching source."""
content = (
    "@echo off\r\n"
    "rem diagnostic copy: CRLF line endings, ASCII comments only\r\n"
    "setlocal\r\n"
    'cd /d "D:\\personal\\Claude \ud504\ub85c\uc81d\ud2b8\\\uae08\uc735\ub3c4\uad6c \uc6f9\uc0ac\uc774\ud2b8"\r\n'
    'echo ==== %date% %time% ==== >> "%TEMP%\\qa_update_data.log"\r\n'
    'python src\\fetch_data.py >> "%TEMP%\\qa_update_data.log" 2>&1\r\n'
    'if errorlevel 1 echo [WARN] fetch_data partial failure >> "%TEMP%\\qa_update_data.log"\r\n'
    'python src\\build_pages.py >> "%TEMP%\\qa_update_data.log" 2>&1\r\n'
    'if errorlevel 1 echo [ERROR] build_pages failed >> "%TEMP%\\qa_update_data.log"\r\n'
    'echo ==== done ==== >> "%TEMP%\\qa_update_data.log"\r\n'
    "endlocal\r\n"
)
import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa_update_data_crlf.bat")
with open(out, "wb") as f:
    f.write(content.encode("cp949"))
print("written:", out)
