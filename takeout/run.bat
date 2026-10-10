@echo off
chcp 65001 >nul
cd /d %~dp0

rem 从 llm_key.txt 读取 API Key（该文件已被 .gitignore 忽略）
if not defined LLM_API_KEY (
  if exist llm_key.txt (
    set /p LLM_API_KEY=<llm_key.txt
  )
)

rem 可选：覆盖模型名与接口地址
if not defined LLM_MODEL set LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
if not defined LLM_BASE_URL set LLM_BASE_URL=https://api.siliconflow.cn/v1

echo LLM_MODEL=%LLM_MODEL%
echo LLM_BASE_URL=%LLM_BASE_URL%
if defined LLM_API_KEY (echo LLM_API_KEY=已设置) else (echo LLM_API_KEY=未设置（将使用内置 Mock）)

.venv\Scripts\python.exe manage.py runserver 8091
