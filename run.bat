@echo off
cd /d "%~dp0"

if not exist ".env" (
    echo [WARNING] .env file not found! Please rename .env.example or create one.
    copy .env .env.bak
)

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

echo.
echo Starting Application...
echo Open http://localhost:8000 in your browser if it doesn't open automatically.
echo.

::start http://localhost:8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
