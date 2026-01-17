.PHONY: infra.up infra.down 


infra.up: ## Start the infrastructure (InfluxDB) in detached mode
	docker compose --env-file ./cmd/local-setup/.env -f ./cmd/local-setup/docker-compose.infra.yml up -d

infra.down: ## Stop and remove the infrastructure containers
	docker compose --env-file ./cmd/local-setup/.env -f ./cmd/local-setup/docker-compose.infra.yml down