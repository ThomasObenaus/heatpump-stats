.PHONY: help lint format all

all: format lint


lint: ## Run Ruff linting via uv and ruff
	uv run ruff check

help: ## Show this help message with available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed -e 's/:.*##/:\t/'

format: ## Format codebase using Ruff via uv
	uv run ruff format
