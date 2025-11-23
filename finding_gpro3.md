# Review of Heatpump Monitoring System Plan

Here are the findings after reviewing `PLAN.md`.

## 1. Critical: Missing Flow Rate for Accurate COP Calculation

The plan mentions calculating COP via `Flow Rate x DeltaT`. However, **Flow Rate** is missing from the "Required Viessmann Data" section. Without a flow meter, this calculation is impossible.

- **Impact**: You must rely entirely on the `Rated Power * Modulation %` estimation for Thermal Power.
- **Recommendation**: Remove the reference to Flow Rate calculation unless you verify the API provides it. Explicitly state that COP will be an _estimate_ based on modeled output.

## 2. Accuracy of Energy Integration (JAZ)

Calculating energy (kWh) by integrating instantaneous power sampled every **30 minutes** is highly inaccurate for a heat pump.

- **Reason**: Heat pumps modulate or cycle on/off. A 30-minute snapshot assumes the device ran at that specific power level for the entire half-hour. If the pump cycles off 1 minute after the poll, you will overestimate energy by 29 minutes.
- **Impact**: The JAZ (Seasonal COP) calculation will likely be significantly off.
- **Recommendation**:
  - Check if the Viessmann API provides **cumulative energy counters** (e.g., compressor runtimes or energy stats). Using counters is the only accurate way to track energy with low-frequency polling.
  - If counters are unavailable, acknowledge this as a significant margin of error in the plan.

## 3. Data Alignment for COP

The plan proposes using "Average Electrical Power (Shelly, 30m)" vs "Instantaneous Thermal Power (Viessmann, snapshot)".

- **Issue**: Comparing an _average_ input over a window with an _instantaneous_ output at the end of that window is mathematically inconsistent. If the heat pump turned off 5 minutes before the poll, the "Average Input" will be non-zero, but "Instantaneous Output" will be zero, resulting in a COP of 0 (incorrect).
- **Recommendation**: For the COP calculation, use the **average electrical power of a short window** (e.g., 1-2 minutes) surrounding the Viessmann poll timestamp, rather than the full 30-minute average. This aligns the input and output states more closely.

## 4. Token Management & Reliability

The plan mentions polling but omits **OAuth2 Token Refresh** logic.

- **Risk**: The collector will fail once the initial token expires (usually 1 hour).
- **Recommendation**: Add a specific task in "Phase 1" to implement robust token refreshing and error handling (e.g., exponential backoff on API errors) to prevent data gaps.

## 5. InfluxDB Retention Policies

Storing Shelly data at **10-second resolution** indefinitely will generate a lot of data (~3 million points/year per field).

- **Recommendation**: Add a step to configure **InfluxDB Retention Policies and Downsampling Tasks**. For example, keep 10s data for 7 days, then downsample to 1m or 5m for long-term storage.

## 6. Change Log State Persistence

To detect configuration changes ("Compare with previous state"), the Collector needs a persistent "State Cache".

- **Recommendation**: Explicitly mention that the Collector must load the "last known state" from SQLite or a file on startup to avoid detecting "changes" every time the container restarts.
