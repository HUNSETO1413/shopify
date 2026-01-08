@echo off
chcp 65001 >nul
echo ========================================
echo Shop 工具合集 - 一键打包脚本
echo ========================================
echo.

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8 或更高版本
    pause
    exit /b 1
)
echo [成功] Python 环境正常
echo.

echo [2/3] 安装打包依赖...
python -m pip install --upgrade pip
python -m pip install pyinstaller
if errorlevel 1 (
    echo [警告] 安装依赖时出现问题，但将继续尝试打包
)
echo.

echo [3/3] 开始打包...
echo 这可能需要几分钟时间，请耐心等待...
echo.
python build_exe.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请查看上面的错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo exe 文件位置: dist\Shop工具合集.exe
echo.
echo 提示：
echo 1. 可以将 exe 文件复制到任何位置使用
echo 2. 首次运行可能需要几秒钟启动
echo 3. 如果杀毒软件误报，请添加信任
echo.
pause
