# Viessmann API / PyViCare Research Notes

## Search for "Thermal Energy Produced" (Cumulative Heat Generation/Yield)

### Findings in PyViCare Library

I analyzed the `PyViCare` library code (specifically `PyViCareHeatPump.py` and `PyViCareHeatingDevice.py`) to find methods related to heat production and energy yield.

#### 1. Solar Production (`heating.solar.power.production`)

The library supports retrieving solar power production if the device supports it.

- **Feature:** `heating.solar.power.production`
- **Methods in `PyViCareHeatingDevice.py`:**
  - `getSolarPowerProductionDays()`
  - `getSolarPowerProductionToday()`
  - `getSolarPowerProductionWeeks()`
  - `getSolarPowerProductionThisWeek()`
  - `getSolarPowerProductionMonths()`
  - `getSolarPowerProductionThisMonth()`
  - `getSolarPowerProductionYears()`
  - `getSolarPowerProductionThisYear()`

#### 2. Heat Pump Production (Current)

For heat pumps, the library exposes **current** heat production values, but I did not find explicit methods for **cumulative** heat production (yield) for the compressor/heat pump itself in the same way as consumption or solar production.

- **Feature:** `heating.compressors.{compressor}.heat.production.current`
- **Method:** `getCompressor(id).getHeatProductionCurrent()`
- **Feature:** `heating.heatingRod.heat.production.current`
- **Method:** `getHeatingRodHeatProductionCurrent()`

#### 3. Power Consumption (Input Energy)

Extensive support for power consumption (input) is available.

- **Feature:** `heating.power.consumption.total`, `heating.power.consumption.summary.heating`, `heating.power.consumption.summary.dhw`
- **Methods:**
  - `getPowerConsumptionToday()`
  - `getPowerSummaryConsumptionHeatingCurrentDay()`
  - `getPowerSummaryConsumptionHeatingCurrentMonth()`
  - `getPowerSummaryConsumptionHeatingCurrentYear()`
  - (And similar for DHW and Cooling)

#### 4. Efficiency / Performance Factors

- **Feature:** `heating.spf.total`, `heating.spf.heating`, `heating.spf.dhw`
- **Methods:**
  - `getSeasonalPerformanceFactorTotal()`
  - `getSeasonalPerformanceFactorHeating()`
  - `getSeasonalPerformanceFactorDHW()`

### Conclusion

- **Direct Cumulative Yield:** There is no direct method in `PyViCareHeatPump.py` visible for "Total Thermal Energy Produced" (cumulative yield) for the heat pump, unlike for Solar.
- **Current Production:** Only "current" heat production rate seems to be available via `getHeatProductionCurrent`.
- **Estimation:** It might be possible that `heating.power.production` exists in the raw API for some devices but is not mapped in the library, or one might need to calculate it (e.g., Consumption \* SPF, though this is an approximation).

### Recommendation

- Use `getHeatProductionCurrent` for real-time monitoring.
- Check if `heating.power.production` feature exists on your specific device by dumping all features (using `vicare.devices[0].dump_secure()`).
