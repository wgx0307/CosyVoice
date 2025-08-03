@echo off
REM 激活 Conda 环境并运行 FastAPI 服务器

call conda activate CosyVoice3
if %errorlevel% neq 0 (
    echo 错误: 无法激活 Conda 环境 CosyVoice3
    pause
    exit /b
)

python .\runtime\python\fastapi\server.py
if %errorlevel% neq 0 (
    echo 错误: 运行 FastAPI 服务器时出错
    pause
    exit /b
)

pause