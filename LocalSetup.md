# Local Setup

This document describes how to run the application locally.

## Build and run

1. Start the infrastructure services: `make infra.up`
2. Start the backend collector daemon: `make backend.daemon.prod`
3. Start the backend API: `make backend.api.run`
4. Start the frontend: `make frontend.ui.serve`
5. Open The frontend in the browser at http://localhost:5173
6. (optional) Open Grafana at http://localhost:3000

### Details

#### Infrastructure Services

```bash
# starts the surrounding infrastructure that is just used bit not developed:
# InfluxDB
# Grafana
make infra.up

# stops the surrounding infrastructure
make infra.down
```

#### Backend Collector Daemon

```bash
# starts the backend (daemon collector) that collects the data from the heatpump
# a) Using a production configuration (real shelly and real heatpump)
make backend.daemon.prod

# b) Using a development configuration (mock shelly and mock heatpump)
make backend.daemon.mock

# c) Using a simulation configuration (mock shelly and mock heatpump with simulation data)
make backend.daemon.sim
```

#### Backend API

```bash
# starts the backend API that serves the data to the frontend
make backend.api.run
```

#### Frontend

```bash
# starts the frontend
make frontend.ui.serve
```

## Secrets and Environment Variables

The environment-variables for the local setup can be provided via .env file.
This file has to be placed at [cmd/local-setup](cmd/local-setup).
One can just use the example file [.env.example](./cmd/local-setup/.env.example), fill the variables and rename it to .env.
