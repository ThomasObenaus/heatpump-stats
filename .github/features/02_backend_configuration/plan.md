# Plan: Backend Configuration

## Current State Analysis

### What's Already in Place ✅

The codebase already has a solid foundation with pydantic-settings:

- **Central Configuration**: [backend/heatpump_stats/config.py](backend/heatpump_stats/config.py) uses `pydantic_settings.BaseSettings`
- **Environment Variable Support**: Automatically loads from `.env` file and environment variables
- **Type Safety**: All settings have type annotations with defaults
- **Single Instance**: Global `settings` object imported throughout the codebase

### Current Configuration Categories

| Category     | Settings                                                                                                                                                 |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| General      | `LOG_LEVEL`, `TZ`, `COLLECTOR_MODE`                                                                                                                      |
| Viessmann    | `VIESSMANN_USER`, `VIESSMANN_PASSWORD`, `VIESSMANN_CLIENT_ID`, `VIESSMANN_POLL_INTERVAL`, `VIESSMANN_CONFIG_INTERVAL`                                    |
| Shelly       | `SHELLY_HOST`, `SHELLY_PASSWORD`, `SHELLY_POLL_INTERVAL`                                                                                                 |
| InfluxDB     | `INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET_RAW`, `INFLUXDB_BUCKET_DOWNSAMPLED`, `INFLUXDB_ADMIN_USER`, `INFLUXDB_ADMIN_PASSWORD` |
| Metrics      | `HEAT_PUMP_RATED_POWER`, `ESTIMATED_FLOW_RATE`                                                                                                           |
| Persistence  | `SQLITE_DB_PATH`                                                                                                                                         |
| API Security | `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `API_USERNAME`, `API_PASSWORD`                                                                 |

### Files Using Settings

- [daemon.py](backend/heatpump_stats/entrypoints/daemon.py) - Main collector daemon
- [viessmann.py](backend/heatpump_stats/adapters/viessmann.py) - Heat pump API adapter
- [sqlite.py](backend/heatpump_stats/adapters/sqlite.py) - Database adapter
- [main.py](backend/heatpump_stats/entrypoints/api/main.py) - API entrypoint
- [security.py](backend/heatpump_stats/entrypoints/api/security.py) - JWT authentication
- [dependencies.py](backend/heatpump_stats/entrypoints/api/dependencies.py) - FastAPI dependencies

### Direct Environment Variable Access ✅

**Good news**: No direct `os.environ` or `os.getenv` calls found in the source code. All environment variable access goes through the `settings` object.

---

## Improvement Opportunities

### 1. Configuration Validation & Documentation

- Add field descriptions for better documentation
- Add validators for complex constraints (e.g., URL formats, password strength)
- Add computed properties for derived values

### 2. Configuration Grouping

- Organize flat settings into nested groups for better maintainability
- Example: `settings.viessmann.user` instead of `settings.VIESSMANN_USER`

### 3. Configuration Testing

- Add tests to verify all required settings are defined
- Add tests for validation rules
- Ensure tests can override settings cleanly

### 4. Secret Management

- Mark sensitive fields appropriately
- Consider masking secrets in logs/debug output

### 5. Feature Flags

- Add support for feature toggles (useful for gradual rollouts)

---

## Implementation Plan

### Phase 1: Enhance Current Configuration (Low Risk)

**Goal**: Improve the existing configuration without breaking changes

#### Task 1.1: Add Field Descriptions & Validators

- Add `Field(description=...)` to all settings for self-documentation
- Add validators for URL formats, numeric ranges
- Add example values in descriptions

#### Task 1.2: Add Secret Masking

- Use `SecretStr` type for sensitive fields
- Ensures secrets are not accidentally logged

#### Task 1.3: Configuration Documentation

- Generate documentation from settings model
- Add `.env.example` file with all variables documented

### Phase 2: Nested Configuration Groups (Medium Risk)

**Goal**: Better organization with backward compatibility

#### Task 2.1: Create Configuration Sub-models

```python
class ViessmannSettings(BaseModel):
    user: str = Field(default="", description="Viessmann API username")
    password: SecretStr = Field(default="", description="Viessmann API password")
    client_id: str = Field(default="", description="OAuth client ID")
    poll_interval: int = Field(default=300, ge=60, description="Metrics poll interval in seconds")
    config_interval: int = Field(default=18000, ge=300, description="Config poll interval in seconds")
```

#### Task 2.2: Update Settings Class

```python
class Settings(BaseSettings):
    viessmann: ViessmannSettings = Field(default_factory=ViessmannSettings)
    shelly: ShellySettings = Field(default_factory=ShellySettings)
    influxdb: InfluxDBSettings = Field(default_factory=InfluxDBSettings)
    # ... etc
```

#### Task 2.3: Migrate Usages

- Update all files to use new nested access pattern
- Keep backward compatibility aliases if needed during transition

### Phase 3: Testing & Documentation (Low Risk)

**Goal**: Ensure robustness and maintainability

#### Task 3.1: Configuration Tests

- Test that all required settings have sensible defaults
- Test validation rules work correctly
- Test environment variable loading

#### Task 3.2: Test Fixtures

- Create pytest fixtures for common configuration overrides
- Document how to override settings in tests

---

## Recommended Implementation Order

| Order | Task                                    | Risk   | Effort | Impact                   |
| ----- | --------------------------------------- | ------ | ------ | ------------------------ |
| 1     | Task 1.1: Add Descriptions & Validators | Low    | Small  | High (documentation)     |
| 2     | Task 1.2: Add Secret Masking            | Low    | Small  | Medium (security)        |
| 3     | Task 3.1: Configuration Tests           | Low    | Medium | High (reliability)       |
| 4     | Task 1.3: Create `.env.example`         | Low    | Small  | High (onboarding)        |
| 5     | Task 2.1-2.3: Nested Groups             | Medium | Large  | Medium (maintainability) |

---

## Files to Create/Modify

### New Files

- [x] `backend/.env.example` - Documented environment template
- [x] `backend/tests/test_config.py` - Configuration tests

### Modified Files

- [x] `backend/heatpump_stats/config.py` - Enhanced settings with validators, descriptions, groups

### Potentially Modified (if doing Phase 2)

- [x] `backend/heatpump_stats/entrypoints/daemon.py` - Updated to use SecretStr.get_secret_value()
- [x] `backend/heatpump_stats/adapters/viessmann.py` - Updated to use SecretStr.get_secret_value()
- [ ] `backend/heatpump_stats/adapters/sqlite.py`
- [x] `backend/heatpump_stats/entrypoints/api/main.py` - Updated to use SecretStr.get_secret_value()
- [x] `backend/heatpump_stats/entrypoints/api/security.py` - Updated to use SecretStr.get_secret_value()
- [x] `backend/heatpump_stats/entrypoints/api/dependencies.py` - Updated to use SecretStr.get_secret_value()

---

## Decision Points

1. **Nested vs Flat Configuration**: Should we keep flat `VIESSMANN_USER` style or migrate to nested `viessmann.user`?
   - _Recommendation_: Start with enhanced flat configuration (Phase 1), migrate to nested later if needed

2. **Backward Compatibility**: How long to maintain old access patterns?
   - _Recommendation_: If migrating to nested, use deprecation warnings for 1-2 releases

3. **Secret Storage**: Should we integrate with external secret managers (Vault, AWS Secrets)?
   - _Recommendation_: Out of scope for now, but structure should allow future integration
