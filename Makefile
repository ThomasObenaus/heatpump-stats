.PHONY: help lint format all run test

all: format lint ## Run formatting and lint checks


lint: ## Run Ruff linting via uv and ruff
	uv run ruff check

help: ## Show this help message with available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed -e 's/:.*##/:\t/'

format: ## Format codebase using Ruff via uv
	uv run ruff format

run: ## Run the heatpump-stats fetch command via uv
	uv run heatpump-stats fetch

test: ## Execute the test suite via uv and pytest
	uv run python -m pytest
