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

## Docker

Please refer to [Docker.md](Docker.md)
