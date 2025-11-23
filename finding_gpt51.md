# Review of PLAN.md (Heatpump Monitoring System)

## 1. Overall assessment

The plan is coherent and technically feasible. Architecture (InfluxDB + FastAPI + React + Docker) fits the problem well, and the metrics/JAZ strategy is reasonable given Viessmann API constraints.

Below are concrete findings: potential gaps, risks, and a few clarifications that may help before you start implementing.

---

## 2. Viessmann API & data model

- **Token refresh / authentication flow not specified**

  - PLAN.md assumes Viessmann API access is “given”, but there’s no explicit strategy for:
    - How you will obtain and refresh access/refresh tokens (PyViCare vs. own OAuth flow).
    - Where tokens/credentials will be stored (env vars vs. file vs. Docker secrets).
  - **Suggestion**: Add a short “Authentication & Secrets” subsection describing:
    - Use of PyViCare’s token handling or your own wrapper.
    - Storage of credentials (e.g. `.env` + Docker secrets; never baked into images).

- **PyViCare feature → measurement mapping only partially covered**

  - The table lists methods/properties, but you don’t yet define the InfluxDB measurement/field/tags mapping (e.g. `measurement=heating`, `field=outside_temp`, `tag=circuit_id`).
  - **Suggestion**: Add a “Data schema for InfluxDB” section with:
    - Measurements (e.g. `viessmann_sensors`, `shelly_power`, `cop`, `jaz`).
    - Tags (e.g. `source`, `circuit`, `sensor_type`).
    - Field names and units.

- **Configuration change detection strategy needs more detail**

  - You state: _“Compare with previous state -> Write changes to SQLite”_ but do not define:
    - How you represent the “current snapshot” for comparison (JSON blob per poll? normalized per circuit?)
    - How to avoid noisy changes (rounding temps, schedule order changes, daylight saving time shifts).
  - **Suggestion**:
    - Define a normalized config model in SQLite (circuits, DHW, circulation, schedule entries).
    - Use hashing or canonical JSON representation to detect “real” changes.

- **Missing handling for partially unavailable data**
  - Some devices/firmware may not expose all documented properties (e.g. certain schedules or modulation properties).
  - **Suggestion**: Explicitly plan for:
    - Optional metrics (graceful handling when a feature is missing).
    - Logging of missing/unsupported features so you can adjust.

---

## 3. Shelly Pro3EM integration

- **Local IP / discovery not specified**

  - Assumes you know the Shelly IP and it is static.
  - **Suggestion**: Add a note that Shelly should use a DHCP reservation / static IP, and that the IP is configured via env var.

- **Time synchronization & timestamp source**

  - PLAN.md doesn’t define whether you trust Shelly’s timestamp or assign timestamps in the collector.
  - **Suggestion**: Decide that the collector assigns timestamps (using host time in UTC) to all readings, to ensure consistency across Viessmann and Shelly sources.

- **Error handling / retries and backoff**
  - No plan for connection failures or Shelly reboots.
  - **Suggestion**: Add high-level behavior:
    - Retry with exponential backoff for transient failures.
    - Log and skip intervals instead of blocking the main loop.

---

## 4. InfluxDB details

- **InfluxDB v2 org/bucket/retention policy not detailed**

  - You mention bucket `heatpump` but not retention or downsampling.
  - **Suggestion**:
    - Define default retention (e.g. raw Shelly data 6–12 months, downsampled series for long-term).
    - Plan for continuous queries / tasks (if needed) for downsampling to coarser resolutions.

- **Write strategy & batching**

  - You mention “batched data points”, but not how batching interacts with 10 s reads.
  - **Suggestion**:
    - Specify batch size or flush interval (e.g. write every N points or every M seconds).
    - Confirm that batching is separate for Shelly and Viessmann to avoid mixing different cadences.

- **Time zones**
  - Time zone handling is not explicitly described.
  - **Suggestion**: Decide:
    - All timestamps stored as UTC in InfluxDB.
    - UI/backend applies local time zone for display.

---

## 5. Collector service behavior

- **Concurrency / scheduling model not spelled out**

  - You have two cadences (10s and 30m) plus background metric calculations (COP).
  - **Suggestion**:
    - Decide whether to use a single event loop (e.g. `asyncio`) with scheduled tasks, or a threaded approach.
    - Document that the collector is a long-running process (one per deployment) with graceful shutdown.

- **Rate limit enforcement**

  - You note the 1450 calls/24h but don’t define:
    - Calls per poll (how many PyViCare calls per 30m cycle).
    - Safety margin (e.g. stay < 50% of the limit).
  - **Suggestion**:
    - Explicitly calculate expected calls per day and document the budget.
    - Implement a central Viessmann client wrapper that rate-limits and logs usage.

- **Resilience and restart behavior**

  - There is no mention of:
    - What happens on backend/container restart (e.g. last config snapshot, missed data windows).
    - Whether the collector can resume using persisted state for config comparison.
  - **Suggestion**:
    - Store last known configuration in SQLite and reuse it after restart.
    - Accept that power data is missing for downtime; do not try to backfill.

- **Logging and observability**
  - No explicit logging strategy.
  - **Suggestion**:
    - Add at least a minimal plan: structured logs from the collector and FastAPI (JSON or key=value), log level env-var controlled.

---

## 6. Metrics & calculations

- **COP & JAZ calculations: edge cases**

  - You describe formulas but not:
    - Handling of intervals with zero or near-zero electrical power (avoid division by zero).
    - Handling of intervals where Viessmann data is missing or stale.
  - **Suggestion**:
    - Define minimum data quality requirements for a valid COP point (e.g. require Shelly data coverage > X% of the 30min window and valid modulation data).

- **Rated power constant vs configuration**

  - PLAN.md assumes `Rated Power (16 kW)` but does not say where this constant comes from.
  - **Suggestion**:
    - If possible, read rated power from the API and store it in config/SQLite; only fall back to a constant.

- **Derivation of daily/weekly/annual stats**

  - You mention Flux `spread` on `total_act_energy`, which is good, but:
    - No mention of how to handle counter resets (e.g. Shelly firmware upgrade, device reset).
  - **Suggestion**:
    - Plan a sanity-check for large negative deltas or sudden drops and either mark them as resets or have a mitigation strategy.

- **Yearly estimation assumptions**
  - PLAN.md proposes extrapolation from current average daily consumption but not how you bound or label it.
  - **Suggestion**:
    - Clearly label estimations as such in the API/Frontend (e.g. `estimate: true`).
    - Consider exposing both YTD actuals and forecast separately.

---

## 7. Backend (FastAPI)

- **Project layout / modules not defined**

  - Only endpoints are listed; no structure.
  - **Suggestion**: Add a brief structure, e.g.:
    - `app/main.py` (FastAPI app + lifespan).
    - `app/api/` (routers for status/history/changelog).
    - `app/services/` (InfluxDB & SQLite access, COP/JAZ calculations).
    - `app/models/` (Pydantic models / DTOs).

- **Authentication / access control**

  - Not mentioned.
  - For home-network only, you might accept “open” access, but it’s worth documenting.
  - **Suggestion**:
    - State explicitly whether API is LAN-only, behind reverse proxy, or protected (e.g. basic auth or token).

- **Pagination and query limits**

  - `GET /api/history` and `/api/changelog` may need:
    - Time range parameters (already mentioned) plus limit/offset or cursor.
  - **Suggestion**: Plan for reasonable defaults and max window to avoid huge responses.

- **Error handling / status codes**
  - Not yet specified.
  - **Suggestion**: Document that the API will return structured error responses (e.g. problem+json style or a custom simple schema).

---

## 8. Frontend (React + Tailwind)

- **State management and data fetching strategy**

  - You mention charts and status cards but not how data is fetched/cached.
  - **Suggestion**:
    - Decide early whether to use React Query (TanStack Query) or a simple custom hook layer for API calls.

- **Time range and resolution controls**

  - The plan mentions history but not UI controls for date range and aggregation.
  - **Suggestion**:
    - Include a basic requirement: dropdown or date-picker for time range (e.g. last 24h, 7d, 30d, custom).

- **Responsive layout**

  - Not mentioned, but important for tablets/phones.
  - **Suggestion**: Confirm dashboard is mobile-friendly in the design goals.

- **Error & loading states**
  - No explicit mention of how the frontend shows API errors or loading skeletons.
  - **Suggestion**: Add acceptance criteria that all main views handle loading/error/empty states.

---

## 9. Docker & deployment

- **docker-compose details**

  - Only high-level components are listed.
  - **Suggestion**:
    - Define in the plan:
      - Volume mounts for InfluxDB and SQLite (e.g. `influxdb-data`, `backend-data`).
      - Network mode (bridge with a dedicated network).
      - Env var handling for all services.

- **Secrets management**

  - Viessmann tokens and InfluxDB admin credentials should not be hard-coded.
  - **Suggestion**:
    - Mention `.env` + `docker-compose` `env_file` or Docker secrets for sensitive data.

- **Backup and upgrade strategy**
  - Not mentioned.
  - **Suggestion**:
    - Briefly note how you plan to back up InfluxDB and SQLite volumes (e.g. periodic `docker run --rm` backup jobs or host-level backups).

---

## 10. Testing & validation

- **No explicit testing strategy**

  - PLAN.md doesn’t mention tests.
  - **Suggestion**:
    - Add a small section:
      - Unit tests for metric calculations (COP, JAZ, aggregation).
      - Integration tests for the FastAPI endpoints using a test InfluxDB/SQLite.
      - At least a basic end-to-end sanity check script that polls both sources and writes to InfluxDB.

- **Simulation / mock mode**
  - For development, relying on real Viessmann/Shelly devices is limiting.
  - **Suggestion**:
    - Define a "simulation mode" where the collector uses mocked data sources and writes to a dev bucket.

---

## 11. Security & privacy

- **Network exposure**

  - Not explicitly stated where the stack is reachable from.
  - **Suggestion**:
    - Clarify that the stack is meant for a trusted home LAN and should not be directly exposed to the public internet.

- **Data privacy**
  - Some metrics (schedules, occupancy patterns via heating behavior) are sensitive.
  - **Suggestion**:
    - Mention that data remains local; no cloud uploads beyond Viessmann’s existing cloud API.

---

## 12. Documentation & operations

- **Missing minimal README / operations notes**
  - PLAN.md is excellent as a design spec but doesn’t cover day-2 operations.
  - **Suggestion**:
    - Add a brief checklist:
      - How to start/stop the system.
      - How to rotate logs.
      - Where to look if data stops flowing (InfluxDB UI, backend logs, collector logs).

---

## 13. Summary of key additions to consider

- Clarify authentication & secret management for Viessmann, InfluxDB, and Shelly.
- Define InfluxDB schema (measurements/fields/tags) and retention/downsampling strategy.
- Flesh out configuration change detection (SQLite schema, snapshot strategy, noise reduction).
- Make explicit decisions about timestamp source (UTC) and handling partial/missing data.
- Add basic plans for resilience (retries, restarts), logging, and simple test coverage.
- Specify a bit more structure for the FastAPI backend and React frontend (layout, state management).
- Document deployment/ops basics: volumes, backups, LAN-only access.

These additions don’t change your core design but will significantly reduce surprises during implementation and operation.
