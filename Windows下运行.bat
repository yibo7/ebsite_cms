@echo off
chcp 65001 >nul

echo Running index.py...
python index.py

if errorlevel 1 (
    echo 运行出错！错误代码: %errorlevel%
) else (
    echo 运行成功！
)

pause