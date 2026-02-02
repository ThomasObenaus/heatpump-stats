# Plan: Initial Grafana Dashboards

## Data Sources Available

Based on the collector daemon, the following data is stored in InfluxDB:

### Measurement: `heat_pump` (collected every ~5 minutes)

- `outside_temp` - Outside temperature
- `return_temp` - Return temperature (water returning to heat pump)
- `dhw_storage_temp` - Domestic hot water storage temperature
- `compressor_modulation` - Compressor modulation percentage (0-100%)
- `compressor_power_rated` - Rated power in kW
- `compressor_runtime` - Total compressor runtime hours
- `dhw_pump_active` - DHW circulation pump status (0/1)
- `thermal_power` - Estimated thermal power (modulation-based) in kW
- `thermal_power_delta_t` - Estimated thermal power (delta-T method) in kW
- `primary_supply_temp` - Brine temperature going TO heat pump (ground source)
- `primary_return_temp` - Brine temperature coming FROM heat pump
- `primary_pump_rotation` - Primary pump speed in %
- `secondary_supply_temp` - Heated water leaving condenser

### Measurement: `heating_circuit` (collected every ~5 minutes)

- `circuit_id` (tag) - Circuit identifier (0 or 1)
- `supply_temp` - Supply temperature for the circuit
- `pump_status` - Pump status (on/off)

### Measurement: `power_meter` (collected every ~10 seconds)

- `power_watts` - Current power consumption in watts
- `voltage` - Voltage (average of 3 phases)
- `current` - Total current
- `total_energy_wh` - Cumulative energy consumption in Wh

### Measurement: `system_status` (collected every ~5 minutes)

- `hp_online` - Heat pump online status (0/1)
- `pm_online` - Power meter online status (0/1)
- `db_connected` - Database connection status (0/1)
- `message` - Status message

---

## Suggested Dashboards (Ordered by Priority)

### 1. 🔥 **Overview Dashboard** (Priority: HIGH)

**Purpose:** Quick system health check and current state at a glance.

**Panels:**

- **Stat Panels (single values):**
  - Current power consumption (W)
  - Current outside temperature (°C)
  - Current compressor modulation (%)
  - DHW storage temperature (°C)
  - Circuit 0 supply temperature (°C)
  - Circuit 1 supply temperature (°C)
  - System status (Online/Offline indicators)
- **Gauges:**
  - Compressor modulation (0-100%)
  - Primary pump rotation (0-100%)

- **Time Series (last 1 hour):**
  - Power consumption trend
  - Temperatures overlay (outside, return, DHW)

---

### 2. ⚡ **Power & Energy Dashboard** (Priority: HIGH)

**Purpose:** Analyze electrical consumption patterns and costs.

**Panels:**

- **Time Series:**
  - Power consumption (W) over time - high resolution
  - Daily energy consumption bar chart (kWh)
  - Weekly/Monthly energy totals
- **Stats:**
  - Current power (W)
  - Today's energy (kWh)
  - This month's energy (kWh)
  - Average power (last 24h)
  - Peak power (last 24h)

- **Heatmap:**
  - Power consumption by hour of day (to identify usage patterns)

---

### 3. 🌡️ **Temperatures Dashboard** (Priority: HIGH)

**Purpose:** Monitor all temperature sensors and trends.

**Panels:**

- **Time Series (multi-line):**
  - All temperatures on one graph:
    - Outside temperature
    - DHW storage temperature
    - Primary Circuit (Ground/Brine):
      - Primary supply temp (from ground)
      - Primary return temp (to ground)
    - Secondary Circuit (Heating/House):
      - Secondary supply temp (to house)
      - Return temp (from house)
    - Circuit supply temperatures (0 and 1)

- **Dedicated panels:**
  - Outside temperature vs compressor modulation correlation
  - DHW temperature with target line overlay
  - Primary circuit delta-T (supply - return)
  - Secondary circuit delta-T (supply - return)

- **Table:**
  - Current values of all temperature sensors

---

### 4. **System Health Dashboard** (Priority: LOW)

**Purpose:** Monitor system reliability and debug issues.

**Panels:**

- **Status indicators:**
  - Heat pump online/offline
  - Power meter online/offline
  - Database connected

- **Time Series:**
  - Compressor runtime hours (cumulative)
  - System uptime tracking

- **Logs/Annotations:**
  - Error events
  - Configuration changes (from changelog)

- **Table:**
  - Last N status messages

---

### 5. 🌍 **Ground Source (Primary Circuit) Dashboard** (Priority: LOW)

**Purpose:** Monitor ground loop performance for geothermal systems.

**Panels:**

- **Time Series:**
  - Primary supply temperature (from ground)
  - Primary return temperature (to ground)
  - Delta-T (ground extraction rate)
  - Primary pump rotation

- **Stats:**
  - Average ground temperature trend
  - Seasonal comparison

---

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
