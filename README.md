# Heatpump Stats

A Python utility for collecting and analyzing data from Viessmann heat pumps using the Viessmann API.

## Features

- Fetch current heat pump data from the Viessmann API
- Monitor heat pump data at regular intervals
- Store data in CSV format for easy analysis
- Generate statistics from collected data
- Create plots of temperature trends and heat pump activity

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/heatpump-stats.git
   cd heatpump-stats
   ```

2. Install the package and dependencies:
   ```bash
   pip install -e .
   ```
   
   Or without installation:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your Viessmann credentials
   ```

## Usage

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

#### Monitor data over time

Continuously monitor and save heat pump data:

```bash
heatpump-stats monitor
```

Customize the interval and duration:

```bash
heatpump-stats monitor --interval 5 --duration 48
```

This will collect data every 5 minutes for 48 hours.

#### View statistics

Show statistics from collected data:

```bash
heatpump-stats stats
```

View stats for a specific number of days:

```bash
heatpump-stats stats --days 30
```

View stats for a specific date:

```bash
heatpump-stats stats --date 2025-04-10
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