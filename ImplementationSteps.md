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

- [x] Create `backend/heatpump_stats/domain/entities.py`: Define `SystemStatus`, `PowerReading`, `HeatPumpData`.
- [x] Create `backend/heatpump_stats/ports/heat_pump.py`: Define `HeatPumpPort` (Protocol).
- [x] Create `backend/heatpump_stats/ports/power_meter.py`: Define `PowerMeterPort` (Protocol).
- [x] Create `backend/heatpump_stats/ports/repository.py`: Define `RepositoryPort` (Protocol).
- **Deliverable**: Core interfaces defined without external dependencies.

### Step 1.3: Adapters (Infrastructure)

- Create `backend/heatpump_stats/adapters/shelly.py`: Implement `PowerMeterPort` using `aiohttp`.
- Create `backend/heatpump_stats/adapters/viessmann.py`: Implement `HeatPumpPort` using `PyViCare`.
- Create `backend/heatpump_stats/adapters/influxdb.py`: Implement `RepositoryPort` (metrics) using `influxdb-client`.
- Create `backend/heatpump_stats/adapters/sqlite.py`: Implement `RepositoryPort` (logs) using `SQLAlchemy`.
- **Deliverable**: Concrete classes that can talk to the outside world.

### Step 1.4: Services (Application Logic)

- Create `backend/heatpump_stats/services/collector.py`:
  - Inject ports via constructor.
  - Implement the main polling logic (fetch -> calculate -> save).
  - Implement **In-Memory Buffering** for Shelly data.
- Create `backend/heatpump_stats/services/reporting.py`: Logic for querying history.
- **Deliverable**: Testable business logic that runs with mocks or real adapters.

### Step 1.5: Entrypoints (Wiring it up)

- Create `backend/heatpump_stats/entrypoints/daemon.py`:
  - Load config.
  - Instantiate adapters (Real or Mock based on `COLLECTOR_MODE`).
  - Instantiate `CollectorService` with adapters.
  - Run the loop.
- **Deliverable**: Running service populating InfluxDB.

### Step 1.6: Configuration Change Detection

- Implement logic in `backend/heatpump_stats/services/change_detector.py` (or inside Collector).
- Normalize JSON, compute SHA256 hashes.
- Use `RepositoryPort` to save changes.
- **Deliverable**: System automatically logs schedule changes.

## Phase 2: Backend API

### Step 2.1: API Skeleton & Authentication

- Initialize FastAPI app in `backend/heatpump_stats/entrypoints/api/main.py`.
- Implement `POST /token` using `OAuth2PasswordBearer`.
- Inject `ReportingService` into API endpoints.
- **Deliverable**: Secure API responding to health checks.

### Step 2.2: Data Endpoints (InfluxDB Integration)

- Implement `GET /api/status`: Fetch latest system state.
- Implement `GET /api/history`: Flux queries for historical data (resampled).
- **Deliverable**: API serving JSON data for charts.

### Step 2.3: Changelog Endpoints (SQLite Integration)

- Implement `GET /api/changelog`: List changes with filtering.
- Implement `POST /api/changelog`: Add manual user notes.
- **Deliverable**: Full CRUD for system logs.

## Phase 3: Frontend Dashboard

### Step 3.1: Project Scaffold & Authentication

- Initialize Vite + React + TypeScript + Tailwind.
- Implement Login Page and `AuthProvider`.
- **Deliverable**: Frontend app with protected routes.

### Step 3.2: Dashboard Layout & Real-time Status

- Create layout shell (Sidebar/Header).
- Create "Current Status" widgets (Power, Temps, COP).
- Hook up to `GET /api/status` with polling.
- **Deliverable**: Dashboard showing live numbers.

### Step 3.3: Historical Charts

- Integrate a charting library (e.g., Recharts).
- Create components for Power, Temperatures, and Efficiency.
- Hook up to `GET /api/history`.
- **Deliverable**: Interactive charts.

### Step 3.4: Changelog UI

- Create a timeline view for the Changelog.
- Add a form to submit new notes.
- **Deliverable**: Complete monitoring solution.
