.PHONY: help infra.up infra.down

help: ## Show this help message
	@grep -E '^[a-zA-Z0-9._-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

infra.up: ## Start the infrastructure (InfluxDB) in detached mode
	docker-compose up -d

infra.down: ## Stop and remove the infrastructure containers
	docker-compose down

verify.viessmann-api: ## Run the Viessmann API verification script
	./.venv/bin/python cmd/viessmann_api_verify/verify_api.py

backend.test.unit: ## Run unit tests
	cd backend && ../.venv/bin/python -m pytest tests/ -v --cov=heatpump_stats --cov-report=term-missing
