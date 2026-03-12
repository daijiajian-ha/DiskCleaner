@echo off
echo ========================================
echo   DiskCleaner 打包脚本
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 安装依赖...
pip install pyinstaller

echo.
echo [2/4] 打包为 EXE (CLI模式，极致精简)...
pyinstaller --onefile --console --name DiskCleaner --clean --strip ^
  --exclude-module=psutil --exclude-module=tkinter --exclude-module=tcl --exclude-module=turtle ^
  --exclude-module=xml --exclude-module=email --exclude-module=html --exclude-module=http ^
  --exclude-module=urllib --exclude-module=ssl --exclude-module=cryptography ^
  --exclude-module=pkg_resources --exclude-module=unittest --exclude-module=pydoc ^
  --exclude-module=lib2to3 --exclude-module=distutils --exclude-module=multiprocessing ^
  --exclude-module=concurrent --exclude-module=logging --exclude-module=csv ^
  disk_cleaner.py

echo.
echo [3/4] 压缩 EXE...
upx -9 --best --force dist\DiskCleaner.exe -o dist\DiskCleaner.exe.upx
if exist dist\DiskCleaner.exe.upx (
    move /Y dist\DiskCleaner.exe.upx dist\DiskCleaner.exe >nul
)

echo.
echo [4/4] 完成!
powershell -Command "if (Test-Path 'dist\DiskCleaner.exe') { $size = (Get-Item 'dist\DiskCleaner.exe').Length / 1MB; Write-Host ('文件大小: {0:N2} MB' -f $size) -ForegroundColor Green }"
echo.
echo 生成的 EXE 文件在: dist\DiskCleaner.exe
echo.

pause
