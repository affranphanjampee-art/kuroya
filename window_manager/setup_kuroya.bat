@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Kuroya Window Manager Setup

set "RAW=https://raw.githubusercontent.com/affranphanjampee-art/kuroya"
set "BR1=main"
set "BR2=arena/d7201cd1-kuroya"
set "INSTALL_ROOT=%LOCALAPPDATA%\KuroyaWM"
set "APP_DIR=%INSTALL_ROOT%\"

echo ==================================================
echo   Kuroya Window Manager - ตัวติดตั้งอัตโนมัติ
echo   ดับเบิลคลิกไฟล์นี้ไฟล์เดียว จบทุกขั้นตอน
echo ==================================================
echo.

REM ---------- โหมด repo: ถ้ามี window_manager.py อยู่ข้างตัว setup ให้ใช้โฟลเดอร์นั้นเลย ----------
if exist "%~dp0window_manager.py" (
  set "APP_DIR=%~dp0"
  echo โหมด repo: ใช้ไฟล์จากโฟลเดอร์นี้ - %~dp0
  goto step_python
)

echo ขั้นที่ 1 จาก 4: ดาวน์โหลดโปรแกรมไปที่ %INSTALL_ROOT%
if not exist "%INSTALL_ROOT%" mkdir "%INSTALL_ROOT%"
call :download window_manager.py
call :download media_bar.py
call :download run_window_manager.bat
if not exist "%APP_DIR%window_manager.py" (
  echo ดาวน์โหลดไม่สำเร็จ - ตรวจว่าอินเทอร์เน็ตเชื่อมต่อได้แล้วลองใหม่อีกครั้ง
  pause
  exit /b 1
)
echo.

:step_python
echo ขั้นที่ 2 จาก 4: ตรวจหา Python...
call :pick_python
if defined PYCMD goto python_ok

echo   ยังไม่มี Python บนเครื่อง - กำลังติดตั้งให้ ใช้เวลา 1-2 นาที โปรดรอ
where winget >nul 2>nul
if %errorlevel%==0 (
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
) else (
  echo   ดาวน์โหลดตัวติดตั้งจาก python.org...
  powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile $env:TEMP\python-setup.exe -UseBasicParsing"
  if exist "%TEMP%\python-setup.exe" "%TEMP%\python-setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=1
)
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts;%LOCALAPPDATA%\Programs\Python\Python314;%LOCALAPPDATA%\Programs\Python\Python314\Scripts"
call :pick_python
if not defined PYCMD (
  echo   ติดตั้ง Python ไม่สำเร็จ
  echo   ลองปิดหน้าต่างนี้แล้วเปิด setup ใหม่อีกครั้ง หรือติดตั้งเองจาก https://www.python.org/downloads/
  pause
  exit /b 1
)

:python_ok
for /f "delims=" %%V in ('%PYCMD% -c "import sys;print(sys.version.split()[0])"') do set PYVER=%%V
echo   Python %PYVER% พร้อมใช้งานแล้ว
echo.

echo ขั้นที่ 3 จาก 4: ติดตั้งไลบรารีสำหรับแถบเพลง - winsdk กับ Pillow...
%PYCMD% -m pip install --upgrade pip >nul 2>nul
%PYCMD% -m pip install --quiet winsdk Pillow
if errorlevel 1 %PYCMD% -m pip install --quiet winrt-runtime winrt-Windows.Media.Control winrt-Windows.Storage.Streams winrt-Windows.Foundation Pillow
if errorlevel 1 (
  echo   เตือน: ติดตั้งไลบรารีเพลงไม่สำเร็จ - โปรแกรมจัดการหน้าต่างยังใช้ได้ปกติ แค่แถบเพลงปิดอยู่
) else (
  echo   ไลบรารีพร้อมแล้ว - แถบเพลงจะทำงานเมื่อเปิดเพลงใน Chrome หรือ Spotify
)
echo.

echo ขั้นที่ 4 จาก 4: สร้างปุ่มลัด...
powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $lnk=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Kuroya Window Manager.lnk'); $lnk.TargetPath='%APP_DIR%run_window_manager.bat'; $lnk.WindowStyle=7; $lnk.Save()"
powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $lnk=$ws.CreateShortcut([Environment]::GetFolderPath('Startup')+'\KuroyaWM.lnk'); $lnk.TargetPath='%APP_DIR%run_window_manager.bat'; $lnk.WindowStyle=7; $lnk.Save()"
echo   - ปุ่มลัด Kuroya Window Manager บนเดสก์ท็อป สร้างแล้ว
echo   - เปิดอัตโนมัติตอนเปิดเครื่อง ตั้งแล้ว ถ้าจะเอาออก: กด Win+R พิมพ์ shell:startup แล้วลบไฟล์ KuroyaWM.lnk
echo.

echo เสร็จแล้วทั้งหมด! กำลังเปิดโปรแกรม...
call :pick_gui
start "" /min "%PYGUI%" "%APP_DIR%window_manager.py"
echo แถบจัดการหน้าต่างจะลอยขึ้นมาที่กลางล่างของจอใน 3-5 วินาที
echo ครั้งต่อไปเปิดจากปุ่มลัดบนเดสก์ท็อปได้เลย หรือรอเปิดเองตอนเปิดเครื่อง
timeout /t 5 >nul
exit /b 0

:download
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; $dst='%APP_DIR%%~1'; $urls=@('%RAW%/%BR1%/window_manager/%~1','%RAW%/%BR2%/window_manager/%~1'); foreach($u in $urls){ try{ Invoke-WebRequest $u -OutFile $dst -UseBasicParsing; exit 0 }catch{} }; exit 1"
if exist "%APP_DIR%%~1" (echo   ดาวน์โหลด %~1 สำเร็จ) else (echo   ดาวน์โหลด %~1 ไม่สำเร็จ)
goto :eof

:pick_python
set "PYCMD="
for %%C in (python py) do (
  if not defined PYCMD (
    %%C -c "print('ok')" >nul 2>nul
    if not errorlevel 1 set "PYCMD=%%C"
  )
)
goto :eof

:pick_gui
set "PYGUI=python"
where pythonw >nul 2>nul
if not errorlevel 1 set "PYGUI=pythonw"
if not defined PYGUI goto :eof
if "%PYGUI%"=="pythonw" goto :eof
where pyw >nul 2>nul
if not errorlevel 1 set "PYGUI=pyw"
goto :eof
