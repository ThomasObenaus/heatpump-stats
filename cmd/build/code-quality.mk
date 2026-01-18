.PHONY: backend.test.unit backend.code-quality

backend.test.unit: ## Run unit tests
	cd backend && uv run pytest tests/ -v --cov=heatpump_stats --cov-report=term-missing

backend.code-quality: ## Lint and format the backend code using ruff
	cd backend && uv run ruff check . --fix && uv run ruff format .