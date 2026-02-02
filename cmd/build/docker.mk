.PHONY: docker.build docker.push

docker.build: ## Build backend and frontend Docker images (tags: docker.io/thobe/heatpump-stats-*)
	@echo "Building backend image which includes the backend api and the backend daemon..."
	docker build -t docker.io/thobe/heatpump-stats-backend:latest -f backend/Dockerfile backend
	@echo "Building frontend image..."
	docker build -t docker.io/thobe/heatpump-stats-frontend:latest -f frontend/Dockerfile frontend
	@echo "Building grafana image..."
	docker build -t docker.io/thobe/heatpump-stats-grafana:latest -f cmd/local-setup/grafana/Dockerfile cmd/local-setup/grafana

docker.push: ## Push images with optional tag (default: next patch based on latest git tag)
	@BASE=$$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0"); \
	read -p "Tag to push (default: $$BASE): " TAG; \
	TAG=$${TAG:-$$BASE}; \
	docker tag docker.io/thobe/heatpump-stats-backend:latest docker.io/thobe/heatpump-stats-backend:$$TAG; \
	docker tag docker.io/thobe/heatpump-stats-frontend:latest docker.io/thobe/heatpump-stats-frontend:$$TAG; \
	docker tag docker.io/thobe/heatpump-stats-grafana:latest docker.io/thobe/heatpump-stats-grafana:$$TAG; \
	docker push docker.io/thobe/heatpump-stats-backend:$$TAG; \
	docker push docker.io/thobe/heatpump-stats-frontend:$$TAG; \
	docker push docker.io/thobe/heatpump-stats-grafana:$$TAG; \
	docker push docker.io/thobe/heatpump-stats-backend:latest; \
	docker push docker.io/thobe/heatpump-stats-frontend:latest; \
	docker push docker.io/thobe/heatpump-stats-grafana:latest; \
	echo "Pushed tag $$TAG (base $$BASE)"