@echo off
rem ------------------------------------------------------------
rem  เริ่ม Kuroya Window Manager แบบไม่แสดงหน้าต่างคอนโซล
rem  ดับเบิลคลิกไฟล์นี้เพื่อรันโปรแกรมได้เลย (Windows + Python 3.8+)
rem ------------------------------------------------------------
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw "%~dp0window_manager.py"
) else (
  start "" python "%~dp0window_manager.py"
)
