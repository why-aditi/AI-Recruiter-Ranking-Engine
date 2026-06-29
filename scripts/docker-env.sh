# Source from Git Bash scripts: export Docker Desktop tools to PATH
export PATH="/c/Program Files/Docker/Docker/resources/bin:$PATH"
# Host port for Docker Postgres (5434: local PG16=5432, PG18=5433 on this machine)
export DOCKER_PG_HOST_PORT="${DOCKER_PG_HOST_PORT:-5434}"
