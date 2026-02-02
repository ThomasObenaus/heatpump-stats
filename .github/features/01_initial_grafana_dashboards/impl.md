# Implementation: Initial Grafana Dashboards

## Implementation Order

1. **Overview Dashboard** - Provides immediate value for debugging
2. **Power & Energy Dashboard** - Critical for understanding consumption
3. **Temperatures Dashboard** - Core operational data
4. **System Health Dashboard** - Reliability monitoring
5. **Ground Source Dashboard** - Advanced analysis

---

## Technical Notes

- Dashboards will be provisioned via JSON files in `cmd/local-setup/grafana/provisioning/dashboards/`
- Time ranges should default to "Last 24 hours" for most panels
- Use InfluxDB Flux queries for data retrieval
- Consider creating dashboard variables for:
  - Time range presets
  - Circuit selection
  - Aggregation window (1m, 5m, 1h)
