# Implementation Steps

## Phase 1: Infrastructure & Core Data Collection

### Step 0: API Verification (Completed)

- Verified that `CU401B_G` supports necessary data points.
- Confirmed JAZ calculation strategy (Modulation \* Rated Power).

### Step 1.1: Environment & Docker Infrastructure (Completed)

- [x] Create `.env.example` with all required variables.
- [x] Create `docker-compose.yml` defining the `influxdb` service.
- [x] Create `backend/heatpump_stats/config.py` to load environment variables using Pydantic `BaseSettings`.
- **Deliverable**: Running InfluxDB container and verified config loading.

### Step 1.2: Domain & Ports (The Core) (Completed)

- [x] Create `backend/heatpump_stats/domain/metrics.py`: Define `SystemStatus`, `PowerReading`, `HeatPumpData`.
- [x] Create `backend/heatpump_stats/ports/heat_pump.py`: Define `HeatPumpPort` (Protocol).
- [x] Create `backend/heatpump_stats/ports/power_meter.py`: Define `PowerMeterPort` (Protocol).
- [x] Create `backend/heatpump_stats/ports/repository.py`: Define `RepositoryPort` (Protocol).
- **Deliverable**: Core interfaces defined without external dependencies.

### Step 1.3: Adapters (Infrastructure) (Completed)

- [x] Create `backend/heatpump_stats/adapters/shelly.py`: Implement `PowerMeterPort` using `aiohttp`.
- [x] Create `backend/heatpump_stats/adapters/viessmann.py`: Implement `HeatPumpPort` using `PyViCare`.
- [x] Create `backend/heatpump_stats/adapters/influxdb.py`: Implement `RepositoryPort` (metrics) using `influxdb-client`.
- [x] Create `backend/heatpump_stats/adapters/sqlite.py`: Implement `RepositoryPort` (logs) using `SQLAlchemy`. (Deferred: Using InfluxDB for status for now)
- **Deliverable**: Concrete classes that can talk to the outside world.

### Step 1.4: Services (Application Logic) (Completed)

- [x] Create `backend/heatpump_stats/services/collector.py`:
  - [x] Inject ports via constructor.
  - [x] Implement the main polling logic (fetch -> calculate -> save).
  - [x] Implement **In-Memory Buffering** for Shelly data.
- [x] Create `backend/heatpump_stats/services/reporting.py`: Logic for querying history.
- **Deliverable**: Testable business logic that runs with mocks or real adapters.

### Step 1.5: Entrypoints (Wiring it up) (Completed)

- [x] Create `backend/heatpump_stats/entrypoints/daemon.py`:
  - [x] Load config.
  - [x] Instantiate adapters (Real or Mock based on `COLLECTOR_MODE`).
  - [x] Instantiate `CollectorService` with adapters.
  - [x] Run the loop.
- **Deliverable**: Running service populating InfluxDB.

### Step 1.6: Configuration Change Detection (Completed)

- [x] Implement logic in `backend/heatpump_stats/services/change_detector.py` (or inside Collector/Adapter).
- [x] Normalize JSON, compute SHA256 hashes (Implemented via Dict comparison in SqliteAdapter).
- [x] Use `RepositoryPort` to save changes.
- **Deliverable**: System automatically logs schedule changes.

## Phase 2: Backend API

### Step 2.1: API Skeleton & Authentication (Completed)

- [x] Initialize FastAPI app in `backend/heatpump_stats/entrypoints/api/main.py`.
- [x] Implement `POST /token` using `OAuth2PasswordBearer`.
- [x] Inject `ReportingService` into API endpoints.
- **Deliverable**: Secure API responding to health checks.

### Step 2.2: Data Endpoints (InfluxDB Integration) (Completed)

- [x] Implement `GET /api/status`: Fetch latest system state.
- [x] Implement `GET /api/history`: Flux queries for historical data (resampled).
- **Deliverable**: API serving JSON data for charts.

### Step 2.3: Changelog Endpoints (SQLite Integration) (Completed)

- [x] Implement `GET /api/changelog`: List changes with filtering.
- [x] Implement `POST /api/changelog`: Add manual user notes.
- **Deliverable**: Full CRUD for system logs.

### Step 2.4: Graceful Shutdown & Resource Management (Completed)

- [x] Implement FastAPI `lifespan` context manager in `main.py`.
- [x] Manage `InfluxDBAdapter` and `SqliteAdapter` lifecycle (open/close).
- [x] Ensure dependencies in `dependencies.py` use the shared/managed instances or close their own.
- **Deliverable**: No resource leaks (unclosed connections) on application shutdown.

### Step 2.5: To be implemented (Completed)

- [x] Add unit tests for `POST /token` endpoint (success and failure cases).
- [x] Add unit test for `ReportingService.get_system_status()`.
- [x] Add unit tests for `/health` endpoint.

## Phase 3: Frontend Dashboard

### Step 3.1: Project Scaffold & Authentication (Completed)

- [x] Initialize Vite + React + TypeScript + Tailwind.
- [x] Implement Login Page and `AuthProvider`.
- **Deliverable**: Frontend app with protected routes.

### Step 3.2: Dashboard Layout & Real-time Status (Completed)

- [x] Create layout shell (Sidebar/Header).
- [x] Create "Current Status" widgets (Power, Temps, COP).
- [x] Hook up to `GET /api/status` with polling.
- **Deliverable**: Dashboard showing live numbers.

### Step 3.3: Historical Charts (Completed)

- [x] Integrate a charting library (Recharts).
- [x] Create components for Power, Temperatures, and Efficiency.
- [x] Hook up to `GET /api/history`.
- [x] Create PowerChart component with electrical and thermal power visualization.
- [x] Create TemperatureChart component with multiple temperature sensors and delta-T calculations.
- [x] Create CircuitChart component for heating circuits and DHW temperatures.
- [x] Create EfficiencyChart component for COP and modulation display.
- [x] Create EnergyChart component for accumulated energy statistics.
- [x] Implement interactive legend toggling for all charts.
- [x] Add time range selection (6h, 12h, 24h, 48h, 7d).
- [x] Implement loading states and error handling.
- **Deliverable**: Interactive charts with comprehensive heat pump metrics.

### Step 3.4: Changelog UI (Completed)

- [x] Create a timeline view for the Changelog.
- [x] Add a form to submit new notes.
- **Deliverable**: Complete monitoring solution.

#### 3.5 Improvements for the History Charts (To be implemented)

- [ ] **Export EnergyChart from index.ts**: Add `EnergyChart` to the chart exports in `frontend/src/components/charts/index.ts` for consistency.
- [ ] **Improve TypeScript typing**: Replace `any` types in legend click handlers with proper Recharts types.
- [ ] **Add zoom/pan functionality**: Consider adding chart zoom capabilities for detailed analysis of specific time periods.
- [ ] **Add keyboard navigation**: Implement keyboard controls for chart interaction and navigation.
- [ ] **Add chart synchronization**: Synchronize tooltips/crosshairs across multiple charts for better correlation analysis.
- [ ] **Add data point markers**: Option to show/hide data point markers on line charts for sparse data.
- [ ] **Add statistical overlays**: Add trend lines, moving averages, or statistical annotations.
- [ ] **Performance optimization**: Implement data downsampling for very long time ranges to improve rendering performance.
- [ ] **Add chart customization**: Allow users to customize colors, line styles, or visible metrics via settings.
- [ ] **Add comparison mode**: Enable comparing current period with previous periods (day-over-day, week-over-week).
- [ ] **Add alerts/annotations**: Visual markers for system events, configuration changes, or anomalies.
- [ ] **Improve error states**: Add more detailed error messages and recovery options when data fetching fails.
- [ ] **Add refresh controls**: Manual refresh button and auto-refresh toggle for history data.
- [ ] **Add chart print/screenshot**: Functionality to export charts as images for reports.
- [ ] **Add tooltip enhancements**: Show more context in tooltips (e.g., outdoor temp, system status at that time).
- [ ] **Add loading skeleton**: Replace spinner with skeleton screens for better perceived performance.

## Phase 4: Deployment Setup

### Step 4.0: Create Docker Assets

- **Backend Dockerfile** (`backend/Dockerfile`):
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY pyproject.toml poetry.lock* ./
  RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false && poetry install --only main
  COPY backend ./backend
  ENV PYTHONPATH=/app
  CMD ["python", "-m", "heatpump_stats.entrypoints.api.main"]
  ```
- **Frontend Dockerfile** (`frontend/Dockerfile`):

  ```dockerfile
  FROM node:20-alpine AS build
  WORKDIR /app
  COPY package*.json ./
  RUN npm ci
  COPY . .
  RUN npm run build

  FROM nginx:stable-alpine
  COPY --from=build /app/dist /usr/share/nginx/html
  EXPOSE 80
  ```

- **.dockerignore**: Add `node_modules`, `dist`, `.venv`, `__pycache__`, `*.pyc`, and `.git` to reduce build context.
- **docker-compose.yml** (root): reference built images (see 4.2) and bind mounts for data.

### Step 4.1: Build and Push Images to Docker Hub

- **Registry**: Use Docker Hub private repos, e.g., `docker.io/<user>/heatpump-stats-backend` and `docker.io/<user>/heatpump-stats-frontend`.
- **Login**:
  ```bash
  docker login
  ```
- **Build (amd64)** — your NAS is not multi-arch:
  ```bash
  docker build -t docker.io/<user>/heatpump-stats-backend:latest backend
  docker build -t docker.io/<user>/heatpump-stats-frontend:latest frontend
  docker push docker.io/<user>/heatpump-stats-backend:latest
  docker push docker.io/<user>/heatpump-stats-frontend:latest
  ```
- **InfluxDB image**: Use the official `influxdb:2` from Docker Hub (no build needed).

### Step 4.2: Start All Components on Synology (Docker Compose)

1. **Prepare folders on Synology** (example):

   - `/volume1/docker/heatpump-stats/env/.env` (secrets)
   - `/volume1/docker/heatpump-stats/influxdb` (InfluxDB data/config)
   - `/volume1/docker/heatpump-stats/backend` (SQLite changelog)
   - `/volume1/docker/heatpump-stats/backups` (backup outputs)

2. **Create or update `docker-compose.yml`** to reference pushed images:

   ```yaml
   services:
     influxdb:
       image: influxdb:2
       volumes:
         - ./influxdb:/var/lib/influxdb2
         - ./influxdb:/etc/influxdb2
       ports:
         - "8086:8086"

     backend:
       image: docker.io/<user>/heatpump-stats-backend:latest
       env_file: ./env/.env
       depends_on:
         - influxdb
       volumes:
         - ./backend:/app/data

     frontend:
       image: docker.io/<user>/heatpump-stats-frontend:latest
       ports:
         - "8080:80"
       depends_on:
         - backend
   ```

3. **Deploy on Synology (SSH terminal)**:

   ```bash
   cd /volume1/docker/heatpump-stats
   docker compose pull
   docker compose up -d
   ```

4. **Reverse proxy/TLS (optional)**: Use Synology Application Portal to terminate HTTPS and forward to `frontend:8080` and, if exposed, to `backend`.

5. **Backups**: Run the backup container/task (described in PLAN.md) to dump InfluxDB and SQLite into `./backups`, and include that folder in Hyper Backup.
