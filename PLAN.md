# Heatpump Monitoring System Plan

## 1. Goal

Build a software solution to monitor the performance of a Viessmann heatpump system over time.
The system will combine data from:

- **Viessmann API**: Temperature sensors, supply power, status.
- **Shelly Pro3EM**: Real-time power consumption (since it's not available via the Viessmann API).

The solution will be containerized and run on a home server, providing a web dashboard for visualization.

## 2. Architecture & Tech Stack

### Database: **InfluxDB v2**

- **Why**: Industry standard for IoT time-series data. Handles high-frequency writes (from Shelly) efficiently and integrates well with Python.
- **Deployment**: Docker container.

### Backend: **Python + FastAPI**

- **Why**: Modern, high-performance, and easy to build REST APIs. Python is already used for the data collection logic.
- **Role**:
  - Expose data from InfluxDB to the frontend.
  - Manage the data collection service (background tasks).

### Frontend: **React**

- **Why**: Modern component-based framework with a rich ecosystem for charting (e.g., Recharts, Victory).
- **Role**: Visualize time-series data, status, and efficiency metrics.

### Infrastructure: **Docker**

- **Why**: Easy deployment and isolation.
- **Components**:
  - `influxdb`: Time-series database.
  - `collector`: Python service fetching data.
  - `backend`: FastAPI service (can be combined with collector or separate).
  - `frontend`: Nginx serving the React app.

## 3. Implementation Steps

### Phase 1: Infrastructure & Data Collection

1. **Docker Setup**: Create `docker-compose.yml` to spin up InfluxDB.
2. **Shelly Integration**: Implement a Python module to fetch power data from the Shelly Pro3EM (using local RPC API `http://<ip>/rpc/EM.GetStatus`).
3. **Collector Service**:
   - Create a main loop in Python.
   - **Viessmann**: Poll every ~5-10 minutes (to respect ~1450 calls/day rate limit).
   - **Shelly**: Poll every ~10-30 seconds for high resolution.
   - **Storage**: Write batched data points to InfluxDB.

### Phase 2: Backend API

1. **FastAPI Setup**: Initialize a project structure.
2. **API Endpoints**:
   - `GET /api/status`: Current system status (latest readings).
   - `GET /api/history`: Historical data for charts (accepting time ranges).
3. **InfluxDB Querying**: Implement Flux queries to retrieve aggregated data for the API.

### Phase 3: Frontend Dashboard

1. **Scaffold React App**: Use Vite for a fast setup.
2. **Dashboard Layout**:
   - **Current Status Cards**: Current Power (W), Outside Temp (°C), Supply Temp (°C).
   - **Charts**: Power consumption over time, Temperature curves.
3. **Integration**: Connect frontend to FastAPI endpoints.

## 4. Key Considerations

- **Rate Limiting**: Strict enforcement of Viessmann API limits is crucial to avoid bans.
- **Data Correlation**: Timestamps need to be aligned. InfluxDB handles this well, but we might need to interpolate data if we want to calculate COP (Coefficient of Performance) in real-time (combining slow Viessmann data with fast Shelly data).
- **Local Access**: Shelly should be accessed via local IP to avoid cloud dependency.
