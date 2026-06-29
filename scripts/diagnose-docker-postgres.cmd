@echo off
set "DOCKER=C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if not exist "%DOCKER%" set "DOCKER=docker"

echo === Docker container ===
"%DOCKER%" ps -a --filter name=recruiter-ranking-db --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"
echo.

echo === Test INSIDE container ===
"%DOCKER%" exec recruiter-ranking-db psql -U recruiter -d recruiter_ranking -c "SELECT current_user, current_database();" 2>&1
echo.

echo === Extensions ===
"%DOCKER%" exec recruiter-ranking-db psql -U recruiter -d recruiter_ranking -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname FROM pg_extension;" 2>&1
echo.

echo === POSTGRES env ===
"%DOCKER%" inspect recruiter-ranking-db --format "{{range .Config.Env}}{{println .}}{{end}}" 2>&1 | findstr POSTGRES
