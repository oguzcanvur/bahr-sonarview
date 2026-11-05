@echo off
rem BAHR SONARVIEW'u kaynaktan yeniden derler.
rem Derleme _derleme\dist altina yapilir, sonra "BAHR SONARVIEW" klasorune kopyalanir.
rem "Projeler" klasoru ve pencere ayarlari kopyalamada HARIC tutulur (silinmez).
cd /d "%~dp0"
set PY=..\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
tasklist /FI "IMAGENAME eq BAHR SONARVIEW.exe" | find /I "BAHR SONARVIEW.exe" >nul && (
  echo BAHR SONARVIEW acik. Once programi kapatin.
  pause
  exit /b 1
)
"%PY%" -m pip install -q -r kaynak\gereksinimler.txt
"%PY%" kaynak\simge_olustur.py
"%PY%" -m PyInstaller --noconfirm --windowed --name "BAHR SONARVIEW" ^
  --icon "%~dp0kaynak\simge.ico" ^
  --distpath _derleme\dist --workpath _derleme\is --specpath _derleme ^
  --paths kaynak --paths kaynak\motor ^
  --add-data "%~dp0kaynak\static;static" ^
  --add-data "%~dp0kaynak\motor;motor" ^
  --add-data "%~dp0kaynak\simge.ico;." ^
  --collect-all pingverter --collect-data pyproj --collect-submodules uvicorn ^
  --exclude-module tkinter --exclude-module IPython --exclude-module pytest ^
  kaynak\bahr_sonarview.py || (echo DERLEME BASARISIZ & pause & exit /b 1)
robocopy "_derleme\dist\BAHR SONARVIEW" "BAHR SONARVIEW" /MIR /XD Projeler .pencere /XF .port program_gunlugu.txt hata_gunlugu.txt /NFL /NDL /NJH /NP
echo.
echo Derleme bitti: "%~dp0BAHR SONARVIEW\BAHR SONARVIEW.exe"
pause
