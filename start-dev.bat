@echo off
echo ========================================
echo AI小说拆书系统 - 开发环境启动
echo ========================================
echo.

echo [1/2] 启动 Mock Server (端口 3001)...
start "Mock Server" cmd /k "cd /d %~dp0backend && python mock_server.py"
timeout /t 2 >nul

echo [2/2] 启动前端静态服务 (端口 8080)...
start "Frontend" cmd /k "cd /d %~dp0 && python -m http.server 8080"
timeout /t 2 >nul

echo.
echo ========================================
echo 服务已启动:
echo - Mock API: http://localhost:3001
echo - Mock API文档: http://localhost:3001/docs
echo - 前端页面: http://localhost:8080
echo ========================================
echo.
pause
