.PHONY: help infra.up infra.down frontend.run frontend.build docker.build docker.push docker.up docker.up.local docker.down

help: ## Show this help message
	@grep -E '^[a-zA-Z0-9._-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

infra.up: ## Start the infrastructure (InfluxDB) in detached mode
	docker compose up -d

infra.down: ## Stop and remove the infrastructure containers
	docker compose down

verify.viessmann-api: ## Run the Viessmann API verification script
	./.venv/bin/python cmd/viessmann_api_verify/verify_api.py

backend.test.unit: ## Run unit tests
	cd backend && uv run pytest tests/ -v --cov=heatpump_stats --cov-report=term-missing

backend.daemon.mock: ## Start the daemon in mock mode
	cd backend && export COLLECTOR_MODE=mock && ../.venv/bin/python -m heatpump_stats.entrypoints.daemon

backend.daemon.sim: ## Start the daemon in simulation mode (Mock Sensors, Real DB)
	cd backend && export COLLECTOR_MODE=simulation && ../.venv/bin/python -m heatpump_stats.entrypoints.daemon

backend.daemon.prod: ## Start the daemon in production mode
	cd backend && export COLLECTOR_MODE=production && uv run python -m heatpump_stats.entrypoints.daemon

backend.code-quality: ## Lint and format the backend code using ruff
	cd backend && uv run ruff check . --fix && uv run ruff format .

backend.api: ## Start the backend API
	cd backend && uv run uvicorn heatpump_stats.entrypoints.api.main:app --reload

frontend.run: ## Start the frontend development server
	@echo "Starting frontend development server..."
	@echo "Open your browser and navigate to http://localhost:5173"
	cd frontend && npm run dev

frontend.build: ## Build the frontend for production
	cd frontend && npm run build

docker.build: ## Build backend and frontend Docker images (tags: docker.io/thobe/heatpump-stats-*)
	docker build -t docker.io/thobe/heatpump-stats-backend:latest -f backend/Dockerfile backend
	docker build -t docker.io/thobe/heatpump-stats-frontend:latest -f frontend/Dockerfile frontend

docker.push: ## Push images with optional tag (default: next patch based on latest git tag)
	@BASE=$$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0"); \
	read -p "Tag to push (default: $$BASE): " TAG; \
	TAG=$${TAG:-$$BASE}; \
	docker tag docker.io/thobe/heatpump-stats-backend:latest docker.io/thobe/heatpump-stats-backend:$$TAG; \
	docker tag docker.io/thobe/heatpump-stats-frontend:latest docker.io/thobe/heatpump-stats-frontend:$$TAG; \
	docker push docker.io/thobe/heatpump-stats-backend:$$TAG; \
	docker push docker.io/thobe/heatpump-stats-frontend:$$TAG; \
	echo "Pushed tag $$TAG (base $$BASE)"

docker.up: ## Start full dockerized stack locally (frontend, backend, influxdb)
	docker compose up -d

docker.up.local: ## Start stack using local build contexts (docker-compose.local.yml)
	docker compose -f docker-compose.local.yml up -d --build

docker.down: ## Stop and remove current docker-compose stack
	docker compose down