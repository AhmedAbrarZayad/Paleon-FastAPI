@echo off
REM ===================================================================
REM START SERVER SCRIPT - Paleon FastAPI Backend
REM ===================================================================

echo.
echo ========================================
echo   Paleon Fossil Classification API
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please create it first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Create .env file with your OPENAI_API_KEY
    echo.
)

echo Starting server...
echo.
echo Server will be available at:
echo   http://127.0.0.1:8000
echo.
echo API Documentation:
echo   http://127.0.0.1:8000/docs
echo.
echo Press CTRL+C to stop the server
echo.
echo ========================================
echo.

REM Start server
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
