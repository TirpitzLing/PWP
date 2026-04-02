@echo off
title DBMS API Auto Deploy Watchdog
cd /d X:\YOUR\PATH\HERE

:loop
echo =========================================
echo [%date% %time%] Checking GitHub for updates on 'main' branch...

git fetch origin main

git status -uno | findstr /i "behind" > nul

if %errorlevel% equ 0 (
    echo [!] New updates detected! Pulling code...
    git pull origin main
    
    echo [!] Rebuilding Docker containers...
    docker-compose down
    docker-compose up --build -d
    
    echo [!] Deployment successful!
) else (
    echo [*] Everything is up to date.
)

echo Waiting for 15 minutes...
timeout /t 900 /nobreak > nul
goto loop