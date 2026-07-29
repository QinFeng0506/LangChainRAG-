@echo off
chcp 65001 >nul
echo ========================================
echo   LangChain RAG 知识库问答系统
echo ========================================
echo.

start "Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo 后端 API: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo 前端页面: http://localhost:5173
echo.
echo 管理员账号: admin / 123456
echo ========================================
