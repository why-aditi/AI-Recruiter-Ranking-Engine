$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
docker compose -f "$Root\infra\docker-compose.yml" up -d postgres redis mlflow
