.PHONY: frontend.ui.build


frontend.ui.build: ## Build the frontend for production
	cd frontend && npm run build