@echo off
echo Starting Task Bar Hero - Inventory Value Companion...
python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo Application failed to start or closed with errors.
    pause
)
