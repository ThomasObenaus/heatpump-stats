# Implementation: Initial Grafana Dashboards

## Technical Notes

- Dashboards will be provisioned via JSON files in `cmd/local-setup/grafana/provisioning/dashboards/`
- Time ranges should default to "Last 24 hours" for most panels
- Use InfluxDB Flux queries for data retrieval
- Consider creating dashboard variables for:
  - Time range presets
  - Circuit selection
  - Aggregation window (1m, 5m, 1h)

## Hints

1. The backend daemon to collect the data is already running.
2. To start the infrastructure (InfluxDB + Grafana) locally for testing, run: `make infra.down && make infra.up`
3. Access Grafana at `http://localhost:3000` (default credentials: admin/admin)

---

## Implementation Order

1. **Overview Dashboard** - Provides immediate value for debugging
2. **Power & Energy Dashboard** - Critical for understanding consumption
3. **Temperatures Dashboard** - Core operational data
4. **System Health Dashboard** - Reliability monitoring
5. **Ground Source Dashboard** - Advanced analysis
