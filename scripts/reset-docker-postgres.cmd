@echo off
setlocal
set "PATH=C:\Program Files\Docker\Docker\resources\bin;%PATH%"
set "DOCKER_PG_HOST_PORT=5434"

echo Using docker from PATH
echo Stopping and removing container...
docker rm -f recruiter-ranking-db 2>nul

echo Removing project volumes...
docker volume rm recruiter-ranking-pgdata 2>nul
for /f "tokens=*" %%v in ('docker volume ls -q --filter name=recruiter 2^>nul') do docker volume rm %%v 2>nul

echo Pulling pgvector/pgvector:pg18...
docker pull pgvector/pgvector:pg18

echo Starting fresh pgvector/pgvector:pg18 on port %DOCKER_PG_HOST_PORT%...
docker run -d ^
  --name recruiter-ranking-db ^
  -e POSTGRES_USER=recruiter ^
  -e POSTGRES_PASSWORD=recruiter ^
  -e POSTGRES_DB=recruiter_ranking ^
  -p %DOCKER_PG_HOST_PORT%:5432 ^
  -v recruiter-ranking-pgdata:/var/lib/postgresql ^
  pgvector/pgvector:pg18

echo Waiting 8s for init...
ping -n 9 127.0.0.1 >nul

echo.
echo === Internal test (must succeed) ===
docker exec recruiter-ranking-db psql -U recruiter -d recruiter_ranking -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT 1 AS ok;"

echo.
echo === Host test (Git Bash) ===
echo PGPASSWORD=recruiter "/c/Program Files/PostgreSQL/16/bin/psql.exe" -h 127.0.0.1 -p %DOCKER_PG_HOST_PORT% -U recruiter -d recruiter_ranking -c "SELECT 1;"
