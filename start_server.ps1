# ===================================================================
# START SERVER SCRIPT - Paleon FastAPI Backend
# ===================================================================
# 
# This script starts the FastAPI development server.
# 
# Usage:
#   .\start_server.ps1
#
# What it does:
#   1. Checks if virtual environment exists
#   2. Starts uvicorn server with auto-reload
#   3. Server runs on http://127.0.0.1:8000
#
# Press CTRL+C to stop the server
# ===================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Paleon Fossil Classification API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-Not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it first:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Check if .env file exists
if (-Not (Test-Path ".env")) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Create .env file with your OPENAI_API_KEY" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Starting server..." -ForegroundColor Green
Write-Host ""
Write-Host "Server will be available at:" -ForegroundColor White
Write-Host "  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Documentation:" -ForegroundColor White
Write-Host "  http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start server
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
