@echo off
chcp 65001 >nul
cd /d %~dp0
echo 启动三个前端 Vite 开发服务器（需先启动 Django: takeout\run.bat）
echo   顾客端  http://localhost:5173
echo   商户端  http://localhost:5174
echo   骑手端  http://localhost:5175
npm run dev
