# Docker

This document describes how to build, push and run the application as a dockerized service.

## Image Structure

The frontend image contains an nginx that serves the UI application.
The backend image contains both the python API and the data collector daemon.

### API and Collector Containers

Because of this the backend image can be instanciated as a api container and a data collector daemon container. This is possible using the entrypoints as defined in

## Build and run

```bash
# builds the:
# 1. backend image 'docker.io/thobe/heatpump-stats-backend' tagged as latest
# 2. frontend image 'docker.io/thobe/heatpump-stats-frontend' tagged as latest
make docker.build

# start with locally build images
make docker.up.local

# start with images from docker hub (latest)
make docker.up

# push images
# maybe a docker login is required first
make docker.push

# start with images from docker hub
make docker.up

# stop
make docker.down

# to stop and remove all data
make docker.clean
```

## Environment Variables

### Local Setup

The environment-variables for the local setup can be provided via .env.docker file.
This file has to be placed at [cmd/local-setup](cmd/local-setup).
One can just use the example file [.env.docker.example](./cmd/local-setup/.env.docker.example), fill the variables and rename it to .env.docker.

### Portainer, Synology, Kubernetes or similar

The environment-variables can be also provided via pure environment variables.
