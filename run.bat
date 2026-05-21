@echo off
title DataNova - Text-to-SQL Agent
color 0A
cls

echo.
echo ⚡ DataNova - Text-to-SQL Agent
echo ================================
echo.
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.8+ and add to PATH.
    pause
    exit /b 1
)

echo ✓ Python found
echo.
echo Installing dependencies...
pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✓ Dependencies installed
echo.
echo 🚀 Starting DataNova...
echo.
echo Opening http://localhost:8501
echo.
streamlit run app.py

pause
