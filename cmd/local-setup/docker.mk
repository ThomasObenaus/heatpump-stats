
.PHONY: docker.prod.up docker.prod.down docker.local.up docker.local.down

docker.prod.up: ## Start full dockerized stack locally. Images from the docker registry are pulled for that. (frontend, backend, influxdb)
	docker compose --env-file ./cmd/local-setup/.env.docker -f ./cmd/local-setup/docker-compose.prod.yml up -d

docker.prod.down: ## Stop and remove current docker-compose stack
	docker compose --env-file ./cmd/local-setup/.env.docker -f ./cmd/local-setup/docker-compose.prod.yml down

docker.local.up: ## Start stack using local docker build contexts instead of pulling images from a remote registry (docker-compose.local.yml)
	docker compose --env-file ./cmd/local-setup/.env.docker -f ./cmd/local-setup/docker-compose.local.yml up -d --build

docker.local.down: ## Stop and remove current docker-compose stack
	docker compose --env-file ./cmd/local-setup/.env.docker -f ./cmd/local-setup/docker-compose.local.yml down