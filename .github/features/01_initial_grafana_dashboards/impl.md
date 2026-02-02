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

---

## Dashboard 1: Overview Dashboard ✅ DONE

**File:** `cmd/local-setup/grafana/provisioning/dashboards/overview.json`

### Step 1: Create Dashboard Structure

```json
{
  "title": "Heat Pump Overview",
  "uid": "heatpump-overview",
  "refresh": "30s",
  "time": { "from": "now-1h", "to": "now" }
}
```

### Step 2: Add Stat Panels (Row 1)

Create stat panels for current values. Each panel uses a Flux query with `last()` aggregation.

**Panel 1.1: Current Power (W)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "power_meter")
  |> filter(fn: (r) => r["_field"] == "power_watts")
  |> last()
```

- Type: Stat
- Unit: Watt (W)
- Color mode: Value thresholds (green < 1000W, yellow < 3000W, red > 3000W)

**Panel 1.2: Outside Temperature (°C)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "outside_temp")
  |> last()
```

- Type: Stat
- Unit: Celsius (°C)
- Color mode: Value thresholds (blue < 5°C, green 5-20°C, red > 30°C)

**Panel 1.3: Compressor Modulation (%)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "compressor_modulation")
  |> last()
```

- Type: Stat
- Unit: Percent (%)

**Panel 1.4: DHW Storage Temperature (°C)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "dhw_storage_temp")
  |> last()
```

- Type: Stat
- Unit: Celsius (°C)
- Color mode: Value thresholds (blue < 45°C, green 45-55°C, red > 60°C)

**Panel 1.5: Circuit 0 Supply Temperature (°C)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heating_circuit")
  |> filter(fn: (r) => r["circuit_id"] == "0")
  |> filter(fn: (r) => r["_field"] == "supply_temp")
  |> last()
```

- Type: Stat
- Unit: Celsius (°C)

**Panel 1.6: Circuit 1 Supply Temperature (°C)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heating_circuit")
  |> filter(fn: (r) => r["circuit_id"] == "1")
  |> filter(fn: (r) => r["_field"] == "supply_temp")
  |> last()
```

- Type: Stat
- Unit: Celsius (°C)

**Panel 1.7: System Status**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "system_status")
  |> filter(fn: (r) => r["_field"] == "hp_online")
  |> last()
```

- Type: Stat
- Value mappings: 1 → "Online" (green), 0 → "Offline" (red)

### Step 3: Add Gauge Panels (Row 2)

**Panel 2.1: Compressor Modulation Gauge**

- Same query as Panel 1.3
- Type: Gauge
- Min: 0, Max: 100
- Thresholds: 0-30 (green), 30-70 (yellow), 70-100 (orange)

**Panel 2.2: Primary Pump Rotation Gauge**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_pump_rotation")
  |> last()
```

- Type: Gauge
- Min: 0, Max: 100
- Unit: Percent (%)

### Step 4: Add Time Series Panels (Row 3)

**Panel 3.1: Power Consumption Trend**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "power_meter")
  |> filter(fn: (r) => r["_field"] == "power_watts")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
```

- Type: Time series
- Unit: Watt (W)
- Fill opacity: 10

**Panel 3.2: Temperatures Overlay**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "outside_temp" or r["_field"] == "return_temp" or r["_field"] == "dhw_storage_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
```

- Type: Time series
- Unit: Celsius (°C)
- Legend: Show (bottom)
- Multiple Y-axes if needed

---

## Dashboard 2: Power & Energy Dashboard ✅ DONE

**File:** `cmd/local-setup/grafana/provisioning/dashboards/power-energy.json`

### Step 1: Create Dashboard Structure

```json
{
  "title": "Power & Energy",
  "uid": "heatpump-power",
  "refresh": "30s",
  "time": { "from": "now-24h", "to": "now" }
}
```

### Step 2: Add Time Series Panel - Power Consumption

**Panel 1: Power Consumption (W) - High Resolution**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "power_meter")
  |> filter(fn: (r) => r["_field"] == "power_watts")
```

- Type: Time series
- Unit: Watt (W)
- Line width: 1
- Fill opacity: 20

### Step 3: Add Daily Energy Bar Chart

**Panel 2: Daily Energy Consumption (kWh)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "power_meter")
  |> filter(fn: (r) => r["_field"] == "power_watts")
  |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ r with _value: r._value * 24.0 / 1000.0 }))
```

- Type: Bar chart
- Unit: kWh
- Note: This approximates daily energy by averaging power and multiplying by 24h

### Step 4: Add Stat Panels

**Panel 3: Current Power (W)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -5m)
  |> filter(fn: (r) => r["_measurement"] == "power_meter")
  |> filter(fn: (r) => r["_field"] == "power_watts")
  |> last()
```

- Type: Stat
- Unit: Watt (W)

**Panel 4: Today's Energy (kWh)**

```flux
import "date"

from(bucket: "heatpump_raw")
  |> range(start: date.truncate(t: now(), unit: 1d))
  |> filter(fn: (r) => r["_measurement"] == "power_meter")
  |> filter(fn: (r) => r["_field"] == "power_watts")
  |> mean()
  |> map(fn: (r) => ({ r with _value: r._value * float(v: date.hour(t: now())) / 1000.0 }))
```

- Type: Stat
- Unit: kWh

**Panel 5: Average Power (Last 24h)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "power_meter")
  |> filter(fn: (r) => r["_field"] == "power_watts")
  |> mean()
```

- Type: Stat
- Unit: Watt (W)

**Panel 6: Peak Power (Last 24h)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_measurement"] == "power_meter")
  |> filter(fn: (r) => r["_field"] == "power_watts")
  |> max()
```

- Type: Stat
- Unit: Watt (W)
- Color: Orange/Red

### Step 5: Add Heatmap (Optional - Advanced)

**Panel 7: Power by Hour of Day**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "power_meter")
  |> filter(fn: (r) => r["_field"] == "power_watts")
  |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
```

- Type: Heatmap
- Calculate from data
- Y Bucket: By hour of day (requires transformation)

---

## Dashboard 3: Temperatures Dashboard ✅ DONE

**File:** `cmd/local-setup/grafana/provisioning/dashboards/temperatures.json`

### Step 1: Create Dashboard Structure

```json
{
  "title": "Temperatures",
  "uid": "heatpump-temps",
  "refresh": "1m",
  "time": { "from": "now-24h", "to": "now" }
}
```

### Step 2: Add All Temperatures Time Series (Main Panel)

**Panel 1: All Temperatures**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) =>
    r["_field"] == "outside_temp" or
    r["_field"] == "dhw_storage_temp" or
    r["_field"] == "primary_supply_temp" or
    r["_field"] == "primary_return_temp" or
    r["_field"] == "secondary_supply_temp" or
    r["_field"] == "return_temp"
  )
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
```

- Type: Time series
- Unit: Celsius (°C)
- Legend: Show (right side)
- Line width: 2

**Panel 1b: Circuit Supply Temperatures (separate query)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heating_circuit")
  |> filter(fn: (r) => r["_field"] == "supply_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
```

- Add as second query to Panel 1
- Will show circuit_id as legend differentiator

### Step 3: Add Dedicated Panels

**Panel 2: Outside Temp vs Compressor Modulation**

Query A - Outside Temperature:

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "outside_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
```

Query B - Compressor Modulation:

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "compressor_modulation")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
```

- Type: Time series
- Dual Y-axis: Left for temperature (°C), Right for modulation (%)

**Panel 3: DHW Temperature with Target Line**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "dhw_storage_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
```

- Type: Time series
- Add threshold line at 50°C (typical DHW target)
- Color zones: < 45°C (blue), 45-55°C (green), > 55°C (orange)

**Panel 4: Primary Circuit Delta-T**

```flux
supply = from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_supply_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)

return_t = from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_return_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)

join(tables: {supply: supply, return_t: return_t}, on: ["_time"])
  |> map(fn: (r) => ({ r with _value: r._value_supply - r._value_return_t }))
```

- Type: Time series
- Unit: Kelvin (K) or Delta °C
- Title: "Primary Circuit ΔT (Ground Extraction)"

**Panel 5: Secondary Circuit Delta-T**

```flux
supply = from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "secondary_supply_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)

return_t = from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "return_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)

join(tables: {supply: supply, return_t: return_t}, on: ["_time"])
  |> map(fn: (r) => ({ r with _value: r._value_supply - r._value_return_t }))
```

- Type: Time series
- Unit: Kelvin (K) or Delta °C
- Title: "Secondary Circuit ΔT (Heat Delivery)"

### Step 4: Add Current Values Table

**Panel 6: Current Temperature Values**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -10m)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) =>
    r["_field"] == "outside_temp" or
    r["_field"] == "dhw_storage_temp" or
    r["_field"] == "primary_supply_temp" or
    r["_field"] == "primary_return_temp" or
    r["_field"] == "secondary_supply_temp" or
    r["_field"] == "return_temp"
  )
  |> last()
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
```

- Type: Table
- Column styles: Apply °C unit to all value columns

---

## Dashboard 4: System Health Dashboard ✅ DONE

**File:** `cmd/local-setup/grafana/provisioning/dashboards/system-health.json`

### Step 1: Create Dashboard Structure

```json
{
  "title": "System Health",
  "uid": "heatpump-health",
  "refresh": "1m",
  "time": { "from": "now-24h", "to": "now" }
}
```

### Step 2: Add Status Indicator Panels

**Panel 1: Heat Pump Online**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -10m)
  |> filter(fn: (r) => r["_measurement"] == "system_status")
  |> filter(fn: (r) => r["_field"] == "hp_online")
  |> last()
```

- Type: Stat
- Value mappings: 1 → "Online" (green bg), 0 → "Offline" (red bg)
- Color mode: Background

**Panel 2: Power Meter Online**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -10m)
  |> filter(fn: (r) => r["_measurement"] == "system_status")
  |> filter(fn: (r) => r["_field"] == "pm_online")
  |> last()
```

- Type: Stat
- Value mappings: 1 → "Online" (green bg), 0 → "Offline" (red bg)
- Color mode: Background

**Panel 3: Database Connected**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -10m)
  |> filter(fn: (r) => r["_measurement"] == "system_status")
  |> filter(fn: (r) => r["_field"] == "db_connected")
  |> last()
```

- Type: Stat
- Value mappings: 1 → "Connected" (green bg), 0 → "Disconnected" (red bg)
- Color mode: Background

### Step 3: Add Compressor Runtime

**Panel 4: Compressor Runtime Hours**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -10m)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "compressor_runtime")
  |> last()
```

- Type: Stat
- Unit: Hours (h)
- Title: "Total Compressor Runtime"

### Step 4: Add Status History Time Series

**Panel 5: System Status History**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "system_status")
  |> filter(fn: (r) => r["_field"] == "hp_online" or r["_field"] == "pm_online" or r["_field"] == "db_connected")
```

- Type: State timeline
- Value mappings: 1 → "Online/Connected" (green), 0 → "Offline/Disconnected" (red)
- Show legend

---

## Dashboard 5: Ground Source (Primary Circuit) Dashboard ✅ DONE

**File:** `cmd/local-setup/grafana/provisioning/dashboards/ground-source.json`

### Step 1: Create Dashboard Structure

```json
{
  "title": "Ground Source (Primary Circuit)",
  "uid": "heatpump-ground",
  "refresh": "1m",
  "time": { "from": "now-7d", "to": "now" }
}
```

### Step 2: Add Primary Circuit Time Series

**Panel 1: Primary Circuit Temperatures**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_supply_temp" or r["_field"] == "primary_return_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
```

- Type: Time series
- Unit: Celsius (°C)
- Legend: Show
- Colors: Supply (blue - cold from ground), Return (orange - warmer back to ground)

**Panel 2: Primary Circuit Delta-T (Ground Extraction)**

```flux
supply = from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_supply_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)

return_t = from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_return_temp")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)

join(tables: {supply: supply, return_t: return_t}, on: ["_time"])
  |> map(fn: (r) => ({ r with _value: r._value_supply - r._value_return_t }))
```

- Type: Time series
- Unit: Kelvin (K)
- Title: "Ground Heat Extraction Rate (ΔT)"
- Positive values = extracting heat from ground

**Panel 3: Primary Pump Rotation**

```flux
from(bucket: "heatpump_raw")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_pump_rotation")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
```

- Type: Time series
- Unit: Percent (%)
- Fill opacity: 30

### Step 3: Add Stat Panels

**Panel 4: Average Ground Temperature (7d)**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_supply_temp")
  |> mean()
```

- Type: Stat
- Unit: Celsius (°C)
- Title: "Avg Ground Temp (7d)"

**Panel 5: Current Ground Temperature**

```flux
from(bucket: "heatpump_raw")
  |> range(start: -10m)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_supply_temp")
  |> last()
```

- Type: Stat
- Unit: Celsius (°C)
- Title: "Current Ground Temp"

**Panel 6: Average Delta-T (7d)**

```flux
supply = from(bucket: "heatpump_raw")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_supply_temp")
  |> mean()

return_t = from(bucket: "heatpump_raw")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "heat_pump")
  |> filter(fn: (r) => r["_field"] == "primary_return_temp")
  |> mean()

join(tables: {supply: supply, return_t: return_t}, on: ["_stop"])
  |> map(fn: (r) => ({ r with _value: r._value_supply - r._value_return_t }))
```

- Type: Stat
- Unit: Kelvin (K)
- Title: "Avg ΔT (7d)"
