## Review of PLAN.md (GPT-5.1)

### 1. Overall architecture

- The end-to-end architecture is coherent and technically feasible.
- Clear separation of concerns between data collection (Collector), storage (InfluxDB/SQLite), backend (FastAPI), and frontend (React).

### 2. Potential gaps / missing details

1. **InfluxDB bucket & auth wiring**

   - Buckets `heatpump_raw` and `heatpump_downsampled` are defined conceptually, but:
     - No explicit plan for **bucket creation & retention setup** (init script, Influx CLI, or API call) is described.
     - InfluxDB **org, token, and bucket names** should be spelled out as env vars (`INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET_RAW`, `INFLUX_BUCKET_DOWNSAMPLED`).
   - Downsampling tasks are mentioned, but the **deployment mechanism** (e.g., bootstrap script in the backend container) could be clarified.

2. **Collector scheduling & process model**

   - The Collector runs 10s and 5m tasks, but it is not fully specified whether:
     - It runs as a **standalone process** in the backend container (e.g., a supervisor/`gunicorn`+`uvicorn`+background process) or as a **FastAPI background task**.
     - How **graceful shutdown** and restart (e.g., container restarts) are handled so that intervals are not double-counted.
   - Consider explicitly deciding between:
     - One container with `FastAPI + Collector` (single process with scheduler library like `APScheduler` or `asyncio` loops), or
     - Two processes/containers: `collector` and `api`, both talking to InfluxDB+SQLite.

3. **Time alignment for COP/JAZ**

   - Strategy for alignment (Shelly avg over 5m window) is described conceptually, but:
     - It is not clear **where** this aggregation happens: inside the Collector using Shelly 10s samples from InfluxDB vs. InfluxDB tasks feeding pre-aggregated power.
     - If using InfluxDB to aggregate, the **exact Flux query/window alignment** for COP calculation should be defined (e.g., `aggregateWindow(every: 5m, offset: 0m, createEmpty: false)`).

4. **Shelly Pro3EM connectivity & auth**

   - Plan assumes local `http://<ip>/rpc/EM.GetStatus` without mentioning:
     - Whether **auth** (basic token / password) is required or disabled in your setup.
     - How to handle **IP changes** (DHCP vs. static lease); the plan assumes a fixed IP.
   - Might be worth defining env vars (`SHELLY_HOST`, `SHELLY_AUTH`) and a brief retry/backoff strategy beyond the single retry.

5. **Viessmann API token lifecycle**

   - Rate limiting strategy is well defined, but the **auth flow** details are light:
     - How refresh tokens are stored (file vs. env vs. SQLite) and rotated.
     - How the Collector reacts to **expired/invalid tokens** (e.g., backoff vs. reauth).
   - Given `token.save` exists, you might want an explicit subsection describing the **token cache** mechanism and failure modes.

6. **SQLite deployment & schema migration details**

   - Alembic is mentioned but without:
     - Concrete **directory layout** (e.g., `backend/alembic/`, `alembic.ini`).
     - Strategy for **first-run DB creation** (bootstrap script vs. entrypoint running `alembic upgrade head`).
   - Backups use `sqlite3` CLI; ensure that binary is actually present in the backup container (currently implicit).

7. **Security & auth hardening**

   - Plan has a basic username/password auth for FastAPI, but misses:
     - Password **hashing** vs. plain text in env vars.
     - **HTTPS termination** strategy (reverse proxy in front of Nginx? handled by home router / Traefik / Caddy?).
     - Protection against **CSRF** is probably not needed for a pure token-based API used by a JS SPA, but worth stating explicitly.
   - Consider whether the API is only reachable on the **LAN** and if so, mention that in the Security section.

8. **Error logging & observability**

   - Error reactions are described, but no concrete logging strategy:
     - Centralized log format (JSON vs. plain text).
     - Log levels (INFO/WARN/ERROR) and where logs end up (Docker stdout vs. file).
   - No explicit mention of **alerts** or at least visual indicators beyond dashboard status; for a home setup this might be fine, but you might want optional email/Push/Telegram alerts for prolonged outages.

9. **Testing scope for collector & hardware integration**

   - Unit and integration testing are nicely described for backend.
   - The **Collector** logic (scheduling, retry, rate limiting, COP/JAZ math) should be explicitly listed as a test target, ideally separated from I/O so it can run in simulation.
   - Simulation mode is planned but not explicitly wired into the testing section (e.g., "integration tests will use simulation mode data sources").

10. **Configuration management** - Many runtime knobs (intervals, buckets, flow rate, thresholds, backup retention) are described textually but not grouped: - It may help to define a dedicated **"Configuration"** section that lists all env vars and their defaults (collector intervals, paths, tokens, `ESTIMATED_FLOW_RATE`, rate limit thresholds, etc.). - That will reduce drift between docs and implementation.

11. **Docker Compose & volumes** - Compose file is mentioned but not shaped yet: - Volumes for `influxdb`, `sqlite` (mounted directory), and `backups` should be explicitly named and mapped. - Networking between containers (default bridge network is fine) could be briefly stated (e.g., service names used as hosts). - Nothing is technically wrong, but a short subsection with **service definitions summary** would remove ambiguity.

12. **InfluxDB schema vs. raw Viessmann data** - `heatpump_sensors` model is sound but it assumes all fields are present for all tag combinations: - In practice, different circuits or DHW may miss some fields; document that non-applicable values are stored as **null/missing**, not 0. - Clarify whether compressor statistics (`hours`) are stored directly in InfluxDB (and if so, under which measurement/fields).

13. **Derived metric calculation location** - COP/JAZ are described as calculated by Collector and/or backend API: - For `COP` you state "Collector Service"; for `JAZ` you state "calculated dynamically by the Backend API". - This split is fine, but you may want a clear rule: **all per-interval metrics in Collector, long-range aggregates in API**, or similar.

14. **Backup container lifecycle** - Backup strategy is sound, but a few operational edges are not mentioned: - How the backup job is triggered (cron inside container vs. host cron hitting `docker exec`). - Where backup logs go and how failures are surfaced. - What happens if `influx backup` or `sqlite3` fails (retry/log-only?).

15. **Local development ergonomics** - There is no explicit plan for: - A `Makefile`/`justfile` or helper scripts to run "dev stack" (e.g., `docker compose up`, `backend` reload, `frontend` dev server). - Seed/sample data in simulation mode for frontend development without hardware.

16. **Versioning & upgrades** - InfluxDB v2, Shelly firmware, and Viessmann API/pyViCare versions are not pinned in the plan. - Consider stating that container images and Python deps will be **version-pinned** and periodically updated, to avoid silent behaviour changes.

### 3. Things that look especially solid

- **Shadow State + hashing** for change detection is a robust approach.
- **Rate limiting strategy** with safety cutoff and HTTP 429 backoff is well thought out.
- **Tiered storage + downsampling** in InfluxDB is appropriate for the data rates.
- **Simulation mode** is an excellent idea for both development and testing.

### 4. Suggested concrete additions to PLAN.md

- Add a **Configuration** section listing all important env vars and intervals.
- Add a short **"Collector Process Model"** subsection specifying whether it is an internal FastAPI task or a separate process/container.
- Add a **"Token Management"** subsection clarifying how Viessmann tokens are stored/rotated and how failures are handled.
- Add a concise **Docker Compose overview** (services, volumes, and main env vars per service).
- In the **Testing Strategy**, explicitly mention tests for:
  - Rate limiting logic.
  - COP/JAZ calculation using simulated data across realistic intervals.
  - Shadow state change detection using canonicalization & hashing.
