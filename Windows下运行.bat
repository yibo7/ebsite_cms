@echo off
echo 正在运行 index.py...
python index.py
if %errorlevel% neq 0 (
    echo 运行出错！错误代码: %errorlevel%
) else (
    echo 运行成功！
)
pause