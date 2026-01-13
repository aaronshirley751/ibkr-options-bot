@echo off
set "PYTHONPATH=%CD%"
.venv\Scripts\python -m src.bot.app > logs\bot_production.log 2>&1
