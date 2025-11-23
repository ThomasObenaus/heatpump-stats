# Review Findings for Heatpump Monitoring System Plan

## Overview

This document contains a comprehensive review of the PLAN.md file, identifying potential issues, missing considerations, and recommendations for improvement.

## Critical Issues

### 1. **COP Calculation Method Inconsistency** (X)

- **Issue**: The plan mentions calculating COP using "Flow Rate x DeltaT x Specific Heat Capacity" but doesn't list flow rate as a required data point from the Viessmann API.
- **Impact**: Cannot calculate actual thermal power without flow rate data.
- **Current Workaround**: Uses estimated power (Rated Power \* Modulation %), but this is an estimation, not actual thermal output.
- **Recommendation**:
  - Verify if flow rate data is available via the Viessmann API
  - If not available, document clearly that COP will be estimated, not measured
  - Consider alternative: Use supply-return temperature delta with estimated flow rate

### 2. **Rate Limiting Strategy Missing**

- **Issue**: While the plan mentions the 1450 calls/24h limit, there's no concrete strategy for handling rate limit enforcement.
- **Calculation**: Polling every 30 minutes = 48 polls/day. Assuming ~20 data points per poll = 960 calls/day.
- **Risk**: No buffer for retries, errors, or manual API interactions.
- **Recommendation**:
  - Implement exponential backoff for retries
  - Add rate limit monitoring/alerting
  - Consider implementing a token bucket algorithm
  - Add configurable polling intervals

### 3. **Data Persistence & Backup Strategy Missing**

- **Issue**: No mention of backup strategy for InfluxDB and SQLite data.
- **Impact**: Risk of data loss if container or host fails.
- **Recommendation**:
  - Define backup schedules (daily/weekly)
  - Document restore procedures
  - Consider using Docker volume backups or external storage

## Important Missing Components

### 4. **Error Handling & Resilience**

- **Missing**: No strategy for handling API failures, network issues, or data collection gaps.
- **Considerations Needed**:
  - What happens if Viessmann API is down for hours?
  - What happens if Shelly is unreachable?
  - How to handle incomplete data for COP calculations?
  - Should the system queue failed requests for retry?
- **Recommendation**: Add a dedicated section on error handling and resilience patterns.

### 5. **Authentication & Security**

- **Missing**:
  - No mention of securing the FastAPI endpoints
  - No authentication strategy for the web dashboard
  - Viessmann API credentials management not detailed
  - No mention of HTTPS/TLS for the frontend
- **Risk**: Exposed system with sensitive home data.
- **Recommendation**:
  - Add authentication (JWT, OAuth, or basic auth)
  - Use environment variables for credentials (mentioned .env exists)
  - Consider reverse proxy with TLS termination
  - Document credential rotation strategy

### 6. **Monitoring & Observability**

- **Missing**: No strategy for monitoring the monitoring system itself.
- **Needed**:
  - Health checks for all services
  - Logging strategy (log levels, retention, rotation)
  - Alerting for system failures
  - Metrics about the collector service (API call success rate, data collection latency)
- **Recommendation**: Add Prometheus + Grafana or similar for system monitoring, separate from heatpump monitoring.

### 7. **Configuration Management**

- **Missing**: How to configure system parameters without rebuilding containers.
- **Examples**:
  - Polling intervals
  - Shelly IP address
  - InfluxDB retention policies
  - Alert thresholds
- **Recommendation**: Use environment variables and/or a configuration file mounted as a volume.

### 8. **Data Retention Policy**

- **Missing**: No mention of how long to keep data in InfluxDB.
- **Considerations**:
  - Raw 10-second Shelly data grows quickly
  - Should old data be downsampled?
  - What's the retention period for different data resolutions?
- **Recommendation**:
  - Define retention policies (e.g., 7 days of 10s data, 90 days of 1m data, infinite yearly aggregates)
  - Use InfluxDB's automatic downsampling features

## Technical Concerns

### 9. **JAZ Calculation Accuracy**

- **Issue**: JAZ calculation uses estimated thermal power, not measured.
- **Accuracy Concern**: Modulation percentage may not linearly correspond to actual heat output due to:
  - Defrost cycles
  - Startup/shutdown inefficiencies
  - Varying outdoor temperatures affecting efficiency
- **Impact**: JAZ figures may be optimistic or inaccurate.
- **Recommendation**:
  - Clearly document this limitation
  - Consider adding calibration factors based on outdoor temperature
  - Validate against utility bills or other measurements

### 10. **Time Synchronization**

- **Missing**: No mention of time synchronization between components.
- **Issue**: Docker containers may have time drift, affecting timestamp correlation.
- **Recommendation**:
  - Ensure NTP is configured on the host
  - Use UTC consistently across all services
  - Document timezone handling strategy

### 11. **Network Architecture**

- **Missing**: Docker networking configuration details.
- **Questions**:
  - Should services use bridge network or custom network?
  - How does the backend container reach the local Shelly device?
  - What ports need to be exposed?
- **Recommendation**: Document Docker network configuration in the docker-compose.yml design.

### 12. **Shelly Data Buffering**

- **Issue**: Polling Shelly every 10 seconds generates 8640 data points/day.
- **Concern**: Writing to InfluxDB every 10s may be inefficient.
- **Recommendation**:
  - Implement batching (e.g., write every minute with 6 data points)
  - Document buffering strategy and memory implications

## Missing Implementation Details

### 13. **Frontend State Management**

- **Missing**: No mention of state management for React (Redux, Zustand, Context API).
- **Recommendation**: Decide on state management approach, especially for real-time updates.

### 14. **Real-time Updates**

- **Missing**: How does the frontend get real-time data?
- **Options**: Polling, WebSockets, Server-Sent Events.
- **Recommendation**: Define the real-time update strategy.

### 15. **API Versioning**

- **Missing**: No API versioning strategy.
- **Recommendation**: Use versioned endpoints (e.g., `/api/v1/status`) from the start.

### 16. **Testing Strategy**

- **Missing**: No mention of testing (unit tests, integration tests, end-to-end tests).
- **Recommendation**: Define testing approach for each component.

### 17. **Deployment & CI/CD**

- **Missing**: How to deploy updates? Manual or automated?
- **Recommendation**: Document deployment process, consider GitHub Actions for CI/CD.

### 18. **Documentation**

- **Missing**: Plan for API documentation (OpenAPI/Swagger).
- **Recommendation**: FastAPI auto-generates Swagger docs - plan to use this feature.

## Data Model Concerns

### 19. **InfluxDB Schema Design**

- **Missing**: Detailed schema design (measurements, tags, fields).
- **Recommendation**: Define:
  - Measurement names (e.g., `temperature`, `power`, `cop`)
  - Tags for grouping (e.g., `source=viessmann`, `circuit=0`, `sensor=supply`)
  - Field keys and data types

### 20. **SQLite Change Log Schema**

- **Missing**: Table structure for the change log database.
- **Recommendation**: Define schema with fields like:
  - `id`, `timestamp`, `change_type` (manual/automatic), `component`, `old_value`, `new_value`, `notes`

## Edge Cases & Scenarios

### 21. **System State Changes**

- **Missing**: How to handle heatpump state changes (e.g., switched off, maintenance mode).
- **Recommendation**: Track operational state and filter metrics accordingly.

### 22. **Seasonal Considerations**

- **Issue**: JAZ calculation is yearly, but partial year results may be misleading.
- **Example**: Starting monitoring in summer shows unrealistic JAZ.
- **Recommendation**: Add context indicators (e.g., "90 days of data collected").

### 23. **Data Migration**

- **Missing**: Strategy for schema changes or data migration.
- **Recommendation**: Version the database schemas and plan for migrations.

## Performance Considerations

### 24. **Query Performance**

- **Missing**: No mention of expected data volume and query optimization.
- **Calculation**: 1 year of 10s Shelly data ≈ 3.15M data points.
- **Recommendation**:
  - Plan for indexing strategy
  - Consider using InfluxDB continuous queries for pre-aggregation
  - Define query performance requirements

### 25. **Frontend Bundle Size**

- **Missing**: No consideration for frontend performance.
- **Recommendation**:
  - Plan for code splitting
  - Consider lazy loading for charts
  - Document target bundle size

## Operational Concerns

### 26. **Cost Analysis**

- **Missing**: Resource requirements (CPU, RAM, disk space).
- **Recommendation**: Estimate and document resource requirements for each container.

### 27. **Maintenance Windows**

- **Missing**: How to handle system updates without data loss.
- **Recommendation**: Document update procedures and expected downtime.

### 28. **User Management**

- **Missing**: Multi-user support or single user assumption?
- **Recommendation**: Clarify if this is needed and plan accordingly.

## Recommendations Summary

### High Priority

1. ✅ Clarify COP calculation limitations and accuracy
2. ✅ Implement comprehensive error handling and retry logic
3. ✅ Add authentication and security measures
4. ✅ Define data retention and backup strategy
5. ✅ Document InfluxDB and SQLite schemas

### Medium Priority

6. Add system monitoring and health checks
7. Implement rate limiting enforcement
8. Define configuration management approach
9. Document Docker networking architecture
10. Plan testing strategy

### Low Priority

11. Add API versioning
12. Define CI/CD pipeline
13. Consider frontend performance optimizations
14. Document maintenance procedures
15. Add multi-user support (if needed)

## Positive Aspects

The plan demonstrates:

- ✅ Well-thought-out technology choices
- ✅ Clear separation of concerns
- ✅ Appropriate use of time-series database
- ✅ Recognition of API rate limiting constraints
- ✅ Good understanding of COP/JAZ metrics
- ✅ Practical approach to data resolution mismatch
- ✅ Clear phase-based implementation strategy

## Conclusion

The plan is solid and well-structured but would benefit from addressing the above concerns, particularly around error handling, security, data persistence, and operational aspects. Most issues are not blockers but should be addressed before production deployment.
