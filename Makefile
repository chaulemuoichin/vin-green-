.PHONY: help dev up down logs test lint format type-check build clean prod-up prod-down prod-logs prod-build e2e backtest

help:
	@echo "Hanoi Air Forecast — Development Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make dev              - Run locally without Docker (Streamlit, FastAPI, Celery)"
	@echo "  make up               - Start all services with Docker Compose"
	@echo "  make down             - Stop all Docker services"
	@echo "  make logs             - Tail logs from all running services"
	@echo "  make logs-api         - Tail API logs only"
	@echo "  make logs-worker      - Tail worker logs only"
	@echo "  make logs-dashboard   - Tail dashboard logs only"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             - Run pytest suite"
	@echo "  make lint             - Run ruff linter"
	@echo "  make format           - Format code with black"
	@echo "  make type-check       - Run mypy strict type checking"
	@echo "  make quality          - Run lint + format + type-check all together"
	@echo ""
	@echo "Docker (dev):"
	@echo "  make build            - Build Docker image"
	@echo "  make build-no-cache   - Build Docker image without cache"
	@echo ""
	@echo "Docker (prod):"
	@echo "  make prod-up          - Start production stack (nginx + api + worker + dashboard + redis)"
	@echo "  make prod-down        - Stop production stack"
	@echo "  make prod-logs        - Tail all production logs"
	@echo "  make prod-build       - Rebuild production image (hanoi_air:0.3.0)"
	@echo "  make e2e              - Run end-to-end tests against the running stack"
	@echo "  make backtest         - Run scripts/run_backtest.py against archived readings"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove Docker containers and volumes"
	@echo "  make clean-all        - Remove everything (containers, volumes, images)"
	@echo ""

# Local development
dev:
	@echo "Starting local development (requires: Python venv, Redis local, .env file)"
	@if not exist .env (echo ".env file not found. Copy .env.example and fill in keys." & exit /b 1)
	@echo "Starting Streamlit dashboard..."
	@start "Streamlit" streamlit run app/streamlit_app.py
	@echo "Starting FastAPI server (port 8000)..."
	@start "API" uvicorn api.main:app --reload --port 8000
	@echo "To start Celery worker in another terminal, run: celery -A worker.tasks worker -B --loglevel=info"
	@echo ""
	@echo "Endpoints:"
	@echo "  - Dashboard: http://localhost:8501"
	@echo "  - API: http://localhost:8000"
	@echo "  - API docs: http://localhost:8000/docs"
	@echo ""

# Docker Compose
up:
	@echo "Starting Hanoi Air Forecast stack with Docker Compose..."
	@if not exist .env (echo ".env file not found. Copy .env.example and fill in keys." & exit /b 1)
	docker-compose up -d
	@echo ""
	@echo "✓ Services started. Check status:"
	@echo "  - Redis: redis:6379"
	@echo "  - API: http://localhost:8000"
	@echo "  - Dashboard: http://localhost:8501"
	@echo "  - API docs: http://localhost:8000/docs"
	@echo ""
	@echo "To view logs: make logs"
	@echo "To stop: make down"
	@echo ""

down:
	@echo "Stopping Hanoi Air Forecast stack..."
	docker-compose down
	@echo "✓ Services stopped"

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-worker:
	docker-compose logs -f worker

logs-dashboard:
	docker-compose logs -f dashboard

# Testing
test:
	@echo "Running pytest suite..."
	python -m pytest tests/ -v

test-cov:
	@echo "Running pytest with coverage..."
	python -m pytest tests/ -v --cov=src/hanoi_air --cov-report=html

# Linting & Formatting
lint:
	@echo "Running ruff linter..."
	ruff check src/ tests/ api/ worker/
	@echo "✓ Linting passed"

format:
	@echo "Formatting code with black..."
	black src/ tests/ api/ worker/ --line-length=100
	@echo "✓ Code formatted"

type-check:
	@echo "Running mypy strict type checking..."
	mypy src/hanoi_air --strict
	@echo "✓ Type checking passed"

quality: lint format type-check
	@echo "✓ All quality checks passed"

# Docker
build:
	@echo "Building Docker image..."
	docker-compose build
	@echo "✓ Image built"

build-no-cache:
	@echo "Building Docker image (no cache)..."
	docker-compose build --no-cache
	@echo "✓ Image built"

# Cleanup
clean:
	@echo "Removing Docker containers and volumes..."
	docker-compose down -v
	@echo "✓ Cleaned up"

clean-all: clean
	@echo "Removing Docker images..."
	docker rmi vin_startup_api vin_startup_worker vin_startup_dashboard 2>nul || true
	@echo "✓ Fully cleaned"

# Production stack (docker-compose.prod.yml)
prod-up:
	@echo "Starting Hanoi Air Forecast production stack..."
	@if not exist .env (echo ".env file not found. Copy .env.example and fill in keys." & exit /b 1)
	docker-compose -f docker-compose.prod.yml up -d
	@echo ""
	@echo "Production stack starting. Healthchecks take ~30s."
	@echo "  - Single entrypoint:    http://localhost/"
	@echo "  - API:                  http://localhost/api/forecast?district=hoan_kiem&hours=24"
	@echo "  - API docs:             http://localhost/docs"
	@echo "  - Dashboard:            http://localhost/"
	@echo ""
	@echo "Direct ports also exposed for debugging:"
	@echo "  - API:                  http://localhost:8000  (via docker-compose only if added)"
	@echo "  - Dashboard:            http://localhost:8501  (via docker-compose only if added)"
	@echo ""

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

prod-build:
	docker-compose -f docker-compose.prod.yml build

e2e:
	@echo "Running end-to-end tests against http://localhost..."
	set E2E=1&& set API_BASE=http://localhost&& python -m pytest tests/test_e2e.py -v

backtest:
	python scripts/run_backtest.py --days 7

# Helper targets
ps:
	docker-compose ps

shell-api:
	docker-compose exec api /bin/bash

shell-worker:
	docker-compose exec worker /bin/bash

shell-redis:
	docker-compose exec redis redis-cli
