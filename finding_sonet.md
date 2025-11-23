# Review Findings for PLAN.md

## Critical Issues

### 1. **COP Calculation Timing Logic Flaw**

**Location**: Section 5 (Metrics & Calculations)

**Problem**: The plan states COP will be calculated at 5-minute intervals using "average electrical power from Shelly over the last 5m (queried from InfluxDB)". However, the Collector Service writes to InfluxDB but also needs to read from it to calculate COP. This creates a circular dependency and timing complexity.

**Impact**:

- The collector needs to query InfluxDB during its own write cycle
- Risk of race conditions or incomplete data if Shelly writes haven't finished
- Adds unnecessary database round-trips

**Recommendation**: Calculate the 5-minute average electrical power directly in the Collector Service's memory buffer before writing to InfluxDB, rather than querying back from the database.

---

### 2. **Compressor Runtime Delta Calculation Gap**

**Location**: Section 5, JAZ calculation

**Problem**: The plan mentions using `heating.compressors.0.statistics.hours` (cumulative runtime) to determine runtime fraction within 5-minute intervals: `Hours_Current - Hours_Previous`. However, there's no mention of:

- How to handle the initial state (first poll has no "previous" value)
- How to handle counter resets (if they occur)
- Persistence of the previous value across collector restarts

**Impact**: Could lead to incorrect thermal energy calculations or crashes on first run/restart.

**Recommendation**:

- Store the previous runtime value in SQLite or a persistent state file
- Implement counter reset detection logic
- Handle the cold-start case gracefully

---

### 3. **Rate Limiting Persistence Location Ambiguity**

**Location**: Section 6 (Key Considerations)

**Problem**: States "The Collector Service will track API usage in a persistent store (SQLite)" but this table is never defined in Section 10 (Database Schema).

**Impact**: Implementation gap - developers don't know what table structure to create.

**Recommendation**: Add a `rate_limit_log` table to Section 10 with columns: `timestamp`, `endpoint`, `response_code`, etc.

---

## Design Concerns

### 4. **JAZ Calculation Complexity vs. User Value**

**Location**: Section 5, JAZ metric

**Concern**: The plan proposes two methods for thermal power estimation (Modulation-based and Delta-T-based), with the Delta-T method requiring user-configured flow rate. This adds significant complexity:

- Users may not know their flow rate
- Wrong flow rate = wrong JAZ
- Two metrics to maintain and explain to users

**Question**: Is the Delta-T method necessary for MVP? Consider making it a "Phase 2" feature.

---

### 5. **Missing Authentication Implementation Details**

**Location**: Section 2 (Architecture), Section 7 (Phase 2)

**Gap**: The plan mentions "Token-based authentication (OAuth2 Password Flow)" and a single user, but doesn't specify:

- How the password will be hashed (bcrypt? argon2?)
- Where user credentials are stored (environment variable? SQLite?)
- Token expiration strategy and refresh mechanism
- JWT signing secret management

**Recommendation**: Add explicit security requirements, e.g., "Use bcrypt for password hashing, store credentials in environment variables, JWT tokens expire after 24h."

---

### 6. **Backup Strategy - Missing SQLite Locking Consideration**

**Location**: Section 13 (Backup Strategy)

**Problem**: The backup command `sqlite3 /data/changelog.db ".backup '/backups/...'` is mentioned as ensuring a "hot backup without locking the DB for long." However:

- SQLite still acquires locks during backup
- If the collector is writing during backup, it could fail or be delayed
- No mention of WAL mode (Write-Ahead Logging) which would minimize lock contention

**Recommendation**:

- Enable WAL mode for SQLite: `PRAGMA journal_mode=WAL;`
- Document this in the implementation phase
- Consider using `PRAGMA wal_checkpoint(TRUNCATE)` before backup

---

## Missing Components

### 7. **No Error Recovery for Partial API Responses**

**Location**: Section 7 (Error Handling)

**Gap**: The plan handles complete API failures (Viessmann/Shelly down) but doesn't address scenarios where:

- Viessmann API returns HTTP 200 but with partial/malformed JSON
- Some features are present but others missing in the batch response
- Invalid data values (e.g., temperature = -999 indicating sensor error)

**Recommendation**: Add data validation layer:

- Use Pydantic models with validation for all API responses
- Log warnings for out-of-range values (e.g., outside temp < -40°C or > 50°C)
- Skip writing individual bad data points while keeping good ones

---

### 8. **Shelly Phase Imbalance Detection Missing**

**Location**: Section 11 (InfluxDB Schema)

**Observation**: The schema includes per-phase power data (`phase` tag: "a", "b", "c") but there's no mention of why or how this will be used. If it's for monitoring phase imbalance, this should be explicit.

**Question**: Is phase-level data just for debugging, or will there be a dashboard feature showing phase distribution? If not needed, remove the complexity.

---

### 9. **Time Zone Handling for Schedules**

**Location**: Section 6 (Time Zone Handling)

**Gap**: While the plan correctly specifies UTC storage and local display, it doesn't address how **heating schedules** (which are inherently local-time-based) will be handled:

- Viessmann API likely returns schedules in local time
- Storing them as-is means daylight saving time changes could trigger false "change detections"
- Comparing schedules across DST boundaries is complex

**Recommendation**:

- Document the assumption that schedules are in device local time
- Store schedules in SQLite with a timezone field
- Add DST-aware comparison logic for change detection

---

### 10. **No Monitoring/Alerting Strategy**

**Location**: Missing from plan

**Gap**: For a long-running system that needs to be reliable, there's no mention of:

- How to monitor if the collector crashes (Docker restart policy?)
- Alerting if data collection stops (email? push notification?)
- Health check endpoints for Docker

**Recommendation**: Add Section 17: "Monitoring & Alerting"

- Implement Docker health checks for all containers
- Add a `/health` endpoint to FastAPI that checks DB connectivity
- Consider a simple "data freshness" check that alerts if no new data in 10+ minutes

---

## Minor Issues

### 11. **InfluxDB Task Scheduling Overlap**

**Location**: Section 8 (Data Retention & Downsampling)

**Concern**: The 5-minute aggregation task "runs every 15m". This means it processes 3 windows at once. While not incorrect, it's less intuitive than running every 5 minutes (processing 1 window per run).

**Recommendation**: Consider running the task every 5 minutes for simpler mental model, or document why the 15-minute interval was chosen (e.g., reducing task overhead).

---

### 12. **React Query Configuration Missing**

**Location**: Section 2 (Frontend)

**Gap**: React Query is mentioned as the state management solution, but there's no guidance on critical configuration like:

- `staleTime` / `cacheTime` for efficient polling
- `refetchInterval` for live dashboard updates
- Error retry logic

**Recommendation**: Add a subsection under Phase 3 with recommended React Query defaults for time-series dashboards.

---

### 13. **Docker Compose Networking Not Specified**

**Location**: Section 2 (Infrastructure)

**Gap**: Three containers (InfluxDB, Backend, Frontend) need to communicate, but there's no mention of:

- Docker network configuration
- Whether containers use default bridge or custom network
- Port exposure strategy (which ports are exposed to host?)

**Recommendation**: Add a "Docker Networking" section specifying:

- Custom bridge network for inter-container communication
- Only expose Frontend (port 80/443) and optionally Backend API (port 8000) to host
- Keep InfluxDB internal-only

---

## Positive Observations

### ✅ Well-Considered Areas:

1. **Rate limiting strategy** with clear budget calculation and safety margins
2. **Data quality** approach with gaps instead of zeros for missing data
3. **Shadow state** mechanism for change detection is sophisticated and handles restarts correctly
4. **Tiered storage** with raw + downsampled buckets is industry best practice
5. **Simulation mode** for development is excellent for iteration speed

---

## Summary

**Critical (Must Fix)**:

- #1: COP calculation timing
- #2: Compressor runtime delta handling
- #3: Rate limiting schema missing

**High Priority (Should Fix)**:

- #5: Authentication details
- #6: SQLite backup + WAL mode
- #7: Partial API response handling
- #10: Monitoring strategy

**Medium Priority (Consider)**:

- #4: Simplify JAZ calculation for MVP
- #9: Schedule timezone handling
- #13: Docker networking specification

**Low Priority (Nice to Have)**:

- #8: Phase data usage clarification
- #11: Task scheduling documentation
- #12: React Query configuration guidance

---

**Overall Assessment**: The plan is comprehensive and shows strong architectural thinking, particularly around time-series data handling and change detection. The main gaps are in operational concerns (monitoring, error handling edge cases) and some implementation details that would block development (missing schemas, authentication specifics). With the critical issues addressed, this is a solid foundation for implementation.
