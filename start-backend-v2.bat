@echo off
set "BASE_PATH=%~dp0backend-v2"

echo Checking for backend-v2 directory...
if not exist "%BASE_PATH%" (
    echo Could not find backend-v2 directory at %BASE_PATH%
    exit /b 1
)

echo Copying .env file to services...
copy "%BASE_PATH%\.env" "%BASE_PATH%\auth-service\.env" /Y
copy "%BASE_PATH%\.env" "%BASE_PATH%\storage-service\.env" /Y

echo =============================================
echo Starting Backend Services (without Docker)...
echo =============================================

echo -^> Launching Auth Service (Port 8001)...
start "Auth Service (8001)" cmd /k "cd /d "%BASE_PATH%\auth-service" && (if not exist venv python -m venv venv) && call venv\Scripts\activate.bat && pip install -r requirements.txt && uvicorn app.main:app --reload --host 127.0.0.1 --port 8001"

echo -^> Launching Storage Service (Port 8002)...
start "Storage Service (8002)" cmd /k "cd /d "%BASE_PATH%\storage-service" && (if not exist venv python -m venv venv) && call venv\Scripts\activate.bat && pip install -r requirements.txt && uvicorn app.main:app --reload --host 127.0.0.1 --port 8002"

echo =============================================
echo Services are starting in separate windows!
echo Don't forget to ensure PostgreSQL and Redis are running locally.
echo =============================================
