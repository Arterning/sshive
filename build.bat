@echo off
echo ==========================================
echo SSHive 打包脚本
echo ==========================================
echo.

echo [1/3] 安装打包依赖...
uv sync
if errorlevel 1 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

echo.
echo [2/3] 开始打包应用...
uv run pyinstaller build.spec --clean
if errorlevel 1 (
    echo 错误: 打包失败
    pause
    exit /b 1
)

echo.
echo [3/3] 打包完成！
echo.
echo 可执行文件位置: dist\SSHive.exe
echo.
echo ==========================================
echo 打包成功！
echo ==========================================
pause
