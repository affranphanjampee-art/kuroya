@echo off
setlocal EnableExtensions
chcp 65001 >nul
rem ------------------------------------------------------------
rem  เริ่ม Kuroya Window Manager แบบไม่แสดงหน้าต่างคอนโซล
rem  ดับเบิลคลิกไฟล์นี้เพื่อรันโปรแกรม (ต้องมี Python - ถ้ายังไม่มี
rem  ให้ดับเบิลคลิก setup_kuroya.bat ก่อน จะติดตั้งทุกอย่างให้เอง)
rem ------------------------------------------------------------
set "PYGUI="
where pythonw >nul 2>nul
if not errorlevel 1 set "PYGUI=pythonw"
if not defined PYGUI (
  where pyw >nul 2>nul
  if not errorlevel 1 set "PYGUI=pyw"
)
if not defined PYGUI (
  where python >nul 2>nul
  if not errorlevel 1 set "PYGUI=python"
)
if not defined PYGUI (
  echo ยังไม่พบ Python บนเครื่อง - ดับเบิลคลิก setup_kuroya.bat ก่อน แล้วจะติดตั้งให้เอง
  pause
  exit /b 1
)
start "" /min "%PYGUI%" "%~dp0window_manager.py"
