# heatpump-stats

## Default Login

un: admin
pq: admin

![login](doc/login.png)

## Secrets And Configuration

**IMPORTANT**: To get access to the services, secrets have to be provided.
The secrets and other settings are passed via environment files.

## Local Setup

For the docker setup one has to provide a .env file in the root folder.
An example file is provided as [.env.example](./.env.example).

```bash
# start infrastructure services (influxdb)
make infra.up

# start collector, backend-api and frontend
make backend.daemon.prod
make backend.api
make frontend.run
```

## Docker Setup

For the docker setup one has to provide a .env.docker file in the root folder.
An example file is provided as [.env.docker.example](./.env.docker.example).

```bash
# build local images
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
