@echo off
chcp 65001 >nul 2>&1
title 纺织面料平台 - 后端服务

echo.
echo ══════════════════════════════════════════════════
echo   纺织面料智能查询与供需对接平台 - 后端一键启动
echo ══════════════════════════════════════════════════
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: ──────────────────────────────────────
:: 1. 检查 Python 是否已安装
:: ──────────────────────────────────────
echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [错误] 未检测到 Python！
    echo  请先安装 Python 3.11 或以上版本：
    echo  下载地址: https://www.python.org/downloads/
    echo  安装时请务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
    echo         已检测到 Python %%v
)

:: ──────────────────────────────────────
:: 2. 创建/激活虚拟环境
:: ──────────────────────────────────────
echo.
echo [2/4] 配置虚拟环境...
if not exist "venv" (
    echo         首次运行，正在创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  [错误] 创建虚拟环境失败！
        pause
        exit /b 1
    )
    echo         虚拟环境创建成功！
) else (
    echo         虚拟环境已存在，跳过创建。
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: ──────────────────────────────────────
:: 3. 安装依赖
:: ──────────────────────────────────────
echo.
echo [3/4] 检查并安装依赖...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo.
    echo  [错误] 依赖安装失败！请检查网络连接。
    echo  你也可以尝试使用国内镜像：
    echo  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
    exit /b 1
)
echo         依赖安装完成！

:: ──────────────────────────────────────
:: 4. 初始化测试数据（仅首次）
:: ──────────────────────────────────────
echo.
echo [4/4] 检查数据库...
if not exist "instance\dev.db" (
    echo         首次运行，正在初始化数据库和测试账号...
    python seed_users.py
    echo.
    echo  ┌─────────────────────────────────────────┐
    echo  │         测试账号信息                      │
    echo  ├──────────┬───────────┬──────────────────┤
    echo  │ 角色     │ 手机号        │ 密码             │
    echo  ├──────────┼───────────┼──────────────────┤
    echo  │ 管理员   │ 13800000001   │ admin123         │
    echo  │ 采购商   │ 13800000002   │ buyer123         │
    echo  │ 供应商   │ 13800000003   │ supplier123      │
    echo  └──────────┴───────────┴──────────────────┘
    echo.
) else (
    echo         数据库已存在，跳过初始化。
)

:: ──────────────────────────────────────
:: 启动服务器
:: ──────────────────────────────────────
echo.
echo ══════════════════════════════════════════════════
echo   后端服务启动中...
echo   访问地址: http://localhost:5000
echo   按 Ctrl+C 可停止服务
echo ══════════════════════════════════════════════════
echo.

python run_server.py

:: 如果服务器退出
echo.
echo  服务已停止。
pause
