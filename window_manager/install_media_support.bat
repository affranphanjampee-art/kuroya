@echo off
rem ------------------------------------------------------------
rem  Install optional libraries for the Kuroya MEDIA BAR
rem  (floating music widget like Windows 11 media flyout)
rem  The main window manager works without this - only the
rem  media bar needs these packages.
rem ------------------------------------------------------------
echo Installing libraries for the media bar...
python -m pip install --upgrade pip
python -m pip install winsdk Pillow
if errorlevel 1 (
  echo.
  echo winsdk install failed - trying the newer winrt package set...
  python -m pip install winrt-runtime winrt-Windows.Media.Control winrt-Windows.Storage.Streams winrt-Windows.Foundation Pillow
)
echo.
echo Done. Run run_window_manager.bat again, then play a song in
echo Chrome/Edge/Spotify - the media bar will pop up by itself.
pause
