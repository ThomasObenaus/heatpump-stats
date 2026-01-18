.PHONY: infra.up infra.down helper.verify.viessmann-api backend.daemon.mock backend.daemon.sim backend.daemon.prod backend.api.run frontend.ui.serve


infra.up: ## Start the infrastructure (InfluxDB) in detached mode
	docker compose --env-file ./cmd/local-setup/.env -f ./cmd/local-setup/docker-compose.infra.yml up -d

infra.down: ## Stop and remove the infrastructure containers
	docker compose --env-file ./cmd/local-setup/.env -f ./cmd/local-setup/docker-compose.infra.yml down

helper.verify.viessmann-api: ## Run the Viessmann API verification script
	.venv/bin/python cmd/viessmann_api_verify/verify_api.py

backend.daemon.mock: ## Start the daemon in mock mode
	cd backend && export COLLECTOR_MODE=mock && ../.venv/bin/python -m heatpump_stats.entrypoints.daemon

backend.daemon.sim: ## Start the daemon in simulation mode (Mock Sensors, Real DB)
	cd backend && export COLLECTOR_MODE=simulation && ../.venv/bin/python -m heatpump_stats.entrypoints.daemon

backend.daemon.prod: ## Start the daemon in production mode
	cd backend && export COLLECTOR_MODE=production && uv run python -m heatpump_stats.entrypoints.daemon

backend.api.run: ## Start the backend API
	cd backend && uv run uvicorn heatpump_stats.entrypoints.api.main:app --reload

frontend.ui.serve: ## Start the frontend development server
	@echo "Starting frontend development server..."
	@echo "Open your browser and navigate to http://localhost:5173"
	cd frontend && npm run dev

