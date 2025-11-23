# Review Findings for PLAN.md

1. **[High] COP/JAZ math uses the wrong compressor signal**

   - Reference: PLAN.md §3 "Required Viessmann Data" (Compressor Modulation row) and §5 "Metrics & Calculations".
   - `heating.compressors.0.sensors.power` exposes the instantaneous compressor power draw in watts, not a modulation percentage. Using it as the modulation factor and multiplying by rated power will greatly overestimate thermal output (and therefore COP/JAZ). Viessmann exposes the modulation percentage via `heating.compressors.0.modulation` (value 0–100).
   - Suggested fix: Fetch `heating.compressors.0.modulation` (or fallback to `heating.circuits.<id>.sensors.power.consumption` if modulation is unavailable) and store the rated thermal power separately. Rework the COP/JAZ formulas so they rely on either actual flow/ΔT data or on the modulation percentage when/if confirmed to be exposed by your device.

2. **[Medium] Viessmann rate-limit pressure from frequent schedule polling**

   - Reference: PLAN.md §4 Phase 1 Step 3.
   - Pulling every schedule (heating circuits, DHW, circulation pump) every 30 minutes multiplies the number of API feature requests. Depending on the number of available programs/circuits, you can approach or exceed the 1,450 calls/24h limit—especially once retries and metadata calls are included.
   - Suggested fix: Reduce schedule polling frequency (e.g., every few hours), cache the last snapshot in SQLite, and trigger comparisons only when a change notification is needed. Also account for exponential backoff/retry budgets inside the daily quota.

3. **[Medium] OAuth token lifecycle and secret handling not covered**

   - Reference: PLAN.md Phase 1 Collector Service & Infrastructure sections.
   - The plan doesnt call out how Viessmann OAuth tokens/refresh tokens will be issued, securely stored (e.g., Docker secrets), refreshed, and rotated in the long-running collector container. Manual token files (like the current `token.save`) expire quickly; without an automated refresh process the whole system will stall.
   - Suggested fix: Document an auth flow (client credentials or PKCE) and bake token refresh into the collector startup, with persisted encrypted storage and alerting when refresh fails.

4. **[Low] Change-log diff strategy under-specified**
   - Reference: PLAN.md §4 Phase 1 Step 3.
   - Schedules returned by the API include arrays ordered by weekday and time-slot objects; naïvely comparing raw JSON every poll risks false positives (e.g., different ordering or timestamp formatting) and noisy change-log entries.
   - Suggested fix: Normalize the fetched schedules (sort slots, coerce time formats) before hashing/comparing and store a baseline snapshot per entity in SQLite so only meaningful changes trigger inserts.
