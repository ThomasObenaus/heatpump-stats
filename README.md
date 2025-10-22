# Heatpump Stats

- [Heatpump Stats](#heatpump-stats)
  - [Features](#features)
  - [Installation](#installation)
  - [Development](#development)
  - [Usage](#usage)
    - [Command Line Interface](#command-line-interface)
      - [Fetch current data](#fetch-current-data)
      - [Generate plots](#generate-plots)
    - [Python API](#python-api)
  - [Data Storage](#data-storage)
  - [License](#license)

A Python utility for collecting and analyzing data from Viessmann heat pumps using the Viessmann API.

## Features

- Fetch current heat pump data from the Viessmann API
- Store data in CSV format for easy analysis
- Create plots of temperature trends and heat pump activity

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/heatpump-stats.git
   cd heatpump-stats
   ```

2. Install the package and dependencies:

   ```bash
   # Install the package with development dependencies
   pip install -e ".[dev]"

   # Or install only runtime dependencies
   pip install -e .
   ```

3. Configure your environment:

   ```bash
   cp .env.example .env
   # Edit .env with your Viessmann credentials
   ```

## Development

This project uses modern Python packaging with `pyproject.toml` and the following development tools:

- **Ruff**: For linting and formatting code

  ```bash
  # Run linting
  ruff check .

  # Apply automatic fixes
  ruff check --fix .

  # Format code
  ruff format .
  ```

## Usage

After installing the package and configuring your `.env` file (see Installation section), you can run the project using the following command-line interface (CLI) commands:

### Command Line Interface

The package provides a command line interface with several commands:

#### Fetch current data

Fetch the current status and data from your heat pump:

```bash
heatpump-stats fetch
```

Add the `--save` flag to store the data in the data store:

```bash
heatpump-stats fetch --save
```

#### Generate plots

Create visualizations of heat pump data:

```bash
heatpump-stats plot
```

Save the plot to a file:

```bash
heatpump-stats plot --output temperatures.png
```

### Python API

You can also use the library in your own Python scripts:

```python
from heatpump_stats.api import ViessmannClient
from heatpump_stats.models import HeatPumpDataStore

# Initialize client and authenticate
client = ViessmannClient()
client.authenticate()

# Get the heat pump device
heat_pump = client.get_heat_pump()

# Fetch current data
data = client.collect_heat_pump_data()
print(data)

# Store data point
data_store = HeatPumpDataStore()
data_store.save_data_point(data)

# Load and analyze historical data
df = data_store.load_data(days=7)
print(f"Average temperature: {df['outside_temperature'].mean()}°C")
```

## Data Storage

By default, data is stored in `~/heatpump_data/` in the following files:

- `heatpump_data.csv`: Main data store with all readings
- `latest.json`: Latest data point
- `daily/`: Directory containing snapshots for each day

You can customize the data directory by setting the `DATA_DIR` environment variable in your `.env` file.

## License

See the [LICENSE](LICENSE) file for details.
